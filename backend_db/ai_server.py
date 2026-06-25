"""
I-Study AI Service (FastAPI) — 시선추적 전용

이 서비스는 **실시간 시선추적 WebSocket(/ws/gaze)** 만 담당한다.
그 외 모든 REST API(users/admins/schedules/stats/whitelist/gaze-settings/
calibration/legacy/headpose)와 정적 웹 서빙은 Spring Boot(backend_spring)로 이전되었다.

실행:
    python run_ai_server.py
    # 또는
    uvicorn ai_server:app --host 0.0.0.0 --port 8001

포트:
    - Spring Boot(REST + 웹): 8000
    - FastAPI(AI WebSocket):   8001

JWT:
    /ws/gaze 는 Spring Boot 가 발급한 토큰을 검증한다.
    두 서비스의 JWT_SECRET(HS256) 이 반드시 동일해야 한다.
"""
import os
import sys

# backend_db 디렉터리를 import 루트로 (api.*, auth 모듈 해석용)
_HERE = os.path.dirname(os.path.abspath(__file__))
if _HERE not in sys.path:
    sys.path.insert(0, _HERE)

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from api.gaze_ws import router as gaze_ws_router

app = FastAPI(title="I-Study AI Service", description="실시간 시선추적 WebSocket 전용")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(gaze_ws_router)


@app.get("/health")
def health():
    return {"status": "ok", "service": "ai", "ws": "/ws/gaze"}
