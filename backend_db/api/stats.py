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


# ─── 시간별 통계 (특정 날짜의 시간대별 집중도) ───

@router.get("/hourly")
def hourly_stats(
    date: str = Query(..., description="조회할 날짜 YYYY-MM-DD"),
    student_id: Optional[int] = Query(default=None, description="Admin/Teacher: 조회할 학생 ID"),
    db: Session = Depends(get_db),
    account_info: tuple = Depends(get_current_user_or_admin),
):
    """
    특정 날짜의 시간대(0~23시)별 평균 집중도.
    - y축: 집중도(0~100), x축: 시간(1시간 단위)
    - start_time 의 시(hour)를 기준으로 버킷팅
    """
    account, account_type = account_info
    target_uid, target_lid = _resolve_target(db, account, account_type, student_id)

    q = db.query(
        StudySession.start_time,
        StudySession.focus_score,
        StudySession.duration_min,
    ).filter(StudySession.date == date)

    if target_uid is not None:
        q = q.filter(
            or_(StudySession.user_id == target_uid,
                StudySession.login_id == target_lid)
        )

    rows = q.all()

    buckets = {
        h: {"score_sum": 0.0, "count": 0, "duration_min": 0}
        for h in range(24)
    }
    for r in rows:
        hour = r.start_time.hour if r.start_time is not None else 0
        b = buckets[hour]
        b["score_sum"] += float(r.focus_score or 0)
        b["count"] += 1
        b["duration_min"] += int(r.duration_min or 0)

    items = []
    for h in range(24):
        b = buckets[h]
        avg = round(b["score_sum"] / b["count"], 1) if b["count"] else 0.0
        items.append({
            "hour": h,
            "focus_score": avg,
            "duration_min": b["duration_min"],
            "has_data": b["count"] > 0,
        })

    return {"date": date, "items": items}


# ─── 주 단위 일별 통계 (선택한 주의 월~일) ───

@router.get("/week-days")
def week_days_stats(
    date: str = Query(..., description="조회할 주에 포함된 날짜 YYYY-MM-DD"),
    student_id: Optional[int] = Query(default=None, description="Admin/Teacher: 조회할 학생 ID"),
    db: Session = Depends(get_db),
    account_info: tuple = Depends(get_current_user_or_admin),
):
    """
    선택한 날짜가 포함된 주(월요일~일요일)의 일별 학습/집중 시간.
    - 막대 2개: 총 학습시간(duration_min), 순수 집중시간(focused_min)
    """
    account, account_type = account_info
    target_uid, target_lid = _resolve_target(db, account, account_type, student_id)

    target = _date.fromisoformat(date)
    monday = target - timedelta(days=target.weekday())
    sunday = monday + timedelta(days=6)

    q = db.query(
        StudySession.date,
        func.sum(StudySession.duration_min).label("duration_min"),
        func.sum(StudySession.focused_min).label("focused_min"),
        func.avg(StudySession.focus_score).label("focus_score"),
    ).filter(
        StudySession.date >= monday.isoformat(),
        StudySession.date <= sunday.isoformat(),
    )

    if target_uid is not None:
        q = q.filter(
            or_(StudySession.user_id == target_uid,
                StudySession.login_id == target_lid)
        )

    rows = q.group_by(StudySession.date).all()
    by_date = {r.date: r for r in rows}

    result = []
    for i in range(7):
        d = (monday + timedelta(days=i)).isoformat()
        r = by_date.get(d)
        result.append({
            "date": d,
            "duration_min": int(r.duration_min or 0) if r else 0,
            "focused_min": int(r.focused_min or 0) if r else 0,
            "focus_score": round(float(r.focus_score or 0), 1) if r else 0.0,
        })

    return {
        "week_start": monday.isoformat(),
        "week_end": sunday.isoformat(),
        "items": result,
    }


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


# ─── 월별 통계 ───

@router.get("/monthly")
def monthly_stats(
    months: int = Query(default=6, ge=1, le=12),
    student_id: Optional[int] = Query(default=None, description="Admin/Teacher: 조회할 학생 ID"),
    db: Session = Depends(get_db),
    account_info: tuple = Depends(get_current_user_or_admin),
):
    """
    최근 N개월(기본 6개월) 학습 통계.
    - 학생: 본인 통계
    - 지도자: 본인 또는 student_id로 매칭된 학생
    - 관리자: student_id로 어떤 학생이든 / 없으면 전체
    """
    account, account_type = account_info
    target_uid, target_lid = _resolve_target(db, account, account_type, student_id)

    today = _date.today()
    # 시작월 1일부터
    start_month = today.month - months + 1
    start_year = today.year
    while start_month <= 0:
        start_month += 12
        start_year -= 1
    start = _date(start_year, start_month, 1)

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

    # 월별 집계
    buckets = {}
    current = start
    while current <= today:
        key = current.strftime("%Y-%m")
        last_day = 28
        for d in (31, 30, 29, 28):
            try:
                _date(current.year, current.month, d)
                last_day = d
                break
            except ValueError:
                continue
        buckets[key] = {
            "month": key,
            "month_start": _date(current.year, current.month, 1).isoformat(),
            "month_end": _date(current.year, current.month, last_day).isoformat(),
            "duration_min": 0,
            "_score_sum": 0.0,
            "_score_count": 0,
        }
        # 다음 달로 이동
        if current.month == 12:
            current = _date(current.year + 1, 1, 1)
        else:
            current = _date(current.year, current.month + 1, 1)

    for r in rows:
        d = datetime.fromisoformat(r.date).date()
        key = d.strftime("%Y-%m")
        if key in buckets:
            buckets[key]["duration_min"] += int(r.duration_min or 0)
            buckets[key]["_score_sum"] += float(r.focus_score or 0)
            buckets[key]["_score_count"] += 1

    items = []
    for key in sorted(buckets.keys()):
        b = buckets[key]
        avg = b["_score_sum"] / b["_score_count"] if b["_score_count"] else 0.0
        items.append({
            "month": b["month"],
            "month_start": b["month_start"],
            "month_end": b["month_end"],
            "duration_min": b["duration_min"],
            "focus_score": round(avg, 1),
        })

    return {"months": months, "items": items}


# ─── 학습 세션 저장 (데스크톱 앱) ───

def _parse_dt(v):
    """ISO 문자열 → datetime (실패/없음 → None)"""
    if not v:
        return None
    try:
        return datetime.fromisoformat(v)
    except (ValueError, TypeError):
        return None


@router.post("/sessions")
def save_session(
    payload: dict,
    db: Session = Depends(get_db),
    account_info: tuple = Depends(get_current_user_or_admin),
):
    """
    학습 세션 저장 (데스크톱 앱이 학습 종료 시 호출).
    payload: {date, start_time, end_time, total_time_seconds, focus_time_seconds,
              duration_min, focus_score, focused_min, dazed_min, distracted_min}
    """
    account, account_type = account_info
    if account_type == "admin":
        raise HTTPException(403, "관리자는 세션을 직접 저장할 수 없습니다.")
    item = StudySession(
        user_id=account.id,
        login_id=account.login_id,
        date=payload.get("date", _date.today().isoformat()),
        start_time=_parse_dt(payload.get("start_time")),
        end_time=_parse_dt(payload.get("end_time")),
        total_time_seconds=int(payload.get("total_time_seconds", 0)),
        focus_time_seconds=int(payload.get("focus_time_seconds", 0)),
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


# ─── 원시 세션 기록 / 오늘 집중 시간 (데스크톱 통계 페이지) ───

@router.get("/logs")
def session_logs(
    limit: int = Query(default=30, ge=1, le=200),
    db: Session = Depends(get_db),
    account_info: tuple = Depends(get_current_user_or_admin),
):
    """
    본인 학습 세션 원시 기록 (최신순).
    데스크톱 stats_page 가 기대하는 키 형식으로 반환.
    """
    account, account_type = account_info
    if account_type == "admin":
        return {"items": []}  # 관리자는 본인 학습 세션이 없음

    rows = (
        db.query(StudySession)
        .filter(
            or_(StudySession.user_id == account.id,
                StudySession.login_id == account.login_id)
        )
        .order_by(StudySession.created_at.desc())
        .limit(limit)
        .all()
    )
    items = [{
        "id": r.id,
        "study_date": r.date,
        "start_time": r.start_time.isoformat() if r.start_time else None,
        "end_time": r.end_time.isoformat() if r.end_time else None,
        "total_time_seconds": r.total_time_seconds or 0,
        "focus_time_seconds": r.focus_time_seconds or 0,
        "duration_min": r.duration_min or 0,
        "focus_score": r.focus_score or 0.0,
        "created_at": r.created_at.isoformat() if r.created_at else None,
    } for r in rows]
    return {"items": items}


@router.get("/today")
def today_focus(
    db: Session = Depends(get_db),
    account_info: tuple = Depends(get_current_user_or_admin),
):
    """오늘 누적 집중 시간(초)."""
    account, account_type = account_info
    if account_type == "admin":
        return {"focus_time_seconds": 0}

    today = _date.today().isoformat()
    total = (
        db.query(func.coalesce(func.sum(StudySession.focus_time_seconds), 0))
        .filter(
            StudySession.date == today,
            or_(StudySession.user_id == account.id,
                StudySession.login_id == account.login_id),
        )
        .scalar()
    )
    return {"focus_time_seconds": int(total or 0)}
