"""
I-Study Beta - 일정표 (Schedule) 라우터
- 일정 확인 / 추가 / 삭제 / 완료 토글
- 지도자(Teacher): 매칭된 학생의 일정 조회 (read-only)
"""

from typing import Optional
from datetime import datetime

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session
from pydantic import BaseModel, Field, ConfigDict

from database import get_db
from models import Schedule, User, UserRole
from auth import get_current_user, get_current_user_or_admin

router = APIRouter(prefix="/schedules", tags=["Schedules"])


# ─── Schemas ───

class ScheduleCreate(BaseModel):
    date: str = Field(pattern=r"^\d{4}-\d{2}-\d{2}$")
    start_time: Optional[str] = Field(default=None, pattern=r"^\d{2}:\d{2}$")
    end_time: Optional[str] = Field(default=None, pattern=r"^\d{2}:\d{2}$")
    title: str = Field(min_length=1, max_length=200)
    memo: Optional[str] = None
    color: Optional[str] = "blue"


class ScheduleUpdate(BaseModel):
    is_done: Optional[int] = Field(default=None, ge=0, le=1)


class ScheduleResponse(BaseModel):
    id: int
    date: str
    start_time: Optional[str]
    end_time: Optional[str]
    title: str
    memo: Optional[str]
    color: Optional[str]
    is_done: int = 0
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)


# ─── Helper: 지도자가 해당 학생을 관리하는지 확인 ───

def _ensure_can_view_student(db: Session, account, account_type: str, student_id: int) -> User:
    """Admin은 모든 학생, Teacher는 매칭된 학생만 조회 가능"""
    student = db.query(User).filter(User.id == student_id).first()
    if not student:
        raise HTTPException(404, "학생을 찾을 수 없습니다.")
    if student.role != UserRole.STUDENT:
        raise HTTPException(400, "학생 계정이 아닙니다.")
    if account_type == "admin":
        return student  # Admin은 모든 학생 조회 가능
    if account.role != UserRole.TEACHER or student.teacher_id != account.id:
        raise HTTPException(403, "해당 학생을 관리할 권한이 없습니다.")
    return student


# ─── 본인 일정 (학생/지도자 본인) ───

@router.get("", response_model=list[ScheduleResponse])
def list_schedules(
    date_from: Optional[str] = Query(default=None, pattern=r"^\d{4}-\d{2}-\d{2}$"),
    date_to: Optional[str] = Query(default=None, pattern=r"^\d{4}-\d{2}-\d{2}$"),
    db: Session = Depends(get_db),
    current: User = Depends(get_current_user),
):
    """본인의 일정 조회 (날짜 범위 선택 가능)"""
    q = db.query(Schedule).filter(Schedule.user_id == current.id)
    if date_from:
        q = q.filter(Schedule.date >= date_from)
    if date_to:
        q = q.filter(Schedule.date <= date_to)
    return q.order_by(Schedule.date.asc(), Schedule.start_time.asc()).all()


@router.post("", response_model=ScheduleResponse, status_code=201)
def add_schedule(
    payload: ScheduleCreate,
    db: Session = Depends(get_db),
    current: User = Depends(get_current_user),
):
    """일정 추가 (학생만 가능)"""
    if current.role != UserRole.STUDENT:
        raise HTTPException(403, "일정은 학생 본인만 추가할 수 있습니다.")
    item = Schedule(
        user_id=current.id,
        date=payload.date,
        start_time=payload.start_time,
        end_time=payload.end_time,
        title=payload.title,
        memo=payload.memo,
        color=payload.color or "blue",
        is_done=0,
    )
    db.add(item)
    db.commit()
    db.refresh(item)
    return item


@router.patch("/{schedule_id}", response_model=ScheduleResponse)
def update_schedule(
    schedule_id: int,
    payload: ScheduleUpdate,
    db: Session = Depends(get_db),
    current: User = Depends(get_current_user),
):
    """일정 수정 (현재는 완료 여부만)"""
    item = db.query(Schedule).filter(
        Schedule.id == schedule_id,
        Schedule.user_id == current.id,
    ).first()
    if not item:
        raise HTTPException(404, "일정을 찾을 수 없습니다.")
    if current.role != UserRole.STUDENT:
        raise HTTPException(403, "본인의 일정만 수정할 수 있습니다.")
    if payload.is_done is not None:
        item.is_done = int(bool(payload.is_done))
    db.commit()
    db.refresh(item)
    return item


@router.delete("/{schedule_id}")
def delete_schedule(
    schedule_id: int,
    db: Session = Depends(get_db),
    current: User = Depends(get_current_user),
):
    """일정 삭제 (학생 본인만)"""
    if current.role != UserRole.STUDENT:
        raise HTTPException(403, "본인의 일정만 삭제할 수 있습니다.")
    item = db.query(Schedule).filter(
        Schedule.id == schedule_id,
        Schedule.user_id == current.id,
    ).first()
    if not item:
        raise HTTPException(404, "일정을 찾을 수 없습니다.")
    db.delete(item)
    db.commit()
    return {"status": "deleted", "id": schedule_id}


# ─── 지도자: 매칭된 학생의 일정 조회 (read-only) ───

@router.get("/student/{student_id}", response_model=list[ScheduleResponse])
def list_student_schedules(
    student_id: int,
    date_from: Optional[str] = Query(default=None, pattern=r"^\d{4}-\d{2}-\d{2}$"),
    date_to: Optional[str] = Query(default=None, pattern=r"^\d{4}-\d{2}-\d{2}$"),
    db: Session = Depends(get_db),
    account_info: tuple = Depends(get_current_user_or_admin),
):
    """지도자/관리자: 학생의 일정 조회 (read-only)"""
    account, account_type = account_info
    _ensure_can_view_student(db, account, account_type, student_id)
    q = db.query(Schedule).filter(Schedule.user_id == student_id)
    if date_from:
        q = q.filter(Schedule.date >= date_from)
    if date_to:
        q = q.filter(Schedule.date <= date_to)
    return q.order_by(Schedule.date.asc(), Schedule.start_time.asc()).all()
