"""
I-Study Beta - 인증/인가 모듈

- 비밀번호 해싱: bcrypt (passlib)
- 토큰: JWT (python-jose)
- 라우터 보호: FastAPI Dependency

JWT 페이로드 구조:
{
    "sub": "login_id" or "admin_id",
    "account_type": "user" | "admin",
    "role": "STUDENT" | "TEACHER" | "ADMIN",
    "user_id": 1,
    "exp": 1234567890
}
"""

import os
from datetime import datetime, timedelta, timezone
from typing import Optional

from fastapi import Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer
import bcrypt
from jose import jwt, JWTError
from sqlalchemy.orm import Session

from database import get_db
from models import User, Admin, UserRole


# ─────────────────────────────────────────────
# 설정
# ─────────────────────────────────────────────

# ⚠️ 운영 시 환경변수로 교체하세요. (예: os.getenv("JWT_SECRET"))
SECRET_KEY = os.getenv("JWT_SECRET", "i-study-beta-change-this-in-production-please")
ALGORITHM = "HS256"
ACCESS_TOKEN_EXPIRE_MINUTES = 60 * 24  # 24 시간

# 두 라우터(users/admins)에서 모두 토큰 추출에 사용
oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/users/login")


# ─────────────────────────────────────────────
# 비밀번호 해싱 (bcrypt 직접 사용)
# ─────────────────────────────────────────────

def hash_password(plain: str) -> str:
    # bcrypt 는 72바이트 초과 시 에러 → 사전 절단
    pw = plain.encode("utf-8")[:72]
    return bcrypt.hashpw(pw, bcrypt.gensalt()).decode("utf-8")


def verify_password(plain: str, hashed: str) -> bool:
    pw = plain.encode("utf-8")[:72]
    try:
        return bcrypt.checkpw(pw, hashed.encode("utf-8"))
    except Exception:
        return False


# ─────────────────────────────────────────────
# JWT 토큰
# ─────────────────────────────────────────────

def create_access_token(
    *, subject: str, account_type: str, role: str, user_id: int,
    expires_delta: Optional[timedelta] = None
) -> str:
    """
    JWT 발급
    - subject: login_id (user) | admin_id (admin)
    - account_type: "user" | "admin"
    - role: "STUDENT" | "TEACHER" | "ADMIN"
    - user_id: 해당 테이블의 PK
    """
    expire = datetime.now(timezone.utc) + (
        expires_delta or timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
    )
    payload = {
        "sub": subject,
        "account_type": account_type,
        "role": role,
        "user_id": user_id,
        "exp": expire,
    }
    return jwt.encode(payload, SECRET_KEY, algorithm=ALGORITHM)


def decode_token(token: str) -> dict:
    try:
        return jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
    except JWTError as e:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail=f"Invalid token: {e}",
            headers={"WWW-Authenticate": "Bearer"},
        )


# ─────────────────────────────────────────────
# 의존성 (Router Protection)
# ─────────────────────────────────────────────

def get_current_payload(token: str = Depends(oauth2_scheme)) -> dict:
    """토큰 → 페이로드 (모든 보호 엔드포인트의 기본)"""
    return decode_token(token)


def get_current_user(
    payload: dict = Depends(get_current_payload),
    db: Session = Depends(get_db),
) -> User:
    """일반 사용자(Student/Teacher) 인증"""
    if payload.get("account_type") != "user":
        raise HTTPException(status_code=403, detail="User account required")
    user = db.query(User).filter(User.id == payload.get("user_id")).first()
    if not user or not user.is_active:
        raise HTTPException(status_code=401, detail="User not found or inactive")
    return user


def get_current_admin(
    payload: dict = Depends(get_current_payload),
    db: Session = Depends(get_db),
) -> Admin:
    """관리자 인증"""
    if payload.get("account_type") != "admin":
        raise HTTPException(status_code=403, detail="Admin account required")
    admin = db.query(Admin).filter(Admin.id == payload.get("user_id")).first()
    if not admin:
        raise HTTPException(status_code=401, detail="Admin not found")
    return admin


# ─── Role 기반 가드 (사용자 라우터에서) ───

def require_role(*allowed: UserRole):
    """
    특정 Role(Student/Teacher)만 접근 허용하는 의존성 팩토리.

    사용 예:
        @router.get("/me/sessions",
                    dependencies=[Depends(require_role(UserRole.STUDENT))])
    """
    allowed_values = {r.value for r in allowed}

    def _checker(user: User = Depends(get_current_user)) -> User:
        if user.role.value not in allowed_values:
            raise HTTPException(
                status_code=403,
                detail=f"Required role: {', '.join(allowed_values)}",
            )
        return user

    return _checker


def get_current_user_or_admin(
    payload: dict = Depends(get_current_payload),
    db: Session = Depends(get_db),
) -> tuple:
    """
    User 또는 Admin 모두 허용하는 통합 인증.
    반환: (account, account_type)
      - account: User 또는 Admin 인스턴스
      - account_type: "user" | "admin"

    Admin은 최상위 권한이므로 모든 데이터 접근 가능.
    """
    account_type = payload.get("account_type")
    if account_type == "admin":
        admin = db.query(Admin).filter(Admin.id == payload.get("user_id")).first()
        if not admin:
            raise HTTPException(status_code=401, detail="Admin not found")
        return admin, "admin"
    elif account_type == "user":
        user = db.query(User).filter(User.id == payload.get("user_id")).first()
        if not user or not user.is_active:
            raise HTTPException(status_code=401, detail="User not found or inactive")
        return user, "user"
    raise HTTPException(status_code=403, detail="Invalid account type")


def require_admin_level(min_level: int = 1):
    """관리자 등급 가드 (예: level >= 9 → 최고 관리자)"""
    def _checker(admin: Admin = Depends(get_current_admin)) -> Admin:
        if admin.level < min_level:
            raise HTTPException(
                status_code=403,
                detail=f"Admin level >= {min_level} required",
            )
        return admin
    return _checker
