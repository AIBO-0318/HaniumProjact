"""
I-Study 방향 인식 성능 데모 — (2) 사진 방향 판정 도구
=========================================================
저장된 사진들을 **우리 앱의 실제 엔진**(ai_core/gaze_tracker.py)으로 판정해
각 사진을 어느 방향으로 인식하는지 출력한다.

핵심:
  - predict.py(model.pkl, 학습 분류기) 가 아니라, 실제 제품이 쓰는
    MediaPipe FaceLandmarker + 기하 계산 엔진을 그대로 사용한다.
  - 폴더명이 라벨(front/center/left/right/up/down)이면 정확도 / 클래스별 정확도 /
    혼동행렬까지 출력한다. (center 와 front 는 같은 클래스로 취급)
  - 결과를 CSV 로 저장하고, --save 로 판정 결과를 사진 위에 그려 저장한다.

사용법:
  # 폴더 전체 판정 (하위 라벨 폴더 자동 인식)
  python model_test/judge_webcam.py model_test/captures

  # 사진 몇 장만
  python model_test/judge_webcam.py 사진1.jpg 사진2.png

  # 판정 결과를 이미지에 그려 model_test/judge_out/ 에 저장
  python model_test/judge_webcam.py model_test/captures --save

  # 임의의 사진(앱 반전 안 된 사진)을 앱과 같은 기준으로 보려면 --flip
  python model_test/judge_webcam.py 외부사진.jpg --flip
"""

import os
import sys
import csv
import glob
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

IMG_EXTS = (".jpg", ".jpeg", ".png", ".bmp", ".webp")
LABEL_KO = {"front": "정면", "center": "정면", "left": "좌측", "right": "우측",
            "up": "위쪽", "down": "아래", "no_face": "얼굴없음"}
KNOWN = {"front", "center", "left", "right", "up", "down"}
ORDER = ["front", "left", "right", "up", "down"]


def norm(label):
    """center 와 front 를 같은 클래스로 취급한다."""
    return "front" if label == "center" else label


def collect_image_paths(args_paths):
    """CLI 인자 → 실제 이미지 경로 목록 (폴더면 하위 전체)."""
    paths = []
    for a in args_paths:
        if os.path.isdir(a):
            for ext in IMG_EXTS:
                paths += glob.glob(os.path.join(a, "**", "*" + ext), recursive=True)
        elif os.path.isfile(a):
            paths.append(a)
        else:
            print(f"  경로 없음: {a}")
    return sorted(set(os.path.normpath(p) for p in paths))


def build_engine(left, right, up, down):
    """우리 앱의 실제 엔진을 카메라 없이 준비한다."""
    from ai_core.gaze_tracker import GazeTracker
    eng = GazeTracker()          # __init__ 은 카메라를 열지 않는다
    eng._create_landmarker()
    # 임계값은 앱 기본값과 동일 (필요하면 CLI 로 조정)
    eng.left_threshold = left
    eng.right_threshold = right
    eng.up_threshold = up
    eng.down_threshold = down
    return eng


def annotate(img, pred, out_dir, name):
    cv2.rectangle(img, (0, 0), (img.shape[1], 40), (0, 0, 0), -1)
    cv2.putText(img, f"AI: {pred}", (10, 28), cv2.FONT_HERSHEY_SIMPLEX,
                0.9, (0, 255, 120), 2, cv2.LINE_AA)
    cv2.imwrite(os.path.join(out_dir, "judged_" + name), img)


def print_binary_metrics(confusion):
    """5클래스 혼동행렬을 '정상(front/center) vs 이탈(좌·우·상·하)' 2분류로 접어
    정밀도·재현율·F1·F2 출력 (양성=이탈)."""
    AWAY = {"left", "right", "up", "down"}

    def away(c):
        return c in AWAY

    TP = FP = FN = TN = 0
    for (t, p), n in confusion.items():
        if away(t) and away(p):
            TP += n
        elif (not away(t)) and away(p):
            FP += n
        elif away(t) and (not away(p)):
            FN += n
        else:
            TN += n
    total = TP + FP + FN + TN
    if total == 0:
        return
    prec = TP / (TP + FP) if (TP + FP) else 0.0
    rec = TP / (TP + FN) if (TP + FN) else 0.0
    f1 = 2 * prec * rec / (prec + rec) if (prec + rec) else 0.0
    f2 = 5 * prec * rec / (4 * prec + rec) if (4 * prec + rec) else 0.0   # β=2 (재현율 가중)
    acc = (TP + TN) / total

    print("\n  ── '정상 vs 이탈' 2분류 지표 (양성=이탈) ──")
    print(f"    TP(이탈→이탈)={TP}   FN(이탈→정상, 놓침)={FN}")
    print(f"    FP(정상→이탈, 헛알람)={FP}   TN(정상→정상)={TN}")
    print(f"    정밀도(Precision)   : {prec:.1%}")
    print(f"    재현율(Recall)      : {rec:.1%}")
    print(f"    F1-score            : {f1:.3f}")
    print(f"    F2-score(재현율 가중): {f2:.3f}")
    print(f"    정확도(2분류)       : {acc:.1%}")


def print_summary(confusion, labels_present, n_correct, n_labeled):
    acc = n_correct / n_labeled if n_labeled else 0.0
    print(f"\n  ▶ 전체 정확도: {acc:.1%}  ({n_correct}/{n_labeled})")

    order = [l for l in ORDER if l in labels_present]

    print("\n  클래스별 재현율(Recall):")
    for t in order:
        tot = sum(confusion.get((t, p), 0) for p in order)
        cor = confusion.get((t, t), 0)
        if tot:
            print(f"    {LABEL_KO.get(t, t):4s}: {cor / tot:5.1%}  ({cor}/{tot})")

    print("\n  혼동행렬 (행=정답, 열=예측):")
    print("          " + "".join(f"{p:>7}" for p in order))
    for t in order:
        print(f"    {t:6s}" + "".join(f"{confusion.get((t, p), 0):>7}" for p in order))

    print_binary_metrics(confusion)


def main():
    ap = argparse.ArgumentParser(description="저장된 사진을 우리 앱 엔진으로 방향 판정")
    ap.add_argument("paths", nargs="+", help="이미지 파일 또는 폴더 (폴더면 하위 전체)")
    ap.add_argument("--save", action="store_true",
                    help="판정 결과를 사진 위에 그려 model_test/judge_out/ 에 저장")
    ap.add_argument("--flip", action="store_true",
                    help="판정 전에 좌우 반전 (capture_webcam.py 로 만든 사진엔 불필요)")
    ap.add_argument("--csv", default=os.path.join(BASE_DIR, "judge_results.csv"),
                    help="결과 CSV 경로")
    ap.add_argument("--limit", type=int, default=0,
                    help="앞에서 N장만 판정 (0=전체, 대용량 폴더 빠른 확인용)")
    ap.add_argument("--left", type=float, default=0.20)
    ap.add_argument("--right", type=float, default=0.80)
    ap.add_argument("--up", type=float, default=0.38)
    ap.add_argument("--down", type=float, default=0.62)
    args = ap.parse_args()

    images = collect_image_paths(args.paths)
    if not images:
        print("판정할 이미지를 찾지 못했습니다.")
        return
    if args.limit:
        images = images[:args.limit]

    engine = build_engine(args.left, args.right, args.up, args.down)
    out_dir = os.path.join(BASE_DIR, "judge_out")
    if args.save:
        os.makedirs(out_dir, exist_ok=True)

    print("엔진: ai_core.GazeTracker (MediaPipe FaceLandmarker + 기하 계산)")
    print(f"임계값  L<{args.left}  R>{args.right}  U<{args.up}  D>{args.down}")
    print(f"이미지 {len(images)}장 판정 시작\n")

    rows = []
    labels_present = set()
    confusion = {}                     # (정답, 예측) -> 개수
    n_judge = n_noface = n_correct = n_labeled = 0

    for path in images:
        img = cv2.imread(path)
        name = os.path.basename(path)
        if img is None:
            print(f"  [읽기 실패] {name}")
            continue
        if args.flip:
            img = cv2.flip(img, 1)

        ok, direction = engine._detect_gaze(img)

        if not ok:
            n_noface += 1
            print(f"  [얼굴 미감지]  {name}")
            rows.append([path, "", "no_face", "", "", ""])
            if args.save:
                annotate(img, "no_face", out_dir, name)
            continue

        n_judge += 1
        pred = norm(direction)
        h_ratio = round(engine.current_gaze_ratio, 3)
        v_ratio = round(engine.vertical_gaze_ratio, 3)

        parent = os.path.basename(os.path.dirname(path)).lower()
        true_label = norm(parent) if parent in KNOWN else ""
        correct_str = ""
        mark = ""
        if true_label:
            labels_present.add(true_label)
            labels_present.add(pred)
            n_labeled += 1
            hit = (true_label == pred)
            n_correct += int(hit)
            confusion[(true_label, pred)] = confusion.get((true_label, pred), 0) + 1
            correct_str = "1" if hit else "0"
            mark = "  OK" if hit else f"  X(정답:{LABEL_KO.get(true_label, true_label)})"

        print(f"  {LABEL_KO.get(pred, pred):4s}  h={h_ratio:.3f} v={v_ratio:.3f}{mark}   {name}")
        rows.append([path, true_label, pred, correct_str, h_ratio, v_ratio])
        if args.save:
            annotate(img, pred, out_dir, name)

    # 엔진 정리
    try:
        if engine.landmarker:
            engine.landmarker.close()
    except Exception:
        pass

    # CSV 저장 (엑셀 호환 위해 utf-8-sig)
    with open(args.csv, "w", newline="", encoding="utf-8-sig") as f:
        w = csv.writer(f)
        w.writerow(["path", "true_label", "predicted", "correct", "h_ratio", "v_ratio"])
        w.writerows(rows)

    print("\n=== 판정 완료 ===")
    print(f"  판정: {n_judge}장   얼굴 미감지: {n_noface}장")
    print(f"  결과 CSV: {args.csv}")
    if args.save:
        print(f"  주석 이미지: {out_dir}")

    if n_labeled:
        print_summary(confusion, labels_present, n_correct, n_labeled)
    else:
        print("\n  (폴더명이 라벨이 아니라 정확도는 계산하지 않았습니다. "
              "정확도를 보려면 front/left/right/up/down 폴더로 정리하세요.)")


if __name__ == "__main__":
    main()
