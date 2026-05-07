"""
I-Study - API Client
FastAPI 서버(localhost:8000)와 통신하는 HTTP 클라이언트
서버 연결 실패 시 로컬 SQLite DB를 폴백으로 사용합니다.
"""

import requests
from typing import List, Tuple

API_BASE = "http://localhost:8000"


def _get_local_db():
    """로컬 DB 인스턴스 반환 (폴백용)"""
    from ai_core.database import FocusDatabase
    return FocusDatabase()


def get_all_whitelist_urls() -> List[Tuple[int, str, str]]:
    """서버에서 화이트리스트 조회 → [(id, name, url), ...]"""
    try:
        res = requests.get(f"{API_BASE}/whitelist", timeout=3)
        res.raise_for_status()
        return [(item["id"], item["name"], item["url"]) for item in res.json()]
    except Exception:
        db = _get_local_db()
        try:
            return db.get_all_whitelist_urls()
        finally:
            db.close()


def add_whitelist_url(name: str, url: str) -> bool:
    """서버에 화이트리스트 URL 추가"""
    try:
        res = requests.post(
            f"{API_BASE}/whitelist",
            json={"name": name, "url": url},
            timeout=3,
        )
        res.raise_for_status()
        return True
    except Exception:
        db = _get_local_db()
        try:
            return db.add_whitelist_url(name, url)
        finally:
            db.close()


def remove_whitelist_url(url_id: int) -> bool:
    """서버에서 화이트리스트 URL 삭제"""
    try:
        res = requests.delete(f"{API_BASE}/whitelist/{url_id}", timeout=3)
        res.raise_for_status()
        return True
    except Exception:
        db = _get_local_db()
        try:
            return db.remove_whitelist_url(url_id)
        finally:
            db.close()
