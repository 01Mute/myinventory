"""Generate a realistic, high-volume dataset for database benchmarking.

The shipped demo fixture holds 17 items. That is far too small to expose the
cost of any query plan: Postgres answers everything from a single page, so every
measurement reads as "fast" and no index choice can be justified with evidence.
This module fills the same schema with a few million rows so that index
selection, join order and (later) partition pruning become measurable.

Two loaders are implemented on purpose. COPY is what you would reach for in
production; bulk_create is what an application developer reaches for first.
Running both at the same scale and comparing the wall clock is the first
concrete lesson this dataset teaches.
"""

from __future__ import annotations

import json
import random
from dataclasses import dataclass, replace
from datetime import timedelta

from django.contrib.auth.hashers import make_password
from django.db import connection
from django.utils import timezone

# Generated rows start well above anything a human would create by hand, so a
# database that already holds a demo account stays untouched and the two sets
# remain easy to tell apart when reading raw query output.
ID_BASE = 1_000_000

USERNAME_PREFIX = "load_user_"
LOAD_PASSWORD = "loadtest1234"


@dataclass(frozen=True)
class Shape:
    """How many rows of each kind to generate.

    The tree fan-out values are structural: they decide how deep and how wide
    every home's location tree is, which is what the recursive queries and the
    path/full_code prefix searches actually exercise. They are not scaled by
    --scale, because changing the shape of the tree between runs would make two
    benchmark results incomparable.
    """

    users: int = 100
    floor_plans_per_home: int = 2
    rooms_per_floor_plan: int = 3
    furniture_per_room: int = 4
    compartments_per_furniture: int = 4
    boxes_per_compartment: int = 4
    categories_per_user: int = 5
    tags_per_user: int = 20
    items_per_home: int = 5_000
    tags_per_item: int = 3
    history_per_item: int = 10
    months_of_history: int = 24

    # Every home owns exactly one home record, so owner filters have the same
    # selectivity for every tenant. Uneven tenants would make it impossible to
    # tell a bad plan apart from a user who simply owns more rows.
    @property
    def homes(self) -> int:
        return self.users

    @property
    def floor_plans(self) -> int:
        return self.homes * self.floor_plans_per_home

    @property
    def rooms_per_plan(self) -> int:
        return self.rooms_per_floor_plan

    @property
    def furniture_per_plan(self) -> int:
        return self.rooms_per_plan * self.furniture_per_room

    @property
    def compartments_per_plan(self) -> int:
        return self.furniture_per_plan * self.compartments_per_furniture

    @property
    def boxes_per_plan(self) -> int:
        return self.compartments_per_plan * self.boxes_per_compartment

    @property
    def nodes_per_plan(self) -> int:
        return (
            self.rooms_per_plan
            + self.furniture_per_plan
            + self.compartments_per_plan
            + self.boxes_per_plan
        )

    @property
    def nodes_per_home(self) -> int:
        return self.nodes_per_plan * self.floor_plans_per_home

    @property
    def location_nodes(self) -> int:
        return self.nodes_per_home * self.homes

    @property
    def categories(self) -> int:
        return self.users * self.categories_per_user

    @property
    def tags(self) -> int:
        return self.users * self.tags_per_user

    @property
    def items(self) -> int:
        return self.homes * self.items_per_home

    @property
    def item_tags(self) -> int:
        return self.items * self.tags_per_item

    @property
    def histories(self) -> int:
        return self.items * self.history_per_item

    def scaled(self, factor: float) -> "Shape":
        """Shrink or grow the row counts without changing the tree shape."""
        return replace(
            self,
            users=max(1, round(self.users * factor)),
            items_per_home=max(1, round(self.items_per_home * factor)),
        )

    def summary(self) -> list[tuple[str, int]]:
        return [
            ("사용자", self.users),
            ("집", self.homes),
            ("플로어플랜", self.floor_plans),
            ("위치노드", self.location_nodes),
            ("카테고리", self.categories),
            ("태그", self.tags),
            ("아이템", self.items),
            ("아이템-태그", self.item_tags),
            ("이동이력", self.histories),
        ]


# ---------------------------------------------------------------------------
# Vocabulary
#
# Item names are built from a fixed noun list so that search selectivity is
# predictable: with 20 nouns spread evenly, ?q=<noun> matches about 5% of the
# table. That is the interesting range for index work - large enough that a
# sequential scan hurts, small enough that an index could win.
# ---------------------------------------------------------------------------

ITEM_NOUNS = [
    "드라이버", "케이블", "충전기", "건전지", "가위",
    "테이프", "볼펜", "노트", "상비약", "마스크",
    "전구", "나사", "장갑", "우산", "여분열쇠",
    "리모컨", "이어폰", "USB메모리", "보조배터리", "랜선",
]
ITEM_ADJECTIVES = [
    "검정", "흰색", "작은", "큰", "여분의",
    "새", "오래된", "파란", "빨간", "투명",
]
ROOM_NAMES = ["거실", "안방", "주방", "서재", "아이방", "베란다", "현관", "다용도실"]
FURNITURE_NAMES = ["책상", "옷장", "서랍장", "책장", "수납장", "선반", "협탁", "캐비닛"]
CATEGORY_NAMES = ["공구", "문구", "전자기기", "생활용품", "의약품", "주방용품", "의류", "취미"]
TAG_NAMES = [
    "자주쓰는", "비상용", "계절용", "귀중품", "소모품",
    "충전필요", "빌려준것", "선물", "보증서있음", "폐기예정",
    "여행용", "사무용", "청소용", "요리용", "운동용",
    "아이용", "반려동물", "차량용", "캠핑", "수리필요",
]
STATUSES = ["ACTIVE", "ACTIVE", "ACTIVE", "ACTIVE", "MISSING", "ARCHIVED"]


# ---------------------------------------------------------------------------
# Column lists
#
# The schema carries no database-level defaults (Django does not emit them), so
# every NOT NULL column has to be supplied explicitly on the COPY path.
# ---------------------------------------------------------------------------

USER_COLUMNS = (
    "id", "password", "last_login", "is_superuser", "username", "first_name",
    "last_name", "email", "is_staff", "is_active", "date_joined", "nickname",
    "created_at", "updated_at",
)
HOME_COLUMNS = ("id", "name", "address_optional", "created_at", "updated_at", "owner_id")
FLOOR_PLAN_COLUMNS = (
    "id", "name", "width", "height", "unit", "background_image",
    "created_at", "updated_at", "home_id",
)
NODE_COLUMNS = (
    "id", "node_type", "code", "name", "full_code", "path", "level",
    "geometry_json", "metadata_json", "sort_order", "created_at", "updated_at",
    "floor_plan_id", "home_id", "parent_id",
)
CATEGORY_COLUMNS = ("id", "name", "created_at", "updated_at", "owner_id")
TAG_COLUMNS = ("id", "name", "created_at", "owner_id")
ITEM_COLUMNS = (
    "id", "name", "description", "quantity", "photo", "purchase_price",
    "purchase_date", "status", "last_checked_at", "created_at", "updated_at",
    "category_id", "current_location_node_id", "owner_id",
)
ITEM_TAG_COLUMNS = ("id", "item_id", "tag_id")
HISTORY_COLUMNS = (
    "id", "memo", "moved_at", "created_at", "created_by_id",
    "from_location_node_id", "item_id", "to_location_node_id",
)

JSON_COLUMNS = frozenset({"geometry_json", "metadata_json"})


class Generator:
    """Streams row tuples for every table, in foreign-key dependency order.

    Nothing is materialised as a list: at the target scale the history table
    alone is five million rows, and holding that in memory would dwarf the
    database it is being written into. Every method here is a generator, and the
    loaders consume them one row at a time.

    Primary keys are assigned arithmetically rather than read back from the
    database. Row N of a table always lands on a known id, so foreign keys can
    be computed instead of looked up - which is what makes a single streaming
    pass possible.
    """

    def __init__(self, shape: Shape, seed: int = 20260731):
        self.shape = shape
        self.seed = seed
        self.now = timezone.now()
        # Hashing is deliberately slow, and every generated user shares the same
        # password. Paying for one PBKDF2 run instead of `users` of them keeps
        # account creation off the critical path.
        self.password_hash = make_password(LOAD_PASSWORD)

    def _rng(self, stream: int) -> random.Random:
        """A generator seeded per stream, so runs are byte-for-byte repeatable.

        Benchmarks compare two runs against each other. If the data differed
        between them, a change in timing could not be attributed to the change
        under test.
        """
        return random.Random(self.seed + stream)

    # -- id arithmetic ----------------------------------------------------

    def user_id(self, user_index: int) -> int:
        return ID_BASE + user_index

    def home_id(self, home_index: int) -> int:
        return ID_BASE + home_index

    def floor_plan_id(self, home_index: int, plan_index: int) -> int:
        return ID_BASE + home_index * self.shape.floor_plans_per_home + plan_index

    def node_id(self, home_index: int, local_index: int) -> int:
        return ID_BASE + home_index * self.shape.nodes_per_home + local_index

    def category_id(self, user_index: int, offset: int) -> int:
        return ID_BASE + user_index * self.shape.categories_per_user + offset

    def tag_id(self, user_index: int, offset: int) -> int:
        return ID_BASE + user_index * self.shape.tags_per_user + offset

    def item_id(self, item_index: int) -> int:
        return ID_BASE + item_index

    # -- local index layout inside one home's tree ------------------------
    #
    # Nodes are emitted plan by plan, and level by level within a plan. That
    # gives every tier a contiguous local index range, so "pick a random
    # compartment or box" is arithmetic rather than a lookup.

    def _plan_base(self, plan_index: int) -> int:
        return plan_index * self.shape.nodes_per_plan

    def _rooms_start(self, plan_index: int) -> int:
        return self._plan_base(plan_index)

    def _furniture_start(self, plan_index: int) -> int:
        return self._rooms_start(plan_index) + self.shape.rooms_per_plan

    def _compartments_start(self, plan_index: int) -> int:
        return self._furniture_start(plan_index) + self.shape.furniture_per_plan

    def _boxes_start(self, plan_index: int) -> int:
        return self._compartments_start(plan_index) + self.shape.compartments_per_plan

    # -- row streams ------------------------------------------------------

    def users(self):
        for i in range(self.shape.users):
            yield {
                "id": self.user_id(i),
                "password": self.password_hash,
                "last_login": None,
                "is_superuser": False,
                "username": f"{USERNAME_PREFIX}{i}",
                "first_name": "",
                "last_name": "",
                "email": f"{USERNAME_PREFIX}{i}@example.com",
                "is_staff": False,
                "is_active": True,
                "date_joined": self.now,
                "nickname": f"부하테스트{i}",
                "created_at": self.now,
                "updated_at": self.now,
            }

    def homes(self):
        for i in range(self.shape.homes):
            yield {
                "id": self.home_id(i),
                "name": f"부하테스트 집 {i}",
                "address_optional": f"서울시 테스트구 테스트로 {i}",
                "created_at": self.now,
                "updated_at": self.now,
                "owner_id": self.user_id(i),
            }

    def floor_plans(self):
        for home_index in range(self.shape.homes):
            for plan_index in range(self.shape.floor_plans_per_home):
                yield {
                    "id": self.floor_plan_id(home_index, plan_index),
                    "name": f"{plan_index + 1}층",
                    "width": 1000,
                    "height": 700,
                    "unit": "PX",
                    "background_image": None,
                    "created_at": self.now,
                    "updated_at": self.now,
                    "home_id": self.home_id(home_index),
                }

    def location_nodes(self):
        """Emit the location tree with full_code/path/level precomputed.

        LocationNode.save() derives these three fields from the parent chain and
        then resyncs descendants, but neither COPY nor bulk_create calls save().
        The values are therefore computed here, top-down, exactly the way
        _set_hierarchy_fields() would: full_code joins ancestor codes with "-",
        path joins ancestor names with " / ".

        Sibling codes must stay distinct or the four partial unique indexes on
        the table will reject the load. Room codes are numbered across the whole
        home rather than per plan, so full_code stays readable.
        """
        shape = self.shape
        rng = self._rng(1)
        empty_json = {}

        for home_index in range(shape.homes):
            home_id = self.home_id(home_index)

            for plan_index in range(shape.floor_plans_per_home):
                plan_id = self.floor_plan_id(home_index, plan_index)
                rooms_start = self._rooms_start(plan_index)
                furniture_start = self._furniture_start(plan_index)
                compartments_start = self._compartments_start(plan_index)
                boxes_start = self._boxes_start(plan_index)

                # Level 0: rooms.
                for r in range(shape.rooms_per_plan):
                    room_number = plan_index * shape.rooms_per_plan + r + 1
                    code = f"R{room_number}"
                    name = ROOM_NAMES[room_number % len(ROOM_NAMES)]
                    yield {
                        "id": self.node_id(home_index, rooms_start + r),
                        "node_type": "ROOM",
                        "code": code,
                        "name": name,
                        "full_code": code,
                        "path": name,
                        "level": 0,
                        "geometry_json": {
                            "x": rng.randint(0, 800),
                            "y": rng.randint(0, 500),
                            "w": 180,
                            "h": 140,
                        },
                        "metadata_json": empty_json,
                        "sort_order": r,
                        "created_at": self.now,
                        "updated_at": self.now,
                        "floor_plan_id": plan_id,
                        "home_id": home_id,
                        "parent_id": None,
                    }

                # Level 1: furniture inside each room.
                for r in range(shape.rooms_per_plan):
                    room_number = plan_index * shape.rooms_per_plan + r + 1
                    room_code = f"R{room_number}"
                    room_name = ROOM_NAMES[room_number % len(ROOM_NAMES)]
                    for f in range(shape.furniture_per_room):
                        local = furniture_start + r * shape.furniture_per_room + f
                        code = f"F{f + 1}"
                        name = FURNITURE_NAMES[(room_number + f) % len(FURNITURE_NAMES)]
                        yield {
                            "id": self.node_id(home_index, local),
                            "node_type": "FURNITURE",
                            "code": code,
                            "name": name,
                            "full_code": f"{room_code}-{code}",
                            "path": f"{room_name} / {name}",
                            "level": 1,
                            "geometry_json": empty_json,
                            "metadata_json": empty_json,
                            "sort_order": f,
                            "created_at": self.now,
                            "updated_at": self.now,
                            "floor_plan_id": plan_id,
                            "home_id": home_id,
                            "parent_id": self.node_id(home_index, rooms_start + r),
                        }

                # Level 2: compartments inside each piece of furniture.
                for r in range(shape.rooms_per_plan):
                    room_number = plan_index * shape.rooms_per_plan + r + 1
                    room_code = f"R{room_number}"
                    room_name = ROOM_NAMES[room_number % len(ROOM_NAMES)]
                    for f in range(shape.furniture_per_room):
                        furniture_local = furniture_start + r * shape.furniture_per_room + f
                        furniture_name = FURNITURE_NAMES[
                            (room_number + f) % len(FURNITURE_NAMES)
                        ]
                        for c in range(shape.compartments_per_furniture):
                            local = (
                                compartments_start
                                + (r * shape.furniture_per_room + f)
                                * shape.compartments_per_furniture
                                + c
                            )
                            code = f"C{c + 1}"
                            name = f"{c + 1}번 칸"
                            yield {
                                "id": self.node_id(home_index, local),
                                "node_type": "COMPARTMENT",
                                "code": code,
                                "name": name,
                                "full_code": f"{room_code}-F{f + 1}-{code}",
                                "path": f"{room_name} / {furniture_name} / {name}",
                                "level": 2,
                                "geometry_json": empty_json,
                                "metadata_json": empty_json,
                                "sort_order": c,
                                "created_at": self.now,
                                "updated_at": self.now,
                                "floor_plan_id": plan_id,
                                "home_id": home_id,
                                "parent_id": self.node_id(home_index, furniture_local),
                            }

                # Level 3: boxes inside each compartment.
                for r in range(shape.rooms_per_plan):
                    room_number = plan_index * shape.rooms_per_plan + r + 1
                    room_code = f"R{room_number}"
                    room_name = ROOM_NAMES[room_number % len(ROOM_NAMES)]
                    for f in range(shape.furniture_per_room):
                        furniture_name = FURNITURE_NAMES[
                            (room_number + f) % len(FURNITURE_NAMES)
                        ]
                        for c in range(shape.compartments_per_furniture):
                            compartment_local = (
                                compartments_start
                                + (r * shape.furniture_per_room + f)
                                * shape.compartments_per_furniture
                                + c
                            )
                            for b in range(shape.boxes_per_compartment):
                                local = (
                                    boxes_start
                                    + (
                                        (r * shape.furniture_per_room + f)
                                        * shape.compartments_per_furniture
                                        + c
                                    )
                                    * shape.boxes_per_compartment
                                    + b
                                )
                                code = f"B{b + 1}"
                                name = f"상자{b + 1}"
                                yield {
                                    "id": self.node_id(home_index, local),
                                    "node_type": "BOX",
                                    "code": code,
                                    "name": name,
                                    "full_code": (
                                        f"{room_code}-F{f + 1}-C{c + 1}-{code}"
                                    ),
                                    "path": (
                                        f"{room_name} / {furniture_name} / "
                                        f"{c + 1}번 칸 / {name}"
                                    ),
                                    "level": 3,
                                    "geometry_json": empty_json,
                                    "metadata_json": empty_json,
                                    "sort_order": b,
                                    "created_at": self.now,
                                    "updated_at": self.now,
                                    "floor_plan_id": plan_id,
                                    "home_id": home_id,
                                    "parent_id": self.node_id(
                                        home_index, compartment_local
                                    ),
                                }

    def categories(self):
        for user_index in range(self.shape.users):
            for offset in range(self.shape.categories_per_user):
                yield {
                    "id": self.category_id(user_index, offset),
                    "name": CATEGORY_NAMES[offset % len(CATEGORY_NAMES)],
                    "created_at": self.now,
                    "updated_at": self.now,
                    "owner_id": self.user_id(user_index),
                }

    def tags(self):
        for user_index in range(self.shape.users):
            for offset in range(self.shape.tags_per_user):
                yield {
                    "id": self.tag_id(user_index, offset),
                    "name": TAG_NAMES[offset % len(TAG_NAMES)],
                    "created_at": self.now,
                    "owner_id": self.user_id(user_index),
                }

    def items(self):
        shape = self.shape
        rng = self._rng(2)
        item_index = 0

        for home_index in range(shape.homes):
            home_owner = self.user_id(home_index)
            for _ in range(shape.items_per_home):
                noun = ITEM_NOUNS[item_index % len(ITEM_NOUNS)]
                adjective = rng.choice(ITEM_ADJECTIVES)
                # Items live in compartments and boxes, never in a bare room:
                # that matches how the product is actually used and keeps the
                # deep end of the tree - the expensive end - well populated.
                plan_index = rng.randrange(shape.floor_plans_per_home)
                local = rng.randrange(
                    self._compartments_start(plan_index),
                    self._plan_base(plan_index) + shape.nodes_per_plan,
                )
                yield {
                    "id": self.item_id(item_index),
                    "name": f"{adjective} {noun} {item_index}",
                    "description": f"{noun} 관련 물건입니다. 일련번호 {item_index}.",
                    "quantity": rng.randint(1, 9),
                    "photo": None,
                    "purchase_price": None,
                    "purchase_date": None,
                    "status": rng.choice(STATUSES),
                    "last_checked_at": None,
                    "created_at": self.now,
                    "updated_at": self.now,
                    "category_id": self.category_id(
                        home_index, rng.randrange(shape.categories_per_user)
                    ),
                    "current_location_node_id": self.node_id(home_index, local),
                    "owner_id": home_owner,
                }
                item_index += 1

    def item_tags(self):
        shape = self.shape
        rng = self._rng(3)
        row_id = ID_BASE
        item_index = 0

        for home_index in range(shape.homes):
            for _ in range(shape.items_per_home):
                # sample() rather than repeated choice(): the (item, tag) pair
                # carries a unique constraint, so a duplicate would abort the
                # whole load.
                for tag_offset in rng.sample(
                    range(shape.tags_per_user), shape.tags_per_item
                ):
                    yield {
                        "id": row_id,
                        "item_id": self.item_id(item_index),
                        "tag_id": self.tag_id(home_index, tag_offset),
                    }
                    row_id += 1
                item_index += 1

    def histories(self):
        shape = self.shape
        rng = self._rng(4)
        row_id = ID_BASE
        item_index = 0
        window = timedelta(days=30 * shape.months_of_history)

        for home_index in range(shape.homes):
            owner = self.user_id(home_index)
            for _ in range(shape.items_per_home):
                for _ in range(shape.history_per_item):
                    plan_index = rng.randrange(shape.floor_plans_per_home)
                    origin = rng.randrange(
                        self._compartments_start(plan_index),
                        self._plan_base(plan_index) + shape.nodes_per_plan,
                    )
                    destination = rng.randrange(
                        self._compartments_start(plan_index),
                        self._plan_base(plan_index) + shape.nodes_per_plan,
                    )
                    yield {
                        "id": row_id,
                        "memo": "",
                        "moved_at": self.now
                        - timedelta(seconds=rng.randrange(int(window.total_seconds()))),
                        "created_at": self.now,
                        "created_by_id": owner,
                        "from_location_node_id": self.node_id(home_index, origin),
                        "item_id": self.item_id(item_index),
                        "to_location_node_id": self.node_id(home_index, destination),
                    }
                    row_id += 1
                item_index += 1


# ---------------------------------------------------------------------------
# Loaders
# ---------------------------------------------------------------------------


def copy_rows(table: str, columns: tuple[str, ...], rows) -> int:
    """Stream rows into `table` with COPY.

    COPY skips the per-statement parse, plan and round-trip that INSERT pays for
    every row, and writes through a single WAL path. It is the reason a
    five-million-row table can be built in under a minute.
    """
    written = 0
    statement = f"COPY {table} ({', '.join(columns)}) FROM STDIN"

    with connection.cursor() as cursor:
        # Django hands back a CursorWrapper; COPY lives on the psycopg cursor
        # underneath it.
        raw_cursor = getattr(cursor, "cursor", cursor)
        with raw_cursor.copy(statement) as copy:
            for row in rows:
                copy.write_row(
                    tuple(
                        json.dumps(row[column]) if column in JSON_COLUMNS else row[column]
                        for column in columns
                    )
                )
                written += 1
    return written


def bulk_rows(model, rows, batch_size: int = 5_000) -> int:
    """Stream rows through the ORM's bulk_create, for comparison against COPY.

    Kept honest on memory: rows arrive as a generator and are batched here
    rather than materialised. Note that fields declared auto_now_add/auto_now
    still run through pre_save on this path, so created_at/updated_at are set by
    Django rather than by the generator - the only value-level difference
    between the two loaders.
    """
    written = 0
    batch = []

    for row in rows:
        batch.append(model(**row))
        if len(batch) >= batch_size:
            model.objects.bulk_create(batch)
            written += len(batch)
            batch = []

    if batch:
        model.objects.bulk_create(batch)
        written += len(batch)
    return written
