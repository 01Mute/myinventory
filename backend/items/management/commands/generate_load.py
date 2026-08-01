"""Fill the database with benchmark-scale data.

Companion to seed_demo, which builds the 17-row fixture used to click through
the UI. This command builds the several-million-row dataset used to measure
query plans. The two are kept apart on purpose: the demo has to stay small and
readable, and the benchmark set has to stay large and disposable.
"""

import time
from dataclasses import replace

from django.contrib.auth import get_user_model
from django.core.management.base import BaseCommand, CommandError
from django.core.management.color import no_style
from django.db import connection, transaction

from benchmarks.loadgen import (
    CATEGORY_COLUMNS,
    FLOOR_PLAN_COLUMNS,
    HISTORY_COLUMNS,
    HOME_COLUMNS,
    ID_BASE,
    ITEM_COLUMNS,
    ITEM_TAG_COLUMNS,
    NODE_COLUMNS,
    TAG_COLUMNS,
    USER_COLUMNS,
    USERNAME_PREFIX,
    Generator,
    Shape,
    bulk_rows,
    copy_rows,
)
from homes.models import FloorPlan, Home
from items.models import Category, Item, ItemLocationHistory, ItemTag, Tag
from locations.models import LocationNode

User = get_user_model()

# Ordered from least to most dependent, so a load runs top-down and a delete
# runs bottom-up.
TABLES = (
    ("accounts_user", USER_COLUMNS, "users", User),
    ("homes_home", HOME_COLUMNS, "homes", Home),
    ("homes_floorplan", FLOOR_PLAN_COLUMNS, "floor_plans", FloorPlan),
    ("locations_locationnode", NODE_COLUMNS, "location_nodes", LocationNode),
    ("items_category", CATEGORY_COLUMNS, "categories", Category),
    ("items_tag", TAG_COLUMNS, "tags", Tag),
    ("items_item", ITEM_COLUMNS, "items", Item),
    ("items_itemtag", ITEM_TAG_COLUMNS, "item_tags", ItemTag),
    ("items_itemlocationhistory", HISTORY_COLUMNS, "histories", ItemLocationHistory),
)

# Deleting by owner rather than by id range keeps the command correct even if
# somebody has since inserted rows above ID_BASE through the UI.
DELETE_STATEMENTS = (
    """
    DELETE FROM items_itemlocationhistory
     WHERE item_id IN (SELECT id FROM items_item WHERE owner_id = ANY(%(ids)s))
    """,
    """
    DELETE FROM items_itemtag
     WHERE item_id IN (SELECT id FROM items_item WHERE owner_id = ANY(%(ids)s))
    """,
    "DELETE FROM items_item WHERE owner_id = ANY(%(ids)s)",
    """
    DELETE FROM locations_locationnode
     WHERE home_id IN (SELECT id FROM homes_home WHERE owner_id = ANY(%(ids)s))
    """,
    """
    DELETE FROM homes_floorplan
     WHERE home_id IN (SELECT id FROM homes_home WHERE owner_id = ANY(%(ids)s))
    """,
    "DELETE FROM homes_home WHERE owner_id = ANY(%(ids)s)",
    "DELETE FROM items_category WHERE owner_id = ANY(%(ids)s)",
    "DELETE FROM items_tag WHERE owner_id = ANY(%(ids)s)",
    "DELETE FROM accounts_user WHERE id = ANY(%(ids)s)",
)


class Command(BaseCommand):
    help = "성능 측정을 위한 대량 데이터를 생성합니다."

    def add_arguments(self, parser):
        parser.add_argument(
            "--scale",
            type=float,
            default=1.0,
            help="사용자 수와 집당 아이템 수에 곱할 배수입니다. 예: --scale=0.01",
        )
        parser.add_argument("--users", type=int, help="사용자 수를 직접 지정합니다.")
        parser.add_argument(
            "--items-per-home",
            type=int,
            help="집당 아이템 수를 직접 지정합니다.",
        )
        parser.add_argument(
            "--history-per-item",
            type=int,
            help="아이템당 이동이력 수를 직접 지정합니다.",
        )
        parser.add_argument(
            "--loader",
            choices=("copy", "bulk"),
            default="copy",
            help="적재 방식입니다. copy는 COPY, bulk는 ORM bulk_create를 씁니다.",
        )
        parser.add_argument(
            "--constraints",
            choices=("deferred", "immediate"),
            default="deferred",
            help=(
                "외래키 검사 시점입니다. deferred는 Django 기본값 그대로 COMMIT까지 "
                "미루고, immediate는 적재 중에 검사합니다."
            ),
        )
        parser.add_argument("--seed", type=int, default=20260731)
        parser.add_argument(
            "--no-vacuum",
            action="store_true",
            help=(
                "적재 후 VACUUM ANALYZE를 건너뜁니다. 측정 목적이라면 권장하지 "
                "않습니다. 이유는 _vacuum_analyze()의 주석을 참고하세요."
            ),
        )
        parser.add_argument(
            "--force",
            action="store_true",
            help="생성 범위의 기본키를 쓰는 다른 데이터가 있어도 진행합니다.",
        )

    def handle(self, *args, **options):
        if connection.vendor != "postgresql":
            raise CommandError(
                "이 명령은 PostgreSQL 전용입니다. COPY와 시퀀스 조작에 의존합니다."
            )

        shape = self._build_shape(options)
        generator = Generator(shape, seed=options["seed"])
        loader = options["loader"]

        self.stdout.write("생성할 규모:")
        for label, count in shape.summary():
            self.stdout.write(f"  {label}: {count:,}건")
        self.stdout.write(f"  적재 방식: {loader}")

        removed = self._delete_existing()
        if removed:
            self.stdout.write(f"기존 부하 데이터 {removed:,}건을 지웠습니다.")
        self._check_id_range(force=options["force"])

        timings = []
        total_started = time.perf_counter()

        # One transaction for the whole load. A partially built dataset is worse
        # than none: foreign keys would dangle and every later measurement would
        # be taken against a shape nobody can reproduce.
        with transaction.atomic():
            self._set_constraint_timing(options["constraints"])

            for table, columns, stream, model in TABLES:
                rows = getattr(generator, stream)()
                started = time.perf_counter()
                if loader == "copy":
                    written = copy_rows(table, columns, rows)
                else:
                    written = bulk_rows(model, rows)
                elapsed = time.perf_counter() - started
                timings.append((table, written, elapsed))
                self.stdout.write(f"  {table}: {written:,}건 / {elapsed:.2f}초")

            self._reset_sequences()
            body_elapsed = time.perf_counter() - total_started

        total_elapsed = time.perf_counter() - total_started
        # Timed separately because it is not a rounding error. Django declares
        # every foreign key DEFERRABLE INITIALLY DEFERRED, so with the default
        # timing none of the referential checks run during COPY - they all queue
        # up and fire when the transaction commits.
        commit_elapsed = total_elapsed - body_elapsed
        self.stdout.write(
            f"  COMMIT: {commit_elapsed:.2f}초 (외래키 검사 시점: {options['constraints']})"
        )

        if not options["no_vacuum"]:
            started = time.perf_counter()
            self._vacuum_analyze()
            self.stdout.write(
                f"VACUUM ANALYZE 완료 / {time.perf_counter() - started:.2f}초"
            )

        rows_written = sum(written for _, written, _ in timings)
        self.stdout.write(
            self.style.SUCCESS(
                f"완료: {rows_written:,}건 / {total_elapsed:.2f}초 "
                f"({rows_written / total_elapsed:,.0f} rows/s)"
            )
        )
        self.stdout.write(f"  로그인: {USERNAME_PREFIX}0 / loadtest1234")

    def _build_shape(self, options):
        shape = Shape().scaled(options["scale"])
        overrides = {}
        if options["users"]:
            overrides["users"] = options["users"]
        if options["items_per_home"]:
            overrides["items_per_home"] = options["items_per_home"]
        if options["history_per_item"]:
            overrides["history_per_item"] = options["history_per_item"]
        if overrides:
            shape = replace(shape, **overrides)

        if shape.tags_per_item > shape.tags_per_user:
            raise CommandError(
                "아이템당 태그 수가 사용자당 태그 수보다 많을 수 없습니다."
            )
        return shape

    def _delete_existing(self):
        """Remove a previous run so the command is repeatable.

        Rows go out through explicit DELETEs in dependency order rather than
        through the ORM's cascade, which would first pull every primary key into
        Python - untenable at five million history rows.

        Worth noting for later: this DELETE is the slow, WAL-heavy way to drop a
        large time-series table, and the dead tuples it leaves behind are
        autovacuum's problem afterwards. Range partitioning turns the same job
        into a DROP TABLE.
        """
        ids = list(
            User.objects.filter(username__startswith=USERNAME_PREFIX).values_list(
                "id", flat=True
            )
        )
        if not ids:
            return 0

        removed = 0
        with transaction.atomic(), connection.cursor() as cursor:
            for statement in DELETE_STATEMENTS:
                cursor.execute(statement, {"ids": ids})
                removed += cursor.rowcount
        return removed

    def _check_id_range(self, force):
        """Refuse to write over primary keys that belong to somebody else.

        Generated rows sit at deterministic ids starting at ID_BASE. If any
        table already holds a row up there that the delete above did not claim,
        the load would collide.
        """
        occupied = []
        with connection.cursor() as cursor:
            for table, _, _, _ in TABLES:
                cursor.execute(
                    f"SELECT count(*) FROM {table} WHERE id >= %s", [ID_BASE]
                )
                count = cursor.fetchone()[0]
                if count:
                    occupied.append(f"{table} {count}건")

        if not occupied:
            return
        if force:
            self.stdout.write(
                self.style.WARNING(f"기존 데이터와 기본키가 겹칩니다: {', '.join(occupied)}")
            )
            return

        raise CommandError(
            "생성 범위의 기본키를 이미 쓰는 데이터가 있습니다: "
            + ", ".join(occupied)
            + f"\n(id >= {ID_BASE}) 진행하려면 --force를 붙이세요."
        )

    def _set_constraint_timing(self, timing):
        """Choose when referential integrity is verified.

        Django creates every foreign key as DEFERRABLE INITIALLY DEFERRED, which
        lets fixtures load rows in any order. The cost is that no check runs
        during the load: each one is queued as a deferred trigger and they all
        fire at COMMIT, in one burst, after the last row is written.

        Switching to IMMEDIATE moves the checks to the end of each COPY
        statement instead. That is only safe because TABLES is ordered
        parent-before-child, so every reference already exists by the time its
        statement finishes.
        """
        if timing != "immediate":
            return
        with connection.cursor() as cursor:
            cursor.execute("SET CONSTRAINTS ALL IMMEDIATE")

    def _reset_sequences(self):
        """Advance id sequences past the rows just written.

        COPY and bulk_create both supply explicit primary keys, which leaves the
        sequence untouched. Without this the next row created through the UI
        collides with a generated one.
        """
        models = [model for _, _, _, model in TABLES]
        statements = connection.ops.sequence_reset_sql(no_style(), models)
        with connection.cursor() as cursor:
            for statement in statements:
                cursor.execute(statement)

    def _vacuum_analyze(self):
        """Refresh planner statistics and build the visibility map.

        ANALYZE alone is not enough, and the difference is not subtle. A freshly
        loaded table has no statistics, so the planner falls back on hardcoded
        guesses and picks plans it would never pick in production - that part
        ANALYZE fixes.

        What it does not fix is the visibility map, which only VACUUM writes.
        Without it an index-only scan cannot prove a row is visible to every
        transaction, so it drops to the heap for each row it returns and stops
        being index-only in anything but name. Measured on this dataset, running
        the benchmark after ANALYZE but before VACUUM reported 229,729 buffer
        hits for the item search; after VACUUM the same query reported 18,713.
        The twelvefold difference was an artefact of the load, not a property of
        the query.
        """
        with connection.cursor() as cursor:
            for table, _, _, _ in TABLES:
                cursor.execute(f"VACUUM (ANALYZE) {table}")
