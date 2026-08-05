# Home Inventory Map

집 안의 물건 위치를 위치 트리와 위치 코드로 관리하는 웹 서비스입니다.

> **데이터베이스 작업 기록**은 [`docs/db/`](docs/db/)에 따로 정리되어 있습니다.
> 700만 행 규모에서 측정한 실행계획과 개선 근거를 담고 있습니다. → [베이스라인 리포트](docs/db/00-baseline.md)

## 주요 기능

### 1. 백엔드 기본 구조

- Django 기반 백엔드 프로젝트 구성
- Django REST Framework 설정
- PostgreSQL 데이터베이스 연결
- Django Admin 등록
- 세션 기반 회원가입, 로그인, 로그아웃, 내 정보 API 제공
- 이메일 인증 코드 기반 비밀번호 찾기 API 제공

### 2. 집 / 도면 관리

- 집 CRUD API 제공
- 도면 CRUD API 제공
- 집 추가 시 기본 도면 자동 생성
- 선택된 집 기준으로 층 및 도면 추가
- 집 목록 클릭 시 우측 도면 목록 자동 변경
- 마지막으로 선택한 집과 도면 자동 기억
- 도면 카드 클릭 시 도면 편집 화면으로 이동
- 도면 삭제 전 확인창 표시
- 도면 편집 화면에서 도면 이름 변경

### 3. 위치 노드 관리

- 위치 노드 트리 CRUD API 제공
- 위치 코드 자동 생성
- 방, 가구, 칸 구조의 계층형 위치 관리
- 방 > 가구 > 칸 형태의 폴더형 위치 목록 제공
- 선택한 위치의 하위 물건 목록 표시
- 특정 위치 하위 물건 조회
- 위치 선택 시 하위 위치까지 포함하여 검색
- 선택 위치 타입 즉시 반영
- 선택 위치에서 이름을 우선 표시하고 위치 코드는 숨김 처리

### 4. 물건 관리

- 물건 CRUD API 제공
- 카테고리 CRUD API 제공
- 태그 CRUD API 제공
- 물건 등록, 조회, 수정, 삭제 기능
- 목록 중심의 물건 관리 화면 제공
- 필요 시 등록/수정 패널 표시
- 물건 목록 클릭 시 상세정보 수정
- 빈 공간 클릭 시 수정 패널 닫기 및 저장 여부 확인
- 물건 수정 패널 및 목록 행에서 물건 삭제
- 구매일자 입력
- 물건 등록 시 구매일자 오늘 날짜 기본 설정
- 물건, 위치, 수량, 마지막 검색일자 표시
- 동일 이름 물건 등록 전 확인창 표시

### 5. 검색 기능

- 물건명, 카테고리, 태그, 위치 코드 기반 검색
- 태그 검색 입력 지원
- 드롭다운형 접이식 위치 검색 제공
- 검색 결과의 마지막 검색일자 자동 갱신
- 검색어 입력이 1초 동안 멈춘 뒤 현재 검색 결과만 마지막 검색일자 갱신

### 6. 위치 이동 및 이력 관리

- 물건 위치 이동 기능
- 위치 변경 저장 시 이동 이력 자동 생성
- 물건 위치 이동 이력 저장
- 위치 이동 이력 조회
- 이동 이력 항목이 많아질 경우 내부 스크롤 표시

### 7. 이미지 업로드

- JPG, PNG, GIF, WEBP 사진 선택 지원
- 이미지 미리보기 제공
- 이미지 업로드 기능
- 서버에서 실제 이미지 파일 검증

### 8. 도면 편집 기능

- SVG 기반 도면 편집 화면 제공
- 도면 사각형 추가, 선택, 이동, 크기 조절, 저장
- 도면 배치 영역 마우스 휠 확대/축소
- 도면 배치 영역 배경 드래그 이동
- 도면 배치 영역 스크롤바 제거
- 방/가구 드래그 이동 우선 처리
- 선택 사각형 방향키 미세 이동 및 입력 정지 후 서버 저장
- 사각형 드래그에 따른 좌우상하 무제한 표시 범위 확장
- 도면 경계 10px 밖으로 나가기 전까지 표시 범위 확장 지연
- 사각형 배치에 따른 도면 크기 자동 확장
- 방/가구 사각형 최소/최대 크기 제한
- 사각형 코드 자동 생성
- 방/가구 타입 중심의 도면 사각형 관리
- 가구 사각형을 방 위에 표시
- 같은 타입 도형과 도면 경계 기준 자동 정렬
- 가구가 방 안에 들어가면 상위 위치 자동 할당
- 잠기지 않은 사각형 점선 표시
- 선택 위치 잠금 및 잠금 시 실선 표시, 드래그/방향키 이동/크기 조절 차단
- 방 추가 버튼과 가구 추가 버튼 분리
- 잘못된 임시 좌표로 인한 배치 화면 깨짐 방지

### 9. 가구 내부 칸 관리

- 가구 내부 칸 추가
- 칸별 쓰레기통 아이콘으로 삭제
- 칸 삭제 전 확인창 표시
- 선택 위치 삭제 버튼 제공
- Delete 키를 통한 선택 위치 삭제

### 10. 프론트엔드

- React + TypeScript 기반 프론트엔드 구현
- 로그인 / 회원가입 화면 제공
- 포트폴리오 확인용 테스트 계정 안내 및 자동 입력 버튼 제공
- 기존 비밀번호 입력 없는 이메일 코드 기반 비밀번호 찾기 화면 제공
- 로그인 후 집과 도면이 있으면 물건 검색 화면을 첫 화면으로 표시
- 집 / 도면 관리 화면 제공
- 도면 편집 화면 제공
- 위치별 포함 물건 조회 화면 제공
- 물건 검색 / 등록 화면 제공
- 물건 목록 항목이 많아질 경우 내부 스크롤 표시
- 위치별 포함 물건 조회 화면에서 내부 스크롤 목록 제공

### 11. Docker 및 운영 환경

- Docker Compose 로컬 실행 설정
- 운영용 Docker Compose 설정
- Nginx 기반 프론트엔드 정적 파일 제공
- Nginx를 통한 백엔드 API 프록시 구성
- 정적 파일과 업로드 파일 볼륨 분리
- 운영용 환경 변수 예시 제공
- PostgreSQL 병렬 처리를 위한 `shm_size` 설정 (Docker 기본값 64MB로는 병렬 VACUUM이 실패)

### 12. 데이터베이스 엔지니어링

성능에 대한 판단을 수치 없이 하지 않기 위해, 측정 도구부터 만들고 기준선을 기록했습니다.
전체 내용은 [`docs/db/`](docs/db/)에 있습니다.

- 700만 행 규모 데이터 생성기 (`COPY` 기반, 스트리밍, 멱등 재실행)
- 실제 뷰를 구동해 SQL을 캡처하는 벤치마크 러너 (`EXPLAIN (ANALYZE, BUFFERS)`)
- 측정 결과를 JSON으로 보존해 이후 변경과 비교 가능

측정에서 나온 것들:

- `COPY`는 `bulk_create`보다 적재가 4.7배 빠르지만, 전체 시간은 1.5배 차이에 그침 —
  지배적 비용은 로더가 아니라 커밋이었음
- 전체 적재 694초 중 **COMMIT이 605초**. Django가 모든 외래키를
  `DEFERRABLE INITIALLY DEFERRED`로 만들어 참조 검사 약 2,470만 건이 커밋 시점에 몰림
- 적재 후 `ANALYZE`만으로는 부족. visibility map이 없으면 index-only scan이 힙을 확인해
  같은 쿼리가 버퍼 **12배**를 읽음 (`VACUUM` 필요)
- 검색 API 1회 = 총건수 + 페이지 두 쿼리 = **54.3 ms / 278 MB 버퍼**,
  그중 80%가 다섯 겹 `OR` 중 태그 조건 하나를 평가하기 위한 조인
- `PATCH /api/items/{id}/`가 아이템 저장과 이력 삽입을 트랜잭션 없이 수행하던 결함 수정
  (재현 테스트 추가 후 수정)


## 개발 실행

```bash
cp .env.example .env
docker compose up --build
```

접속 주소:

```text
Backend API: http://localhost:8000/api/
Django Admin: http://localhost:8000/admin/
Frontend: http://localhost:5173/
Floor Plan Editor: http://localhost:5173/editor
```

테스트 계정과 예시 데이터 생성:

```bash
docker compose exec backend python manage.py seed_demo
```

로그인 화면의 테스트 계정(`test` / `test1234`)은 이 명령으로 만들어집니다.
집 2개, 도면 2개, 위치 10개, 물건 17개와 물건 사진, 이동 이력이 함께 생성됩니다.
다시 실행하면 테스트 계정의 데이터를 지우고 처음 상태로 되돌립니다.

```bash
# 계정 정보를 바꾸려면
docker compose exec backend python manage.py seed_demo --username demo --password demo1234
```

예시 데이터는 원래 기본키를 그대로 사용하므로, 다른 사용자의 데이터와 겹치면
명령이 중단됩니다. 그래도 덮어쓰려면 `--force`를 붙입니다.

### 테스트 계정 백업과 복원

테스트 계정은 누구나 로그인할 수 있어서, 곧 아무나 고칠 수 있는 계정이기도 합니다.
`backup_demo`는 그 계정의 데이터와 사진을 날짜별 디렉터리로 남깁니다.

```bash
docker compose exec backend python manage.py backup_demo
```

```
backups/demo-20260803-034100/
  data.json      # 계정이 소유한 행 전부 (소유자는 픽스처 플레이스홀더로 기록)
  media/         # 그 행들이 참조하는 이미지만
```

`data.json`은 `seed_demo`가 읽는 형식과 같아서 그대로 되돌릴 수 있습니다.
백업 디렉터리를 지정하면 이미지도 그 안의 `media/`에서 복원합니다.

```bash
docker compose exec backend python manage.py seed_demo \
  --fixture backups/demo-20260803-034100/data.json
```

| 옵션 | 설명 |
|---|---|
| `--username` | 백업할 계정. 기본값 `test` |
| `--out` | 저장 위치. 기본값은 `BACKUP_ROOT` 설정 |
| `--keep-days` | 이 일수보다 오래된 백업을 삭제. 기본 14일, `0`이면 삭제 안 함 |
| `--no-media` | 이미지를 빼고 행 데이터만 백업 |

백업은 이름 붙은 볼륨이 아니라 **호스트 바인드 마운트**(`BACKUP_DIR`, 기본 `./backups`)에
씁니다. 백업의 목적이 이 서버 밖으로 복사해 두는 것이고, 이미지 안의 경로는 다음
재빌드 때 사라지기 때문입니다. 하필 백업이 살아남아야 하는 그 순간에 말입니다.

운영 서버에서 매일 자동 실행하려면:

```bash
sh ~/myinventory/scripts/backup-cron.sh
```

관리자 계정 생성:

```bash
docker compose exec backend python manage.py createsuperuser
```

## 운영 실행 준비

운영용 실행은 `docker-compose.prod.yml`을 사용합니다.

```bash
cp .env.example .env
```

`.env`에서 반드시 바꿀 값:

```text
DJANGO_SECRET_KEY=충분히 긴 임의 문자열
DJANGO_ALLOWED_HOSTS=your-domain.com
CSRF_TRUSTED_ORIGINS=https://your-domain.com
POSTGRES_PASSWORD=강한 비밀번호
```

비밀번호 찾기 메일을 실제로 보내려면 `.env`에 SMTP 값도 설정합니다.
DuckDNS 도메인만으로는 이메일 발송이 되지 않으므로 Gmail 앱 비밀번호, AWS SES, Mailgun 같은 SMTP 발송 계정이 필요합니다.

```text
EMAIL_BACKEND=django.core.mail.backends.smtp.EmailBackend
EMAIL_HOST=smtp.example.com
EMAIL_PORT=587
EMAIL_HOST_USER=SMTP 사용자
EMAIL_HOST_PASSWORD=SMTP 비밀번호 또는 앱 비밀번호
EMAIL_USE_TLS=true
EMAIL_USE_SSL=false
DEFAULT_FROM_EMAIL=no-reply@example.com
```

도메인 없이 같은 PC에서만 확인할 때는 `localhost,127.0.0.1` 값을 유지해도 됩니다.
실제 HTTPS 배포에서는 `DJANGO_SESSION_COOKIE_SECURE=true`, `DJANGO_CSRF_COOKIE_SECURE=true`로 바꿉니다.

운영용 컨테이너 실행:

```bash
docker compose -f docker-compose.prod.yml up --build -d
```

운영용 관리자 계정 생성:

```bash
docker compose -f docker-compose.prod.yml exec backend python manage.py createsuperuser
```

운영용 접속 주소:

```text
Frontend: http://localhost/
Backend API: http://localhost/api/
Django Admin: http://localhost/admin/
Uploaded Media: http://localhost/media/
```

실제 서버에서는 `your-domain.com`을 배포 도메인으로 바꾸고, 서버 앞단 또는 별도 프록시에서 HTTPS를 연결합니다.

## 주요 API

```text
POST /api/auth/register/
GET  /api/auth/csrf/
POST /api/auth/login/
POST /api/auth/logout/
GET  /api/auth/me/
POST /api/auth/password-reset/request/
POST /api/auth/password-reset/confirm/

GET/POST/PATCH/DELETE /api/homes/
GET/POST/PATCH/DELETE /api/floor-plans/
GET/POST/PATCH/DELETE /api/location-nodes/
GET /api/location-nodes/{id}/tree/

GET/POST/PATCH/DELETE /api/categories/
GET/POST/PATCH/DELETE /api/tags/
GET/POST/PATCH/DELETE /api/items/
GET /api/items/export-csv/
POST /api/items/touch-searched/
POST /api/items/{id}/photo/
POST /api/items/{id}/move/
POST /api/items/{id}/touch-last-checked/
GET /api/items/{id}/history/
```

목록 응답은 페이지네이션됩니다. `count`, `next`, `previous`, `results` 형태이며
`next`를 따라가면 전체 목록을 받을 수 있습니다. 한 페이지 크기는 `PAGE_SIZE`로 조정합니다.

```json
{ "count": 120, "next": "http://.../api/items/?page=2", "previous": null, "results": [] }
```

검색 예시:

```text
GET /api/items/?q=여권
GET /api/items/?category=문서
GET /api/items/?tag=중요문서
GET /api/items/?location_code=A-1-3
GET /api/items/?location_node_id=10&include_children=true
```

검색 결과의 마지막 검색일자를 갱신할 때는 조회가 아니라 쓰기 전용 경로를 씁니다.
같은 검색 조건을 쿼리 파라미터로 넘기며 `q`는 필수입니다.

```text
POST /api/items/touch-searched/?q=여권
```

`/api/auth/login/`, `/api/auth/register/`, `/api/auth/password-reset/*`는 요청 제한이
걸려 있습니다. 초과하면 `429`를 반환하며, 비율은 `.env`의 `THROTTLE_*` 값으로 조정합니다.
