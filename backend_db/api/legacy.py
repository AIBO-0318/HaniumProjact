"""
I-Study - 데스크톱 앱 호환용 레거시 라우터 (anonymous, /api/* 경로)

데스크톱 앱(`utils/api_client.py`)이 사용하는 단순 엔드포인트.
인증 없이 접근 가능하지만 동일한 PostgreSQL DB(beta 스키마)를 공유한다.

- GET    /api/whitelist          기본 사이트(user_id IS NULL) 목록
- POST   /api/whitelist          기본 사이트 추가
- DELETE /api/whitelist/{id}     기본 사이트 삭제
- GET    /api/calibration        가장 최근에 보정한 학생의 시야각 임계치 (없으면 기본값)
"""
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from sqlalchemy import desc
from pydantic import BaseModel, ConfigDict

from database import get_db
from models import WhitelistUrl, GazeSettings, User, UserRole

router = APIRouter(prefix="/api", tags=["Legacy (desktop)"])


# ─── 화이트리스트 ───

class WhitelistCreate(BaseModel):
    name: str
    url: str


class WhitelistOut(BaseModel):
    id: int
    name: str
    url: str
    model_config = ConfigDict(from_attributes=True)


@router.get("/whitelist", response_model=list[WhitelistOut])
def list_default_whitelist(db: Session = Depends(get_db)):
    """기본(공통) 화이트리스트만 반환 — 데스크톱 '빠른 링크' / 차단 모드용"""
    rows = db.query(WhitelistUrl).filter(
        WhitelistUrl.user_id.is_(None)
    ).order_by(WhitelistUrl.created_at.desc()).all()
    return rows


@router.post("/whitelist", response_model=WhitelistOut, status_code=201)
def add_default_whitelist(body: WhitelistCreate, db: Session = Depends(get_db)):
    """기본 화이트리스트에 사이트 추가 (데스크톱 호환)"""
    if db.query(WhitelistUrl).filter(
        WhitelistUrl.user_id.is_(None), WhitelistUrl.url == body.url
    ).first():
        raise HTTPException(400, "이미 등록된 URL입니다.")
    item = WhitelistUrl(name=body.name, url=body.url, user_id=None)
    db.add(item)
    db.commit()
    db.refresh(item)
    return item


@router.delete("/whitelist/{url_id}")
def delete_default_whitelist(url_id: int, db: Session = Depends(get_db)):
    """기본 화이트리스트에서 삭제"""
    item = db.query(WhitelistUrl).filter(WhitelistUrl.id == url_id).first()
    if not item:
        raise HTTPException(404, "URL을 찾을 수 없습니다.")
    db.delete(item)
    db.commit()
    return {"status": "deleted", "id": url_id}


# ─── 캘리브레이션 ───
# 데스크톱은 단일 사용자 환경 → 가장 최근에 보정한 학생의 값을 반환.
# 키 이름은 데스크톱 GazeTracker.apply_calibration() 시그니처에 맞춤.

DEFAULTS = dict(
    center_ratio=0.50,
    left_threshold=0.20,
    right_threshold=0.80,
    up_threshold=0.38,
    down_threshold=0.62,
    gaze_lost_threshold=2.0,
    eye_closure_threshold=5.0,
    calibrated=0,
)


@router.get("/calibration")
def get_calibration_for_desktop(db: Session = Depends(get_db)):
    """
    가장 최근에 웹에서 보정한 학생의 시야각 임계치를 반환.
    아무도 보정하지 않았으면 기본값 반환.
    데스크톱 `GazeTracker.apply_calibration(dict)` 가 직접 받을 수 있는 형태.
    """
    row = (
        db.query(GazeSettings)
        .filter(GazeSettings.calibrated == 1)
        .order_by(desc(GazeSettings.updated_at))
        .first()
    )
    if row is None:
        return DEFAULTS
    return {
        "center_ratio":         row.center_ratio if row.center_ratio is not None else 0.5,
        "left_threshold":       row.h_left_threshold if row.h_left_threshold is not None else 0.20,
        "right_threshold":      row.h_right_threshold if row.h_right_threshold is not None else 0.80,
        "up_threshold":         row.v_up_threshold if row.v_up_threshold is not None else 0.38,
        "down_threshold":       row.v_down_threshold if row.v_down_threshold is not None else 0.62,
        "gaze_lost_threshold":  row.gaze_lost_threshold if row.gaze_lost_threshold is not None else 2.0,
        "eye_closure_threshold": row.eye_closure_threshold if row.eye_closure_threshold is not None else 5.0,
        "calibrated":           int(row.calibrated or 0),
    }
