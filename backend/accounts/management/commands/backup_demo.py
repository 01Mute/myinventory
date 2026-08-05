"""Take a restorable snapshot of the demo account.

The demo account is the one anybody can log into, which is exactly why it is
the one that gets edited by strangers and is worth keeping copies of. This
writes a dated directory holding the account's rows and the media files those
rows point at, then drops directories older than the retention window.

The output is the same shape seed_demo loads, so restoring is:

    python manage.py seed_demo --fixture backups/demo-20260803-041500/data.json

Backups are written to a bind-mounted host directory. A path inside the
container image would not survive the next rebuild.
"""

import json
import shutil
from datetime import datetime
from pathlib import Path

from django.conf import settings
from django.contrib.auth import get_user_model
from django.core.management.base import BaseCommand, CommandError

from accounts.demo_data import SEEDED_MODELS, dump_objects, media_names, owned_queryset

User = get_user_model()

DIRECTORY_PREFIX = "demo-"
TIMESTAMP_FORMAT = "%Y%m%d-%H%M%S"


class Command(BaseCommand):
    help = "테스트 계정의 데이터와 이미지를 백업합니다."

    def add_arguments(self, parser):
        parser.add_argument("--username", default="test")
        parser.add_argument(
            "--out",
            help="백업을 저장할 디렉터리입니다. 기본값은 BACKUP_ROOT 설정입니다.",
        )
        parser.add_argument(
            "--keep-days",
            type=int,
            default=14,
            help="이 일수보다 오래된 백업을 지웁니다. 0이면 지우지 않습니다.",
        )
        parser.add_argument(
            "--no-media",
            action="store_true",
            help="이미지 파일을 빼고 행 데이터만 백업합니다.",
        )

    def handle(self, *args, **options):
        user = User.objects.filter(username=options["username"]).first()
        if user is None:
            raise CommandError(f"{options['username']} 계정이 없습니다.")

        root = Path(options["out"]) if options["out"] else Path(settings.BACKUP_ROOT)
        stamp = datetime.now().strftime(TIMESTAMP_FORMAT)
        target = root / f"{DIRECTORY_PREFIX}{stamp}"
        if target.exists():
            raise CommandError(f"같은 이름의 백업이 이미 있습니다: {target}")

        # Build into a temporary name and rename at the end, so a backup that
        # dies halfway through never leaves a directory that looks complete.
        staging = root / f".{DIRECTORY_PREFIX}{stamp}.partial"
        if staging.exists():
            shutil.rmtree(staging)
        staging.mkdir(parents=True)

        try:
            rows = self._write_data(staging, user)
            copied = 0 if options["no_media"] else self._copy_media(staging, user)
            staging.rename(target)
        except Exception:
            shutil.rmtree(staging, ignore_errors=True)
            raise

        self.stdout.write(self.style.SUCCESS(f"백업했습니다: {target}"))
        for model in SEEDED_MODELS:
            count = owned_queryset(model, user).count()
            if count:
                self.stdout.write(f"  {model._meta.verbose_name}: {count}건")
        self.stdout.write(f"  전체 행: {rows}건")
        self.stdout.write(f"  이미지 파일: {copied}개")

        removed = self._prune(root, options["keep_days"])
        if removed:
            self.stdout.write(f"  오래된 백업 {removed}개를 지웠습니다.")

    def _write_data(self, staging, user):
        objects = dump_objects(user)
        (staging / "data.json").write_text(
            json.dumps(objects, indent=2, ensure_ascii=False, default=str),
            encoding="utf-8",
        )
        return len(objects)

    def _copy_media(self, staging, user):
        """Copy the files the dumped rows reference.

        Only referenced files, not the whole media directory: /media/ also holds
        uploads belonging to other accounts, and a demo backup has no business
        carrying those.
        """
        media_root = Path(settings.MEDIA_ROOT)
        copied = 0
        for name in media_names(user):
            source = media_root / name
            if not source.is_file():
                self.stdout.write(self.style.WARNING(f"  이미지가 없습니다: {name}"))
                continue
            destination = staging / "media" / name
            destination.parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(source, destination)
            copied += 1
        return copied

    def _prune(self, root, keep_days):
        """Drop backups past the retention window.

        Retention is counted from the timestamp in the directory name rather
        than from the filesystem mtime, which a restore or a file copy would
        otherwise reset and keep alive forever.
        """
        if keep_days <= 0:
            return 0

        cutoff = datetime.now().timestamp() - keep_days * 86400
        removed = 0
        for path in root.glob(f"{DIRECTORY_PREFIX}*"):
            if not path.is_dir():
                continue
            try:
                taken = datetime.strptime(
                    path.name[len(DIRECTORY_PREFIX):], TIMESTAMP_FORMAT
                )
            except ValueError:
                # Not one of ours; leave it alone rather than guess.
                continue
            if taken.timestamp() < cutoff:
                shutil.rmtree(path, ignore_errors=True)
                removed += 1
        return removed
