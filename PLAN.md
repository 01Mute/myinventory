# Home Inventory Map 개발 계획

## 0. 진행 현황

최종 업데이트: 2026-06-15

현재 구현 위치:

```text
C:\Users\dbdkd\Documents\Codex\2026-06-12\files-mentioned-by-the-user-item\outputs\home-inventory-map
```

현재 상태:

| Phase | 상태 | 요약 |
|---|---|---|
| Phase 1. 백엔드 기반 구축 | 완료 | Django/DRF, PostgreSQL 설정, 핵심 모델, Admin, CRUD API, 검색 API, 위치 이동 이력 API 구현 |
| Phase 2. 프론트엔드 기본 화면 | 완료 | React/TypeScript, 인증 화면, 집 생성 후 기본 도면 자동 생성/편집 화면 이동, 집/도면 관리, 위치 트리 관리, 물건 검색/등록 화면 구현 |
| Phase 3. 간단한 도면 편집기 | 완료 | SVG 기반 사각형 도면 편집기, 도형 추가/선택/이동/리사이즈/저장, 자동 코드 생성, 도면 자동 확장, 선택 위치 물건 목록 구현 |
| Phase 4. 물건 관리 고도화 | 완료 | 사진 업로드 검증, 태그 관리, 위치 이동 이력 조회 UI, 특정 위치 하위 물건 조회, 최근 확인일 업데이트 구현 |
| Phase 5. 배포 준비 | 완료 | 개발/운영 Docker Compose, 운영용 Nginx, Gunicorn, 정적/미디어 파일 볼륨, 환경 변수 예시, README 실행 안내 구현 |

현재 검증 결과:

- `frontend`에서 `npm.cmd run build` 성공
- `backend/items/views.py` 문법 확인 성공
- `backend/config/settings.py` 문법 확인 성공
- 백엔드 Python 파일 40개 문법 파싱 성공
- `docker compose --env-file .env.example -f docker-compose.yml config --quiet` 성공
- `docker compose --env-file .env.example -f docker-compose.prod.yml config --quiet` 성공
- 면접용 기술 스택 설명 문서 `INTERVIEW_TECH_STACK_GUIDE.md` 작성 완료
- 면접 발표용 PPT `outputs/home-inventory-map-interview-tech-stack.pptx` 작성 완료
- PPT는 12장으로 렌더링 확인, PowerPoint 패키지 내 슬라이드 수와 한글 글꼴 정보 확인 완료
- 전체 컨테이너 실행 검증은 아직 미완료
- 로컬 Python 환경에 Django가 설치되어 있지 않아 `python manage.py check`는 미완료
- 앱 브라우저 도구가 현재 세션에 노출되지 않아 화면 클릭 검증은 미완료

최근 반영된 사용자 흐름:

- 로그인 후 집/도면이 있으면 `물건 검색`을 첫 화면으로, 집 또는 도면이 없으면 `집/도면`을 첫 화면으로 보여준다.
- 포트폴리오 확인용으로 로그인 화면에 테스트 계정 `test / test1234` 안내와 자동 입력 버튼을 표시한다.
- 집을 추가하면 해당 집이 자동 선택되고, 기본 도면이 자동 생성된 뒤 도면 편집 화면으로 이동한다.
- 집/도면 페이지의 집 목록에서 집 카드를 클릭하면 우측 도면 목록이 해당 집 기준으로 즉시 바뀐다.
- 집/도면 페이지는 마지막으로 선택한 도면의 집과 도면 카드를 다시 선택된 상태로 보여준다.
- 도면 관리 화면에서는 집을 선택한 뒤 버튼 하나로 층/도면을 추가한다.
- 도면 관리 화면의 도면 카드를 클릭하면 해당 도면 편집 화면으로 이동한다.
- 도면 이름은 직접 입력하지 않고 선택된 집 이름을 기준으로 자동 생성한다.
- 도면 너비/높이는 처음에 직접 입력하지 않고 기본값으로 시작한다.
- 도면 편집 중 사각형 위치가 도면 범위를 넘어가면 도면 크기를 자동으로 넓힌다.
- 사각형 추가 시 사용자는 이름만 입력하고 코드는 자동 생성한다.
- 도면 사각형 타입은 `방`과 `가구`를 중심으로 사용한다.
- 선택 위치에서 타입을 바꾸면 별도 저장 버튼 없이 바로 반영된다.
- 도면에서는 가구 사각형이 방 사각형 위에 표시된다.
- 사각형을 이동하거나 크기를 조절할 때 가까운 도형/도면 경계에 맞춰 자동 정렬된다.
- 가구 사각형이 방 사각형 안에 완전히 들어가면 해당 방이 자동으로 상위 위치가 된다.
- 선택 위치 패널에서는 X/Y 좌표를 노출하지 않는다.
- 가구를 선택하면 `칸 추가` 버튼으로 서랍 층 같은 하위 칸을 만들 수 있다. 처음 누르면 1층/2층으로 나뉘고, 이후 한 칸씩 추가된다.
- 도면 편집 상단에서 도면 삭제와 사각형 추가를 바로 실행할 수 있다.
- 왼쪽 패널은 사각형 생성 폼 대신 방 > 가구 > 칸 구조의 폴더형 위치 목록만 보여준다.
- 선택 위치 패널 맨 아래 삭제 버튼 또는 키보드 Delete 키로 선택한 위치를 삭제할 수 있다.
- 가구의 칸 목록에서는 각 칸 오른쪽의 쓰레기통 아이콘으로 해당 칸만 삭제할 수 있다.
- 칸을 삭제할 때는 확인창을 한 번 거친다.
- 로그인 후에는 집/도면이 있으면 `물건 검색`을 첫 화면으로, 집 또는 도면이 없으면 `집/도면`을 첫 화면으로 보여준다.
- 메뉴 순서는 `물건`, `도면 편집`, `위치`, `집/도면`이다.
- 도면 삭제는 `집/도면` 페이지의 도면 목록에서 확인창을 거친 뒤 실행한다.
- 도면 편집 화면에서는 도면 생성/삭제를 하지 않고 사각형 추가만 한다.
- 도면 편집의 배치 영역에서는 도면 크기 숫자를 표시하지 않는다.
- 도면 편집의 배치 영역은 마우스 휠 위로 확대, 아래로 축소한다.
- 도면 편집의 배치 영역은 사각형을 좌우상하로 끌면 CAD 도면처럼 표시 범위가 자동으로 확장된다.
- 도면 편집의 배치 영역은 스크롤바 없이 흰 화면만 보이며, 흰 배경을 드래그해 도면을 이동한다.
- 도면 편집의 배치 영역에서 방/가구 사각형을 클릭해 드래그하면 배경 이동보다 사각형 이동이 우선된다.
- 도면 편집의 배치 영역에서 선택된 방/가구 사각형은 방향키로 1px씩, Shift+방향키로 10px씩 부드럽게 이동하고, 서버 저장은 키 입력이 잠시 멈춘 뒤 반영된다.
- 도면 편집의 배치 영역은 방/가구가 도면 경계를 10px 넘어서기 전까지 표시 범위를 확장하지 않는다.
- 방과 가구 사각형에는 최소/최대 크기 제한을 둔다.
- 도면 편집의 선택 위치 패널은 화면 높이를 넘으면 내부 스크롤로 물건 목록을 보여준다.
- 도면 편집의 선택 위치 패널에는 잠금 버튼이 있고, 잠긴 방/가구는 실선으로 보이며 드래그/방향키 이동과 크기 조절이 되지 않는다.
- 잠기지 않은 방/가구는 점선으로 표시한다.
- 도면 편집 상단에서 선택된 도면의 이름을 변경할 수 있다.
- 도면 편집 화면은 마지막으로 선택한 도면을 기억해 다음 진입 시 우선 선택한다.
- 도면 편집의 선택 위치 패널은 이름을 타입보다 먼저 보여주고 위치 코드는 숨긴다.
- 도면 편집 상단의 초록 버튼은 방을 추가하고, 노란 버튼은 가구를 추가한다.
- 도면 편집에서 잘못된 임시 사각형 좌표가 생겨도 배치 화면이 흰 화면으로 깨지지 않도록 좌표 검증을 강화했다.
- 자동정렬은 방은 방끼리, 가구는 가구끼리만 작동한다.
- 물건 목록은 물건, 위치, 수량, 마지막 검색일자를 중심으로 보여준다.
- 물건 검색 화면은 평소 목록 중심으로 보이고, `물건 추가`를 누르면 등록 패널이 부드럽게 열린다.
- 물건 검색 화면에서는 CSV 내보내기 버튼과 하위 위치 포함 체크박스를 표시하지 않는다.
- 물건 목록에서 항목을 클릭하면 같은 패널에서 상세정보를 보고 수정할 수 있다.
- 물건 수정 패널 밖의 빈 공간을 클릭하면 패널이 닫히며, 수정사항이 있으면 저장 여부를 먼저 확인한다.
- 물건 수정 패널 하단의 `물건 삭제` 버튼 또는 목록 행의 쓰레기통 버튼으로 물건을 삭제할 수 있다.
- 물건 수정에서 위치를 바꾸고 저장하면 위치 이동 이력이 자동으로 생성된다.
- 물건 목록과 물건 수정의 이동 이력은 항목이 많아지면 내부 스크롤로 보여준다.
- 물건 등록/수정에는 구매일자를 입력할 수 있고 상태 입력은 화면에서 숨긴다.
- 물건 등록을 열면 구매일자는 오늘 날짜로 기본 설정된다.
- 물건 등록에서 카테고리는 드롭다운 안의 `새 카테고리 추가`로 만들고, 태그는 `#태그` 형식으로 입력하면 자동 저장된다.
- 동일한 이름의 물건을 등록하려 하면 기존 물건의 위치/수량/카테고리를 보여준 뒤 확인을 받는다.
- 검색 필터가 있는 물건 검색 결과는 마지막 검색일자를 자동으로 갱신한다.
- 물건 검색에서 태그는 드롭다운이 아니라 검색 입력으로 찾고, 위치는 계층형 드롭다운으로 선택한다.
- 위치 선택은 처음에 방만 보여주고 펼치기 버튼으로 가구/칸을 연다.
- 위치 선택 UI는 접힌 드롭다운으로 보이며, 방을 클릭하면 선택과 함께 하위 위치가 펼쳐진다.
- 물건 검색에서 위치를 선택하면 하위 위치까지 자동으로 포함해 검색한다.
- 마지막 검색일자는 검색어가 1초 동안 변하지 않은 뒤, 해당 검색어 결과에 대해서만 갱신된다.
- 마지막 검색일자 갱신 결과는 검색 목록과 전체 목록 캐시에 함께 반영된다.
- 물건 검색 목록에서 물건을 클릭해 수정 패널을 연 뒤 1초가 지나면 해당 물건의 마지막 검색일자를 서버 시간으로 자동 갱신한다.
- 카테고리/위치/태그 필터만 바꾸는 조회는 마지막 검색일자를 갱신하지 않는다.
- 물건 등록/수정 패널에서 JPG, PNG, GIF, WEBP 사진만 선택하고 미리볼 수 있으며, 저장 시 서버에서도 실제 이미지 여부를 검증한다.
- 물건 상세 패널에서 위치 이동 이력을 시간순으로 확인할 수 있다.
- 위치 페이지는 위치 생성 폼 대신 집/도면/위치 드롭다운으로 조회하고, 선택 위치 아래에 포함된 모든 물건을 보여준다.
- 위치 페이지의 포함된 물건 목록은 항목이 많아지면 내부 스크롤로 보여준다.
- 각 페이지 제목 아래의 설명 문구는 표시하지 않는다.
- 운영 실행은 `docker-compose.prod.yml`과 Nginx를 통해 프론트엔드, API, Admin, 정적 파일, 업로드 파일을 한 포트에서 제공한다.
- `.env.example`에 개발/운영에서 바꿔야 하는 환경 변수 예시를 제공한다.
- 비밀번호 찾기 화면에서 기존 비밀번호 입력 없이 이메일로 6자리 인증 코드를 받고 새 비밀번호를 설정할 수 있다.
- 비밀번호 찾기 이메일 발송은 SMTP 환경 변수를 통해 설정한다.

진행 관리 원칙:

- 앞으로 기능을 추가하거나 구조를 바꾸면 이 `PLAN.md`의 진행 현황과 해당 Phase 내용을 함께 갱신한다.
- 이미 완료된 Phase라도 구현 방식이 바뀌면 “실제 구현 내용” 항목을 최신 상태로 수정한다.
- 실행 또는 검증에 실패한 내용은 숨기지 않고 “확인 필요”로 남긴다.

## 1. 서비스 개요

Home Inventory Map은 집 안의 물건 위치를 도면과 계층형 위치 구조로 관리하는 개인 물건 위치 관리 서비스다.

사용자는 집, 도면, 방, 구역, 가구, 서랍, 칸 단위로 위치 구조를 만들고 각 물건을 특정 위치에 등록한다. 이후 물건명, 태그, 카테고리, 위치 코드로 빠르게 검색할 수 있다.

예시:

```text
우리집 > 1층 도면 > 거실 > A구역 > 서랍장 1 > 3번째 칸 > 여권
위치 코드: LIVING-A-1-3
```

## 2. 기술 스택

### Backend

- Django
- Django REST Framework
- Django Admin
- PostgreSQL

### Frontend

- React
- TypeScript
- Vite
- React Router
- TanStack Query
- Zustand 또는 React Context
- 현재 구현: SVG 기반 도면 편집기
- 향후 검토: Konva.js 또는 Fabric.js

### Database

- PostgreSQL
- 초기 도면 좌표는 `JSONB` 필드에 저장
- 위치 트리는 self-referencing foreign key로 구성

### Deployment

- Docker
- Docker Compose
- Nginx
- 운영 DB는 PostgreSQL 컨테이너 또는 외부 Managed PostgreSQL 사용

## 3. MVP 목표

초기 목표는 정밀 CAD 도구가 아니라, 물건을 빠르게 찾을 수 있는 공간 기반 인벤토리 서비스다.

MVP에서 반드시 완성할 기능:

- 회원가입 및 로그인
- 집과 도면 생성
- 방, 구역, 가구, 칸으로 이어지는 위치 트리 생성
- 위치 코드 자동 생성
- 물건 등록 및 위치 지정
- 물건명, 태그, 카테고리, 위치 코드 검색
- 특정 위치 하위의 모든 물건 조회
- 물건 위치 이동 이력 저장
- React 화면에서 사각형 기반 방과 구역 표시
- Docker Compose로 로컬 실행

MVP에서 제외할 기능:

- CAD 수준의 정밀 도면 편집
- 3D 도면
- 실시간 공동 편집
- AI 물건 인식
- AR 위치 표시
- 복잡한 공유 권한
- QR 코드 자동 출력 시스템

## 4. 시스템 구조

```text
React + TypeScript
        |
        | REST API
        v
Django REST Framework
        |
        v
PostgreSQL
```

Docker 구성:

```text
docker-compose.yml
 ├─ backend: Django + DRF
 ├─ frontend: React build or Vite dev server
 ├─ db: PostgreSQL
 └─ nginx: reverse proxy, production only
```

권장 프로젝트 구조:

```text
home-inventory-map/
 ├─ backend/
 │   ├─ config/
 │   ├─ accounts/
 │   ├─ homes/
 │   ├─ locations/
 │   ├─ items/
 │   ├─ media/
 │   ├─ manage.py
 │   └─ requirements.txt
 ├─ frontend/
 │   ├─ src/
 │   │   ├─ api/
 │   │   ├─ components/
 │   │   ├─ features/
 │   │   ├─ pages/
 │   │   ├─ stores/
 │   │   └─ types/
 │   ├─ package.json
 │   └─ dist/
 ├─ docker-compose.yml
 ├─ .env.example
 └─ README.md
```

## 5. 핵심 도메인 모델

### User

Django 기본 User 또는 커스텀 User를 사용한다.

필드:

- id
- email
- password
- nickname
- created_at
- updated_at

### Home

사용자가 관리하는 집 단위다.

필드:

- id
- owner
- name
- address_optional
- created_at
- updated_at

### FloorPlan

집 안의 도면 단위다. 1층, 2층, 방별 도면처럼 확장할 수 있다.

필드:

- id
- home
- name
- width
- height
- unit
- background_image
- created_at
- updated_at

### LocationNode

위치 구조의 핵심 모델이다. 방, 구역, 가구, 서랍, 칸을 모두 하나의 트리로 관리한다.

필드:

- id
- home
- floor_plan
- parent
- node_type
- code
- full_code
- name
- path
- level
- geometry_json
- metadata_json
- sort_order
- created_at
- updated_at

node_type:

- HOME
- FLOOR
- ROOM
- ZONE
- FURNITURE
- COMPARTMENT
- BOX
- CUSTOM

제약:

- 같은 parent 아래에서 `code`는 중복될 수 없다.
- `full_code`는 부모 코드와 현재 코드를 조합해서 생성한다.
- 노드 삭제 시 하위 노드와 연결된 물건 처리 정책을 정해야 한다.

### Category

물건 분류다.

필드:

- id
- owner
- name
- created_at
- updated_at

### Item

사용자가 등록한 물건이다.

필드:

- id
- owner
- name
- category
- description
- quantity
- current_location_node
- photo
- purchase_price
- purchase_date
- status
- last_checked_at
- created_at
- updated_at

### Tag

물건 검색용 태그다.

필드:

- id
- owner
- name
- created_at

### ItemTag

물건과 태그의 다대다 연결 테이블이다.

필드:

- id
- item
- tag

### ItemLocationHistory

물건 위치 이동 이력을 저장한다.

필드:

- id
- item
- from_location_node
- to_location_node
- memo
- moved_at
- created_by
- created_at

## 6. 주요 API 계획

### 인증 API

| Method | URL | 설명 |
|---|---|---|
| POST | `/api/auth/register/` | 회원가입 |
| GET | `/api/auth/csrf/` | 세션 인증용 CSRF 쿠키 발급 |
| POST | `/api/auth/login/` | 로그인 |
| POST | `/api/auth/logout/` | 로그아웃 |
| GET | `/api/auth/me/` | 내 정보 조회 |

초기에는 Django Session 인증 또는 JWT 중 하나를 선택한다. 웹 MVP만 우선하면 Session 인증으로 시작해도 된다. 모바일 앱 확장을 빠르게 고려한다면 JWT를 선택한다.

### Home API

| Method | URL | 설명 |
|---|---|---|
| POST | `/api/homes/` | 집 등록 |
| GET | `/api/homes/` | 내 집 목록 조회 |
| GET | `/api/homes/{id}/` | 집 상세 조회 |
| PATCH | `/api/homes/{id}/` | 집 수정 |
| DELETE | `/api/homes/{id}/` | 집 삭제 |

### FloorPlan API

| Method | URL | 설명 |
|---|---|---|
| POST | `/api/floor-plans/` | 도면 생성 |
| GET | `/api/homes/{home_id}/floor-plans/` | 집의 도면 목록 조회 |
| GET | `/api/floor-plans/{id}/` | 도면 상세 조회 |
| PATCH | `/api/floor-plans/{id}/` | 도면 수정 |
| DELETE | `/api/floor-plans/{id}/` | 도면 삭제 |

### LocationNode API

| Method | URL | 설명 |
|---|---|---|
| POST | `/api/location-nodes/` | 위치 노드 생성 |
| GET | `/api/floor-plans/{id}/location-nodes/` | 도면의 위치 노드 목록 조회 |
| GET | `/api/location-nodes/{id}/tree/` | 하위 위치 트리 조회 |
| PATCH | `/api/location-nodes/{id}/` | 위치 노드 수정 |
| DELETE | `/api/location-nodes/{id}/` | 위치 노드 삭제 |

### Item API

| Method | URL | 설명 |
|---|---|---|
| POST | `/api/items/` | 물건 등록 |
| GET | `/api/items/` | 물건 목록 검색 |
| GET | `/api/items/{id}/` | 물건 상세 조회 |
| PATCH | `/api/items/{id}/` | 물건 수정 |
| DELETE | `/api/items/{id}/` | 물건 삭제 |
| POST | `/api/items/{id}/move/` | 물건 위치 이동 |
| GET | `/api/items/{id}/history/` | 물건 위치 이동 이력 조회 |

검색 파라미터 예시:

```text
GET /api/items/?q=여권
GET /api/items/?category=문서
GET /api/items/?tag=중요문서
GET /api/items/?location_code=A-1-3
GET /api/items/?location_node_id=10&include_children=true
```

## 7. 프론트엔드 화면 계획

### 필수 화면

- 로그인
- 회원가입
- 집 목록
- 도면 목록
- 도면 편집 화면
- 위치별 물건 조회 화면
- 물건 목록 및 검색 화면
- 물건 등록/수정 화면
- 물건 상세 화면
- 위치 이동 이력 화면

### 도면 편집 화면 구성

```text
상단 툴바
 ├─ 선택
 ├─ 방 추가
 ├─ 구역 추가
 ├─ 가구 추가
 └─ 저장

왼쪽 패널
 └─ 위치 트리

중앙
 └─ 캔버스 도면

오른쪽 패널
 ├─ 선택한 위치 정보
 ├─ 해당 위치의 물건 목록
 └─ 위치 코드
```

### 프론트엔드 상태 관리

관리해야 할 주요 상태:

- 현재 선택된 집
- 현재 선택된 도면
- 위치 노드 트리
- 캔버스 도형 목록
- 현재 선택된 도형
- 저장되지 않은 변경사항
- 검색 조건
- 물건 목록

서버 데이터는 TanStack Query로 관리하고, 캔버스 편집 중인 임시 상태는 Zustand 또는 컴포넌트 상태로 관리한다.

## 8. Docker 계획

### 로컬 개발용 컨테이너

```text
backend
frontend
db
```

로컬 실행 목표:

```bash
docker compose up
```

실행 후 접근:

```text
Frontend: http://localhost:5173
Backend API: http://localhost:8000/api/
Django Admin: http://localhost:8000/admin/
PostgreSQL: localhost:5432
```

### 환경 변수

`.env.example`에 포함할 값:

```text
DJANGO_SECRET_KEY=
DJANGO_DEBUG=
DJANGO_ALLOWED_HOSTS=
DATABASE_URL=
POSTGRES_DB=
POSTGRES_USER=
POSTGRES_PASSWORD=
CORS_ALLOWED_ORIGINS=
MEDIA_URL=
MEDIA_ROOT=
```

### 운영 배포 흐름

1. React 앱 빌드
2. Django 정적 파일 수집
3. Docker 이미지 생성
4. PostgreSQL 마이그레이션 실행
5. Nginx에서 정적 파일과 API 라우팅
6. 이미지 업로드 저장소 연결

## 9. 개발 단계

### Phase 1. 백엔드 기반 구축

상태: 완료

목표: 도면 UI 없이도 핵심 데이터 구조가 동작하게 만든다.

작업:

- Django 프로젝트 생성
- PostgreSQL 연결
- accounts, homes, locations, items 앱 생성
- User, Home, FloorPlan, LocationNode, Category, Item, Tag, ItemLocationHistory 모델 생성
- Django Admin 등록
- 모델 마이그레이션 작성
- 기본 serializer, viewset, router 구성
- 사용자별 데이터 접근 제한
- 위치 코드 자동 생성 로직 구현
- 물건 검색 API 구현

완료 기준:

- Admin에서 위치 트리와 물건을 등록할 수 있다.
- API로 위치 노드를 생성하고 트리로 조회할 수 있다.
- API로 물건을 등록하고 위치 코드로 검색할 수 있다.

실제 구현 내용:

- `backend/config` Django 프로젝트 설정
- `accounts` 커스텀 User, 회원가입, 로그인, 로그아웃, 내 정보, CSRF API
- `homes` Home, FloorPlan 모델과 API
- `locations` LocationNode 모델, 위치 코드 자동 생성, 트리 조회 API
- `items` Category, Tag, Item, ItemLocationHistory 모델과 API
- 물건 검색 조건: `q`, `category`, `tag`, `location_code`, `location_node_id`, `include_children`, `status`
- 검색 필터가 있는 물건 목록 조회 시 결과 물건의 `last_checked_at` 자동 갱신
- 물건 이동 API: `/api/items/{id}/move/`
- Django Admin 등록
- 초기 마이그레이션 파일 작성
- 백엔드 핵심 테스트 파일 추가

검증:

- Python AST 문법 파싱 성공
- Django 패키지가 로컬 Python에 직접 설치되어 있지 않아 `manage.py check`는 Docker 실행 후 확인 필요

### Phase 2. 프론트엔드 기본 화면

상태: 완료

목표: 사용자가 웹 화면에서 집, 도면, 위치, 물건을 관리할 수 있게 만든다.

작업:

- React + TypeScript 프로젝트 생성
- 라우팅 구성
- API 클라이언트 구성
- 로그인/회원가입 화면 구현
- 집 목록 및 도면 목록 화면 구현
- 물건 목록 및 검색 화면 구현
- 물건 등록/수정 폼 구현
- 위치 트리 패널 구현

완료 기준:

- 사용자가 로그인 후 집과 도면을 만들 수 있다.
- 위치 트리를 만들고 물건을 등록할 수 있다.
- 물건명과 위치 코드로 검색할 수 있다.

실제 구현 내용:

- `frontend` React + TypeScript + Vite 프로젝트 추가
- React Router 라우팅 구성
- TanStack Query 기반 서버 상태 조회
- 세션 인증과 CSRF 쿠키 대응 API 클라이언트 구현
- 로그인/회원가입 화면 구현
- 집/도면 관리 화면 구현
- 집 추가 후 기본 도면 자동 생성 및 편집 화면 이동 구현
- 선택된 집 기준 층/도면 추가 구현
- 도면 이름/초기 크기 입력 제거
- 위치 트리 생성/조회 화면 구현
- 카테고리, 태그, 물건 등록 화면 구현
- 물건 검색 화면 구현
- 로그인 후 기본 시작 화면을 물건 검색으로 변경하되, 집/도면이 없으면 집/도면으로 이동
- 메뉴 순서를 `물건`, `도면 편집`, `위치`, `집/도면`으로 변경
- 로그인 요청 후 네트워크 오류가 표시되더라도 세션이 생성된 경우 내 정보 조회로 사용자 상태 복구
- 물건 목록 컬럼을 물건, 위치, 수량, 마지막 검색일자로 단순화
- 물건 등록 폼 안에서 새 카테고리 생성 가능
- 물건 검색 화면을 목록 중심으로 변경하고, `물건 추가` 클릭 시 등록 패널이 애니메이션으로 열리도록 구현
- 목록에서 물건 클릭 시 등록과 같은 포맷의 수정 패널 표시
- 물건 등록/수정 폼에 구매일자 추가 및 상태 입력 제거
- 물건 등록 태그를 `#태그` 입력 방식으로 변경하고 저장 시 태그 자동 생성
- 동일 이름 물건 등록 시 기존 물건 상세 요약과 함께 확인창 표시
- 물건 검색 태그 필터를 입력 검색으로 변경
- 물건 검색 위치 필터와 등록 위치 선택을 접이식 계층형 선택 UI로 변경
- 위치 선택 시 하위 위치를 자동 포함하도록 API 요청 처리
- 위치 선택 UI를 상시 펼친 트리에서 접힌 드롭다운으로 변경
- 위치 행 클릭 시 하위 위치 펼치기와 선택이 함께 동작하도록 수정
- 마지막 검색일자 갱신 조건을 `q`와 `touch_last_checked=true`가 있는 요청으로 제한
- 검색어 입력이 1초 동안 멈춘 뒤 별도 갱신 요청을 보내도록 프론트엔드 디바운스 처리
- Docker Compose에 `frontend` 서비스 추가

검증:

- `npm.cmd run build` 성공
- Docker Desktop 미실행으로 전체 컨테이너 구동은 확인 필요

### Phase 3. 간단한 도면 편집기

상태: 완료

목표: 정밀 CAD가 아니라 위치를 시각적으로 이해할 수 있는 도면 UI를 만든다.

작업:

- SVG 기반 편집기 구현
- 사각형 방 생성
- 사각형 가구 생성
- 도형 선택 및 정보 수정
- 도형 타입 즉시 변경
- 도형 자동 정렬
- 도형 위치와 크기를 `geometry_json`에 저장
- 도형 클릭 시 해당 위치의 물건 목록 표시
- 가구 아래 칸 단위 위치 생성

완료 기준:

- 사용자가 방과 구역을 사각형으로 표시할 수 있다.
- 도면에서 도형을 클릭하면 해당 위치의 물건이 보인다.
- 새로고침 후에도 도면 위치 정보가 유지된다.

실제 구현 내용:

- `/editor` 도면 편집 화면 추가
- `/floor-plans/{id}/editor` 도면별 편집 화면 추가
- 집/도면 목록에서 편집 화면으로 이동하는 링크 추가
- 위치 노드를 SVG 사각형으로 렌더링
- 사각형 추가, 선택, 드래그 이동, 리사이즈 구현
- 사각형 추가 시 코드 자동 생성
- 도면 사각형 타입을 `방`과 `가구`로 단순화
- 선택 위치 타입 변경 시 저장 버튼 없이 즉시 API 반영
- 가구 사각형이 방 위에 보이도록 렌더링 순서 정렬
- 이동/리사이즈 중 가까운 도형 모서리, 중앙선, 도면 경계에 맞춰지는 스냅 기능 추가
- 가구 사각형이 방 안에 완전히 들어가면 상위 위치와 위치 코드 자동 재계산
- 사각형 좌표가 도면보다 커지거나 음수 영역으로 이동해도 표시 범위가 자동 확장
- 배치 영역 도면 크기 숫자 표시 제거
- 배치 영역 마우스 휠 확대/축소 구현
- 도형 좌표와 크기를 `LocationNode.geometry_json`에 저장
- 선택한 위치의 이름, 코드, 타입, 크기 수정
- 선택 위치 패널에서 X/Y 좌표 숨김
- 가구 선택 시 `칸 추가`로 `COMPARTMENT` 하위 위치 생성
- 도면 편집 상단에 도면 삭제와 사각형 추가 버튼 배치
- 사각형 추가 시 기본 방 사각형을 생성하고 바로 선택해 오른쪽 패널에서 편집
- 왼쪽 패널을 방 > 가구 > 칸 폴더형 트리 목록으로 변경
- 선택 위치 삭제 버튼과 Delete 키 삭제 지원
- 칸 목록 행 오른쪽에 칸 삭제용 쓰레기통 아이콘 추가
- 로그인 후 시작 라우팅을 집/도면 유무에 따라 `물건 검색` 또는 `집/도면`으로 분기
- 내비게이션 순서를 `물건`, `도면 편집`, `위치`, `집/도면`으로 변경
- 도면 삭제 기능을 도면 편집 화면에서 집/도면 페이지 도면 목록으로 이동
- 도면 삭제 전 `정말 "도면이름" 도면을 삭제하시겠습니까?` 확인창 표시
- 도면 편집 화면의 사각형 추가 버튼을 주요 녹색 버튼으로 변경
- 스냅 자동정렬 대상을 같은 타입 사각형으로 제한
- 선택한 위치와 하위 위치에 연결된 물건 목록 표시

구현 방식:

- 별도 캔버스 라이브러리 없이 SVG와 Pointer Event로 구현
- 현재 단계에서는 자유형 polygon, 배경 이미지 오버레이는 제외

검증:

- `npm.cmd run build` 성공
- 앱 브라우저 확인은 Windows 샌드박스 권한 오류로 미완료

### Phase 4. 물건 관리 고도화

목표: 포트폴리오에서 서비스 완성도를 보여줄 기능을 추가한다.

작업:

- 사진 업로드
- 태그 관리
- 위치 이동 이력 UI
- 특정 위치 하위 전체 물건 조회
- CSV 내보내기
- 최근 확인일 업데이트

완료 기준:

- 물건의 위치 변경 이력이 남는다.
- 특정 구역, 가구, 칸 아래의 모든 물건을 조회할 수 있다.
- 사진과 태그 기반으로 물건 정보를 풍부하게 관리할 수 있다.

실제 구현 내용:

- 물건 등록/수정 패널에 사진 선택, 미리보기, 저장 후 업로드 기능 구현
- `/api/items/{id}/photo/` 사진 업로드 API 구현
- 물건 상세 패널에는 이동 이력만 표시하고, 현재 위치 변경은 수정 폼의 위치 선택으로 처리
- `/api/items/{id}/move/`, `/api/items/{id}/history/` API와 프론트엔드 이동 이력 UI 연결
- 위치 필터에서 선택 위치 아래의 물건까지 자동 조회
- 검색어가 1초 동안 멈춘 뒤 해당 검색어 결과에 대해서만 `last_checked_at` 갱신
- 검색일자 갱신 결과를 검색 목록과 전체 목록 캐시에 함께 반영
- `/api/items/{id}/touch-last-checked/` API와 수정 패널 1초 지연 호출로 클릭한 물건의 `last_checked_at` 갱신
- CSV 내보내기 버튼은 물건 페이지에서 제거

검증:

- `backend/items/views.py` 문법 확인 성공
- `frontend`에서 `npm.cmd run build` 성공

### Phase 5. 배포 준비

목표: Docker 기반으로 실제 배포 가능한 상태를 만든다.

작업:

- Dockerfile 작성
- docker-compose.yml 작성
- 운영용 환경 변수 정리
- CORS, CSRF, Allowed Hosts 설정
- 정적 파일 및 미디어 파일 설정
- Nginx 설정
- 배포 서버 선택
- README 실행 방법 정리

완료 기준:

- 새 환경에서 Docker Compose로 실행할 수 있다.
- README만 보고 로컬 실행과 배포 준비가 가능하다.

실제 구현 내용:

- 개발용 `docker-compose.yml` 유지
- 운영용 `docker-compose.prod.yml` 추가
- 백엔드 컨테이너 기본 실행을 Gunicorn으로 변경
- 운영용 compose에서 마이그레이션, `collectstatic`, Gunicorn 실행을 자동화
- Nginx 이미지에서 React 빌드 결과를 정적 파일로 제공
- Nginx가 `/api/`, `/admin/`을 Django로 프록시하고 `/static/`, `/media/`를 볼륨에서 제공
- Django 설정에 `STATIC_ROOT`, 쿠키 보안 옵션, HSTS 옵션, 프록시 HTTPS 헤더 옵션 추가
- `.env.example` 추가
- `.gitignore` 추가
- README에 개발 실행과 운영 실행 방법 분리 작성

검증:

- `docker compose --env-file .env.example -f docker-compose.prod.yml config --quiet` 성공
- `backend/config/settings.py` 문법 확인 성공
- `frontend`에서 `npm.cmd run build` 성공
- 로컬 Python 환경에 Django가 설치되어 있지 않아 `python manage.py check`는 미완료
- 실제 컨테이너 전체 기동은 Docker Desktop 상태/권한 문제로 미완료

## 10. 테스트 계획

### 백엔드 테스트

- 위치 노드 생성 테스트
- 같은 부모 아래 코드 중복 방지 테스트
- 위치 코드 자동 생성 테스트
- 위치 트리 조회 테스트
- 물건 등록 테스트
- 물건 검색 테스트
- 물건 이동 시 이력 생성 테스트
- 다른 사용자의 데이터 접근 차단 테스트

### 프론트엔드 테스트

- 로그인 후 집 목록 표시
- 물건 검색 동작
- 위치 트리 선택 동작
- 도면 구역 클릭 시 물건 목록 표시
- 물건 등록 폼 검증

### 수동 QA

- 집 생성부터 물건 검색까지 전체 흐름 확인
- 브라우저 새로고침 후 도면 유지 확인
- 모바일 크기에서 주요 화면 깨짐 확인
- Docker로 새로 실행했을 때 초기 구동 확인

## 11. 우선순위

### 1순위

- 데이터 모델
- 위치 트리
- 물건 등록
- 검색 API
- Django Admin

### 2순위

- React 기본 화면
- 위치 트리 UI
- 물건 검색 UI
- 간단한 도면 표시

### 3순위

- 도면 편집 UX 개선
- 사진 업로드
- 태그
- 위치 이동 이력

### 4순위

- QR 코드
- 모바일 앱
- 공유 기능
- 고급 도면 편집

## 12. 핵심 구현 원칙

- 위치 트리와 물건 검색을 먼저 완성한다.
- 도면은 위치를 이해하기 위한 보조 UI로 시작한다.
- 모든 주요 데이터는 사용자 기준으로 격리한다.
- 위치 이동은 현재 위치 변경과 이력 생성을 하나의 흐름으로 처리한다.
- 프론트엔드는 서버 데이터를 기준으로 동작하고, 캔버스 편집 중인 임시 상태만 별도로 관리한다.
- Docker 실행 경험을 초반부터 유지한다.

## 13. 1차 완성 기준

다음이 가능하면 1차 MVP로 본다.

```text
1. 사용자가 로그인할 수 있다.
2. 집과 도면을 만들 수 있다.
3. 방, 구역, 가구, 칸으로 위치 트리를 만들 수 있다.
4. 위치 코드가 자동 생성된다.
5. 물건을 특정 위치에 등록할 수 있다.
6. 물건명 또는 위치 코드로 검색할 수 있다.
7. 물건 위치를 이동하면 이력이 남는다.
8. React 화면에서 사각형 방과 구역을 볼 수 있다.
9. 구역을 클릭하면 해당 위치의 물건 목록이 보인다.
10. Docker Compose로 전체 서비스를 실행할 수 있다.
```
