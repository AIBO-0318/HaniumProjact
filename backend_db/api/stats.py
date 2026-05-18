"""
I-Study Beta - 학습 통계 라우터
- 일별 통계 / 주별 통계
"""

from datetime import datetime, timedelta, date as _date
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import func, or_
from sqlalchemy.orm import Session

from database import get_db
from models import StudySession, User, UserRole
from auth import get_current_user_or_admin

router = APIRouter(prefix="/stats", tags=["Stats"])


# ─── 일별 통계 ───

def _resolve_target(db: Session, account, account_type: str, student_id: Optional[int]):
    """권한에 따라 조회 대상 (user_id, login_id) 결정"""
    if account_type == "admin":
        if student_id is None:
            return None, None  # 전체 조회
        target = db.query(User).filter(User.id == student_id).first()
        if not target:
            raise HTTPException(404, "학생을 찾을 수 없습니다.")
        return target.id, target.login_id
    # user (TEACHER or STUDENT)
    if student_id is not None and account.role == UserRole.TEACHER:
        target = db.query(User).filter(
            User.id == student_id, User.teacher_id == account.id
        ).first()
        if not target:
            raise HTTPException(403, "해당 학생을 관리할 권한이 없습니다.")
        return target.id, target.login_id
    return account.id, account.login_id


@router.get("/daily")
def daily_stats(
    days: int = Query(default=7, ge=1, le=90),
    student_id: Optional[int] = Query(default=None, description="Admin/Teacher: 조회할 학생 ID"),
    db: Session = Depends(get_db),
    account_info: tuple = Depends(get_current_user_or_admin),
):
    """
    최근 N일(기본 7일) 학습 통계.
    - 학생: 본인 통계
    - 지도자: 본인 또는 student_id로 매칭된 학생
    - 관리자: student_id로 어떤 학생이든 / 없으면 전체
    """
    account, account_type = account_info
    target_uid, target_lid = _resolve_target(db, account, account_type, student_id)

    today = _date.today()
    start = today - timedelta(days=days - 1)

    q = db.query(
        StudySession.date,
        func.sum(StudySession.duration_min).label("duration_min"),
        func.avg(StudySession.focus_score).label("focus_score"),
        func.sum(StudySession.focused_min).label("focused_min"),
        func.sum(StudySession.dazed_min).label("dazed_min"),
        func.sum(StudySession.distracted_min).label("distracted_min"),
    ).filter(
        StudySession.date >= start.isoformat(),
        StudySession.date <= today.isoformat(),
    )

    if target_uid is not None:
        q = q.filter(
            or_(StudySession.user_id == target_uid,
                StudySession.login_id == target_lid)
        )

    rows = q.group_by(StudySession.date).all()

    by_date = {r.date: r for r in rows}
    result = []
    for i in range(days):
        d = (start + timedelta(days=i)).isoformat()
        r = by_date.get(d)
        result.append({
            "date": d,
            "duration_min": int(r.duration_min or 0) if r else 0,
            "focus_score": round(float(r.focus_score or 0), 1) if r else 0.0,
            "focused_min": int(r.focused_min or 0) if r else 0,
            "dazed_min": int(r.dazed_min or 0) if r else 0,
            "distracted_min": int(r.distracted_min or 0) if r else 0,
        })
    return {"days": days, "items": result}


# ─── 주별 통계 ───

@router.get("/weekly")
def weekly_stats(
    weeks: int = Query(default=4, ge=1, le=26),
    student_id: Optional[int] = Query(default=None, description="Admin/Teacher: 조회할 학생 ID"),
    db: Session = Depends(get_db),
    account_info: tuple = Depends(get_current_user_or_admin),
):
    """
    최근 N주(기본 4주) 학습 통계 (월요일 시작).
    - 관리자: student_id로 어떤 학생이든 / 없으면 전체
    """
    account, account_type = account_info
    target_uid, target_lid = _resolve_target(db, account, account_type, student_id)

    today = _date.today()
    monday = today - timedelta(days=today.weekday())
    start = monday - timedelta(weeks=weeks - 1)

    q = db.query(
        StudySession.date,
        StudySession.duration_min,
        StudySession.focus_score,
    ).filter(
        StudySession.date >= start.isoformat(),
        StudySession.date <= today.isoformat(),
    )

    if target_uid is not None:
        q = q.filter(
            or_(StudySession.user_id == target_uid,
                StudySession.login_id == target_lid)
        )

    rows = q.all()

    # 주별 집계
    buckets = {}
    for i in range(weeks):
        wk_start = start + timedelta(weeks=i)
        wk_end = wk_start + timedelta(days=6)
        key = wk_start.isoformat()
        buckets[key] = {
            "week_start": key,
            "week_end": wk_end.isoformat(),
            "duration_min": 0,
            "_score_sum": 0.0,
            "_score_count": 0,
        }

    for r in rows:
        d = datetime.fromisoformat(r.date).date()
        wk_start = d - timedelta(days=d.weekday())
        key = wk_start.isoformat()
        if key in buckets:
            buckets[key]["duration_min"] += int(r.duration_min or 0)
            buckets[key]["_score_sum"] += float(r.focus_score or 0)
            buckets[key]["_score_count"] += 1

    items = []
    for key in sorted(buckets.keys()):
        b = buckets[key]
        avg = b["_score_sum"] / b["_score_count"] if b["_score_count"] else 0.0
        items.append({
            "week_start": b["week_start"],
            "week_end": b["week_end"],
            "duration_min": b["duration_min"],
            "focus_score": round(avg, 1),
        })

    return {"weeks": weeks, "items": items}


# ─── 개발용: 샘플 세션 기록 삽입 ───

@router.post("/sessions")
def save_session(
    payload: dict,
    db: Session = Depends(get_db),
    account_info: tuple = Depends(get_current_user_or_admin),
):
    """
    학습 세션 저장 (데스크톱 앱이 학습 종료 시 호출).
    payload: {date, duration_min, focus_score, focused_min, dazed_min, distracted_min}
    """
    account, account_type = account_info
    if account_type == "admin":
        raise HTTPException(403, "관리자는 세션을 직접 저장할 수 없습니다.")
    item = StudySession(
        user_id=account.id,
        date=payload.get("date", _date.today().isoformat()),
        duration_min=int(payload.get("duration_min", 0)),
        focus_score=float(payload.get("focus_score", 0.0)),
        focused_min=int(payload.get("focused_min", 0)),
        dazed_min=int(payload.get("dazed_min", 0)),
        distracted_min=int(payload.get("distracted_min", 0)),
    )
    db.add(item)
    db.commit()
    db.refresh(item)
    return {"status": "ok", "id": item.id}
