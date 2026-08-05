import json
import shutil
from pathlib import Path

from django.conf import settings
from django.contrib.auth import get_user_model
from django.core.management.base import BaseCommand, CommandError
from django.core.management.color import no_style
from django.core.serializers import deserialize
from django.db import connection, transaction

from accounts.demo_data import SEEDED_MODELS, apply_owner, owned_queryset

User = get_user_model()

FIXTURE_PATH = Path(__file__).resolve().parents[2] / "fixtures" / "demo.json"
DEMO_ASSETS_DIR = settings.BASE_DIR / "demo_assets"


class Command(BaseCommand):
    help = "포트폴리오 확인용 테스트 계정과 예시 데이터를 생성합니다."

    def add_arguments(self, parser):
        parser.add_argument("--username", default="test")
        parser.add_argument("--password", default="test1234")
        parser.add_argument("--email", default="test@example.com")
        parser.add_argument(
            "--fixture",
            help=(
                "불러올 데이터 파일입니다. backup_demo가 만든 백업의 data.json을 "
                "지정하면 그 시점으로 복원합니다."
            ),
        )
        parser.add_argument(
            "--force",
            action="store_true",
            help="다른 사용자의 데이터와 기본키가 겹쳐도 진행합니다.",
        )

    def handle(self, *args, **options):
        fixture_path = Path(options["fixture"]) if options["fixture"] else FIXTURE_PATH
        if not fixture_path.exists():
            raise CommandError(f"예시 데이터 파일이 없습니다: {fixture_path}")

        objects = json.loads(fixture_path.read_text(encoding="utf-8"))

        with transaction.atomic():
            user = self._reset_demo_user(options)
            self._check_pk_conflicts(objects, user, force=options["force"])
            self._load(objects, user)
            self._reset_sequences()

        copied = self._copy_assets(fixture_path)

        self.stdout.write(self.style.SUCCESS("예시 데이터를 생성했습니다."))
        self.stdout.write(f"  로그인: {options['username']} / {options['password']}")
        # Scoped to the demo user, not model.objects.count(). A global count
        # reports every row in the table, so on a database that also holds
        # benchmark data the command claimed to have created millions of rows.
        for model in SEEDED_MODELS:
            label = model._meta.verbose_name
            self.stdout.write(f"  {label}: {owned_queryset(model, user).count()}건")
        self.stdout.write(f"  이미지 파일: {copied}개")

    def _reset_demo_user(self, options):
        """Drop the demo account so re-running restores a pristine demo state.

        Deleting the user cascades to every row the fixture owns, which keeps
        the command idempotent without touching anyone else's data.
        """
        deleted, _ = User.objects.filter(username=options["username"]).delete()
        if deleted:
            self.stdout.write(f"기존 {options['username']} 계정과 데이터를 지웠습니다.")

        user = User(username=options["username"], email=options["email"])
        user.set_password(options["password"])
        user.save()
        return user

    def _check_pk_conflicts(self, objects, user, force):
        """Refuse to overwrite rows that belong to somebody else.

        The fixture keeps its original primary keys so the demo reproduces
        exactly, which means a database that already holds unrelated data could
        be clobbered. Detect that instead of silently overwriting.
        """
        conflicts = []
        for model in SEEDED_MODELS:
            label = f"{model._meta.app_label}.{model._meta.model_name}"
            pks = [o["pk"] for o in objects if o["model"] == label]
            if not pks:
                continue
            taken = model.objects.filter(pk__in=pks).count()
            if taken:
                conflicts.append(f"{label} {taken}건")

        if not conflicts:
            return
        if force:
            self.stdout.write(
                self.style.WARNING(f"기존 데이터를 덮어씁니다: {', '.join(conflicts)}")
            )
            return

        raise CommandError(
            "다른 데이터와 기본키가 겹칩니다: "
            + ", ".join(conflicts)
            + "\n비어 있는 데이터베이스에서 실행하거나, 덮어쓰려면 --force를 붙이세요."
        )

    def _load(self, objects, user):
        apply_owner(objects, user.pk)

        # deserialize().save() writes through save_base(), so LocationNode's
        # custom save() does not recompute the stored code/path/level values.
        for wrapper in deserialize("json", json.dumps(objects)):
            wrapper.save()

    def _reset_sequences(self):
        """Advance id sequences past the fixture's explicit primary keys.

        Without this the next item created through the UI collides with a
        seeded row. loaddata does this for us; deserialize() does not.
        """
        statements = connection.ops.sequence_reset_sql(no_style(), list(SEEDED_MODELS))
        with connection.cursor() as cursor:
            for statement in statements:
                cursor.execute(statement)

    def _copy_assets(self, fixture_path):
        """Restore the images the loaded rows point at.

        A backup carries its own media/ beside data.json, and those are the
        files that particular snapshot referenced. The bundled demo_assets are
        the right source only for the bundled fixture; using them to restore a
        backup would put back the wrong photos.
        """
        backup_media = fixture_path.parent / "media"
        if fixture_path != FIXTURE_PATH and backup_media.is_dir():
            return self._copy_tree(backup_media)
        return self._copy_tree(DEMO_ASSETS_DIR)

    def _copy_tree(self, source_dir):
        if not source_dir.exists():
            return 0

        copied = 0
        for source in source_dir.rglob("*"):
            if not source.is_file():
                continue
            target = Path(settings.MEDIA_ROOT) / source.relative_to(source_dir)
            target.parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(source, target)
            copied += 1
        return copied
