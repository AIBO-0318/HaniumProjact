"""
I-Study Beta - Pydantic Schemas
요청/응답 스키마 정의
"""

from datetime import datetime
from typing import Optional
from pydantic import BaseModel, Field, ConfigDict

from models import UserRole


# ─────────────────────────────────────────────
# 공용 스키마
# ─────────────────────────────────────────────

class Token(BaseModel):
    """JWT 토큰 응답"""
    access_token: str
    token_type: str = "bearer"
    account_type: str    # "user" | "admin"
    role: str            # "STUDENT" | "TEACHER" | "ADMIN"
    name: str


class TokenPayload(BaseModel):
    """JWT 토큰 페이로드 (디코드 후 사용)"""
    sub: str             # login_id 또는 admin_id
    account_type: str    # "user" | "admin"
    role: str            # "STUDENT" | "TEACHER" | "ADMIN"
    user_id: int         # PK
    exp: int


# ─────────────────────────────────────────────
# 일반 사용자 (Student / Teacher)
# ─────────────────────────────────────────────

class UserSignup(BaseModel):
    """회원가입 요청"""
    login_id: str = Field(min_length=4, max_length=32, pattern=r"^[a-zA-Z0-9_]+$")
    password: str = Field(min_length=6, max_length=64)
    name: str = Field(min_length=1, max_length=50)
    role: UserRole = UserRole.STUDENT
    # ⚠️ role=TEACHER 일 때 필수: 매칭할 학생의 login_id
    student_login_id: Optional[str] = Field(
        default=None, min_length=4, max_length=32, pattern=r"^[a-zA-Z0-9_]+$"
    )


class UserLogin(BaseModel):
    """로그인 요청"""
    login_id: str
    password: str


class UserResponse(BaseModel):
    """사용자 정보 응답"""
    id: int
    login_id: str
    name: str
    role: UserRole
    is_active: int
    teacher_id: Optional[int] = None
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)


# ─────────────────────────────────────────────
# 관리자
# ─────────────────────────────────────────────

class AdminSignup(BaseModel):
    """관리자 회원가입"""
    admin_id: str = Field(min_length=4, max_length=32, pattern=r"^[a-zA-Z0-9_]+$")
    password: str = Field(min_length=8, max_length=64)
    name: str = Field(min_length=1, max_length=50)
    level: int = Field(default=1, ge=1, le=9)


class AdminLogin(BaseModel):
    """관리자 로그인"""
    admin_id: str
    password: str


class AdminResponse(BaseModel):
    """관리자 정보 응답"""
    id: int
    admin_id: str
    name: str
    level: int
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)
