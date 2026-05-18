# 권한 구조 수정 기록 (롤백용)

> **작업일**: 2026-05-17  
> **목적**: 관리자(Admin)가 학습관리자/학습자의 데이터를 조회할 수 없던 오류 수정  
> **원칙**: Admin은 최상위 권한 — 하위 역할이 볼 수 있는 모든 데이터에 접근 가능

---

## 수정 전 문제

| API | 문제 |
|-----|------|
| `GET /stats/daily` | Admin 토큰 → 403 거부 (User만 허용) |
| `GET /stats/weekly` | Admin 토큰 → 403 거부 |
| `POST /stats/sessions` | Admin 토큰 → 403 거부 |
| `GET /schedules/student/{id}` | Teacher만 허용, Admin 접근 불가 |

**원인**: `get_current_user()`가 `account_type == "user"`만 허용 → Admin 토큰 전부 차단

---

## 수정된 파일 (3개)

### 1. `auth.py` — 통합 인증 의존성 추가

**추가된 함수**: `get_current_user_or_admin()`

```python
# 160~183행에 추가됨
def get_current_user_or_admin(payload, db) -> tuple:
    """(account, account_type) 반환 — Admin/User 모두 허용"""
```

**롤백**: 160~183행 삭제

---

### 2. `api/stats.py` — Admin 통계 조회 허용

**변경 사항**:
- `from auth import get_current_user` → `from auth import get_current_user_or_admin`
- `_resolve_target()` 헬퍼 함수 추가 (22~39행)
- `daily_stats()`: `get_current_user` → `get_current_user_or_admin` + `student_id` 파라미터
- `weekly_stats()`: 동일 변경
- `save_session()`: Admin은 세션 저장 차단 (403)

**롤백 방법**: 아래 원본으로 복원
```python
# import 원본
from auth import get_current_user

# daily_stats 원본
@router.get("/daily")
def daily_stats(
    days: int = Query(default=7, ge=1, le=90),
    db: Session = Depends(get_db),
    current: User = Depends(get_current_user),
):
    # ... or_(StudySession.user_id == current.id, StudySession.login_id == current.login_id) 로 필터

# weekly_stats, save_session 도 동일하게 get_current_user 사용
```

---

### 3. `api/schedules.py` — Admin 일정 조회 허용

**변경 사항**:
- import에 `get_current_user_or_admin` 추가
- `_ensure_can_view_student()`: `account_type == "admin"` 이면 무조건 통과
- `list_student_schedules()`: `get_current_user` → `get_current_user_or_admin`

**롤백 방법**: 아래 원본으로 복원
```python
# _ensure_can_view_student 원본
def _ensure_can_view_student(db: Session, current: User, student_id: int) -> User:
    student = db.query(User).filter(User.id == student_id).first()
    if not student:
        raise HTTPException(404, "학생을 찾을 수 없습니다.")
    if student.role != UserRole.STUDENT:
        raise HTTPException(400, "학생 계정이 아닙니다.")
    if current.role != UserRole.TEACHER or student.teacher_id != current.id:
        raise HTTPException(403, "해당 학생을 관리할 권한이 없습니다.")
    return student

# list_student_schedules 원본
@router.get("/student/{student_id}")
def list_student_schedules(..., current: User = Depends(get_current_user)):
    _ensure_can_view_student(db, current, student_id)
```

---

## 추가 수정된 파일 (웹 UI)

### 4. `ui_ux/web/pages/main.html` — 관리자 타일 확장

**변경 사항**: ADMIN 타일에 3개 메뉴 추가
- 학생 통계 조회 (`/admin-stats`)
- 학생 일정 조회 (`/teacher-schedule`)
- 화이트리스트 관리 (`/teacher-whitelist`)

**롤백**: ADMIN 배열을 원래 1줄로 복원
```javascript
ADMIN: [
  { href: "/mypage", icon: "🛡️", color: "blue", title: "사용자 관리", desc: "가입 승인 · 사용자 목록" },
],
```

---

### 5. `ui_ux/web/pages/teacher-schedule.html` — Admin 접근 허용

**변경 사항**:
- 역할 체크: `role !== "TEACHER"` → `role !== "TEACHER" && account_type !== "admin"`
- 학생 목록: Admin은 `/admins/users` API에서 전체 학생 조회

**롤백**: `if (Auth.getInfo().role !== "TEACHER") { ... }` 로 복원, `loadStudents()` 원본 복원

---

### 6. `ui_ux/web/pages/teacher-whitelist.html` — Admin 접근 허용

**변경 사항**: teacher-schedule.html과 동일한 패턴 적용

---

### 7. `ui_ux/web/pages/admin-stats.html` — 신규 생성

**설명**: 관리자 전용 학생 통계 조회 페이지
**롤백**: 파일 삭제

---

### 8. `backend_db/main.py` — `/admin-stats` 라우트 추가

**변경 사항**: 167~169행 추가
**롤백**: 해당 3행 삭제

---

## 수정 후 권한 구조

```
Admin (최상위) — 모든 데이터 접근 가능
  ├─ 모든 학생 통계 조회 (student_id 파라미터)
  ├─ 전체 통계 조회 (student_id 없으면 전체)
  ├─ 모든 학생 일정 조회
  ├─ 전체 화이트리스트 관리
  └─ 사용자 승인/거절/삭제
  
Teacher (중간)
  ├─ 본인 통계 조회
  ├─ 매칭된 학생 통계 조회
  ├─ 매칭된 학생 일정 조회
  └─ 매칭된 학생 화이트리스트 관리

Student (최하위)
  ├─ 본인 통계 조회
  ├─ 본인 일정 관리
  └─ 본인 화이트리스트 조회 (수정 불가)
```
