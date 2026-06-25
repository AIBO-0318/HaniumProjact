"""
가상 학습 데이터 삽입 스크립트 (2026-05-29 ~ 2026-06-04)
실행: python seed_stats.py
"""

import os
import sys
from datetime import datetime, timedelta

PROJECT_ROOT = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, PROJECT_ROOT)
sys.path.insert(0, os.path.join(PROJECT_ROOT, "backend_db"))

from database import SessionLocal
from models import StudySession, User, UserRole

# ── 가상 세션 정의 ──────────────────────────────────────────
# (date, hour, duration_min, focus_score)
RAW = [
    # 5/29 목
    ("2026-05-29", 14, 90,  75.0),
    ("2026-05-29", 16, 60,  85.0),
    # 5/30 금
    ("2026-05-30",  9, 120, 80.0),
    ("2026-05-30", 14, 60,  70.0),
    # 5/31 토
    ("2026-05-31", 10, 180, 88.0),
    ("2026-05-31", 15, 90,  82.0),
    # 6/1  일
    ("2026-06-01", 13, 60,  65.0),
    # 6/2  월
    ("2026-06-02",  9, 90,  78.0),
    ("2026-06-02", 15, 120, 85.0),
    ("2026-06-02", 20, 60,  72.0),
    # 6/3  화
    ("2026-06-03", 10, 150, 90.0),
    ("2026-06-03", 20, 90,  80.0),
    # 6/4  수
    ("2026-06-04", 14, 120, 83.0),
    ("2026-06-04", 19, 60,  76.0),
]


def make_session(user, date_str, hour, duration_min, focus_score):
    focused   = int(duration_min * (focus_score / 100) * 0.88)
    rest      = duration_min - focused
    dazed     = int(rest * 0.55)
    distracted = rest - dazed

    y, m, d   = map(int, date_str.split("-"))
    start     = datetime(y, m, d, hour, 0, 0)
    end       = start + timedelta(minutes=duration_min)

    return StudySession(
        user_id              = user.id,
        login_id             = user.login_id,
        date                 = date_str,
        start_time           = start,
        end_time             = end,
        total_time_seconds   = duration_min * 60,
        focus_time_seconds   = focused * 60,
        duration_min         = duration_min,
        focus_score          = focus_score,
        focused_min          = focused,
        dazed_min            = dazed,
        distracted_min       = distracted,
    )


def main():
    db = SessionLocal()
    try:
        user = db.query(User).filter(User.name == "김우채").first()

        if not user:
            print("❌ 활성화된 STUDENT 계정이 없습니다. 먼저 회원가입 후 관리자 승인을 받으세요.")
            return

        print(f"✅ 대상 사용자: {user.login_id} (id={user.id})")

        dates = set(r[0] for r in RAW)
        deleted = db.query(StudySession).filter(
            StudySession.user_id == user.id,
            StudySession.date.in_(dates),
        ).delete(synchronize_session=False)
        if deleted:
            print(f"🗑  기존 중복 데이터 {deleted}건 삭제")

        sessions = [make_session(user, *r) for r in RAW]
        db.add_all(sessions)
        db.commit()
        print(f"🎉 {len(sessions)}개의 가상 세션 삽입 완료!")

        print("\n[날짜별 요약]")
        for date in sorted(dates):
            rows = [r for r in RAW if r[0] == date]
            total = sum(r[2] for r in rows)
            avg_f = sum(r[3] for r in rows) / len(rows)
            print(f"  {date}  세션수={len(rows)}  총학습={total}분  평균집중={avg_f:.1f}%")

    finally:
        db.close()


if __name__ == "__main__":
    main()
