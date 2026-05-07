"""
I-Study Beta - 관리자 라우터
회원가입(초기 부트스트랩) · 로그인 · 사용자 승인/관리
"""

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from database import get_db
from models import Admin, User, UserRole
from schemas import (
    AdminSignup, AdminLogin, AdminResponse,
    UserResponse, Token,
)
from auth import (
    hash_password, verify_password, create_access_token,
    get_current_admin, require_admin_level,
)

router = APIRouter(prefix="/admins", tags=["Admins"])


# ─────────────────────────────────────────────
# 회원가입
# ─────────────────────────────────────────────

@router.post("/signup", response_model=AdminResponse, status_code=status.HTTP_201_CREATED)
def signup(payload: AdminSignup, db: Session = Depends(get_db)):
    """
    관리자 회원가입.

    ⚠️ 정책 옵션:
    - 부트스트랩: 첫 관리자만 공개 가입, 이후는 최고 관리자가 발급
    - 운영 시 require_admin_level(9) 추가 권장
    """
    if db.query(Admin).filter(Admin.admin_id == payload.admin_id).first():
        raise HTTPException(status_code=400, detail="이미 존재하는 관리자 아이디입니다.")

    admin = Admin(
        admin_id=payload.admin_id,
        password_hash=hash_password(payload.password),
        name=payload.name,
        level=payload.level,
    )
    db.add(admin)
    db.commit()
    db.refresh(admin)
    return admin


# ─────────────────────────────────────────────
# 로그인
# ─────────────────────────────────────────────

@router.post("/login", response_model=Token)
def login(payload: AdminLogin, db: Session = Depends(get_db)):
    """관리자 로그인 → JWT 발급"""
    admin = db.query(Admin).filter(Admin.admin_id == payload.admin_id).first()
    if not admin or not verify_password(payload.password, admin.password_hash):
        raise HTTPException(status_code=401, detail="아이디 또는 비밀번호가 올바르지 않습니다.")

    token = create_access_token(
        subject=admin.admin_id,
        account_type="admin",
        role="ADMIN",
        user_id=admin.id,
    )
    return Token(
        access_token=token,
        account_type="admin",
        role="ADMIN",
        name=admin.name,
    )


# ─────────────────────────────────────────────
# 관리자 전용 엔드포인트
# ─────────────────────────────────────────────

@router.get("/me", response_model=AdminResponse)
def get_me(current: Admin = Depends(get_current_admin)):
    return current


@router.get("/users")
def list_users(
    db: Session = Depends(get_db),
    current: Admin = Depends(get_current_admin),
):
    """
    전체 사용자 목록 (관리자 전용).
    각 사용자에 매칭 정보를 함께 반환:
      - 학생: teacher_id + teacher_login_id + teacher_name (지도자 정보)
      - 지도자: students[] (관리 중인 학생 목록)
    """
    users = db.query(User).order_by(User.created_at.desc()).all()
    by_id = {u.id: u for u in users}

    # 지도자별 학생 목록 사전 계산
    students_of: dict[int, list[dict]] = {}
    for u in users:
        if u.role == UserRole.STUDENT and u.teacher_id:
            students_of.setdefault(u.teacher_id, []).append({
                "id": u.id, "login_id": u.login_id, "name": u.name,
            })

    result = []
    for u in users:
        item = {
            "id": u.id,
            "login_id": u.login_id,
            "name": u.name,
            "role": u.role.value,
            "is_active": u.is_active,
            "teacher_id": u.teacher_id,
            "created_at": u.created_at.isoformat() if u.created_at else None,
            "teacher_login_id": None,
            "teacher_name": None,
            "students": [],
        }
        if u.role == UserRole.STUDENT and u.teacher_id and u.teacher_id in by_id:
            t = by_id[u.teacher_id]
            item["teacher_login_id"] = t.login_id
            item["teacher_name"] = t.name
        elif u.role == UserRole.TEACHER:
            item["students"] = students_of.get(u.id, [])
        result.append(item)
    return result


@router.post("/users/{user_id}/approve")
def approve_user(
    user_id: int,
    db: Session = Depends(get_db),
    current: Admin = Depends(require_admin_level(1)),
):
    """사용자 계정 승인 (is_active=1)"""
    user = db.query(User).filter(User.id == user_id).first()
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    user.is_active = 1
    db.commit()
    return {"status": "approved", "user_id": user_id}


@router.post("/users/{user_id}/reject")
def reject_user(
    user_id: int,
    db: Session = Depends(get_db),
    current: Admin = Depends(require_admin_level(1)),
):
    """사용자 비활성화"""
    user = db.query(User).filter(User.id == user_id).first()
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    user.is_active = 0
    db.commit()
    return {"status": "rejected", "user_id": user_id}


@router.delete("/users/{user_id}")
def delete_user(
    user_id: int,
    db: Session = Depends(get_db),
    current: Admin = Depends(require_admin_level(9)),
):
    """사용자 영구 삭제 (최고 관리자만)"""
    user = db.query(User).filter(User.id == user_id).first()
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    db.delete(user)
    db.commit()
    return {"status": "deleted", "user_id": user_id}


@router.get("/stats")
def system_stats(
    db: Session = Depends(get_db),
    current: Admin = Depends(get_current_admin),
):
    """시스템 통계 (관리자 전용)"""
    return {
        "total_users": db.query(User).count(),
        "students": db.query(User).filter(User.role == UserRole.STUDENT).count(),
        "teachers": db.query(User).filter(User.role == UserRole.TEACHER).count(),
        "pending": db.query(User).filter(User.is_active == 0).count(),
    }
