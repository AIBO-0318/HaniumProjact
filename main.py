"""
I-Study - ?�마???�습 ?�우�??�선 추적 기반 집중??관�??�스??
?�행: python main.py
"""

import sys
import os
import subprocess
import atexit
import time

# ?�로?�트 루트�?Python 경로??추�?
PROJECT_ROOT = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, PROJECT_ROOT)

_server_process = None


def _is_server_running():
    """?�버가 ?��? ?�행 중인지 ?�인"""
    import requests
    try:
        requests.get("http://127.0.0.1:8000/api/whitelist", timeout=1)
        return True
    except Exception:
        return False


def _start_server():
    """FastAPI ?�버�?백그?�운???�로?�스�??�작"""
    global _server_process
    if _is_server_running():
        print("[I-Study] ?�버가 ?��? ?�행 중입?�다.")
        return

    server_dir = os.path.join(PROJECT_ROOT, "backend_db")
    creation_flags = subprocess.CREATE_NO_WINDOW if sys.platform == "win32" else 0
    _server_process = subprocess.Popen(
        [sys.executable, "-m", "uvicorn", "main:app",
         "--host", "127.0.0.1", "--port", "8000", "--log-level", "warning"],
        cwd=server_dir,
        creationflags=creation_flags,
    )
    atexit.register(_stop_server)

    # ?�버 준�??��?(최�? 10�?
    for _ in range(20):
        if _is_server_running():
            print("[I-Study] ?�버 ?�작 ?�료")
            return
        time.sleep(0.5)
    print("[I-Study] ?�버 ?�작 ?��??�간 초과 ???��? 계속 ?�행?�니??")


def _stop_server():
    """?�버 ?�로?�스 종료"""
    global _server_process
    if _server_process is not None:
        _server_process.terminate()
        try:
            _server_process.wait(timeout=5)
        except subprocess.TimeoutExpired:
            _server_process.kill()
        _server_process = None
        print("[I-Study] ?�버 종료 ?�료")


def main():
    _start_server()
    from ui_ux.desktop.app import FocusEyePro
    app = FocusEyePro()
    app.mainloop()
    _stop_server()


if __name__ == "__main__":
    main()
