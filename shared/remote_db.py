"""
I-Study - 통계 어댑터 (원격 모드)

`ai_core.database.FocusDatabase` 와 동일한 메서드 시그니처를 제공하지만,
로컬 PostgreSQL 직접 연결 대신 `api_client`(HTTP)를 통해 원격 서버와 통신한다.

데스크톱 앱의 `app.db` 를 이 클래스로 교체하면, 통계 페이지 등
`app.db.*` 를 호출하는 UI 코드는 수정 없이 그대로 동작한다.
오프라인(토큰 없음)일 때는 빈 결과/no-op 로 안전하게 동작한다.
"""

from datetime import datetime
from typing import List, Optional

from shared import api_client


class RemoteStatsDB:
    """원격 서버(stats API) 기반 통계 저장/조회 어댑터."""

    # ─── 저장 ───
    def save_study_log(
        self,
        start_time: datetime,
        end_time: datetime,
        total_time_seconds: int,
        focus_time_seconds: int,
        login_id: Optional[str] = None,   # 서버는 토큰으로 본인 식별 → 미사용
        focus_score: Optional[float] = None,
        focused_min: int = 0,
        dazed_min: int = 0,
        distracted_min: int = 0,
    ) -> int:
        duration_min = max(1, int(total_time_seconds) // 60)
        if focus_score is None:
            focus_score = (
                round(focus_time_seconds / total_time_seconds * 100, 1)
                if total_time_seconds > 0 else 0.0
            )
        payload = {
            "date": start_time.date().isoformat() if start_time else None,
            "start_time": start_time.isoformat() if start_time else None,
            "end_time": end_time.isoformat() if end_time else None,
            "total_time_seconds": int(total_time_seconds),
            "focus_time_seconds": int(focus_time_seconds),
            "duration_min": int(duration_min),
            "focus_score": float(focus_score),
            "focused_min": int(focused_min),
            "dazed_min": int(dazed_min),
            "distracted_min": int(distracted_min),
        }
        api_client.save_session(payload)
        return 0  # 원격 모드에서는 행 ID 가 필요 없음

    # ─── 조회 ───
    def get_study_logs(self, limit: int = 30, login_id: Optional[str] = None) -> List[dict]:
        # 서버가 토큰 기준으로 본인 세션만 반환하므로 login_id 인자는 무시
        return api_client.get_study_logs(limit=limit)

    def get_today_total_focus_time(self, login_id: Optional[str] = None) -> int:
        return api_client.get_today_total_focus_time()

    # ─── 생명주기 (인터페이스 호환용) ───
    def close(self):
        pass

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        self.close()
