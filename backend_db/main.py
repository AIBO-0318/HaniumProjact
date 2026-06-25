"""
I-Study - FastAPI Server
백엔드 진입점. PostgreSQL 연결, JWT 인증, 정적 웹사이트 서빙.

라우터:
- /users/*        (회원가입/로그인/Role 보호)
- /admins/*       (관리자: 가입/로그인/사용자관리/등급)
- /ws/gaze        (시선 WebSocket)
- /schedules/*    (일정표)
- /stats/*        (학습 통계)
- /whitelist/*    (화이트리스트)
- /gaze-settings/*(시선 설정)
- /calibration/*  (시선 보정)
- /api/*          (데스크톱 호환용 레거시)
"""
import os
import sys
from contextlib import asynccontextmanager

from fastapi import FastAPI, Depends
from fastapi.responses import RedirectResponse, FileResponse
from fastapi.staticfiles import StaticFiles
from sqlalchemy.orm import Session
from sqlalchemy import text

from database import engine, get_db, SessionLocal, Base
from models import HeadPoseData, WhitelistUrl

# 라우터
from api.users import router as users_router
from api.admins import router as admins_router
from api.gaze_ws import router as gaze_ws_router
from api.schedules import router as schedules_router
from api.stats import router as stats_router
from api.whitelist import router as whitelist_router
from api.gaze_settings import router as gaze_settings_router
from api.calibration import router as calibration_router
from api.legacy import router as legacy_router


# --- 기본 화이트리스트 ---
DEFAULT_SITES = [
    ("EBSI", "https://www.ebsi.co.kr/ebs/pot/poti/main.ebs"),
    ("네이버 사전", "https://dict.naver.com/"),
    ("대성 마이맥", "https://www.mimacstudy.com/main/main.ds"),
    ("메가 스터디", "https://www.megastudy.net/"),
    ("이투스", "https://www.etoos.com/home/default.asp"),
    ("ChatGPT", "https://chatgpt.com/"),
    ("Gemini", "https://gemini.google.com/u/1/app?hl=ko"),
]


def _seed_default_whitelist():
    db = SessionLocal()
    try:
        if db.query(WhitelistUrl).count() == 0:
            for name, url in DEFAULT_SITES:
                db.add(WhitelistUrl(name=name, url=url))
            db.commit()
            print(f"기본 화이트리스트 {len(DEFAULT_SITES)}건 등록")
    finally:
        db.close()


# --- 앱 생명주기 ---
@asynccontextmanager
async def lifespan(app: FastAPI):
    Base.metadata.create_all(bind=engine)
    _seed_default_whitelist()
    print("DB 테이블 생성/마이그레이션 완료")
    yield


app = FastAPI(title="I-Study Server", lifespan=lifespan)

# 라우터 등록
app.include_router(users_router)
app.include_router(admins_router)
app.include_router(gaze_ws_router)
app.include_router(schedules_router)
app.include_router(stats_router)
app.include_router(whitelist_router)
app.include_router(gaze_settings_router)
app.include_router(calibration_router)
app.include_router(legacy_router)


# --- 데스크톱 호환: HeadPose 저장 ---
from pydantic import BaseModel


class HeadPoseCreate(BaseModel):
    student_id: str
    x: float
    y: float


@app.post("/headpose")
def save_head_pose(data: HeadPoseCreate, db: Session = Depends(get_db)):
    record = HeadPoseData(student_id=data.student_id, x=data.x, y=data.y)
    db.add(record)
    db.commit()
    return {"status": "ok"}


# ─── 정적 웹사이트 (ui_ux/web/) 서빙 ───
def _get_base_dir():
    """exe(frozen) 환경과 개발 환경 모두 지원"""
    if getattr(sys, 'frozen', False):
        return os.path.dirname(sys.executable)
    return os.path.join(os.path.dirname(os.path.abspath(__file__)), "..")

WEB_ROOT = os.path.normpath(os.path.join(_get_base_dir(), "ui_ux", "web"))
WEB_PAGES = os.path.join(WEB_ROOT, "pages")
WEB_SCRIPTS = os.path.join(WEB_ROOT, "scripts")
WEB_STYLES = os.path.join(WEB_ROOT, "styles")

if os.path.isdir(WEB_PAGES):
    # 페이지 (HTML)
    app.mount("/static/pages", StaticFiles(directory=WEB_PAGES), name="pages")
    # 스크립트 (HTML이 /static/js/ 로 참조하므로 그 경로에 마운트)
    if os.path.isdir(WEB_SCRIPTS):
        app.mount("/static/js", StaticFiles(directory=WEB_SCRIPTS), name="scripts")
    if os.path.isdir(WEB_STYLES):
        app.mount("/static/css", StaticFiles(directory=WEB_STYLES), name="styles")
    # 호환: 기존 /static/ 이미지/기타 자원 (없어도 무방)
    app.mount("/static", StaticFiles(directory=WEB_ROOT), name="web_root")

    @app.get("/", include_in_schema=False)
    def root():
        return FileResponse(os.path.join(WEB_PAGES, "index.html"))

    @app.get("/signup", include_in_schema=False)
    def page_signup():
        return FileResponse(os.path.join(WEB_PAGES, "signup.html"))

    @app.get("/main", include_in_schema=False)
    def page_main():
        return FileResponse(os.path.join(WEB_PAGES, "main.html"))

    @app.get("/calibration", include_in_schema=False)
    def page_calibration():
        return FileResponse(os.path.join(WEB_PAGES, "calibration.html"))

    @app.get("/whitelist", include_in_schema=False)
    def page_whitelist():
        return FileResponse(os.path.join(WEB_PAGES, "whitelist.html"))

    @app.get("/stats", include_in_schema=False)
    def page_stats():
        return FileResponse(os.path.join(WEB_PAGES, "stats.html"))

    @app.get("/schedule", include_in_schema=False)
    def page_schedule():
        return FileResponse(os.path.join(WEB_PAGES, "schedule.html"))

    @app.get("/mypage", include_in_schema=False)
    def page_mypage():
        return FileResponse(os.path.join(WEB_PAGES, "mypage.html"))

    @app.get("/dashboard", include_in_schema=False)
    def page_dashboard():
        return FileResponse(os.path.join(WEB_PAGES, "dashboard.html"))

    @app.get("/gaze-settings", include_in_schema=False)
    def page_gaze_settings():
        return FileResponse(os.path.join(WEB_PAGES, "gaze-settings.html"))

    @app.get("/teacher-whitelist", include_in_schema=False)
    def page_teacher_whitelist():
        return FileResponse(os.path.join(WEB_PAGES, "teacher-whitelist.html"))

    @app.get("/auto-login", include_in_schema=False)
    def page_auto_login():
        return FileResponse(os.path.join(WEB_PAGES, "auto-login.html"))

    @app.get("/admin-users", include_in_schema=False)
    def page_admin_users():
        return FileResponse(os.path.join(WEB_PAGES, "admin-users.html"))

    @app.get("/admin-stats", include_in_schema=False)
    def page_admin_stats():
        return FileResponse(os.path.join(WEB_PAGES, "admin-stats.html"))

    @app.get("/focus-mode", include_in_schema=False)
    def page_focus_mode():
        return FileResponse(os.path.join(WEB_PAGES, "focus-mode.html"))

    @app.get("/teacher-schedule", include_in_schema=False)
    def page_teacher_schedule():
        return FileResponse(os.path.join(WEB_PAGES, "teacher-schedule.html"))

else:
    @app.get("/", include_in_schema=False)
    def root():
        return RedirectResponse(url="/docs")
