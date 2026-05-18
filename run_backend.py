"""
I-Study - 백엔드 서버만 실행

사용법:
    python run_backend.py

설명:
    FastAPI 서버(http://127.0.0.1:8000) 만 실행합니다.
    웹사이트 접속:  http://127.0.0.1:8000
    API 문서:       http://127.0.0.1:8000/docs
"""

import os
import sys
import socket
import subprocess

PROJECT_ROOT = os.path.dirname(os.path.abspath(__file__))
BACKEND_DIR = os.path.join(PROJECT_ROOT, "backend_db")


def _get_local_ip():
    try:
        s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        s.connect(("8.8.8.8", 80))
        ip = s.getsockname()[0]
        s.close()
        return ip
    except Exception:
        return "127.0.0.1"


def main():
    ip = _get_local_ip()
    print("=" * 60)
    print("  I-Study Backend Server")
    print("=" * 60)
    print(f"  로컬 접속:  http://127.0.0.1:8000")
    print(f"  네트워크:   http://{ip}:8000")
    print(f"  API 문서:   http://127.0.0.1:8000/docs")
    print("=" * 60)

    subprocess.run(
        [sys.executable, "-m", "uvicorn", "main:app",
         "--host", "0.0.0.0", "--port", "8000", "--reload"],
        cwd=BACKEND_DIR,
    )


if __name__ == "__main__":
    main()
