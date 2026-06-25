"""
I-Study 방향 인식 성능 데모 — (1) 웹캠 캡처 도구
=====================================================
우리 앱(ai_core/gaze_tracker.py)과 **완전히 동일한 파이프라인**으로 웹캠 프레임을
캡처해 폴더에 저장한다. 저장된 사진은 judge_webcam.py 로 방향 판정/성능 측정에 쓴다.

핵심:
  - 앱과 동일하게 좌우 반전(mirror) 후 저장 → 판정 결과가 실제 앱과 일치한다.
  - 화면에 실시간으로 "지금 AI가 어느 방향으로 보는지" 를 같이 띄워준다(엔진 그대로).
  - 라벨별 폴더(front/left/right/up/down)에 저장 → judge_webcam.py 가 정확도 자동 계산.
  - 기존 코드/데이터는 건드리지 않고 model_test/captures/ 에 따로 저장한다.

조작:
  1=정면  2=좌측  3=우측  4=위  5=아래   (현재 라벨 선택)
  SPACE = 현재 프레임 저장
  A     = 자동 저장 토글 (기본 0.3초 간격)
  Q/ESC = 종료

사용법:
  python model_test/capture_webcam.py
  python model_test/capture_webcam.py --out model_test/captures --cam 0
  python model_test/capture_webcam.py --no-flip          # 좌우 반전 끄기
  python model_test/capture_webcam.py --interval 0.5     # 자동 저장 간격
"""

import os
import sys
import time
import argparse

import cv2

# ── 프로젝트 루트를 import 경로에 추가 (ai_core 사용) ─────────────────
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
PROJ_ROOT = os.path.dirname(BASE_DIR)
if PROJ_ROOT not in sys.path:
    sys.path.insert(0, PROJ_ROOT)

# Windows 콘솔에서 한글 출력이 깨지지 않도록
try:
    sys.stdout.reconfigure(encoding="utf-8")
except Exception:
    pass

LABELS = ["front", "left", "right", "up", "down"]
LABEL_KO = {"front": "정면", "left": "좌측", "right": "우측", "up": "위쪽", "down": "아래"}
# 엔진은 정면을 "center" 로 돌려준다 → 화면 표기용 매핑
ENG_LABEL = {"center": "front", "left": "left", "right": "right",
             "up": "up", "down": "down", "no_face": "no_face"}


def build_engine():
    """우리 앱의 실제 엔진(GazeTracker)을 카메라 없이 판정용으로만 준비한다."""
    try:
        from ai_core.gaze_tracker import GazeTracker
        eng = GazeTracker()           # __init__ 은 카메라를 열지 않는다
        eng._create_landmarker()      # 랜드마커만 생성
        print("[엔진] ai_core.GazeTracker 로드 완료 — 실시간 방향 표시 ON")
        return eng
    except Exception as e:
        print(f"[엔진] 로드 실패 — 방향 표시 없이 캡처만 진행합니다: {e}")
        return None


def open_camera(cam_index):
    """앱과 동일하게 DSHOW 우선으로 카메라를 연다."""
    cap = cv2.VideoCapture(cam_index, cv2.CAP_DSHOW)
    if not cap.isOpened():
        cap = cv2.VideoCapture(cam_index)
    if not cap.isOpened():
        return None
    cap.set(cv2.CAP_PROP_FRAME_WIDTH, 640)
    cap.set(cv2.CAP_PROP_FRAME_HEIGHT, 480)
    return cap


def save_image(out_dir, label, frame, counts, live_dir):
    """프레임을 라벨 폴더에 저장한다 (오버레이 없는 깨끗한 프레임)."""
    counts[label] += 1
    ts = time.strftime("%Y%m%d_%H%M%S")
    fpath = os.path.join(out_dir, label, f"{label}_{ts}_{counts[label]:04d}.jpg")
    cv2.imwrite(fpath, frame)
    print(f"[저장] {fpath}   (실시간 판정: {live_dir})")


def main():
    ap = argparse.ArgumentParser(description="I-Study 웹캠 캡처 (앱과 동일 파이프라인)")
    ap.add_argument("--out", default=os.path.join(BASE_DIR, "captures"),
                    help="저장 폴더 (기본: model_test/captures)")
    ap.add_argument("--cam", type=int, default=0, help="카메라 인덱스 (기본 0)")
    ap.add_argument("--no-flip", action="store_true",
                    help="좌우 반전 끄기 (앱은 기본적으로 반전한다)")
    ap.add_argument("--interval", type=float, default=0.3, help="자동 저장 간격(초)")
    args = ap.parse_args()

    flip = not args.no_flip
    out_dir = os.path.abspath(args.out)
    for label in LABELS:
        os.makedirs(os.path.join(out_dir, label), exist_ok=True)

    cap = open_camera(args.cam)
    if cap is None:
        print("카메라를 열 수 없습니다. 다른 프로그램(앱 포함)이 카메라를 쓰고 있지 않은지 확인하세요.")
        return

    engine = build_engine()

    current = "front"
    auto = False
    last_auto = 0.0
    counts = {l: len([f for f in os.listdir(os.path.join(out_dir, l))
                      if f.lower().endswith(".jpg")]) for l in LABELS}

    print("\n=== 캡처 시작 ===  1~5 라벨선택 / SPACE 저장 / A 자동저장 / Q 종료")
    win = "I-Study Capture (our pipeline)"

    while True:
        ret, frame = cap.read()
        if not ret:
            time.sleep(0.01)
            continue
        if flip:
            frame = cv2.flip(frame, 1)

        save_frame = frame.copy()   # 저장은 오버레이 그리기 전의 깨끗한 프레임

        # ── 실시간 방향 (엔진 그대로) ──
        live_dir = "(engine off)"
        face_ok = False
        if engine is not None:
            try:
                ok, d = engine._detect_gaze(frame)   # 깨끗한 프레임으로 판정
                face_ok = ok
                live_dir = ENG_LABEL.get(d, d)
            except Exception:
                live_dir = "-"

        # ── 화면 오버레이 (영문: 한글은 OpenCV 에서 깨질 수 있어 영문 사용) ──
        h, w = frame.shape[:2]
        cv2.rectangle(frame, (0, 0), (w, 96), (20, 20, 30), -1)
        cv2.putText(frame, f"LABEL: {current.upper()}", (8, 30),
                    cv2.FONT_HERSHEY_SIMPLEX, 0.8, (80, 255, 120), 2)
        ai_color = (80, 255, 120) if face_ok else (60, 60, 220)
        face_txt = "OK" if face_ok else ("?" if engine is None else "none")
        cv2.putText(frame, f"AI now: {live_dir}   FACE: {face_txt}", (8, 60),
                    cv2.FONT_HERSHEY_SIMPLEX, 0.6, ai_color, 1)
        cnt_txt = "  ".join(f"{l}:{counts[l]}" for l in LABELS)
        cv2.putText(frame, cnt_txt, (8, 86),
                    cv2.FONT_HERSHEY_SIMPLEX, 0.5, (180, 180, 180), 1)
        guide = "AUTO-SAVE ON" if auto else "1-5:label  SPACE:save  A:auto  Q:quit"
        cv2.putText(frame, guide, (8, h - 12), cv2.FONT_HERSHEY_SIMPLEX, 0.5,
                    (0, 220, 255) if auto else (160, 160, 160), 1)

        cv2.imshow(win, frame)

        # ── 자동 저장 ──
        now = time.time()
        if auto and now - last_auto >= args.interval:
            last_auto = now
            save_image(out_dir, current, save_frame, counts, live_dir)

        # ── 키 입력 ──
        key = cv2.waitKey(1) & 0xFF
        if key in (ord("q"), 27):
            break
        elif ord("1") <= key <= ord("5"):
            current = LABELS[key - ord("1")]
            print(f"[라벨] → {current} ({LABEL_KO[current]})")
        elif key == ord(" "):
            save_image(out_dir, current, save_frame, counts, live_dir)
            # 저장 플래시
            flash = frame.copy()
            cv2.rectangle(flash, (0, 0), (w, h), (255, 255, 255), -1)
            cv2.addWeighted(flash, 0.25, frame, 0.75, 0, frame)
            cv2.imshow(win, frame)
            cv2.waitKey(60)
        elif key == ord("a"):
            auto = not auto
            print(f"[자동저장] {'ON' if auto else 'OFF'}")

    cap.release()
    cv2.destroyAllWindows()

    print("\n=== 캡처 종료 ===")
    for l in LABELS:
        print(f"  {l:6s}: {counts[l]}장")
    print(f"\n저장 위치: {out_dir}")
    print(f'판정 실행:  python model_test/judge_webcam.py "{out_dir}" --save')


if __name__ == "__main__":
    main()
