# 00. 베이스라인 — 측정 도구와 손대기 전 기준선

측정일: 2026-07-31 · PostgreSQL 16 (docker, `postgres:16-alpine`) · 데이터 7,053,900행

이 문서는 아무것도 최적화하지 않는다. 최적화할 대상을 **숫자로 특정**하는 것이 목적이다.
데모 픽스처는 17행이라 어떤 쿼리든 단일 페이지에서 끝나고, 그 상태에서는 어떤 인덱스
설계도 근거를 가질 수 없다.

---

## 1. 무엇을 만들었나

| 구성 요소 | 파일 | 역할 |
|---|---|---|
| 데이터 생성기 | [`benchmarks/loadgen.py`](../../backend/benchmarks/loadgen.py) | 스트리밍 행 생성, COPY / `bulk_create` 두 경로 |
| 생성 명령 | [`generate_load.py`](../../backend/items/management/commands/generate_load.py) | 멱등 재실행, 시퀀스 리셋, `VACUUM ANALYZE` |
| 측정 대상 정의 | [`benchmarks/queries.py`](../../backend/benchmarks/queries.py) | 실제 뷰를 구동해 SQL을 확보 |
| 측정 실행 | [`benchmarks/runner.py`](../../backend/benchmarks/runner.py) | `EXPLAIN (ANALYZE, BUFFERS)` 파싱, 중앙값, JSON 보존 |

방법론과 전제는 [README](README.md)에 따로 정리했다. 요약하면 세 가지다.
**측정 대상 SQL은 손으로 쓰지 않는다**(뷰를 실행해 캡처한다),
**cold인 척하지 않는다**(shared buffers를 비울 방법이 없으므로 전부 warm이라고 명시한다),
**쿼리 수도 함께 센다**(`EXPLAIN` 하나로는 N+1이 안 보인다).

---

## 2. 데이터셋

사용자당 집이 정확히 1채다. 소유자 필터의 선택도가 모든 테넌트에 대해 1%로 균일해야,
느린 이유가 "계획이 나빠서"인지 "그 사용자 데이터가 원래 많아서"인지 구분할 수 있다.

| 테이블 | 행 수 | 테이블 크기 | 인덱스 크기 |
|---|---:|---:|---:|
| `items_itemlocationhistory` | 5,000,000 | 444.5 MB | 297.1 MB |
| `items_itemtag` | 1,500,000 | 77.8 MB | **124.8 MB** |
| `items_item` | 500,000 | 89.9 MB | 64.5 MB |
| `locations_locationnode` | 51,000 | 9.8 MB | 9.0 MB |
| `items_tag` | 2,000 | 0.2 MB | 0.3 MB |
| `items_category` | 500 | 0.1 MB | 0.1 MB |
| 합계 | 7,053,900 | 약 622 MB | 약 496 MB |

`items_itemtag`는 **인덱스가 테이블보다 크다**(124.8 MB vs 77.8 MB). 컬럼이 `id`,
`item_id`, `tag_id` 셋뿐인데 인덱스는 넷이다 — 기본키, `item_id` FK 인덱스,
`tag_id` FK 인덱스, 그리고 `unique_item_tag(item, tag)`. 기본키 `id`는 이 테이블에서
어디에도 쓰이지 않는다. `(item, tag)` 복합 기본키로 충분한 구조다.

위치 트리는 집마다 510개 노드(방 6 → 가구 24 → 칸 96 → 상자 384), 깊이 4단이다.
`full_code`/`path`/`level`은 생성기가 직접 계산해 넣는다. COPY도 `bulk_create`도
`LocationNode.save()`를 호출하지 않기 때문이다. 계산이 모델과 일치하는지는 적재 후
부모-자식 관계를 SQL로 대조해 확인했다 — 51,000행 중 불일치 0건.

---

## 3. 적재

### 3-1. COPY vs `bulk_create`

같은 데이터(290,780행, `--scale=0.2`)를 두 경로로 적재했다.

| 테이블 | 행 수 | COPY | `bulk_create` | 배수 |
|---|---:|---:|---:|---:|
| `locations_locationnode` | 10,200 | 0.14초 | 0.97초 | 6.9× |
| `items_item` | 20,000 | 0.23초 | 1.67초 | 7.3× |
| `items_itemtag` | 60,000 | 0.33초 | 1.47초 | 4.5× |
| `items_itemlocationhistory` | 200,000 | 2.56초 | 11.29초 | 4.4× |
| **적재 합계** | 290,780 | **3.26초** | **15.41초** | **4.7×** |
| COMMIT | | 22.03초 | 23.45초 | 1.0× |
| **전체** | | **25.31초** | **38.87초** | **1.5×** |

COPY는 문 단위 파싱·계획·왕복을 건너뛰므로 적재만 놓고 보면 4.7배 빠르다.
그런데 **전체로는 1.5배 차이밖에 나지 않는다.** COMMIT이 22~23초로 양쪽 모두 동일하고,
COPY 경로에서는 그것이 전체 시간의 87%를 차지하기 때문이다.

로더를 바꾸는 것은 지배적 비용이 아닌 쪽을 최적화한 것이었다.

### 3-2. COMMIT이 적재보다 오래 걸린 이유

전체 규모(7,053,900행)에서 그 차이는 훨씬 극적이다.

| 구간 | 시간 |
|---|---:|
| COPY 9개 테이블 | 89.7초 |
| **COMMIT** | **약 605초** |
| `VACUUM ANALYZE` | 1.0초 |
| 전체 | 694.4초 |

**COMMIT이 적재 자체의 6.7배다.** 원인은 Django가 만드는 외래키 정의에 있다.

```sql
SELECT conname, condeferrable, condeferred FROM pg_constraint WHERE contype='f';
-- 모든 외래키가 condeferrable=t, condeferred=t
```

Django는 모든 외래키를 `DEFERRABLE INITIALLY DEFERRED`로 생성한다. 픽스처를 어떤
순서로든 적재할 수 있게 하려는 설계다. 대가는 적재 중에 참조 검사를 **한 건도** 하지
않는다는 것이다. 검사는 전부 지연 트리거 큐에 쌓였다가 커밋 시점에 한꺼번에 터진다.

이 데이터셋에서 그 큐의 크기는:

| 테이블 | 행 수 | FK 개수 | 검사 건수 |
|---|---:|---:|---:|
| `items_itemlocationhistory` | 5,000,000 | 4 | 20,000,000 |
| `items_itemtag` | 1,500,000 | 2 | 3,000,000 |
| `items_item` | 500,000 | 3 | 1,500,000 |
| `locations_locationnode` | 51,000 | 3 | 153,000 |
| 합계 | | | **약 2,470만** |

10분짜리 COMMIT은 이 2,470만 번의 참조 조회다.

### 3-3. 검사 시점을 앞당기면 빨라지는가 — 아니다

`SET CONSTRAINTS ALL IMMEDIATE`로 검사를 적재 중으로 옮겨 두 규모에서 비교했다.

`--scale=0.2` (290,780행)

| 구간 | deferred (기본값) | immediate |
|---|---:|---:|
| 적재 | 3.26초 | 28.55초 |
| COMMIT | 22.03초 | 0.00초 |
| **전체** | **25.31초** | **28.56초** (13% 느림) |

`--scale=1.0` (7,053,900행)

| 구간 | deferred (기본값) | immediate |
|---|---:|---:|
| 적재 | 89.7초 | 720.2초 |
| COMMIT | 약 605초 | 0.01초 |
| **전체** | **694.4초** | **720.2초** (3.7% 느림) |

**비용이 이동할 뿐 줄지 않는다.** 두 규모 모두에서 오히려 조금 느리다. 검사 자체가
건당 약 2.5μs로 고정된 비용이고, 언제 하느냐는 그 총량을 바꾸지 못한다.
COMMIT이 0.01초로 떨어진 만큼이 그대로 적재 시간에 얹혔다.

실패한 최적화지만 버릴 결과는 아니다. 두 가지를 알려준다.

첫째, **줄이려면 검사 횟수 자체를 줄여야 한다.** 적재 중 제약을 떼었다가 끝나고 한 번만
재검증하거나, 애초에 500만 행짜리 이벤트 테이블에 외래키를 4개 달지 않는 설계로 가야
한다. 후자가 단계 2의 이벤트 테이블 설계로 직결된다.

둘째, 총 시간이 같아도 **운영상으로는 immediate가 낫다.** 10분간 아무 진행 표시 없는
COMMIT 대신 어느 테이블이 비용을 유발하는지 그대로 드러나고, 2,470만 건짜리 트리거 큐가
디스크로 넘치는 일도 없다.

두 경로 모두 `--constraints` 플래그로 재현할 수 있게 남겨두었다.

### 3-4. `ANALYZE`만으로는 부족하다 — `VACUUM`이 필요하다

처음 측정한 검색 쿼리는 버퍼 229,729블록을 읽었다. 같은 쿼리가 잠시 후 18,713블록으로
떨어졌다. **12배 차이가 났고, 쿼리는 한 글자도 바뀌지 않았다.**

원인은 visibility map이었다. 확인한 타임스탬프가 그대로 말해준다.

| 사건 | 시각 |
|---|---|
| 첫 벤치마크 실행 | 14:31:32 |
| autovacuum 완료 (`items_itemtag`) | 14:32:13 |

갓 적재된 테이블에는 visibility map이 없다. 그러면 index-only scan이 "이 행이 모든
트랜잭션에 보이는가"를 인덱스만으로 증명할 수 없어서, 반환하는 행마다 힙을 확인하러
간다. 이름만 index-only일 뿐 실제로는 index scan이다.

`ANALYZE`는 통계를 갱신할 뿐 visibility map을 만들지 않는다. 그건 `VACUUM`만 한다.
생성기가 적재 후 `VACUUM (ANALYZE)`를 돌리도록 고친 이유다.

(이 절의 229,729와 18,713은 이 발견을 한 시점의 적재분에서 측정한 값이다. 4절의 표는
이후 다시 적재한 데이터셋 기준이라 18,913으로 조금 다르다. 12배라는 관계는 그대로다.)

**적재 직후에 측정하면 존재하지 않는 데이터베이스를 측정하게 된다.**

---

## 4. 쿼리 베이스라인

전체 규모, warm, `VACUUM ANALYZE` 완료 상태, 5회 반복 중앙값.
`디스크읽기`가 전부 0인 것은 데이터셋 약 1.5GB가 shared buffers에 들어갔기 때문이다.
즉 아래 수치는 **디스크 I/O가 한 번도 없는, 가장 유리한 조건**이다.

| 측정 대상 | 중앙값 | 최상위 노드 | 추정행/실제행 | 버퍼 블록 | 쿼리수 | 준비쿼리 |
|---|---:|---|---:|---:|---:|---:|
| `item_search_page` | **29.7 ms** | Limit | 4 / 200 | **18,913** | 2 | 0 |
| `item_search_count` | **24.6 ms** | Aggregate | 1 / 1 | **16,641** | 1 | 0 |
| `item_by_location_code` | 18.8 ms | Limit | 200 / 200 | 1,369 | 2 | 0 |
| `location_list` | 1.9 ms | Limit | 200 / 200 | 1,532 | 2 | 0 |
| `item_list_unfiltered` | 1.1 ms | Limit | 200 / 200 | 776 | 2 | 0 |
| `location_subtree_rows` | 0.6 ms | Sort | 520 / 510 | 13 | 1 | 0 |
| `item_by_leaf_node` | 0.2 ms | Limit | 1 / 12 | 87 | 2 | **1** |
| `item_history` | 0.2 ms | Sort | 17 / 10 | 68 | 1 | 0 |

읽는 법 몇 가지.

**검색 한 번은 두 쿼리다.** 페이지네이션이 총건수를 먼저 세고 페이지를 가져온다.
사용자가 체감하는 비용은 29.7 + 24.6 = **54.3 ms**이고 버퍼는 35,554블록, 약 **278 MB**다.
페이지 쿼리만 측정했다면 절반을 놓쳤을 것이다.

**같은 테이블에서 217배 차이가 난다.** `item_search_page`는 18,913블록,
`item_by_leaf_node`는 87블록이다. 둘 다 `items_item`에서 한 페이지를 가져온다.
차이는 술어가 인덱스를 탈 수 있는 형태인가 하나뿐이다.

**추정이 50배 틀렸다.** `item_search_page`에서 플래너는 4행을 예상하고 200행을 받았다.
`%검색어%` 형태의 `LIKE` 다섯 개를 세 테이블에 걸쳐 `OR`로 묶으면 선택도를 추정할 근거가
없다. 추정이 틀리면 조인 순서와 방식 선택도 함께 틀린다.

**`item_by_leaf_node`는 준비 쿼리가 1건 있다.** `?location_node_id=`로 필터하면
`apply_filters`가 본 쿼리를 만들기 전에 위치노드를 먼저 조회한다
([`items/views.py:126`](../../backend/items/views.py)). `include_children=true`이면
`get_descendant_ids()`가 트리 깊이만큼 추가로 돈다 — 이 트리에서는 4회다.

---

## 5. 가장 비싼 쿼리 해부

`item_search_page`의 실행계획에서 비용이 어디에 있는지가 분명하게 드러난다.

```
Limit (actual time=27.480..30.032 rows=200)  Buffers: shared hit=18909
└─ Unique
   └─ Gather Merge (Workers Launched: 2)
      └─ Sort  Sort Key: <33개 컬럼 전부>
         └─ Nested Loop Left Join
            └─ Parallel Hash Left Join
               │  Filter: (upper(name) ~~ '%드라이버%' OR upper(description) ~~ ...
               │           OR upper(tag.name) ~~ ... OR upper(full_code) ~~ ...
               │           OR upper(path) ~~ ...)
               │  Rows Removed by Filter: 4750
               ├─ Hash Left Join
               │  ├─ Parallel Bitmap Heap Scan on items_item   Buffers: 118
               │  │     Index Cond: (owner_id = 1000000)
               │  ├─ Index Only Scan using unique_item_tag     Buffers: 15071  ← 80%
               │  │     loops=5000   Heap Fetches: 0
               │  └─ Seq Scan on items_tag (rows=2004)         Buffers: 60
               └─ Parallel Seq Scan on locations_locationnode  Buffers: 약 1300
                     (= 51,000행 전부)
```

**① 전체 비용의 80%가 태그 조인이다.** 18,909블록 중 15,071블록이
`items_itemtag`를 아이템당 한 번씩, 5,000번 훑는 데 쓰였다. 이 조인이 존재하는 유일한
이유는 다섯 개 `OR` 가지 중 하나인 `tags__name__icontains`를 평가하기 위해서다.
나머지 네 가지에는 필요 없다.

**② 남의 집 위치노드까지 전부 읽는다.** `locations_locationnode`를 51,000행 전부
스캔해 해시를 만든다. 이 사용자 소유는 510행뿐이다. 소유자 조건이 `items_item`에만
걸려 있고 조인 대상에는 없어서, 100채 분량을 읽어 해시를 만든 뒤 1%만 매칭한다.
`items_tag`도 마찬가지로 2,004행 전부를 읽는다.

**③ 필터가 조인 뒤에 걸린다.** `Rows Removed by Filter: 4750` — 5,000행을 만들어
4,750행을 버린다. 술어가 세 테이블에 걸친 `OR`이라 어느 한 테이블로 밀어넣을 수 없다.

**④ `DISTINCT`가 33개 컬럼 정렬을 부른다.** 태그 조인이 아이템당 3행으로 부풀리므로
`.distinct()`로 되돌려야 한다. 그런데 `select_related`가 세 테이블의 모든 컬럼을
끌어오기 때문에 `SELECT DISTINCT`의 정렬 키가 33개 컬럼 전부가 된다.

**⑤ 필터가 없어도 `DISTINCT`가 붙는다.** `apply_filters`는 마지막에 무조건
`qs.distinct()`를 반환한다([`items/views.py:140`](../../backend/items/views.py)).
행이 부풀지 않는 경우에도 중복 제거 작업이 붙는다.

---

## 6. 측정하다 발견한 것들

측정 도구를 만드는 과정 자체에서 나온 것들이다. 기록해두지 않으면 다음에 같은 함정을
다시 밟는다.

### 도구의 버그: 버퍼 중복 집계

러너가 처음에는 실행계획 트리 전체를 순회하며 `Shared Hit Blocks`를 더했다. `EXPLAIN`의
버퍼 수치는 **자식 노드를 이미 포함한 누적값**이라, 이러면 층마다 중복으로 센다.
루트가 18,713이라고 말하는 쿼리를 178,565로 보고하고 있었다. 루트 값만 읽도록 고쳤다.

### 도구의 버그: 엉뚱한 쿼리를 측정

`item_by_leaf_node`가 아이템 쿼리가 아니라 `apply_filters`가 먼저 실행하는 위치노드
조회를 측정하고 있었다. 쿼리셋을 **만드는** 행위가 쿼리를 발생시키는데 그게 캡처 구간
안에 있었다. 빌드를 캡처 밖으로 빼고, 부수 쿼리는 `준비쿼리` 열로 따로 세도록 고쳤다.

### 인프라: Docker `/dev/shm` 64MB 제한

`VACUUM (ANALYZE)`가 이렇게 실패했다.

```
could not resize shared memory segment to 67145344 bytes: No space left on device
```

Docker는 컨테이너에 `/dev/shm`을 64MB만 준다. PostgreSQL은 동적 공유 메모리를 여기에
할당하므로 병렬 쿼리 워커와 병렬 인덱스 VACUUM이 테이블이 커지는 순간 실패한다.
메모리 경고가 아니라 쿼리 오류로 나타나기 때문에 쿼리 버그로 오해하기 쉽다.

`docker-compose.yml`과 `docker-compose.prod.yml`의 `db` 서비스에 `shm_size`를 넣었다
(개발 1GB, 운영 256MB — `/dev/shm`은 tmpfs이므로 예약이 아니라 상한이다).

이 계정의 실행계획에는 `Workers Launched: 2`가 찍혀 있다. 병렬 쿼리도 같은 공유 메모리를
쓰므로, 이 설정이 없었다면 데이터가 조금만 더 늘어도 조회 자체가 실패했을 것이다.

---

## 7. 함께 고친 것 — 트랜잭션 경계

측정과는 별개로, 코드를 읽다 발견한 정합성 결함 하나를 고쳤다.

`move` 액션은 `@transaction.atomic`으로 아이템 갱신과 이력 삽입을 묶는다. 그런데 같은
일을 하는 `PATCH /api/items/{id}/` 경로, 즉 `perform_update`는 그 경계 없이 아이템을
먼저 저장하고 이력을 나중에 만들고 있었다.

이력 삽입이 실패하면 **아이템은 옮겨진 채로 남고, 옮겼다는 기록만 사라진다.** 데이터
어디에도 쓰기가 유실됐다는 흔적이 없다.

먼저 재현하는 테스트를 쓰고(`test_update_rolls_back_the_move_when_history_write_fails`),
실패를 확인한 뒤 `perform_update`를 `transaction.atomic()`으로 감쌌다. 위치 변경 시
이력이 생기는지 확인하는 테스트도 함께 추가했다. 백엔드 테스트 32건 전부 통과한다.

---

## 8. 다음 단계

베이스라인이 지목하는 순서다.

**단계 1 — 검색 쿼리.** 지금 가장 비싸고(54.3 ms / 278 MB), 원인이 네 겹으로 분명하다.
`pg_trgm` GIN 인덱스로 `LIKE '%...%'`를 인덱스에 태우고, 다섯 겹 `OR`를 `EXISTS` 또는
`UNION`으로 재작성해 태그 조인을 필요할 때만 만들고, 조인 대상에도 소유자 조건을 걸어
남의 집 노드를 읽지 않게 한다. 무조건 붙는 `.distinct()`도 정리 대상이다.
인덱스 크기와 쓰기 지연을 함께 측정해 기록한다.

**단계 2 — 이벤트 테이블.** `items_itemlocationhistory`는 이미 500만 행이고 AR로 가면
사람이 손으로 옮길 때가 아니라 물건을 집을 때마다 쌓인다. 여기서 월 단위 range
partitioning, BRIN 대 B-tree, 보존 정책(`DELETE` 대 `DROP PARTITION`)이 의미를 갖는다.
3-3에서 확인한 "외래키 4개가 곧 검사 2,000만 건"도 이 테이블 설계에서 다시 다룬다.

**미뤄둔 것.** `items_itemtag`의 불필요한 `id` 기본키(인덱스가 테이블보다 크다),
`get_descendant_ids()`의 깊이만큼 도는 쿼리, 커넥션 풀링(`CONN_MAX_AGE` 미설정).
지금 고칠 수 있지만 근거를 먼저 쌓은 뒤에 손대는 편이 낫다.
