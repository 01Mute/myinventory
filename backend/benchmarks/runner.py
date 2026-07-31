"""Execute the benchmark cases and report what Postgres actually did.

Two things are recorded per case. The first is the SQL the ORM emitted, taken by
capturing it during a real evaluation rather than by reconstructing it - a
reconstruction is a guess, and a guess is exactly what a benchmark must not
contain. The second is EXPLAIN (ANALYZE, BUFFERS) on that SQL, which is the only
evidence that distinguishes "this got faster" from "this got faster on my
machine, this once".

On cold versus warm
-------------------
There is no supported way to empty Postgres' shared buffers or the operating
system's page cache from inside a session. DISCARD ALL resets session state, not
caches, and a runner that claimed otherwise would be reporting a warm number
under a cold label. So every measurement here is warm by construction, and the
honest cold signal is `read_blocks`: blocks that were not already in shared
buffers. For a genuinely cold run, restart the database first
(`docker compose restart db`) and pass --label=cold.
"""

from __future__ import annotations

import json
import statistics
from dataclasses import asdict, dataclass, field
from datetime import datetime, timezone

from django.db import connection
from django.test.utils import CaptureQueriesContext

from .queries import CASES, Context, QueryCase


@dataclass
class CaseResult:
    name: str
    description: str
    sql: str
    query_count: int
    setup_queries: int
    median_ms: float
    min_ms: float
    max_ms: float
    planning_ms: float
    node_type: str
    plan_rows: int
    actual_rows: int
    hit_blocks: int
    read_blocks: int
    samples: list[float] = field(default_factory=list)

    @property
    def row_estimate_ratio(self) -> float:
        """How far the planner's row estimate was from reality.

        A large ratio is the usual first sign that statistics are stale or that
        a predicate's selectivity cannot be estimated - which is itself the
        finding, not a nuisance.
        """
        if self.actual_rows == 0:
            return 0.0
        return self.plan_rows / self.actual_rows


def evaluate(case: QueryCase, queryset):
    if case.mode == "count":
        return queryset.count()
    return list(queryset)


def capture_sql(case: QueryCase, context: Context) -> tuple[str, int, int]:
    """Run the case once and record the SQL it emitted.

    Building the queryset is deliberately kept outside the capture. Assembling
    one can run queries of its own - ItemViewSet.apply_filters resolves
    ?location_node_id= with a LocationNode lookup before it filters anything -
    and those would otherwise be mistaken for the statement under test. They are
    counted separately instead, because "this filter costs an extra round trip
    before the real query even starts" is a finding rather than noise.

    Of the statements that remain, the first is the one under test and any after
    it come from prefetch_related. Their number is reported: a case whose query
    count grows with the dataset is an N+1 regression, which no single EXPLAIN
    would reveal.
    """
    with CaptureQueriesContext(connection) as setup:
        queryset = case.build(context)
        setup_queries = len(setup.captured_queries)

    with CaptureQueriesContext(connection) as captured:
        evaluate(case, queryset)

    if not captured.captured_queries:
        raise RuntimeError(f"{case.name}: 실행된 쿼리가 없습니다.")
    return (
        captured.captured_queries[0]["sql"],
        len(captured.captured_queries),
        setup_queries,
    )


def explain_text(sql: str) -> str:
    """The plan as Postgres prints it, for reading rather than for parsing."""
    with connection.cursor() as cursor:
        cursor.execute(f"EXPLAIN (ANALYZE, BUFFERS) {sql}")
        return "\n".join(row[0] for row in cursor.fetchall())


def explain(sql: str) -> dict:
    with connection.cursor() as cursor:
        cursor.execute(f"EXPLAIN (ANALYZE, BUFFERS, FORMAT JSON) {sql}")
        payload = cursor.fetchone()[0]

    # psycopg returns json as text on some paths and as a parsed object on
    # others depending on the column type EXPLAIN reports.
    if isinstance(payload, str):
        payload = json.loads(payload)

    root = payload[0]["Plan"]

    # Buffer counts in EXPLAIN are cumulative: every node already includes what
    # its children touched, so the root carries the total for the whole plan.
    # Summing the tree instead double-counts each level - it reported 178,565
    # buffer hits for a query whose root node says 18,713.
    return {
        "execution_ms": payload[0]["Execution Time"],
        "planning_ms": payload[0]["Planning Time"],
        "node_type": root["Node Type"],
        "plan_rows": root["Plan Rows"],
        "actual_rows": root["Actual Rows"],
        "hit_blocks": root.get("Shared Hit Blocks", 0),
        "read_blocks": root.get("Shared Read Blocks", 0),
    }


def run_case(case: QueryCase, context: Context, repeat: int) -> CaseResult:
    sql, query_count, setup_queries = capture_sql(case, context)

    samples = []
    last = None
    for _ in range(repeat):
        last = explain(sql)
        samples.append(last["execution_ms"])

    return CaseResult(
        name=case.name,
        description=case.description,
        sql=sql,
        query_count=query_count,
        setup_queries=setup_queries,
        median_ms=statistics.median(samples),
        min_ms=min(samples),
        max_ms=max(samples),
        planning_ms=last["planning_ms"],
        node_type=last["node_type"],
        plan_rows=last["plan_rows"],
        actual_rows=last["actual_rows"],
        hit_blocks=last["hit_blocks"],
        read_blocks=last["read_blocks"],
        samples=samples,
    )


def run_all(context: Context, repeat: int = 5, only=None) -> list[CaseResult]:
    cases = [case for case in CASES if not only or case.name in only]
    if not cases:
        raise LookupError(f"이름이 맞는 측정 대상이 없습니다: {only}")
    return [run_case(case, context, repeat) for case in cases]


# ---------------------------------------------------------------------------
# Reporting
# ---------------------------------------------------------------------------

MARKDOWN_HEADER = (
    "| 측정 대상 | 중앙값(ms) | 최소~최대 | 계획(ms) | 최상위 노드 | "
    "추정행/실제행 | 캐시히트 블록 | 디스크읽기 블록 | 쿼리수 | 준비쿼리 |"
)
MARKDOWN_DIVIDER = "|---|---:|---:|---:|---|---:|---:|---:|---:|---:|"


def to_markdown(results: list[CaseResult]) -> str:
    lines = [MARKDOWN_HEADER, MARKDOWN_DIVIDER]
    for result in results:
        lines.append(
            f"| `{result.name}` "
            f"| {result.median_ms:,.1f} "
            f"| {result.min_ms:,.1f}~{result.max_ms:,.1f} "
            f"| {result.planning_ms:,.2f} "
            f"| {result.node_type} "
            f"| {result.plan_rows:,}/{result.actual_rows:,} "
            f"| {result.hit_blocks:,} "
            f"| {result.read_blocks:,} "
            f"| {result.query_count} "
            f"| {result.setup_queries} |"
        )
    return "\n".join(lines)


def table_sizes() -> list[dict]:
    """Table and index sizes, so a speedup can be weighed against its cost."""
    with connection.cursor() as cursor:
        cursor.execute(
            """
            SELECT relname,
                   n_live_tup,
                   pg_table_size(relid)   AS table_bytes,
                   pg_indexes_size(relid) AS index_bytes
              FROM pg_stat_user_tables
             ORDER BY pg_total_relation_size(relid) DESC
            """
        )
        columns = [column.name for column in cursor.description]
        return [dict(zip(columns, row)) for row in cursor.fetchall()]


def sizes_to_markdown(rows: list[dict]) -> str:
    lines = [
        "| 테이블 | 행 수(추정) | 테이블 | 인덱스 |",
        "|---|---:|---:|---:|",
    ]
    for row in rows:
        if not row["n_live_tup"]:
            continue
        lines.append(
            f"| `{row['relname']}` "
            f"| {row['n_live_tup']:,} "
            f"| {row['table_bytes'] / 1024 / 1024:,.1f} MB "
            f"| {row['index_bytes'] / 1024 / 1024:,.1f} MB |"
        )
    return "\n".join(lines)


def to_payload(results: list[CaseResult], label: str, repeat: int) -> dict:
    return {
        "label": label,
        "recorded_at": datetime.now(timezone.utc).isoformat(),
        "repeat": repeat,
        "postgres_version": _server_version(),
        "tables": table_sizes(),
        "cases": [asdict(result) for result in results],
    }


def _server_version() -> str:
    with connection.cursor() as cursor:
        cursor.execute("SELECT version()")
        return cursor.fetchone()[0]
