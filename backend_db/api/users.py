"""
I-Study Beta - 사용자 라우터 (Student / Teacher)
회원가입 · 로그인 · 본인 정보 조회 · Role 기반 보호 엔드포인트
"""

from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from database import get_db
from models import User, UserRole
from schemas import UserSignup, UserLogin, UserResponse, Token
from auth import (
    hash_password, verify_password, create_access_token,
    get_current_user, require_role,
)

router = APIRouter(prefix="/users", tags=["Users"])


# ─────────────────────────────────────────────
# 회원가입
# ─────────────────────────────────────────────

@router.post("/signup", response_model=UserResponse, status_code=status.HTTP_201_CREATED)
def signup(payload: UserSignup, db: Session = Depends(get_db)):
    """
    일반 사용자 회원가입 (학생/지도자).

    - 학생(STUDENT): 일반 가입
    - 지도자(TEACHER): 'student_login_id' 필수.
      해당 학생이 존재해야 하며, 학생의 teacher_id 가 이 지도자로 설정됨.
    """
    if db.query(User).filter(User.login_id == payload.login_id).first():
        raise HTTPException(status_code=400, detail="이미 존재하는 아이디입니다.")

    # 지도자 가입 시 학생 검증
    target_student: Optional[User] = None
    if payload.role == UserRole.TEACHER:
        if not payload.student_login_id:
            raise HTTPException(
                status_code=400,
                detail="학습 지도자는 '관리할 학생 아이디'를 입력해야 합니다.",
            )
        target_student = db.query(User).filter(
            User.login_id == payload.student_login_id,
            User.role == UserRole.STUDENT,
        ).first()
        if not target_student:
            raise HTTPException(
                status_code=400,
                detail=f"학생 아이디 '{payload.student_login_id}' 를 찾을 수 없습니다.",
            )

    user = User(
        login_id=payload.login_id,
        password_hash=hash_password(payload.password),
        name=payload.name,
        role=payload.role,
        is_active=1,   # ⚠️ 운영 시: 관리자 승인 후 활성화하려면 0으로
    )
    db.add(user)
    db.flush()   # user.id 확보

    # 지도자→학생 매칭
    if payload.role == UserRole.TEACHER and target_student is not None:
        target_student.teacher_id = user.id

    db.commit()
    db.refresh(user)
    return user


# ─────────────────────────────────────────────
# 로그인
# ─────────────────────────────────────────────

@router.post("/login", response_model=Token)
def login(payload: UserLogin, db: Session = Depends(get_db)):
    """일반 사용자 로그인 → JWT 발급"""
    user = db.query(User).filter(User.login_id == payload.login_id).first()
    if not user or not verify_password(payload.password, user.password_hash):
        raise HTTPException(status_code=401, detail="아이디 또는 비밀번호가 올바르지 않습니다.")
    if not user.is_active:
        raise HTTPException(status_code=403, detail="관리자 승인 대기 중입니다.")

    token = create_access_token(
        subject=user.login_id,
        account_type="user",
        role=user.role.value,
        user_id=user.id,
    )
    return Token(
        access_token=token,
        account_type="user",
        role=user.role.value,
        name=user.name,
    )


# ─────────────────────────────────────────────
# 본인 정보
# ─────────────────────────────────────────────

@router.get("/me", response_model=UserResponse)
def get_me(current: User = Depends(get_current_user)):
    """로그인된 본인 정보"""
    return current


# ─────────────────────────────────────────────
# Role 기반 보호 엔드포인트 (예시)
# ─────────────────────────────────────────────

@router.get("/student/sessions", tags=["Student"])
def student_sessions(
    current: User = Depends(require_role(UserRole.STUDENT)),
):
    """학생 전용: 본인의 학습 세션 목록 (시선 기록)"""
    # TODO: study_log / head_pose_data 조회 구현
    return {
        "message": f"{current.name}님의 학습 기록",
        "student_id": current.login_id,
        "sessions": [],
    }


@router.get("/teacher/students", tags=["Teacher"])
def teacher_students(
    db: Session = Depends(get_db),
    current: User = Depends(require_role(UserRole.TEACHER)),
):
    """지도자 전용: 소속 학생 목록 (시선 기록 모니터링)"""
    students = db.query(User).filter(
        User.teacher_id == current.id,
        User.role == UserRole.STUDENT,
    ).all()
    return {
        "teacher": current.name,
        "students": [
            {"id": s.id, "login_id": s.login_id, "name": s.name}
            for s in students
        ],
    }
