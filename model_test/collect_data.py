"""
I-Study 방향 인식률 테스트 — 데이터 수집
========================================
방향 5종: front / left / right / up / down

조작:
  1 = 정면   2 = 좌측   3 = 우측   4 = 위   5 = 아래
  SPACE = 현재 방향으로 이미지 저장
  Q     = 종료
"""

import os
import cv2
import mediapipe as mp

LABELS = ["front", "left", "right", "up", "down"]
LABEL_KO = {"front": "정면", "left": "좌측", "right": "우측", "up": "위쪽", "down": "아래"}
DATA_DIR = os.path.join(os.path.dirname(__file__), "data")

for label in LABELS:
    os.makedirs(os.path.join(DATA_DIR, label), exist_ok=True)

mp_face_mesh = mp.solutions.face_mesh


def count_images():
    return {
        label: len([f for f in os.listdir(os.path.join(DATA_DIR, label)) if f.endswith(".jpg")])
        for label in LABELS
    }


def main():
    cap = cv2.VideoCapture(0)
    if not cap.isOpened():
        print("카메라를 열 수 없습니다.")
        return

    current_label = LABELS[0]

    with mp_face_mesh.FaceMesh(
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
            h, w = frame.shape[:2]
            rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
            results = face_mesh.process(rgb)
            face_ok = results.multi_face_landmarks is not None

            counts = count_images()

            # ── 상단 패널 ──
            cv2.rectangle(frame, (0, 0), (w, 115), (20, 20, 30), -1)

            label_ko = LABEL_KO[current_label]
            color = (80, 255, 120) if face_ok else (60, 60, 200)
            cv2.putText(frame, f"  [{current_label.upper()}]  {label_ko}",
                        (8, 38), cv2.FONT_HERSHEY_SIMPLEX, 1.0, color, 2)

            face_txt = "얼굴 감지 OK" if face_ok else "얼굴 없음 — 카메라 확인"
            cv2.putText(frame, face_txt,
                        (8, 68), cv2.FONT_HERSHEY_SIMPLEX, 0.6, color, 1)

            cnt_txt = "  ".join(f"{l}:{c}" for l, c in counts.items())
            cv2.putText(frame, cnt_txt,
                        (8, 95), cv2.FONT_HERSHEY_SIMPLEX, 0.45, (180, 180, 180), 1)

            # ── 하단 안내 ──
            guide = "1:정면  2:좌  3:우  4:위  5:아래  |  SPACE:저장  Q:종료"
            cv2.putText(frame, guide,
                        (8, h - 10), cv2.FONT_HERSHEY_SIMPLEX, 0.45, (160, 160, 160), 1)

            cv2.imshow("I-Study — 데이터 수집", frame)

            key = cv2.waitKey(1) & 0xFF
            if key == ord("q"):
                break
            elif ord("1") <= key <= ord("5"):
                current_label = LABELS[key - ord("1")]
                print(f"[라벨 변경] → {current_label}")
            elif key == ord(" "):
                if not face_ok:
                    print("얼굴이 감지되지 않아 저장 건너뜀")
                    continue
                save_dir = os.path.join(DATA_DIR, current_label)
                idx = counts[current_label]
                fpath = os.path.join(save_dir, f"img_{idx:04d}.jpg")
                cv2.imwrite(fpath, frame)
                print(f"[저장] {fpath}")
                # 캡처 플래시
                flash = frame.copy()
                cv2.rectangle(flash, (0, 0), (w, h), (255, 255, 255), -1)
                cv2.addWeighted(flash, 0.25, frame, 0.75, 0, frame)
                cv2.imshow("I-Study — 데이터 수집", frame)
                cv2.waitKey(80)

    cap.release()
    cv2.destroyAllWindows()

    print("\n=== 수집 완료 ===")
    for label, cnt in count_images().items():
        status = "✅" if cnt >= 30 else "⚠️  (30장 이상 권장)"
        print(f"  {label:8s}: {cnt:3d}장  {status}")


if __name__ == "__main__":
    main()
