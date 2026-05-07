"""
I-Study - 고개 방향 인식률 테스트 도구 (독립 실행 버전)
메인 앱(GazeTracker)과 동일한 알고리즘으로 상하좌우 인식률 측정

사용법:
  python test_head_pose.py

조작키:
  [C] 캘리브레이션 (정면 응시 상태에서 누르기, 10회)
  [1] 정면(Center) 테스트 시작/종료
  [2] 왼쪽(Left) 테스트 시작/종료
  [3] 오른쪽(Right) 테스트 시작/종료
  [4] 위(Up) 테스트 시작/종료
  [5] 아래(Down) 테스트 시작/종료
  [R] 결과 리포트 출력
  [ESC/Q] 종료
"""

import cv2
import numpy as np
import os
import sys
import time
import urllib.request
import json
from datetime import datetime

import mediapipe as mp
from mediapipe.tasks import python
from mediapipe.tasks.python import vision
from mediapipe import Image, ImageFormat

# ─── 설정 (GazeTracker와 동일한 랜드마크/임계값) ────────
MODEL_URL = "https://storage.googleapis.com/mediapipe-models/face_landmarker/face_landmarker/float16/1/face_landmarker.task"

# 메인 앱 GazeTracker와 동일한 랜드마크 인덱스
NOSE_TIP = 1
LEFT_EYE_OUTER = 33
RIGHT_EYE_OUTER = 263
LEFT_FACE_EDGE = 234
RIGHT_FACE_EDGE = 454
FOREHEAD = 10
CHIN = 152

# 눈 감음 감지 랜드마크
LEFT_EYE_TOP = 159
LEFT_EYE_BOTTOM = 145
RIGHT_EYE_TOP = 386
RIGHT_EYE_BOTTOM = 374

# 메인 앱과 동일한 기본 임계값
LEFT_THRESHOLD = 0.20
RIGHT_THRESHOLD = 0.80
UP_THRESHOLD = 0.38
DOWN_THRESHOLD = 0.62
EYE_CLOSURE_THRESHOLD = 0.010

# 테스트 샘플 수집 시간
TEST_DURATION_SEC = 5.0

DIRECTION_NAMES = {
    "center": "정면(Center)",
    "left":   "왼쪽(Left)",
    "right":  "오른쪽(Right)",
    "up":     "위(Up)",
    "down":   "아래(Down)",
}
DIRECTION_COLORS = {
    "center": (0, 255, 0),
    "left":   (255, 165, 0),
    "right":  (0, 165, 255),
    "up":     (255, 255, 0),
    "down":   (0, 255, 255),
}
KEY_MAP = {
    ord('1'): "center",
    ord('2'): "left",
    ord('3'): "right",
    ord('4'): "up",
    ord('5'): "down",
}


# ─── 모델 다운로드 ──────────────────────────────────────
def ensure_model() -> str:
    """현재 디렉토리에 모델 저장"""
    script_dir = os.path.dirname(os.path.abspath(__file__))
    model_path = os.path.join(script_dir, "face_landmarker.task")
    
    if os.path.exists(model_path):
        print(f"✅ 모델 로드: {model_path}")
        return model_path
    
    print("📥 모델 다운로드 중... (약 50MB, 1~2분 소요)")
    try:
        urllib.request.urlretrieve(MODEL_URL, model_path)
        print("✅ 모델 다운로드 완료")
        return model_path
    except Exception as e:
        print(f"❌ 모델 다운로드 실패: {e}")
        sys.exit(1)


# ─── 방향 계산 (GazeTracker._calculate_head_direction 과 동일) ──
def calculate_head_ratio(landmarks):
    """좌우 방향: 코 위치를 얼굴 좌우 가장자리 기준으로 비율 계산"""
    nose = landmarks[NOSE_TIP]
    left_edge = landmarks[LEFT_FACE_EDGE]
    right_edge = landmarks[RIGHT_FACE_EDGE]

    face_center_x = (left_edge.x + right_edge.x) / 2
    face_width = abs(right_edge.x - left_edge.x)

    if face_width < 0.001:
        return 0.5

    offset = (nose.x - face_center_x) / face_width
    ratio = 0.5 + offset
    return max(0.0, min(1.0, ratio))


def calculate_vertical_ratio(landmarks):
    """상하 방향: 코 위치를 이마-턱 기준으로 비율 계산"""
    nose = landmarks[NOSE_TIP]
    forehead = landmarks[FOREHEAD]
    chin = landmarks[CHIN]

    face_center_y = (forehead.y + chin.y) / 2
    face_height = abs(chin.y - forehead.y)

    if face_height < 0.001:
        return 0.5

    offset = (nose.y - face_center_y) / face_height
    ratio = 0.5 + offset
    return max(0.0, min(1.0, ratio))


def detect_eye_closure(landmarks):
    """눈 감음 감지 (GazeTracker._detect_eye_closure 과 동일)"""
    left_h = abs(landmarks[LEFT_EYE_TOP].y - landmarks[LEFT_EYE_BOTTOM].y)
    right_h = abs(landmarks[RIGHT_EYE_TOP].y - landmarks[RIGHT_EYE_BOTTOM].y)
    avg = (left_h + right_h) / 2
    return avg < EYE_CLOSURE_THRESHOLD


def classify_direction(h_ratio, v_ratio, thresholds):
    """메인 앱 GazeTracker._detect_gaze 과 동일한 판정 순서"""
    if v_ratio < thresholds["up"]:
        return "up"
    if v_ratio > thresholds["down"]:
        return "down"
    if h_ratio < thresholds["left"]:
        return "left"
    if h_ratio > thresholds["right"]:
        return "right"
    return "center"


# ─── 화면 그리기 헬퍼 ───────────────────────────────────
def draw_overlay(frame, h_ratio, v_ratio, eyes_closed, direction,
                 thresholds, calib, test_state, results):
    h, w = frame.shape[:2]
    color = DIRECTION_COLORS.get(direction, (255, 255, 255))

    # 비율 정보 (메인 앱과 동일한 값)
    cv2.putText(frame, f"H Ratio: {h_ratio:.3f}  (L<{thresholds['left']:.2f}  R>{thresholds['right']:.2f})",
                (10, 30), cv2.FONT_HERSHEY_SIMPLEX, 0.55, (255, 255, 255), 1)
    cv2.putText(frame, f"V Ratio: {v_ratio:.3f}  (U<{thresholds['up']:.2f}  D>{thresholds['down']:.2f})",
                (10, 55), cv2.FONT_HERSHEY_SIMPLEX, 0.55, (255, 255, 255), 1)

    # 눈 상태
    eye_txt = "CLOSED" if eyes_closed else "OPEN"
    eye_color = (0, 0, 255) if eyes_closed else (0, 255, 0)
    cv2.putText(frame, f"Eyes: {eye_txt}", (10, 80),
                cv2.FONT_HERSHEY_SIMPLEX, 0.55, eye_color, 1)

    # 방향 표시
    dir_text = DIRECTION_NAMES.get(direction, direction)
    cv2.putText(frame, f"Direction: {dir_text}", (10, 115),
                cv2.FONT_HERSHEY_SIMPLEX, 0.9, color, 2)

    # 비율 바 시각화 (좌우)
    bar_y = 145
    bar_x, bar_w = 10, 300
    cv2.rectangle(frame, (bar_x, bar_y), (bar_x + bar_w, bar_y + 20), (50, 50, 50), -1)
    marker_x = int(bar_x + h_ratio * bar_w)
    cv2.circle(frame, (marker_x, bar_y + 10), 8, color, -1)
    # 임계값 선
    lx = int(bar_x + thresholds["left"] * bar_w)
    rx = int(bar_x + thresholds["right"] * bar_w)
    cv2.line(frame, (lx, bar_y), (lx, bar_y + 20), (0, 0, 255), 2)
    cv2.line(frame, (rx, bar_y), (rx, bar_y + 20), (0, 0, 255), 2)
    cv2.putText(frame, "L", (lx - 5, bar_y - 5), cv2.FONT_HERSHEY_SIMPLEX, 0.35, (0, 0, 255), 1)
    cv2.putText(frame, "R", (rx - 5, bar_y - 5), cv2.FONT_HERSHEY_SIMPLEX, 0.35, (0, 0, 255), 1)

    # 비율 바 시각화 (상하)
    bar_y2 = 175
    cv2.rectangle(frame, (bar_x, bar_y2), (bar_x + bar_w, bar_y2 + 20), (50, 50, 50), -1)
    marker_y = int(bar_x + v_ratio * bar_w)
    cv2.circle(frame, (marker_y, bar_y2 + 10), 8, color, -1)
    uy = int(bar_x + thresholds["up"] * bar_w)
    dy = int(bar_x + thresholds["down"] * bar_w)
    cv2.line(frame, (uy, bar_y2), (uy, bar_y2 + 20), (0, 0, 255), 2)
    cv2.line(frame, (dy, bar_y2), (dy, bar_y2 + 20), (0, 0, 255), 2)
    cv2.putText(frame, "U", (uy - 5, bar_y2 - 5), cv2.FONT_HERSHEY_SIMPLEX, 0.35, (0, 0, 255), 1)
    cv2.putText(frame, "D", (dy - 5, bar_y2 - 5), cv2.FONT_HERSHEY_SIMPLEX, 0.35, (0, 0, 255), 1)

    # 캘리브레이션 상태
    if calib["done"]:
        cv2.putText(frame, f"[CAL] center_h={calib['center_h']:.3f}  center_v={calib['center_v']:.3f}",
                    (10, h - 20), cv2.FONT_HERSHEY_SIMPLEX, 0.45, (0, 255, 0), 1)
    else:
        cv2.putText(frame, "[C] Press C to calibrate (look at center)",
                    (10, h - 20), cv2.FONT_HERSHEY_SIMPLEX, 0.5, (0, 0, 255), 1)

    # 테스트 진행 상태
    if test_state["active"]:
        target = DIRECTION_NAMES[test_state["target"]]
        elapsed = time.time() - test_state["start"]
        remaining = max(0, TEST_DURATION_SEC - elapsed)
        total = test_state["total"]
        correct = test_state["correct"]
        rate = (correct / total * 100) if total > 0 else 0
        cv2.putText(frame, f"TESTING [{target}]  {remaining:.1f}s left  ({correct}/{total} = {rate:.0f}%)",
                    (10, h - 50), cv2.FONT_HERSHEY_SIMPLEX, 0.6, (0, 0, 255), 2)

    # 우측 상단: 결과 요약
    y_pos = 30
    cv2.putText(frame, "=== Results ===", (w - 260, y_pos),
                cv2.FONT_HERSHEY_SIMPLEX, 0.55, (255, 255, 255), 1)
    for d_key in ["center", "left", "right", "up", "down"]:
        y_pos += 25
        if d_key in results:
            r = results[d_key]
            txt = f"{DIRECTION_NAMES[d_key]}: {r['rate']:.1f}% ({r['correct']}/{r['total']})"
            cv2.putText(frame, txt, (w - 260, y_pos),
                        cv2.FONT_HERSHEY_SIMPLEX, 0.45, DIRECTION_COLORS[d_key], 1)
        else:
            txt = f"{DIRECTION_NAMES[d_key]}: --"
            cv2.putText(frame, txt, (w - 260, y_pos),
                        cv2.FONT_HERSHEY_SIMPLEX, 0.45, (128, 128, 128), 1)

    # 조작 안내
    cv2.putText(frame, "[1]Center [2]Left [3]Right [4]Up [5]Down [R]Report [Q]Quit",
                (10, h - 85), cv2.FONT_HERSHEY_SIMPLEX, 0.4, (200, 200, 200), 1)


def draw_no_face(frame):
    h, w = frame.shape[:2]
    cv2.putText(frame, "No Face Detected", (w // 2 - 120, h // 2),
                cv2.FONT_HERSHEY_SIMPLEX, 0.9, (0, 0, 255), 2)


def save_results(results, thresholds):
    """테스트 결과를 JSON 파일로 저장"""
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    filename = f"test_results_{timestamp}.json"
    
    # 평균 정확도 계산
    if results:
        avg_rate = np.mean([r["rate"] for r in results.values()])
    else:
        avg_rate = 0.0
    
    # 저장할 데이터
    data = {
        "timestamp": datetime.now().isoformat(),
        "average_accuracy": round(avg_rate, 1),
        "results": {
            direction: {
                "accuracy": round(r["rate"], 1),
                "correct": r["correct"],
                "total": r["total"]
            }
            for direction, r in results.items()
        },
        "thresholds": {
            "left": round(thresholds["left"], 3),
            "right": round(thresholds["right"], 3),
            "up": round(thresholds["up"], 3),
            "down": round(thresholds["down"], 3),
        }
    }
    
    # 파일 저장
    with open(filename, 'w', encoding='utf-8') as f:
        json.dump(data, f, indent=2, ensure_ascii=False)
    
    print(f"\n✅ 결과 저장됨: {filename}")
    return filename


def print_report(results, thresholds):
    print("\n" + "=" * 60)
    print("        I-Study 고개 방향 인식률 테스트 결과")
    print("=" * 60)
    total_all, correct_all = 0, 0
    for d_key in ["center", "left", "right", "up", "down"]:
        if d_key in results:
            r = results[d_key]
            total_all += r["total"]
            correct_all += r["correct"]
            bar = "█" * int(r["rate"] / 5) + "░" * (20 - int(r["rate"] / 5))
            print(f"  {DIRECTION_NAMES[d_key]:12s}  {bar}  {r['rate']:5.1f}%  ({r['correct']}/{r['total']})")
        else:
            print(f"  {DIRECTION_NAMES[d_key]:12s}  {'░' * 20}  미측정")
    print("-" * 60)
    if total_all > 0:
        overall = correct_all / total_all * 100
        bar = "█" * int(overall / 5) + "░" * (20 - int(overall / 5))
        print(f"  {'전체(Total)':12s}  {bar}  {overall:5.1f}%  ({correct_all}/{total_all})")
    print("-" * 60)
    print(f"  임계값: Left<{thresholds['left']:.2f}  Right>{thresholds['right']:.2f}"
          f"  Up<{thresholds['up']:.2f}  Down>{thresholds['down']:.2f}")
    print("=" * 60 + "\n")


# ─── 메인 ───────────────────────────────────────────────
def main():
    model_path = ensure_model()

    # MediaPipe FaceLandmarker 생성 (메인 앱과 동일한 옵션)
    base_options = python.BaseOptions(model_asset_path=model_path)
    options = vision.FaceLandmarkerOptions(
        base_options=base_options,
        output_face_blendshapes=False,
        output_facial_transformation_matrixes=False,
        num_faces=1,
    )
    landmarker = vision.FaceLandmarker.create_from_options(options)

    # 카메라 (메인 앱과 동일)
    cap = cv2.VideoCapture(0, cv2.CAP_DSHOW)
    if not cap.isOpened():
        cap = cv2.VideoCapture(0)
    if not cap.isOpened():
        print("❌ 카메라를 열 수 없습니다.")
        return
    cap.set(cv2.CAP_PROP_FRAME_WIDTH, 640)
    cap.set(cv2.CAP_PROP_FRAME_HEIGHT, 480)

    # 임계값 (메인 앱 기본값과 동일)
    thresholds = {
        "left": LEFT_THRESHOLD,
        "right": RIGHT_THRESHOLD,
        "up": UP_THRESHOLD,
        "down": DOWN_THRESHOLD,
    }

    # 캘리브레이션 상태
    calib = {
        "done": False,
        "center_h": 0.5,
        "center_v": 0.5,
        "samples_h": [],
        "samples_v": [],
    }

    test_state = {"active": False, "target": "", "start": 0, "total": 0, "correct": 0}
    results = {}

    print("\n" + "=" * 60)
    print("    I-Study 고개 방향 인식률 테스트 도구 (독립 실행 버전)")
    print("=" * 60)
    print("  (메인 앱 GazeTracker와 동일한 알고리즘 사용)")
    print("  [C] 캘리브레이션 (정면 응시 후 10번 누르기)")
    print("  [1~5] 방향 테스트 시작/종료 (5초)")
    print("  [R] 결과 리포트 | [Q/ESC] 종료")
    print("=" * 60 + "\n")

    while True:
        ret, frame = cap.read()
        if not ret:
            continue
        frame = cv2.flip(frame, 1)  # 메인 앱과 동일하게 좌우 반전
        fh, fw = frame.shape[:2]

        # MediaPipe 검출
        rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
        mp_image = Image(image_format=ImageFormat.SRGB, data=rgb)
        detection = landmarker.detect(mp_image)

        h_ratio = 0.5
        v_ratio = 0.5
        eyes_closed = False
        direction = "no_face"

        if detection.face_landmarks:
            lm = detection.face_landmarks[0]

            # 메인 앱과 동일한 계산
            h_ratio = calculate_head_ratio(lm)
            v_ratio = calculate_vertical_ratio(lm)
            eyes_closed = detect_eye_closure(lm)
            direction = classify_direction(h_ratio, v_ratio, thresholds)

            # 주요 랜드마크 시각화
            for idx in [NOSE_TIP, LEFT_FACE_EDGE, RIGHT_FACE_EDGE, FOREHEAD, CHIN,
                        LEFT_EYE_OUTER, RIGHT_EYE_OUTER]:
                px = int(lm[idx].x * fw)
                py = int(lm[idx].y * fh)
                cv2.circle(frame, (px, py), 4, (0, 255, 0), -1)

            # 테스트 진행 중 샘플 수집
            if test_state["active"]:
                test_state["total"] += 1
                if direction == test_state["target"]:
                    test_state["correct"] += 1
                if time.time() - test_state["start"] >= TEST_DURATION_SEC:
                    target = test_state["target"]
                    rate = (test_state["correct"] / test_state["total"] * 100) if test_state["total"] > 0 else 0
                    results[target] = {
                        "total": test_state["total"],
                        "correct": test_state["correct"],
                        "rate": rate,
                    }
                    print(f"  ✅ {DIRECTION_NAMES[target]} 테스트 완료: {rate:.1f}% ({test_state['correct']}/{test_state['total']})")
                    test_state["active"] = False

            draw_overlay(frame, h_ratio, v_ratio, eyes_closed, direction,
                         thresholds, calib, test_state, results)
        else:
            draw_no_face(frame)

        cv2.imshow("Head Pose Test - I-Study", frame)
        key = cv2.waitKey(1) & 0xFF

        if key == 27 or key == ord('q'):
            break

        # 캘리브레이션 (메인 앱 complete_calibration 과 동일한 margin=0.15)
        elif key == ord('c'):
            if detection.face_landmarks:
                calib["samples_h"].append(h_ratio)
                calib["samples_v"].append(v_ratio)
                n = len(calib["samples_h"])
                if n >= 10:
                    center_h = float(np.mean(calib["samples_h"]))
                    center_v = float(np.mean(calib["samples_v"]))
                    margin_h = 0.15
                    margin_v = 0.12
                    thresholds["left"] = max(0.1, center_h - margin_h)
                    thresholds["right"] = min(0.9, center_h + margin_h)
                    thresholds["up"] = max(0.1, center_v - margin_v)
                    thresholds["down"] = min(0.9, center_v + margin_v)
                    calib["done"] = True
                    calib["center_h"] = center_h
                    calib["center_v"] = center_v
                    calib["samples_h"].clear()
                    calib["samples_v"].clear()
                    print(f"  ✅ 캘리브레이션 완료")
                    print(f"     center: h={center_h:.3f}, v={center_v:.3f}")
                    print(f"     임계값: L<{thresholds['left']:.2f} R>{thresholds['right']:.2f}"
                          f" U<{thresholds['up']:.2f} D>{thresholds['down']:.2f}")
                else:
                    print(f"  📸 캘리브레이션 샘플 {n}/10 수집... (C를 계속 누르세요)")

        # 테스트 시작/종료 토글
        elif key in KEY_MAP:
            target = KEY_MAP[key]
            if test_state["active"] and test_state["target"] == target:
                rate = (test_state["correct"] / test_state["total"] * 100) if test_state["total"] > 0 else 0
                results[target] = {
                    "total": test_state["total"],
                    "correct": test_state["correct"],
                    "rate": rate,
                }
                print(f"  ✅ {DIRECTION_NAMES[target]} 테스트 종료: {rate:.1f}% ({test_state['correct']}/{test_state['total']})")
                test_state["active"] = False
            elif not test_state["active"]:
                test_state["active"] = True
                test_state["target"] = target
                test_state["start"] = time.time()
                test_state["total"] = 0
                test_state["correct"] = 0
                print(f"  🎯 {DIRECTION_NAMES[target]} 테스트 시작 ({TEST_DURATION_SEC:.0f}초)")

        # 리포트
        elif key == ord('r'):
            print_report(results, thresholds)

    # 정리
    cap.release()
    cv2.destroyAllWindows()
    landmarker.close()

    if results:
        print_report(results, thresholds)
        save_results(results, thresholds)


if __name__ == "__main__":
    main()
