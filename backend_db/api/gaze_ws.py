"""
I-Study - 웹캠 시선 추적 WebSocket 라우터 (/ws/gaze)

흐름
  브라우저(웹캠)  1) 카메라 프레임 캡처 (canvas → JPEG/base64)
                 2) WebSocket 으로 서버에 전송
  FastAPI        3) 프레임 디코딩 (base64 → numpy)
                 4) FrameGazeAnalyzer 로 분석 (데스크톱 GazeTracker 와 같은 판정 로직)
                 5) 결과(시선 좌표/집중도)를 JSON 으로 응답
  브라우저        6) UI 에 결과 반영 (overlay, score)

- 연결(사용자)마다 별도의 분석기 인스턴스를 만든다.
- 분석(MediaPipe 추론)은 이벤트 루프를 막지 않도록 스레드에서 돌린다.
- base64 JPEG 를 30fps 로 보내면 2~5 Mbps 수준 — MVP 용도로는 충분하다.
"""

import asyncio
import base64
import json
import os
import sys
from typing import Optional

import cv2
import numpy as np
from fastapi import APIRouter, WebSocket, WebSocketDisconnect, Query, status

from auth import decode_token

router = APIRouter(prefix="/ws", tags=["WebSocket"])


def _create_tracker():
    """연결별 분석기 생성 (ai_core 는 프로젝트 루트 기준으로 import)"""
    project_root = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
    if project_root not in sys.path:
        sys.path.insert(0, project_root)

    from ai_core.frame_analyzer import FrameGazeAnalyzer
    from shared.config import GAZE_LOST_THRESHOLD, EYE_CLOSURE_THRESHOLD

    return FrameGazeAnalyzer(gaze_lost_threshold=GAZE_LOST_THRESHOLD,
                             eye_closure_threshold=EYE_CLOSURE_THRESHOLD)


def _decode_frame(data_url: str):
    """'data:image/jpeg;base64,...' 또는 순수 base64 → BGR numpy (실패 시 None)"""
    b64 = data_url.split(",", 1)[1] if "," in data_url else data_url
    try:
        arr = np.frombuffer(base64.b64decode(b64), dtype=np.uint8)
        return cv2.imdecode(arr, cv2.IMREAD_COLOR)
    except Exception:
        return None


@router.websocket("/gaze")
async def gaze_stream(websocket: WebSocket, token: Optional[str] = Query(default=None)):
    """
    클라이언트 → 서버 (JSON)
        { "type": "frame", "image": "<base64 jpeg>", "screen": [w, h] }
        { "type": "ping" }

    서버 → 클라이언트 (JSON)
        { "type": "result", "face_detected": false }
        {
          "type": "result",
          "face_detected": true,
          "gaze": [x, y],                 # 얼굴 방향 비율 0~1 (0.5 = 정면)
          "head": {"yaw": float, "pitch": float},   # 도(°)
          "ear": float,                   # 눈 세로/가로 비율 평균
          "direction": "center" | "left" | "right" | "up" | "down",
          "focus_state": "Focused" | "Dazed" | "Distracted",
          "focus_score": 0~100
        }
        { "type": "pong" }
    """
    # 인증: Spring 이 발급한 JWT 를 query param 으로 받음
    if not token:
        await websocket.close(code=status.WS_1008_POLICY_VIOLATION)
        return
    try:
        payload = decode_token(token)
    except Exception:
        await websocket.close(code=status.WS_1008_POLICY_VIOLATION)
        return

    user_id = payload.get("user_id")
    role = payload.get("role")

    await websocket.accept()
    try:
        tracker = await asyncio.to_thread(_create_tracker)
    except Exception as e:
        print(f"[ws/gaze] tracker init failed: {e}")
        await websocket.close(code=status.WS_1011_INTERNAL_ERROR)
        return
    print(f"[ws/gaze] connected user={user_id} role={role}")

    try:
        while True:
            raw = await websocket.receive_text()
            try:
                msg = json.loads(raw)
            except json.JSONDecodeError:
                continue

            mtype = msg.get("type")
            if mtype == "frame":
                frame = _decode_frame(msg.get("image", ""))
                if frame is None:
                    continue
                result = await asyncio.to_thread(tracker.analyze, frame)
                await websocket.send_json({"type": "result", **result})
            elif mtype == "ping":
                await websocket.send_json({"type": "pong"})

    except WebSocketDisconnect:
        print(f"[ws/gaze] disconnected user={user_id}")
    except Exception as e:
        print(f"[ws/gaze] error: {e}")
        await websocket.close()
