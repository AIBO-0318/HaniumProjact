"""
I-Study 방향 인식률 테스트 — AFLW2000 자동 라벨링
====================================================
AFLW2000 데이터셋의 .mat 파일에서 yaw/pitch 각도를 읽어
방향(front/left/right/up/down)을 자동 판정하고
해당 폴더로 이미지를 복사합니다.

실행:
  python model_test/auto_label.py
"""

import os
import shutil
import glob
import numpy as np
import scipy.io

# ── 경로 ──
PICTURE_DIR = os.path.join(os.path.dirname(__file__), "data", "picture")
DATA_DIR    = os.path.join(os.path.dirname(__file__), "data")
LABELS      = ["front", "left", "right", "up", "down"]

# ── 방향 판정 임계값 (도) ──
YAW_THR   = 20.0   # 절댓값 기준 좌/우
PITCH_THR = 15.0   # 절댓값 기준 위/아래


def classify(yaw_deg, pitch_deg):
    """yaw/pitch 각도 → 방향 라벨"""
    if abs(yaw_deg) >= YAW_THR:
        return "left" if yaw_deg < 0 else "right"
    if pitch_deg < -PITCH_THR:
        return "up"
    if pitch_deg > PITCH_THR:
        return "down"
    return "front"


def load_pose(mat_path):
    """
    AFLW2000 .mat에서 (yaw_deg, pitch_deg) 반환.
    Pose_Para shape: (1, N) — [pitch, yaw, roll, tx, ty, tz, scale] (라디안)
    """
    try:
        mat = scipy.io.loadmat(mat_path)
    except Exception as e:
        return None, None

    # 키 탐색 (pt2d, Pose_Para, pose_para 등 버전마다 다를 수 있음)
    pose = None
    for key in ["Pose_Para", "pose_para", "pose"]:
        if key in mat:
            pose = mat[key].flatten()
            break

    if pose is None or len(pose) < 2:
        return None, None

    # AFLW2000: Pose_Para = [pitch, yaw, roll, ...] (라디안)
    pitch_deg = np.degrees(pose[0])
    yaw_deg   = np.degrees(pose[1])
    return yaw_deg, pitch_deg


def main():
    # .jpg 수집 (하위 폴더 포함)
    jpg_files = glob.glob(os.path.join(PICTURE_DIR, "**", "*.jpg"), recursive=True)
    jpg_files += glob.glob(os.path.join(PICTURE_DIR, "**", "*.JPG"), recursive=True)

    if not jpg_files:
        print("picture 폴더에 .jpg 파일이 없습니다.")
        return

    print(f"총 {len(jpg_files)}개 이미지 처리 중...\n")

    counts   = {l: 0 for l in LABELS}
    skipped  = 0

    for jpg_path in sorted(jpg_files):
        mat_path = os.path.splitext(jpg_path)[0] + ".mat"

        if not os.path.exists(mat_path):
            skipped += 1
            continue

        yaw, pitch = load_pose(mat_path)
        if yaw is None:
            skipped += 1
            continue

        label = classify(yaw, pitch)
        dst_dir = os.path.join(DATA_DIR, label)
        os.makedirs(dst_dir, exist_ok=True)

        # 파일명 충돌 방지
        basename = os.path.basename(jpg_path)
        dst_path = os.path.join(dst_dir, basename)
        if os.path.exists(dst_path):
            name, ext = os.path.splitext(basename)
            dst_path = os.path.join(dst_dir, f"{name}_{counts[label]}{ext}")

        shutil.copy2(jpg_path, dst_path)
        counts[label] += 1
        print(f"  [{label:6s}]  yaw={yaw:+6.1f}°  pitch={pitch:+6.1f}°  → {os.path.basename(dst_path)}")

    print("\n=== 분류 결과 ===")
    total_ok = sum(counts.values())
    for label in LABELS:
        bar    = "█" * counts[label]
        status = "✅" if counts[label] >= 10 else "⚠️  (10장 이상 권장)"
        print(f"  {label:8s}: {counts[label]:3d}장  {bar}  {status}")
    print(f"\n  처리 완료: {total_ok}장  |  스킵: {skipped}장")

    if total_ok > 0:
        print("\n다음 단계:")
        print("  python model_test/train.py")


if __name__ == "__main__":
    main()
