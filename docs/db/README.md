# 데이터베이스 엔지니어링 기록

이 디렉터리는 myinventory의 데이터베이스 작업을 **측정 → 변경 → 재측정** 순서로 기록한다.

수치 없는 주장은 남기지 않는다는 규칙 하나로 운영한다. "파티셔닝하면 빨라진다"는 문장은
어디서든 읽을 수 있고, 그 문장만으로는 이 스키마에서 실제로 무슨 일이 일어나는지 아무것도
알 수 없다. 그래서 모든 문서는 같은 틀을 따른다.

> **증상**(숫자) → **가설** → **실행계획 근거** → **조치** → **재측정**(숫자) → **트레이드오프**

마지막 칸이 특히 중요하다. 어떤 인덱스도 공짜가 아니다. 읽기가 빨라진 만큼 쓰기가 느려지고
디스크를 더 쓴다. 그 대가를 함께 적지 않은 기록은 절반만 맞는 기록이다.

## 문서

| 문서 | 내용 |
|---|---|
| [00-baseline.md](00-baseline.md) | 측정 도구 구축, 데이터셋 형태, 손대기 전 기준선 |

## 도구

### 대량 데이터 생성

```bash
docker compose exec backend python manage.py generate_load --scale=1.0
```

| 옵션 | 설명 |
|---|---|
| `--scale` | 사용자 수와 집당 아이템 수에 곱할 배수. `--scale=0.01`이면 빠른 동작 확인용 |
| `--loader` | `copy`(기본) 또는 `bulk`. COPY와 ORM `bulk_create`의 비교용 |
| `--constraints` | `deferred`(기본, Django 그대로) 또는 `immediate`. 외래키 검사 시점 |
| `--users`, `--items-per-home`, `--history-per-item` | 개별 차원 직접 지정 |
| `--seed` | 난수 시드. 기본값 고정이라 같은 옵션이면 같은 데이터가 나온다 |
| `--no-vacuum` | 적재 후 `VACUUM ANALYZE` 생략 (측정 목적이라면 쓰지 말 것) |
| `--force` | 생성 범위(`id >= 1000000`)의 기본키를 쓰는 데이터가 있어도 진행 |

생성 데이터는 `load_user_0` ~ `load_user_99`가 소유한다. 재실행하면 이전 생성분을 지우고
다시 만들므로 몇 번을 돌려도 결과가 같다. 데모 계정(`test`)의 데이터는 건드리지 않는다.

구현: [`backend/benchmarks/loadgen.py`](../../backend/benchmarks/loadgen.py),
[`backend/items/management/commands/generate_load.py`](../../backend/items/management/commands/generate_load.py)

### 쿼리 측정

```bash
docker compose exec backend python manage.py run_benchmark --repeat=5
```

| 옵션 | 설명 |
|---|---|
| `--repeat` | 쿼리당 반복 횟수. 중앙값을 쓴다 |
| `--label` | 측정에 붙일 이름. 결과 파일명에 들어간다 |
| `--only` | 특정 측정 대상만 실행 |
| `--explain` | SQL 전문과 실행계획을 함께 출력 |
| `--out` | 결과 JSON 경로 |
| `--no-save` | 결과 JSON을 저장하지 않음 |

결과는 `backend/benchmarks/results/`에 JSON으로 남는다. 나중 측정과 비교하기 위한 것이다.
터미널에만 출력하는 벤치마크는 일주일 뒤에 아무것도 증명하지 못한다.

구현: [`backend/benchmarks/queries.py`](../../backend/benchmarks/queries.py),
[`backend/benchmarks/runner.py`](../../backend/benchmarks/runner.py)

## 측정 방법에 대한 전제

### 측정 대상 SQL은 손으로 쓰지 않는다

`queries.py`는 `ItemViewSet`과 `LocationNodeViewSet`을 실제로 인스턴스화해서
`get_queryset()`을 호출하고, 그렇게 만들어진 쿼리셋을 한 번 실행하면서 나온 SQL을
`CaptureQueriesContext`로 잡아낸다.

손으로 옮겨 적은 SQL은 누군가 필터를 수정하는 순간 실제 코드와 어긋나고, 그때부터
벤치마크는 아무도 실행하지 않는 쿼리를 측정하게 된다. 뷰를 거치면 코드가 바뀔 때
측정도 따라 바뀐다.

### cold와 warm

Postgres의 shared buffers나 OS 페이지 캐시를 세션 안에서 비우는 방법은 없다.
`DISCARD ALL`은 세션 상태를 초기화할 뿐 캐시와 무관하다. 그래서 이 도구의 측정은
**전부 warm**이며, 그렇지 않은 척하지 않는다.

디스크에서 실제로 읽었는지는 `read_blocks`(= `Shared Read Blocks`)가 알려준다.
이 값이 크면 shared buffers에 없던 데이터를 가져온 것이다.

진짜 cold 측정이 필요하면 DB를 먼저 재시작한 뒤 라벨을 붙여 기록한다.

```bash
docker compose restart db
docker compose exec backend python manage.py run_benchmark --repeat=1 --label=cold
```

### 반복과 중앙값

1회 측정은 노이즈가 크다. 기본 5회를 돌려 중앙값을 쓰고, 최소~최대를 함께 남겨
편차가 큰 경우를 눈으로 잡을 수 있게 한다.

### 쿼리 수도 함께 센다

각 측정 대상은 실행 중 발생한 쿼리 개수를 함께 기록한다. `EXPLAIN` 하나로는
`prefetch_related`가 만드는 추가 쿼리나 N+1 회귀를 볼 수 없기 때문이다.
데이터가 늘 때 이 숫자가 같이 늘어나면 그것이 곧 결함이다.

### 적재 후 VACUUM ANALYZE

갓 적재된 테이블에는 통계가 없다. 통계가 없으면 플래너는 하드코딩된 추정값으로
계획을 세우고, 운영에서는 절대 고르지 않을 계획을 고른다.

`ANALYZE`만으로는 부족하다. visibility map은 `VACUUM`만 만들고, 그것이 없으면
index-only scan이 반환하는 행마다 힙을 확인하러 간다. 이 데이터셋에서 그 차이는
같은 쿼리에 대해 버퍼 229,729블록과 18,713블록, **12배**였다.
자세한 내용은 [00-baseline.md의 3-4절](00-baseline.md)에 있다.

적재 직후에 측정하면 존재하지 않는 데이터베이스를 측정하게 된다.
