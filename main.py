"""
I-Study - 스마트 학습 도우미 (시선 추적 기반 집중도 관리 시스템)
실행: python main.py
"""

import sys
import os
import subprocess
import atexit
import time
import threading

PROJECT_ROOT = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, PROJECT_ROOT)

_server_process = None
_server_thread = None


def _is_frozen():
    """PyInstaller exe 환경인지 확인"""
    return getattr(sys, 'frozen', False)


def _is_server_running():
    """서버가 이미 실행 중인지 확인"""
    import requests
    try:
        requests.get("http://127.0.0.1:8000/api/whitelist", timeout=1)
        return True
    except Exception:
        return False


def _start_server_thread():
    """exe 환경: uvicorn을 백그라운드 스레드로 실행"""
    global _server_thread
    if _is_server_running():
        print("[I-Study] 서버가 이미 실행 중입니다.")
        return

    sys.path.insert(0, os.path.join(PROJECT_ROOT, "backend_db"))

    def _run():
        import uvicorn
        uvicorn.run(
            "main:app",
            host="0.0.0.0",
            port=8000,
            log_level="warning",
        )

    _server_thread = threading.Thread(target=_run, daemon=True)
    _server_thread.start()

    for _ in range(20):
        if _is_server_running():
            print("[I-Study] 서버 시작 완료")
            return
        time.sleep(0.5)
    print("[I-Study] 서버 시작 대기 시간 초과 - 앱은 계속 실행합니다")


def _start_server_subprocess():
    """개발 환경: uvicorn을 서브프로세스로 실행"""
    global _server_process
    if _is_server_running():
        print("[I-Study] 서버가 이미 실행 중입니다.")
        return

    server_dir = os.path.join(PROJECT_ROOT, "backend_db")
    creation_flags = subprocess.CREATE_NO_WINDOW if sys.platform == "win32" else 0
    _server_process = subprocess.Popen(
        [sys.executable, "-m", "uvicorn", "main:app",
         "--host", "0.0.0.0", "--port", "8000", "--log-level", "warning"],
        cwd=server_dir,
        creationflags=creation_flags,
    )
    atexit.register(_stop_server)

    for _ in range(20):
        if _is_server_running():
            print("[I-Study] 서버 시작 완료")
            return
        time.sleep(0.5)
    print("[I-Study] 서버 시작 대기 시간 초과 - 앱은 계속 실행합니다")


def _stop_server():
    """서브프로세스 서버 종료"""
    global _server_process
    if _server_process is not None:
        _server_process.terminate()
        try:
            _server_process.wait(timeout=5)
        except subprocess.TimeoutExpired:
            _server_process.kill()
        _server_process = None
        print("[I-Study] 서버 종료 완료")


def _is_remote_server() -> bool:
    """원격 서버 URL이 설정되어 있으면 True (로컬 서버 불필요)"""
    try:
        from shared.env_config import API_SERVER_URL
        local = ("127.0.0.1", "localhost")
        return not any(h in API_SERVER_URL for h in local)
    except Exception:
        return False


def main():
    if _is_remote_server():
        print("[I-Study] 원격 서버 모드 — 로컬 서버 시작 생략")
    elif _is_frozen():
        _start_server_thread()
    else:
        _start_server_subprocess()

    from ui_ux.desktop.app import FocusEyePro
    app = FocusEyePro()
    app.mainloop()
    _stop_server()


if __name__ == "__main__":
    main()
