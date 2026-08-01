"""Measure the queries the application actually runs, and record the evidence.

Results are written to docs/db/results/ as JSON so that a later run can be
compared against this one. A benchmark that only prints to a terminal proves
nothing a week later.
"""

import json
from pathlib import Path

from django.conf import settings
from django.core.management.base import BaseCommand, CommandError
from django.db import connection

from benchmarks import runner
from benchmarks.loadgen import USERNAME_PREFIX
from benchmarks.queries import build_context

# Results live beside the tool that produces them. The dev container only
# bind-mounts backend/, so anything written outside it would vanish with the
# container instead of landing in the repository.
DEFAULT_RESULT_DIR = Path(settings.BASE_DIR) / "benchmarks" / "results"


class Command(BaseCommand):
    help = "주요 쿼리의 실행계획과 소요시간을 측정합니다."

    def add_arguments(self, parser):
        parser.add_argument(
            "--repeat",
            type=int,
            default=5,
            help="쿼리마다 반복할 횟수입니다. 중앙값을 사용합니다.",
        )
        parser.add_argument(
            "--label",
            default="warm",
            help="이 측정에 붙일 이름입니다. 예: --label=cold",
        )
        parser.add_argument(
            "--only",
            nargs="+",
            help="지정한 이름의 측정 대상만 실행합니다.",
        )
        parser.add_argument(
            "--out",
            help="결과 JSON을 저장할 경로입니다. 기본값은 docs/db/results/ 입니다.",
        )
        parser.add_argument(
            "--no-save",
            action="store_true",
            help="결과 JSON을 저장하지 않습니다.",
        )
        parser.add_argument(
            "--explain",
            action="store_true",
            help="측정 대상의 SQL과 실행계획 전문을 출력합니다.",
        )

    def handle(self, *args, **options):
        if connection.vendor != "postgresql":
            raise CommandError("이 명령은 PostgreSQL 전용입니다.")
        if options["repeat"] < 1:
            raise CommandError("--repeat는 1 이상이어야 합니다.")

        try:
            context = build_context(USERNAME_PREFIX)
        except LookupError as error:
            raise CommandError(str(error)) from error

        self.stdout.write(
            f"측정 대상 사용자: {context.user.username} (id={context.user.id})"
        )
        self.stdout.write(f"반복 횟수: {options['repeat']}회, 라벨: {options['label']}\n")

        results = runner.run_all(
            context,
            repeat=options["repeat"],
            only=options["only"],
        )

        self.stdout.write("## 쿼리\n")
        self.stdout.write(runner.to_markdown(results))

        if options["explain"]:
            for result in results:
                self.stdout.write(f"\n### {result.name}\n")
                self.stdout.write(f"{result.description}\n")
                self.stdout.write("```sql")
                self.stdout.write(result.sql)
                self.stdout.write("```\n")
                self.stdout.write("```")
                self.stdout.write(runner.explain_text(result.sql))
                self.stdout.write("```")
        self.stdout.write("\n## 테이블 크기\n")
        self.stdout.write(runner.sizes_to_markdown(runner.table_sizes()))
        self.stdout.write("")

        if options["no_save"]:
            return

        payload = runner.to_payload(results, options["label"], options["repeat"])
        path = self._save(payload, options["out"], options["label"])
        self.stdout.write(self.style.SUCCESS(f"결과를 저장했습니다: {path}"))

    def _save(self, payload, out, label):
        if out:
            path = Path(out)
        else:
            stamp = payload["recorded_at"].replace(":", "").replace("-", "")[:15]
            path = DEFAULT_RESULT_DIR / f"{stamp}-{label}.json"

        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(
            json.dumps(payload, indent=2, ensure_ascii=False, default=str),
            encoding="utf-8",
        )
        return path
