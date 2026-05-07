"""
I-Study Beta - 시선 임계치 설정 라우터

- GET  /gaze-settings              : 본인의 임계치 조회 (없으면 기본값 자동 생성)
- PUT  /gaze-settings              : 본인의 임계치 저장 (학생 전용)
- GET  /gaze-settings/student/{id} : 지도자/관리자가 매칭 학생의 임계치 조회

데스크톱 앱은 학습 시작 시 GET /gaze-settings 를 호출해
config/settings.py 기본값 대신 본 값을 사용.
"""

from typing import Optional

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from pydantic import BaseModel, Field, ConfigDict

from database import get_db
from models import GazeSettings, User, UserRole
from auth import get_current_user

router = APIRouter(prefix="/gaze-settings", tags=["GazeSettings"])


# ─── Schemas ───

class GazeSettingsBody(BaseModel):
    ear_threshold:         Optional[float] = Field(default=None, ge=0.05, le=0.5)
    eye_closure_threshold: Optional[float] = Field(default=None, ge=1.0, le=30.0)
    yaw_threshold:         Optional[float] = Field(default=None, ge=5.0, le=60.0)
    pitch_threshold:       Optional[float] = Field(default=None, ge=5.0, le=60.0)
    pose_lost_threshold:   Optional[float] = Field(default=None, ge=0.5, le=15.0)
    daze_variance_thr:     Optional[float] = Field(default=None, ge=50.0, le=2000.0)
    daze_duration_sec:     Optional[float] = Field(default=None, ge=0.5, le=15.0)
    alpha_iris:            Optional[float] = Field(default=None, ge=0.0, le=1.0)


class GazeSettingsResponse(BaseModel):
    user_id: int
    ear_threshold: float
    eye_closure_threshold: float
    yaw_threshold: float
    pitch_threshold: float
    pose_lost_threshold: float
    daze_variance_thr: float
    daze_duration_sec: float
    alpha_iris: float

    model_config = ConfigDict(from_attributes=True)


# ─── 헬퍼 ───

def _get_or_create(db: Session, user_id: int) -> GazeSettings:
    s = db.query(GazeSettings).filter(GazeSettings.user_id == user_id).first()
    if s is None:
        s = GazeSettings(user_id=user_id)
        db.add(s)
        db.commit()
        db.refresh(s)
    return s


# ─── Endpoints ───

@router.get("/me", response_model=GazeSettingsResponse)
def get_my_settings(
    db: Session = Depends(get_db),
    current: User = Depends(get_current_user),
):
    """본인의 시선 임계치 조회 (없으면 기본값으로 자동 생성)"""
    return _get_or_create(db, current.id)


@router.put("/me", response_model=GazeSettingsResponse)
def update_my_settings(
    payload: GazeSettingsBody,
    db: Session = Depends(get_db),
    current: User = Depends(get_current_user),
):
    """
    본인의 시선 임계치 저장 (학생 전용).
    값이 None인 필드는 변경하지 않음.
    """
    if current.role != UserRole.STUDENT:
        raise HTTPException(403, "시선 임계치는 학생 본인만 수정할 수 있습니다.")
    s = _get_or_create(db, current.id)
    data = payload.model_dump(exclude_none=True)
    for k, v in data.items():
        setattr(s, k, v)
    db.commit()
    db.refresh(s)
    return s


@router.get("/student/{student_id}", response_model=GazeSettingsResponse)
def get_student_settings(
    student_id: int,
    db: Session = Depends(get_db),
    current: User = Depends(get_current_user),
):
    """지도자/관리자: 매칭된 학생의 임계치 조회"""
    student = db.query(User).filter(
        User.id == student_id, User.role == UserRole.STUDENT
    ).first()
    if not student:
        raise HTTPException(404, "학생을 찾을 수 없습니다.")
    if current.role != UserRole.TEACHER or student.teacher_id != current.id:
        raise HTTPException(403, "해당 학생을 관리할 권한이 없습니다.")
    return _get_or_create(db, student_id)
