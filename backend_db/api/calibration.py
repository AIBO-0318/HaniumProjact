"""
I-Study Beta - 시야각 초점(캘리브레이션) 라우터

데스크톱 앱과 동일한 방식의 캘리브레이션 결과를 사용자별로 저장한다.
- center_ratio, h_left/right_threshold, v_up/down_threshold, gaze_lost_threshold
- 학생이 웹 /calibration 페이지에서 웹캠 30샘플로 측정 후 PUT
- 데스크톱 앱이 학습 시작 시 GET 해서 GazeTracker.apply_calibration() 에 적용

엔드포인트:
- GET    /calibration/me     본인 캘리브레이션 조회 (없으면 기본값 행 자동 생성)
- PUT    /calibration/me     본인 캘리브레이션 저장
- POST   /calibration/me/reset  기본값으로 초기화
"""
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from pydantic import BaseModel, Field, ConfigDict

from database import get_db
from models import GazeSettings, User, UserRole
from auth import get_current_user

router = APIRouter(prefix="/calibration", tags=["Calibration"])


DEFAULTS = dict(
    center_ratio=0.50,
    h_left_threshold=0.20,
    h_right_threshold=0.80,
    v_up_threshold=0.38,
    v_down_threshold=0.62,
    gaze_lost_threshold=2.0,
)


class CalibrationBody(BaseModel):
    center_ratio:        Optional[float] = Field(default=None, ge=0.0, le=1.0)
    h_left_threshold:    Optional[float] = Field(default=None, ge=0.0, le=1.0)
    h_right_threshold:   Optional[float] = Field(default=None, ge=0.0, le=1.0)
    v_up_threshold:      Optional[float] = Field(default=None, ge=0.0, le=1.0)
    v_down_threshold:    Optional[float] = Field(default=None, ge=0.0, le=1.0)
    gaze_lost_threshold: Optional[float] = Field(default=None, ge=0.3, le=15.0)


class CalibrationOut(BaseModel):
    user_id: int
    center_ratio: float
    h_left_threshold: float
    h_right_threshold: float
    v_up_threshold: float
    v_down_threshold: float
    gaze_lost_threshold: float
    calibrated: int

    model_config = ConfigDict(from_attributes=True)


def _to_out(row: GazeSettings) -> dict:
    return {
        "user_id":             row.user_id,
        "center_ratio":        row.center_ratio if row.center_ratio is not None else 0.5,
        "h_left_threshold":    row.h_left_threshold if row.h_left_threshold is not None else 0.20,
        "h_right_threshold":   row.h_right_threshold if row.h_right_threshold is not None else 0.80,
        "v_up_threshold":      row.v_up_threshold if row.v_up_threshold is not None else 0.38,
        "v_down_threshold":    row.v_down_threshold if row.v_down_threshold is not None else 0.62,
        "gaze_lost_threshold": row.gaze_lost_threshold if row.gaze_lost_threshold is not None else 2.0,
        "calibrated":          row.calibrated if row.calibrated is not None else 0,
    }


def _get_or_create(db: Session, user_id: int) -> GazeSettings:
    row = db.query(GazeSettings).filter(GazeSettings.user_id == user_id).first()
    if row is None:
        row = GazeSettings(user_id=user_id, **DEFAULTS, calibrated=0)
        db.add(row)
        db.commit()
        db.refresh(row)
    return row


@router.get("/me", response_model=CalibrationOut)
def get_my_calibration(
    db: Session = Depends(get_db),
    current: User = Depends(get_current_user),
):
    """본인의 시선 초점 캘리브레이션 값 조회 (없으면 기본값으로 자동 생성)."""
    if current.role != UserRole.STUDENT:
        # 학습자만 본인 캘리브레이션 보유. 지도자/관리자는 별도 엔드포인트로 학생 것을 조회 권장.
        raise HTTPException(403, "학생 본인 전용 엔드포인트입니다.")
    row = _get_or_create(db, current.id)
    return _to_out(row)


@router.put("/me", response_model=CalibrationOut)
def update_my_calibration(
    body: CalibrationBody,
    db: Session = Depends(get_db),
    current: User = Depends(get_current_user),
):
    """본인의 시선 초점 캘리브레이션 값 저장."""
    if current.role != UserRole.STUDENT:
        raise HTTPException(403, "학생 본인 전용 엔드포인트입니다.")
    row = _get_or_create(db, current.id)
    data = body.model_dump(exclude_none=True)

    left  = data.get("h_left_threshold",  row.h_left_threshold or DEFAULTS["h_left_threshold"])
    right = data.get("h_right_threshold", row.h_right_threshold or DEFAULTS["h_right_threshold"])
    up    = data.get("v_up_threshold",    row.v_up_threshold or DEFAULTS["v_up_threshold"])
    down  = data.get("v_down_threshold",  row.v_down_threshold or DEFAULTS["v_down_threshold"])
    if left >= right:
        raise HTTPException(400, "왼쪽 임계값은 오른쪽보다 작아야 합니다.")
    if up >= down:
        raise HTTPException(400, "위쪽 임계값은 아래쪽보다 작아야 합니다.")

    for k, v in data.items():
        setattr(row, k, v)
    row.calibrated = 1
    db.commit()
    db.refresh(row)
    return _to_out(row)


@router.post("/me/reset", response_model=CalibrationOut)
def reset_my_calibration(
    db: Session = Depends(get_db),
    current: User = Depends(get_current_user),
):
    """기본값으로 초기화."""
    if current.role != UserRole.STUDENT:
        raise HTTPException(403, "학생 본인 전용 엔드포인트입니다.")
    row = _get_or_create(db, current.id)
    for k, v in DEFAULTS.items():
        setattr(row, k, v)
    row.calibrated = 0
    db.commit()
    db.refresh(row)
    return _to_out(row)
