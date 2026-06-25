"""
I-Study - API Client
백엔드 서버(로컬/LAN 의 Spring Boot, 기본 8000)와 통신하는 HTTP 클라이언트.

서버에 연결할 수 없을 때(오프라인)는 통신 실패 시
빈 결과([] / 0 / False)를 반환하여 앱이 죽지 않도록 한다.
"""

import requests
from typing import List, Tuple, Optional

try:
    from shared.env_config import API_SERVER_URL as API_BASE
except ImportError:
    API_BASE = "http://127.0.0.1:8000"

_TIMEOUT = 5

# ─── 인증 토큰 (로그인 후 set_token 으로 주입) ───
_TOKEN: Optional[str] = None


def set_token(token: Optional[str]) -> None:
    """로그인 성공 후 JWT 토큰을 보관 (이후 /stats/* 요청에 Bearer 헤더로 첨부)"""
    global _TOKEN
    _TOKEN = token


def _auth_headers() -> dict:
    return {"Authorization": f"Bearer {_TOKEN}"} if _TOKEN else {}


# ─── 화이트리스트 (레거시 /api/whitelist — 인증 불필요, 공통 기본 사이트) ───

def get_all_whitelist_urls() -> List[Tuple[int, str, str]]:
    """서버에서 화이트리스트 조회 → [(id, name, url), ...]"""
    try:
        res = requests.get(f"{API_BASE}/api/whitelist", timeout=_TIMEOUT)
        res.raise_for_status()
        return [(item["id"], item["name"], item["url"]) for item in res.json()]
    except Exception:
        return []


def add_whitelist_url(name: str, url: str) -> bool:
    """서버에 화이트리스트 URL 추가"""
    try:
        res = requests.post(
            f"{API_BASE}/api/whitelist",
            json={"name": name, "url": url},
            timeout=_TIMEOUT,
        )
        res.raise_for_status()
        return True
    except Exception:
        return False


def remove_whitelist_url(url_id: int) -> bool:
    """서버에서 화이트리스트 URL 삭제"""
    try:
        res = requests.delete(f"{API_BASE}/api/whitelist/{url_id}", timeout=_TIMEOUT)
        res.raise_for_status()
        return True
    except Exception:
        return False


# ─── 학습 통계 (/stats/* — JWT 인증 필요) ───

def save_session(payload: dict) -> bool:
    """학습 세션 저장 (학습 종료 시). 토큰이 없으면(오프라인) 저장하지 않음."""
    if not _TOKEN:
        return False
    try:
        res = requests.post(
            f"{API_BASE}/stats/sessions",
            json=payload,
            headers=_auth_headers(),
            timeout=_TIMEOUT,
        )
        res.raise_for_status()
        return True
    except Exception:
        return False


def get_study_logs(limit: int = 30) -> List[dict]:
    """본인 학습 세션 원시 기록 (최신순)."""
    if not _TOKEN:
        return []
    try:
        res = requests.get(
            f"{API_BASE}/stats/logs",
            params={"limit": limit},
            headers=_auth_headers(),
            timeout=_TIMEOUT,
        )
        res.raise_for_status()
        return res.json().get("items", [])
    except Exception:
        return []


def get_today_total_focus_time() -> int:
    """오늘 누적 집중 시간(초)."""
    if not _TOKEN:
        return 0
    try:
        res = requests.get(
            f"{API_BASE}/stats/today",
            headers=_auth_headers(),
            timeout=_TIMEOUT,
        )
        res.raise_for_status()
        return int(res.json().get("focus_time_seconds", 0))
    except Exception:
        return 0
