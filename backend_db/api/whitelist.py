"""
I-Study Beta - 화이트리스트 라우터

권한 정책 (요구사항):
- 학생(STUDENT): 조회/수정 모두 불가 (403)
- 지도자(TEACHER): 본인이 매칭된 학생의 화이트리스트 등록/수정/삭제
- 관리자(ADMIN): 전체 조회/관리

엔드포인트:
- GET    /whitelist/effective          : 데스크톱 앱(학생 본인)이 차단 모드에 사용할 '적용 리스트' (기본 + 본인 전용)
                                          → 학생은 조회만 (수정 불가)
- GET    /whitelist/student/{id}        : 지도자/관리자가 학생의 리스트 조회
- POST   /whitelist/student/{id}        : 지도자/관리자가 학생에게 사이트 추가
- DELETE /whitelist/{url_id}            : 지도자/관리자가 본인이 추가한 사이트 삭제
- GET    /whitelist/admin/all           : 관리자 — 전체 리스트
"""

from typing import Optional

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from pydantic import BaseModel, ConfigDict

from database import get_db
from models import WhitelistUrl, User, UserRole, Admin
from auth import get_current_user, get_current_admin
from auth import oauth2_scheme  # 토큰만으로 user/admin 분기
from jose import JWTError
from auth import decode_token

router = APIRouter(prefix="/whitelist", tags=["Whitelist"])


# ─── Schemas ───

class WhitelistCreate(BaseModel):
    name: str
    url: str


class WhitelistResponse(BaseModel):
    id: int
    name: str
    url: str
    user_id: Optional[int] = None
    is_default: bool = False

    model_config = ConfigDict(from_attributes=True)


def _to_resp(w: WhitelistUrl) -> dict:
    return {
        "id": w.id,
        "name": w.name,
        "url": w.url,
        "user_id": w.user_id,
        "is_default": w.user_id is None,
    }


# ─── Helper: 지도자 → 학생 매칭 검증 ───

def _ensure_teacher_owns_student(db: Session, teacher: User, student_id: int) -> User:
    student = db.query(User).filter(
        User.id == student_id, User.role == UserRole.STUDENT
    ).first()
    if not student:
        raise HTTPException(404, "학생을 찾을 수 없습니다.")
    if teacher.role != UserRole.TEACHER or student.teacher_id != teacher.id:
        raise HTTPException(403, "해당 학생을 관리할 권한이 없습니다.")
    return student


# ─── 학생 본인용 (조회만 — 데스크톱 앱이 차단 모드에 사용) ───

@router.get("/effective", response_model=list[WhitelistResponse])
def get_effective_whitelist(
    db: Session = Depends(get_db),
    current: User = Depends(get_current_user),
):
    """
    학생 본인에게 '적용되는' 화이트리스트 (기본 + 본인 전용).
    조회 전용. 학생은 추가/삭제 불가.
    """
    if current.role != UserRole.STUDENT:
        raise HTTPException(403, "학생 본인 전용 엔드포인트입니다.")
    rows = db.query(WhitelistUrl).filter(
        (WhitelistUrl.user_id.is_(None)) | (WhitelistUrl.user_id == current.id)
    ).order_by(WhitelistUrl.created_at.desc()).all()
    return [_to_resp(r) for r in rows]


# ─── 지도자/관리자: 학생별 리스트 관리 ───

@router.get("/student/{student_id}", response_model=list[WhitelistResponse])
def list_student_whitelist(
    student_id: int,
    db: Session = Depends(get_db),
    token: str = Depends(oauth2_scheme),
):
    """지도자(매칭된 학생) / 관리자가 학생의 리스트 조회"""
    payload = _safe_decode(token)
    rows = _student_rows(db, payload, student_id)
    return [_to_resp(r) for r in rows]


@router.post("/student/{student_id}", response_model=WhitelistResponse, status_code=201)
def add_student_whitelist(
    student_id: int,
    body: WhitelistCreate,
    db: Session = Depends(get_db),
    token: str = Depends(oauth2_scheme),
):
    """지도자/관리자: 학생에게 사이트 추가"""
    payload = _safe_decode(token)
    _ensure_role_can_manage(db, payload, student_id)

    if db.query(WhitelistUrl).filter(
        WhitelistUrl.user_id == student_id,
        WhitelistUrl.url == body.url,
    ).first():
        raise HTTPException(400, "이미 등록된 URL입니다.")

    item = WhitelistUrl(name=body.name, url=body.url, user_id=student_id)
    db.add(item)
    db.commit()
    db.refresh(item)
    return _to_resp(item)


@router.delete("/{url_id}")
def delete_whitelist(
    url_id: int,
    db: Session = Depends(get_db),
    token: str = Depends(oauth2_scheme),
):
    """지도자/관리자: 사이트 삭제 (해당 학생을 관리할 권한 필요)"""
    payload = _safe_decode(token)
    item = db.query(WhitelistUrl).filter(WhitelistUrl.id == url_id).first()
    if not item:
        raise HTTPException(404, "URL을 찾을 수 없습니다.")

    # 기본 사이트(user_id=NULL)는 관리자만 삭제 가능
    if item.user_id is None:
        if payload.get("account_type") != "admin":
            raise HTTPException(403, "기본 사이트는 관리자만 삭제할 수 있습니다.")
    else:
        _ensure_role_can_manage(db, payload, item.user_id)

    db.delete(item)
    db.commit()
    return {"status": "deleted", "id": url_id}


# ─── 관리자 전용 ───

@router.get("/admin/all", response_model=list[WhitelistResponse])
def list_all_whitelist(
    db: Session = Depends(get_db),
    current: Admin = Depends(get_current_admin),
):
    """관리자: 전체 화이트리스트 조회"""
    rows = db.query(WhitelistUrl).order_by(WhitelistUrl.created_at.desc()).all()
    return [_to_resp(r) for r in rows]


@router.post("/admin/default", response_model=WhitelistResponse, status_code=201)
def add_default_whitelist(
    body: WhitelistCreate,
    db: Session = Depends(get_db),
    current: Admin = Depends(get_current_admin),
):
    """관리자: 시스템 기본 사이트 추가 (모든 학생 공통)"""
    if db.query(WhitelistUrl).filter(
        WhitelistUrl.user_id.is_(None), WhitelistUrl.url == body.url
    ).first():
        raise HTTPException(400, "이미 등록된 기본 URL입니다.")
    item = WhitelistUrl(name=body.name, url=body.url, user_id=None)
    db.add(item)
    db.commit()
    db.refresh(item)
    return _to_resp(item)


# ─── 내부 헬퍼 ───

def _safe_decode(token: str) -> dict:
    try:
        return decode_token(token)
    except JWTError:
        raise HTTPException(401, "유효하지 않은 토큰입니다.")


def _student_rows(db: Session, payload: dict, student_id: int):
    """지도자(매칭) 또는 관리자만 조회 가능"""
    _ensure_role_can_manage(db, payload, student_id)
    return db.query(WhitelistUrl).filter(
        WhitelistUrl.user_id == student_id
    ).order_by(WhitelistUrl.created_at.desc()).all()


def _ensure_role_can_manage(db: Session, payload: dict, student_id: int):
    """지도자: 자신이 매칭된 학생만 / 관리자: 모두 / 학생: 차단"""
    account_type = payload.get("account_type")
    if account_type == "admin":
        # 학생 존재 검증만
        if not db.query(User).filter(User.id == student_id, User.role == UserRole.STUDENT).first():
            raise HTTPException(404, "학생을 찾을 수 없습니다.")
        return
    if account_type != "user":
        raise HTTPException(403, "권한이 없습니다.")
    role = payload.get("role")
    if role == "STUDENT":
        raise HTTPException(403, "학생은 화이트리스트를 관리할 수 없습니다.")
    if role == "TEACHER":
        teacher_id = payload.get("user_id")
        teacher = db.query(User).filter(User.id == teacher_id).first()
        if not teacher:
            raise HTTPException(403, "권한이 없습니다.")
        _ensure_teacher_owns_student(db, teacher, student_id)
        return
    raise HTTPException(403, "권한이 없습니다.")
