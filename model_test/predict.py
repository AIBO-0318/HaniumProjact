"""
I-Study 방향 인식률 테스트 — 사진 한 장 판단 (단일 이미지 추론)
==================================================================
학습된 model.pkl 로 이미지 파일의 시선/고개 방향을 판단합니다.
정면 / 좌측 / 우측 / 위 / 아래 중 하나로 분류하고 신뢰도를 출력합니다.

이 프로젝트(ai_core)와 동일한 MediaPipe Tasks(FaceLandmarker) API를 사용합니다.

사용법:
  # 사진 한 장 판단
  python model_test/predict.py 사진.jpg

  # 여러 장 한꺼번에
  python model_test/predict.py a.jpg b.jpg c.png

  # 폴더 안의 모든 이미지 판단 (폴더명이 라벨이면 정확도도 표시)
  python model_test/predict.py model_test/data/left

  # 판단 결과를 이미지에 그려서 저장 (model_test/pred_out/ 에 저장)
  python model_test/predict.py 사진.jpg --save
"""

import os
import sys
import glob
import pickle

import cv2
import numpy as np
import mediapipe as mp
from mediapipe.tasks import python as mp_python
from mediapipe.tasks.python import vision

BASE_DIR   = os.path.dirname(__file__)
PROJ_ROOT  = os.path.dirname(BASE_DIR)
MODEL_PATH = os.path.join(BASE_DIR, "model.pkl")
OUT_DIR    = os.path.join(BASE_DIR, "pred_out")

# face_landmarker.task 탐색 (ai_core/gaze_tracker.py 와 같은 위치들)
TASK_CANDIDATES = [
    os.path.join(PROJ_ROOT, "models", "face_landmarker.task"),
    os.path.join(PROJ_ROOT, "ai_core", "models", "face_landmarker.task"),
    os.path.join(BASE_DIR, "face_landmarker.task"),
]

LABEL_KO = {
    "front": "정면",
    "left":  "좌측",
    "right": "우측",
    "up":    "위쪽",
    "down":  "아래",
}
IMG_EXTS = (".jpg", ".jpeg", ".png", ".bmp", ".webp")


def find_task_model():
    for p in TASK_CANDIDATES:
        if os.path.exists(p):
            return p
    return None


def create_landmarker(task_path):
    base_options = mp_python.BaseOptions(model_asset_path=task_path)
    options = vision.FaceLandmarkerOptions(
        base_options=base_options,
        output_face_blendshapes=False,
        output_facial_transformation_matrixes=False,
        num_faces=1,
    )
    return vision.FaceLandmarker.create_from_options(options)


def extract_features(image_path, landmarker, key_lm):
    """이미지 파일 → 정규화된 랜드마크 벡터 (train.py와 동일 방식)"""
    img = cv2.imread(image_path)
    if img is None:
        return None
    rgb = cv2.cvtColor(img, cv2.COLOR_BGR2RGB)
    mp_image = mp.Image(image_format=mp.ImageFormat.SRGB, data=rgb)
    res = landmarker.detect(mp_image)
    if not res.face_landmarks:
        return None
    lm = res.face_landmarks[0]

    raw = []
    for idx in key_lm:
        if idx >= len(lm):
            return None
        raw.extend([lm[idx].x, lm[idx].y, lm[idx].z])

    # 코 끝(첫 랜드마크) 기준 상대 좌표로 정규화
    nx, ny, nz = raw[0], raw[1], raw[2]
    normed = []
    for i in range(0, len(raw), 3):
        normed.extend([raw[i] - nx, raw[i + 1] - ny, raw[i + 2] - nz])
    return np.array([normed], dtype=np.float32)


def collect_image_paths(args):
    """CLI 인자 → 실제 이미지 경로 목록 (폴더면 내부 이미지 전체)"""
    paths = []
    for a in args:
        if os.path.isdir(a):
            for ext in IMG_EXTS:
                paths += glob.glob(os.path.join(a, "**", "*" + ext), recursive=True)
        elif os.path.isfile(a):
            paths.append(a)
        else:
            print(f"  경로 없음: {a}")
    return sorted(set(os.path.normpath(p) for p in paths))


def save_annotated(image_path, pred, conf):
    """판단 결과를 이미지 위에 그려서 OUT_DIR 에 저장"""
    img = cv2.imread(image_path)
    if img is None:
        return None
    text = f"{pred} ({conf:.0%})"
    cv2.rectangle(img, (0, 0), (img.shape[1], 46), (0, 0, 0), -1)
    cv2.putText(img, text, (12, 32), cv2.FONT_HERSHEY_SIMPLEX,
                1.0, (0, 255, 120), 2, cv2.LINE_AA)
    os.makedirs(OUT_DIR, exist_ok=True)
    out_path = os.path.join(OUT_DIR, "pred_" + os.path.basename(image_path))
    cv2.imwrite(out_path, img)
    return out_path


def main():
    args = [a for a in sys.argv[1:] if not a.startswith("-")]
    save_flag = "--save" in sys.argv[1:]

    if not args:
        print(__doc__)
        print("\n오류: 판단할 이미지 파일(또는 폴더)을 지정하세요.")
        return

    if not os.path.exists(MODEL_PATH):
        print("model.pkl 없음 — 먼저 train.py 를 실행해 모델을 만드세요.")
        return

    task_path = find_task_model()
    if task_path is None:
        print("face_landmarker.task 없음 — 프로젝트를 한 번 실행하면 models/ 에 자동 다운로드됩니다.")
        return

    with open(MODEL_PATH, "rb") as f:
        payload = pickle.load(f)
    model    = payload["model"]
    le       = payload["label_encoder"]
    key_lm   = payload["key_landmarks"]
    mname    = payload.get("model_name", "ML")
    test_acc = payload.get("test_accuracy", 0.0)
    classes  = [str(c) for c in le.classes_]

    print(f"모델: {mname}  (학습 정확도: {test_acc:.1%})")

    image_paths = collect_image_paths(args)
    if not image_paths:
        print("판단할 이미지를 찾지 못했습니다.")
        return
    print(f"이미지 {len(image_paths)}장 판단 시작\n")

    correct = 0          # 폴더명이 정답일 때 맞춘 수
    labeled = 0          # 폴더명이 정답 라벨이었던 판단 수
    judged  = 0
    no_face = 0

    landmarker = create_landmarker(task_path)
    try:
        for path in image_paths:
            feat = extract_features(path, landmarker, key_lm)
            name = os.path.basename(path)

            if feat is None:
                no_face += 1
                print(f"  [얼굴 미감지]  {name}")
                continue

            proba = model.predict_proba(feat)[0]
            idx   = int(np.argmax(proba))
            pred  = classes[idx]
            conf  = float(proba[idx])
            judged += 1

            # 전체 클래스 확률 분포 (내림차순)
            dist = "  ".join(
                f"{LABEL_KO.get(c, c)} {p:.0%}"
                for c, p in sorted(zip(classes, proba), key=lambda t: -t[1])
            )

            # 부모 폴더명이 라벨과 같으면 정답 비교 (data/left 등으로 테스트 시)
            parent = os.path.basename(os.path.dirname(path))
            mark = ""
            if parent in classes:
                ok = parent == pred
                correct += int(ok)
                labeled += 1
                mark = "  OK" if ok else f"  X(정답:{LABEL_KO.get(parent, parent)})"

            print(f"  {LABEL_KO.get(pred, pred):4s} ({conf:5.0%})  | {dist}{mark}   {name}")

            if save_flag:
                out = save_annotated(path, pred, conf)
                if out:
                    print(f"       저장: {out}")
    finally:
        landmarker.close()

    # ── 요약 ──
    print("\n=== 판단 완료 ===")
    print(f"  판단: {judged}장   얼굴 미감지: {no_face}장")
    if labeled:
        acc = correct / labeled
        print(f"  폴더명 기준 정확도: {acc:.1%}  ({correct}/{labeled})")


if __name__ == "__main__":
    main()
