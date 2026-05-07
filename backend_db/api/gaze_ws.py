"""
I-Study Beta - ?�캠 ?�선 추적 WebSocket ?�우??(골격)

??개요 ??브라?��?(?�캠)
   ?? 1) 카메???�레??캡처 (canvas ??JPEG/base64)
   ?? 2) WebSocket ?�로 ?�버???�송
   ??FastAPI WebSocket (???�일)
   ?? 3) ?�레???�코??(base64 ??numpy)
   ?? 4) GazeEstimator �?처리 (FaceTracker ??Kalman ??...)
   ?? 5) 결과(?�선좌표/집중?? JSON ?�로 ?�답
   ??브라?��?
   ?? 6) UI??결과 반영 (overlay, score)

???�합 가?�드 ??1) 기존 ?�선 추적 로직?� 모두 `core/` ?�래 모듈�?분리?�어 ?�습?�다.
   - core/face_tracker.py
   - core/kalman_filter.py
   - core/calibration.py
   - core/focus_analyzer.py
   - core/gaze_estimator.py  (?�합 ?�진)

2) ?�스?�톱 ?�에?�는 `GazeEstimator`가 카메??VideoCapture)�?직접 ?��?�?
   ?�에?�는 **?�레???�력?�만 ?�릅?�다**.
   ??`FaceTracker.process_frame(frame)` �?그�?�??�사?�하�?
     카메??캡처/UI 부분�? 브라?��?가 ?�당?�니??

3) ?�라?????�일?�서??`FaceTracker` + `KalmanFilter` + `FocusAnalyzer` �?   직접 ?�스?�스?�하???�용?�니??

4) ?�용?�별 ?�션 격리: �?WebSocket ?�결마다 별도??추적 ?�스?�스�??�성?�니??

?�️ ?�능 주의:
- WebSocket ?�로 base64 JPEG �??�송?�면 30fps 기�? ??2~5 Mbps ?�래??발생.
- ?�로?�션?�서??WebRTC + MediaSoup/Janus ?�는 WebTransport 가 ???�율?�입?�다.
- MVP ?�계?�서????WebSocket 방식?�로 충분?�니??
"""

import base64
import json
from typing import Optional

import numpy as np
import cv2
from fastapi import APIRouter, WebSocket, WebSocketDisconnect, Query, status
from jose import JWTError

from auth import decode_token

router = APIRouter(prefix="/ws", tags=["WebSocket"])


# ?�?�?�?�?�?�?�?�?�?�?�?�?�?�?�?�?�?�?�?�?�?�?�?�?�?�?�?�?�?�?�?�?�?�?�?�?�?�?�?�?�?�?�?�?�
# ?�선 추적 ?�진 (지??import: core 모듈?� 무거?�)
# ?�?�?�?�?�?�?�?�?�?�?�?�?�?�?�?�?�?�?�?�?�?�?�?�?�?�?�?�?�?�?�?�?�?�?�?�?�?�?�?�?�?�?�?�?�

def _create_tracker():
    """
    ?�용?�별 ?�래�??�스?�스 ?�성.
    core 모듈??server ?� 같�? ?�로?�트???�다�?가??(sys.path ?�인).
    """
    import sys, os
    PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
    if PROJECT_ROOT not in sys.path:
        sys.path.insert(0, PROJECT_ROOT)

    from core.face_tracker import FaceTracker
    from core.kalman_filter import GazeKalmanFilter
    from core.focus_analyzer import FocusAnalyzer

    # ?�면 ?�기???�라?�언?�에??보내?�면 갱신 가??(기본 1920x1080)
    return {
        "face": FaceTracker(),
        "kalman": GazeKalmanFilter(1920, 1080),
        "focus": FocusAnalyzer(),
    }


# ?�?�?�?�?�?�?�?�?�?�?�?�?�?�?�?�?�?�?�?�?�?�?�?�?�?�?�?�?�?�?�?�?�?�?�?�?�?�?�?�?�?�?�?�?�
# WebSocket ?�드?�인??# ?�?�?�?�?�?�?�?�?�?�?�?�?�?�?�?�?�?�?�?�?�?�?�?�?�?�?�?�?�?�?�?�?�?�?�?�?�?�?�?�?�?�?�?�?�

@router.websocket("/gaze")
async def gaze_stream(websocket: WebSocket, token: Optional[str] = Query(default=None)):
    """
    ?�라?�언?????�버 메시지 ?�식 (JSON):
        { "type": "frame", "image": "<base64 jpeg>", "screen": [w, h] }
        { "type": "config", ... }

    ?�버 ???�라?�언???�답 ?�식 (JSON):
        {
          "type": "result",
          "face_detected": bool,
          "gaze": [x, y],          # 0~1 ?�규??(?�는 ?��?)
          "head": {"yaw": float, "pitch": float},
          "ear": float,
          "focus_state": "Focused" | "Dazed" | "Distracted",
          "focus_score": 0~100
        }
    """
    # ?�?�?� ?�증: JWT ?�큰??query param ?�로 받음 ?�?�?�
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
    tracker = _create_tracker()
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
                # 1) base64 ??numpy
                b64 = msg.get("image", "")
                if "," in b64:
                    b64 = b64.split(",", 1)[1]
                try:
                    img_bytes = base64.b64decode(b64)
                    arr = np.frombuffer(img_bytes, dtype=np.uint8)
                    frame = cv2.imdecode(arr, cv2.IMREAD_COLOR)
                except Exception:
                    continue
                if frame is None:
                    continue

                # 2) ?�선 추적 처리
                result = tracker["face"].process_frame(frame)
                if not result.get("face_detected"):
                    await websocket.send_json({
                        "type": "result",
                        "face_detected": False,
                    })
                    continue

                # ?�이브리??결합
                from shared.config import ALPHA_IRIS, ALPHA_HEAD
                gx = ALPHA_IRIS * result["iris_x"] + ALPHA_HEAD * (result["yaw"] / 30.0)
                gy = ALPHA_IRIS * result["iris_y"] + ALPHA_HEAD * (result["pitch"] / 25.0)

                # Kalman
                sx, sy = tracker["kalman"].update(gx, gy)

                # Focus
                tracker["focus"].update(sx, sy, result["ear"], in_window=True)

                await websocket.send_json({
                    "type": "result",
                    "face_detected": True,
                    "gaze": [sx, sy],
                    "head": {"yaw": result["yaw"], "pitch": result["pitch"]},
                    "ear": result["ear"],
                    "focus_state": tracker["focus"].state,
                    "focus_score": round(tracker["focus"].focus_score, 1),
                })

            elif mtype == "ping":
                await websocket.send_json({"type": "pong"})

    except WebSocketDisconnect:
        print(f"[ws/gaze] disconnected user={user_id}")
    except Exception as e:
        print(f"[ws/gaze] error: {e}")
        await websocket.close()
