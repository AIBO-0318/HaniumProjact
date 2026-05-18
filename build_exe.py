"""
I-Study - EXE 빌드 스크립트

사용법:
    python build_exe.py

필요 패키지:
    pip install pyinstaller

결과:
    dist/I-Study/I-Study.exe
"""

import subprocess
import sys
import os
import shutil

PROJECT_ROOT = os.path.dirname(os.path.abspath(__file__))


def check_pyinstaller():
    try:
        import PyInstaller
        print(f"[✓] PyInstaller {PyInstaller.__version__}")
    except ImportError:
        print("[!] PyInstaller가 설치되어 있지 않습니다. 설치합니다...")
        subprocess.check_call([sys.executable, "-m", "pip", "install", "pyinstaller"])
        print("[✓] PyInstaller 설치 완료")


def get_server_url() -> str:
    """서버 URL 결정 순서: 커맨드라인 → 환경변수 → 직접 입력"""
    import argparse

    # 1) 커맨드라인 인자 (GitHub Actions 등 CI 환경)
    parser = argparse.ArgumentParser(add_help=False)
    parser.add_argument("--server-url", default=None)
    args, _ = parser.parse_known_args()
    if args.server_url:
        url = args.server_url.strip().rstrip("/")
        print(f"  → 서버 URL (인자): {url}")
        return url

    # 2) 환경변수
    env_url = os.environ.get("ISTUDY_SERVER_URL", "").strip().rstrip("/")
    if env_url:
        print(f"  → 서버 URL (환경변수): {env_url}")
        return env_url

    # 3) 직접 입력 (로컬 빌드)
    print()
    print("=" * 60)
    print("  서버 URL 설정")
    print("=" * 60)
    print("  배포된 서버 URL을 입력하세요.")
    print("  (엔터만 누르면 로컬 모드로 빌드됩니다)")
    print()
    url = input("  서버 URL (예: https://i-study.onrender.com): ").strip()
    if not url:
        url = "http://127.0.0.1:8000"
        print("  → 로컬 모드로 빌드합니다.")
    else:
        print(f"  → {url} 로 빌드합니다.")
    print()
    return url.rstrip("/")


def build():
    check_pyinstaller()

    server_url = get_server_url()

    # _server_url.txt 생성 (EXE와 같은 폴더에 번들됨)
    server_url_file = os.path.join(PROJECT_ROOT, "_server_url.txt")
    with open(server_url_file, "w", encoding="utf-8") as f:
        f.write(server_url)

    dist_dir = os.path.join(PROJECT_ROOT, "dist", "I-Study")

    # 데이터 파일 목록 (소스 경로, 번들 내 경로)
    datas = [
        # 서버 URL 설정
        ("_server_url.txt", "."),
        # 웹 UI
        (os.path.join("ui_ux", "web", "pages"), os.path.join("ui_ux", "web", "pages")),
        (os.path.join("ui_ux", "web", "scripts"), os.path.join("ui_ux", "web", "scripts")),
        (os.path.join("ui_ux", "web", "styles"), os.path.join("ui_ux", "web", "styles")),
        # AI 모델
        (os.path.join("ai_core", "models", "face_landmarker.task"), os.path.join("ai_core", "models")),
        # 백엔드 소스 (uvicorn이 import할 수 있도록)
        (os.path.join("backend_db", "main.py"), "backend_db"),
        (os.path.join("backend_db", "database.py"), "backend_db"),
        (os.path.join("backend_db", "models.py"), "backend_db"),
        (os.path.join("backend_db", "schemas.py"), "backend_db"),
        (os.path.join("backend_db", "auth.py"), "backend_db"),
        (os.path.join("backend_db", "__init__.py"), "backend_db"),
        (os.path.join("backend_db", "api"), os.path.join("backend_db", "api")),
    ]

    # hidden imports
    hidden = [
        "uvicorn",
        "uvicorn.logging",
        "uvicorn.loops",
        "uvicorn.loops.auto",
        "uvicorn.protocols",
        "uvicorn.protocols.http",
        "uvicorn.protocols.http.auto",
        "uvicorn.protocols.websockets",
        "uvicorn.protocols.websockets.auto",
        "uvicorn.lifespan",
        "uvicorn.lifespan.on",
        "uvicorn.lifespan.off",
        "fastapi",
        "starlette",
        "starlette.routing",
        "starlette.responses",
        "starlette.middleware",
        "starlette.middleware.cors",
        "sqlalchemy",
        "sqlalchemy.dialects.postgresql",
        "psycopg2",
        "passlib",
        "passlib.handlers",
        "passlib.handlers.bcrypt",
        "jose",
        "jose.jwt",
        "bcrypt",
        "mediapipe",
        "customtkinter",
        "cv2",
        "PIL",
        "pyautogui",
        "pygetwindow",
        "engineio.async_drivers.threading",
    ]

    # --add-data 인자 생성
    data_args = []
    for src, dest in datas:
        data_args.extend(["--add-data", f"{src};{dest}"])

    # --hidden-import 인자 생성
    hidden_args = []
    for h in hidden:
        hidden_args.extend(["--hidden-import", h])

    cmd = [
        sys.executable, "-m", "PyInstaller",
        "--name", "I-Study",
        "--windowed",
        "--noconfirm",
        "--icon", "NONE",
        *data_args,
        *hidden_args,
        "--collect-all", "customtkinter",
        "--collect-all", "mediapipe",
        "--collect-data", "starlette",
        "--collect-data", "fastapi",
        "main.py",
    ]

    print("=" * 60)
    print("  I-Study EXE 빌드 시작")
    print("=" * 60)
    print()

    result = subprocess.run(cmd, cwd=PROJECT_ROOT)

    # 임시 파일 정리
    if os.path.exists(server_url_file):
        os.remove(server_url_file)

    if result.returncode == 0:
        is_remote = not any(h in server_url for h in ("127.0.0.1", "localhost"))
        print()
        print("=" * 60)
        print("  빌드 성공!")
        print("=" * 60)
        print(f"  EXE 위치: {os.path.join(dist_dir, 'I-Study.exe')}")
        print(f"  연결 서버: {server_url}")
        print()
        if is_remote:
            print("  배포 모드: 사용자는 PostgreSQL 설치 불필요")
            print("  → GitHub Releases에 dist\\I-Study 폴더를 zip으로 올리세요")
        else:
            print("  로컬 모드: PostgreSQL이 설치된 환경에서만 작동")
        print("=" * 60)
    else:
        print()
        print("[!] 빌드 실패. 위의 에러 메시지를 확인하세요.")


if __name__ == "__main__":
    build()
