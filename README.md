# Home Inventory Map

집 안의 물건 위치를 위치 트리와 위치 코드로 관리하는 웹 서비스입니다.

현재 구현 범위는 `PLAN.md`의 Phase 1, Phase 2, Phase 3, Phase 4, Phase 5입니다.

## 포함된 기능

- Django 프로젝트 기본 설정
- PostgreSQL 연결
- Django REST Framework 설정
- 세션 기반 회원가입, 로그인, 로그아웃, 내 정보 API
- 집과 도면 CRUD API
- 위치 노드 트리 CRUD API
- 위치 코드 자동 생성
- 물건, 카테고리, 태그 CRUD API
- 물건명, 카테고리, 태그, 위치 코드 검색
- 특정 위치 하위 물건 조회
- 물건 위치 이동 및 이동 이력 저장
- Django Admin 등록
- Docker Compose 로컬 실행 설정
- 운영용 Docker Compose 설정
- Nginx 기반 프론트엔드 정적 파일 제공 및 백엔드 프록시
- 정적 파일과 업로드 파일 볼륨 분리
- 운영용 환경 변수 예시
- React + TypeScript 프론트엔드
- 로그인/회원가입 화면
- 로그인 후 집/도면이 있으면 물건 검색을 첫 화면으로 표시
- 집/도면 관리 화면
- 집 추가 후 기본 도면 자동 생성 및 편집 화면 이동
- 집 목록 클릭으로 우측 도면 목록 선택 변경
- 마지막으로 선택한 도면의 집과 도면 카드 자동 선택
- 선택된 집 기준 층/도면 추가
- 집/도면 화면에서 도면 삭제 확인 후 삭제
- 도면 카드 클릭 후 도면 편집 화면 이동
- 위치별 포함 물건 조회 화면과 내부 스크롤 목록
- 물건 검색/등록 화면
- 목록 중심 물건 화면과 필요 시 열리는 등록/수정 패널
- 물건 목록 클릭 후 상세정보 수정
- 물건 목록 항목이 많아질 때 내부 스크롤 표시
- 빈 공간 클릭 시 수정 패널 닫기와 저장 여부 확인
- 물건 수정 패널 및 목록 행에서 물건 삭제
- 위치 변경 저장 시 이동 이력 자동 생성
- 물건 수정의 이동 이력 항목이 많아질 때 내부 스크롤 표시
- 물건 목록의 물건, 위치, 수량, 마지막 검색일자 표시
- 검색 결과의 마지막 검색일자 자동 갱신
- 검색어가 1초 동안 멈춘 뒤 해당 검색 결과만 마지막 검색일자 갱신
- 등록 폼 안에서 새 카테고리 추가
- `#태그` 입력 방식의 태그 자동 생성
- 동일 이름 물건 등록 전 확인창
- 구매일자 입력
- 태그 검색 입력과 드롭다운형 접이식 위치 검색
- 위치 선택 시 하위 위치 자동 포함 검색
- JPG, PNG, GIF, WEBP 사진 선택, 미리보기, 업로드
- 서버의 실제 이미지 파일 검증
- 위치 이동 이력 조회
- SVG 기반 도면 편집 화면
- 도면 사각형 추가, 선택, 이동, 크기 조절, 저장
- 도면 배치 영역 마우스 휠 확대/축소
- 도면 배치 영역 배경 드래그 이동
- 도면 배치 영역에서 방/가구 드래그 이동 우선 처리
- 도면 경계 10px 밖으로 나가기 전까지 표시 범위 확장 지연
- 도면 배치 영역 스크롤바 제거
- 사각형 드래그에 따른 좌우상하 무제한 표시 범위 확장
- 방/가구 사각형 최소/최대 크기 제한
- 사각형 코드 자동 생성
- 사각형 배치에 따른 도면 크기 자동 확장
- 방/가구 타입 중심의 도면 사각형 관리
- 선택 위치 타입 즉시 반영
- 선택 위치에서 이름을 먼저 표시하고 위치 코드 숨김
- 도면 편집 화면에서 선택된 도면 이름 변경
- 도면 편집 화면에서 마지막 선택 도면 기억
- 가구 사각형을 방 위에 표시
- 같은 타입 도형과 도면 경계 기준 자동 정렬
- 가구가 방 안에 들어가면 상위 위치 자동 할당
- 가구 내부 칸 추가
- 선택 위치 삭제 버튼 및 Delete 키 삭제
- 칸별 쓰레기통 아이콘 삭제
- 칸 삭제 전 확인창 표시
- 방 > 가구 > 칸 폴더형 위치 목록
- 선택한 위치의 하위 물건 목록 표시

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

GET/POST/PATCH/DELETE /api/homes/
GET/POST/PATCH/DELETE /api/floor-plans/
GET/POST/PATCH/DELETE /api/location-nodes/
GET /api/location-nodes/{id}/tree/

GET/POST/PATCH/DELETE /api/categories/
GET/POST/PATCH/DELETE /api/tags/
GET/POST/PATCH/DELETE /api/items/
GET /api/items/export-csv/
POST /api/items/{id}/photo/
POST /api/items/{id}/move/
GET /api/items/{id}/history/
```

검색 예시:

```text
GET /api/items/?q=여권
GET /api/items/?category=문서
GET /api/items/?tag=중요문서
GET /api/items/?location_code=A-1-3
GET /api/items/?location_node_id=10&include_children=true
```
