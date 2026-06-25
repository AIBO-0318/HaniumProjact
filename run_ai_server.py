"""
I-Study AI Service 실행 스크립트 (FastAPI / 시선추적 WebSocket 전용)

- /ws/gaze 만 제공 (그 외 REST/웹은 Spring Boot backend_spring 담당)
- 기본 포트: 8001 (Spring Boot 8000 과 분리)

사용:
    python run_ai_server.py
"""
import os
import socket
import subprocess
import sys

PROJECT_ROOT = os.path.dirname(os.path.abspath(__file__))
BACKEND_DIR = os.path.join(PROJECT_ROOT, "backend_db")

HOST = os.getenv("AI_SERVER_HOST", "0.0.0.0")
PORT = int(os.getenv("AI_SERVER_PORT", "8001"))


def _local_ip() -> str:
    try:
        s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        s.connect(("8.8.8.8", 80))
        ip = s.getsockname()[0]
        s.close()
        return ip
    except Exception:
        return "127.0.0.1"


if __name__ == "__main__":
    ip = _local_ip()
    print("=" * 50)
    print(" I-Study AI Service (FastAPI / 시선추적 WebSocket)")
    print("=" * 50)
    print(f"  Local   : http://127.0.0.1:{PORT}/health")
    print(f"  Network : http://{ip}:{PORT}/health")
    print(f"  WS      : ws://{ip}:{PORT}/ws/gaze")
    print("=" * 50)

    subprocess.run(
        [sys.executable, "-m", "uvicorn", "ai_server:app",
         "--host", HOST, "--port", str(PORT), "--reload"],
        cwd=BACKEND_DIR,
    )
