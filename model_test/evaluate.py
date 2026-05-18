"""
I-Study 방향 인식률 테스트 — 실시간 평가 (간단 버전)
======================================================
고개를 움직이면 ML 모델과 임계값 방식이 실시간으로 예측합니다.
아무 버튼 없이 Q만 누르면 종료됩니다.
"""

import os
import pickle

import cv2
import mediapipe as mp
import numpy as np
from PIL import Image, ImageDraw, ImageFont

MODEL_PATH = os.path.join(os.path.dirname(__file__), "model.pkl")

LABEL_KO = {
    "front": "정면",
    "left":  "좌측",
    "right": "우측",
    "up":    "위쪽",
    "down":  "아래",
    "—":     "—",
}
LABEL_COLOR = {
    "front": (80,  220, 120),
    "left":  (80,  180, 255),
    "right": (80,  180, 255),
    "up":    (255, 180,  80),
    "down":  (180,  80, 255),
}

# ── 한글 폰트 로드 ──
_FONT_PATHS = [
    "C:/Windows/Fonts/malgun.ttf",
    "C:/Windows/Fonts/NanumGothic.ttf",
    "C:/Windows/Fonts/gulim.ttc",
]
_font_big  = None
_font_mid  = None
_font_sm   = None
for fp in _FONT_PATHS:
    if os.path.exists(fp):
        _font_big = ImageFont.truetype(fp, 52)
        _font_mid = ImageFont.truetype(fp, 26)
        _font_sm  = ImageFont.truetype(fp, 20)
        break
if _font_big is None:
    _font_big = _font_mid = _font_sm = ImageFont.load_default()


def put_kr(frame, text, xy, color=(255,255,255), font=None):
    """OpenCV frame에 한글 텍스트 그리기 (PIL 사용)"""
    if font is None:
        font = _font_mid
    img_pil = Image.fromarray(cv2.cvtColor(frame, cv2.COLOR_BGR2RGB))
    draw = ImageDraw.Draw(img_pil)
    draw.text(xy, text, font=font, fill=(color[2], color[1], color[0]))
    frame[:] = cv2.cvtColor(np.array(img_pil), cv2.COLOR_RGB2BGR)

YAW_THRESHOLD  = 25.0
PITCH_UP_THR   = -15.0
PITCH_DOWN_THR =  15.0

MODEL_3D = np.array([
    (0.0,    0.0,    0.0),
    (0.0,  -330.0, -65.0),
    (-225.0, 170.0,-135.0),
    (225.0,  170.0,-135.0),
    (-150.0,-150.0,-125.0),
    (150.0, -150.0,-125.0),
], dtype=np.float64)
FACE_IDX = [1, 152, 33, 263, 61, 291]


def head_pose_yaw_pitch(landmarks, shape):
    h, w = shape[:2]
    pts2d = np.array(
        [(landmarks[i].x * w, landmarks[i].y * h) for i in FACE_IDX],
        dtype=np.float64,
    )
    cam = np.array([[w, 0, w/2], [0, w, h/2], [0, 0, 1]], dtype=np.float64)
    ok, rvec, _ = cv2.solvePnP(MODEL_3D, pts2d, cam, np.zeros((4,1)),
                                flags=cv2.SOLVEPNP_ITERATIVE)
    if not ok:
        return None, None
    R, _ = cv2.Rodrigues(rvec)
    sy = np.sqrt(R[0,0]**2 + R[1,0]**2)
    pitch = np.degrees(np.arctan2(-R[2,0], sy))
    yaw   = np.degrees(np.arctan2(R[1,0], R[0,0]))
    return yaw, pitch


def threshold_predict(yaw, pitch):
    if abs(yaw) > YAW_THRESHOLD:
        return "right" if yaw > 0 else "left"
    if pitch < PITCH_UP_THR:
        return "up"
    if pitch > PITCH_DOWN_THR:
        return "down"
    return "front"


def extract_features_live(landmarks, key_lm):
    raw = []
    for idx in key_lm:
        if idx >= len(landmarks):
            return None
        raw.extend([landmarks[idx].x, landmarks[idx].y, landmarks[idx].z])
    nx, ny, nz = raw[0], raw[1], raw[2]
    normed = [raw[i+j] - v for i in range(0, len(raw), 3)
              for j, v in enumerate([nx, ny, nz])]
    return np.array([normed], dtype=np.float32)


def draw_result(frame, ml_pred, ml_conf, thresh_pred, yaw, pitch, face_ok):
    h, w = frame.shape[:2]

    # 배경 어둡게
    overlay = frame.copy()
    cv2.rectangle(overlay, (0, 0), (w, h), (10, 10, 20), -1)
    cv2.addWeighted(overlay, 0.45, frame, 0.55, 0, frame)

    if not face_ok:
        put_kr(frame, "얼굴을 카메라에 맞춰주세요", (w//2 - 200, h//2 - 30),
               color=(80, 80, 200), font=_font_mid)
        put_kr(frame, "Q = 종료", (w//2 - 50, h - 40),
               color=(120, 120, 120), font=_font_sm)
        return

    # ── ML 모델 결과 (왼쪽) ──
    ml_ko  = LABEL_KO.get(ml_pred, ml_pred)
    ml_col = LABEL_COLOR.get(ml_pred, (200, 200, 200))

    put_kr(frame, "ML 모델", (30, 20), color=(160, 160, 160), font=_font_sm)
    put_kr(frame, ml_ko, (30, 55), color=ml_col, font=_font_big)

    # 신뢰도 바
    bar_w = int(ml_conf * (w // 2 - 60))
    cv2.rectangle(frame, (30, 120), (30 + w//2 - 60, 138), (50, 50, 50), -1)
    cv2.rectangle(frame, (30, 120), (30 + bar_w, 138), ml_col, -1)
    put_kr(frame, f"신뢰도 {ml_conf:.0%}", (30, 143), color=ml_col, font=_font_sm)

    # ── 구분선 ──
    cv2.line(frame, (w//2, 20), (w//2, h - 20), (70, 70, 70), 1)

    # ── 임계값 결과 (오른쪽) ──
    th_ko  = LABEL_KO.get(thresh_pred, thresh_pred)
    th_col = LABEL_COLOR.get(thresh_pred, (200, 200, 200))

    put_kr(frame, "현재 시스템", (w//2 + 30, 20), color=(160, 160, 160), font=_font_sm)
    put_kr(frame, th_ko, (w//2 + 30, 55), color=th_col, font=_font_big)

    if yaw is not None:
        put_kr(frame, f"Yaw {yaw:+.0f}°   Pitch {pitch:+.0f}°",
               (w//2 + 30, 143), color=(130, 130, 130), font=_font_sm)

    # ── 일치 여부 ──
    if ml_pred not in ("—",) and thresh_pred not in ("—",):
        match     = ml_pred == thresh_pred
        match_txt = "두 방식 일치" if match else "두 방식 불일치"
        match_col = (80, 220, 80) if match else (80, 80, 220)
        put_kr(frame, match_txt, (w//2 - 80, h - 55), color=match_col, font=_font_mid)

    # ── 종료 안내 ──
    put_kr(frame, "Q = 종료", (w - 110, h - 35), color=(100, 100, 100), font=_font_sm)


def main():
    if not os.path.exists(MODEL_PATH):
        print("model.pkl 없음 — train.py를 먼저 실행하세요.")
        return

    with open(MODEL_PATH, "rb") as f:
        payload = pickle.load(f)
    model    = payload["model"]
    le       = payload["label_encoder"]
    key_lm   = payload["key_landmarks"]
    mname    = payload.get("model_name", "ML")
    test_acc = payload.get("test_accuracy", 0.0)
    print(f"모델: {mname}  (학습 정확도: {test_acc:.1%})")
    print("카메라 창이 열립니다. 고개를 움직여보세요. Q로 종료.")

    cap = cv2.VideoCapture(0)
    if not cap.isOpened():
        print("카메라를 열 수 없습니다.")
        return

    with mp.solutions.face_mesh.FaceMesh(
        max_num_faces=1,
        refine_landmarks=True,
        min_detection_confidence=0.5,
        min_tracking_confidence=0.5,
    ) as face_mesh:

        while cap.isOpened():
            ret, frame = cap.read()
            if not ret:
                break
            frame = cv2.flip(frame, 1)
            rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
            res = face_mesh.process(rgb)

            ml_pred = thresh_pred = "—"
            ml_conf = 0.0
            yaw_val = pitch_val = None
            face_ok = res.multi_face_landmarks is not None

            if face_ok:
                lm = res.multi_face_landmarks[0].landmark

                feat = extract_features_live(lm, key_lm)
                if feat is not None:
                    proba   = model.predict_proba(feat)[0]
                    idx     = int(np.argmax(proba))
                    ml_pred = le.classes_[idx]
                    ml_conf = proba[idx]

                yaw_val, pitch_val = head_pose_yaw_pitch(lm, frame.shape)
                if yaw_val is not None:
                    thresh_pred = threshold_predict(yaw_val, pitch_val)

            draw_result(frame, ml_pred, ml_conf, thresh_pred,
                        yaw_val, pitch_val, face_ok)

            cv2.imshow("I-Study — 방향 인식 비교", frame)
            if cv2.waitKey(1) & 0xFF == ord("q"):
                break

    cap.release()
    cv2.destroyAllWindows()
    print("종료")


if __name__ == "__main__":
    main()
