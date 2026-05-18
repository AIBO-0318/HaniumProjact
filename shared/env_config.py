"""
I-Study - 환경 설정 로더
.env 파일 또는 환경변수에서 설정을 읽어옵니다.
"""

import os
from pathlib import Path


def _load_dotenv():
    """프로젝트 루트의 .env 파일을 읽어 환경변수에 등록"""
    env_path = Path(__file__).resolve().parent.parent / ".env"
    if not env_path.exists():
        return
    with open(env_path, encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if not line or line.startswith("#"):
                continue
            if "=" in line:
                key, _, value = line.partition("=")
                os.environ.setdefault(key.strip(), value.strip())


_load_dotenv()

# ─── 데이터베이스 ───
DB_HOST = os.getenv("DB_HOST", "localhost")
DB_PORT = os.getenv("DB_PORT", "5432")
DB_USER = os.getenv("DB_USER", "postgres")
DB_PASSWORD = os.getenv("DB_PASSWORD", "aisw2026")
DB_NAME = os.getenv("DB_NAME", "istudy")

DATABASE_URL = f"postgresql://{DB_USER}:{DB_PASSWORD}@{DB_HOST}:{DB_PORT}/{DB_NAME}"

# ─── 서버 ───
SERVER_HOST = os.getenv("SERVER_HOST", "0.0.0.0")
SERVER_PORT = int(os.getenv("SERVER_PORT", "8000"))

# ─── JWT ───
JWT_SECRET = os.getenv("JWT_SECRET", "your-secret-key-change-this")

# ─── API 서버 URL (EXE가 연결할 서버) ───
# 빌드된 EXE 옆에 _server_url.txt 가 있으면 그 URL을 사용
# 없으면 환경변수 → 기본값(localhost) 순으로 사용
def _read_bundled_url() -> str:
    """EXE 배포 시 함께 번들된 서버 URL 파일을 읽음"""
    import sys
    if getattr(sys, 'frozen', False):
        base = os.path.dirname(sys.executable)
    else:
        base = os.path.join(os.path.dirname(__file__), "..")
    txt = os.path.join(base, "_server_url.txt")
    if os.path.exists(txt):
        with open(txt, encoding="utf-8") as f:
            url = f.read().strip()
            if url:
                return url
    return ""

API_SERVER_URL = (
    _read_bundled_url()
    or os.getenv("API_SERVER_URL", "http://127.0.0.1:8000")
).rstrip("/")
