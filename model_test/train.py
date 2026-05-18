"""
I-Study 방향 인식률 테스트 — 모델 학습
========================================
MediaPipe 얼굴 랜드마크 → scikit-learn 분류기
3가지 모델(RandomForest / SVM / MLP) 비교 후 최우수 저장

실행:
  python train.py
"""

import os
import pickle

import cv2
import mediapipe as mp
import numpy as np
import matplotlib
import matplotlib.pyplot as plt
from sklearn.ensemble import RandomForestClassifier
from sklearn.metrics import classification_report, confusion_matrix
from sklearn.model_selection import cross_val_score, train_test_split
from sklearn.neural_network import MLPClassifier
from sklearn.preprocessing import LabelEncoder
from sklearn.svm import SVC

matplotlib.rcParams["font.family"] = "Malgun Gothic"
matplotlib.rcParams["axes.unicode_minus"] = False

# ── 경로 ──
DATA_DIR = os.path.join(os.path.dirname(__file__), "data")
MODEL_PATH = os.path.join(os.path.dirname(__file__), "model.pkl")
PLOT_PATH = os.path.join(os.path.dirname(__file__), "confusion_matrix.png")

LABELS = ["front", "left", "right", "up", "down"]

# ── 핵심 랜드마크 인덱스 (코·눈·입·턱·볼) ──
KEY_LM = [
    1,    # 코 끝
    4,    # 콧등
    6,    # 이마 중간
    9,    # 이마 위
    33,   # 왼 눈 외각
    133,  # 왼 눈 내각
    362,  # 오른 눈 외각
    263,  # 오른 눈 내각
    61,   # 입 왼쪽
    291,  # 입 오른쪽
    199,  # 턱 하단
    152,  # 아래턱 중앙
    10,   # 이마 최상
    234,  # 왼쪽 볼
    454,  # 오른쪽 볼
]
FEAT_DIM = len(KEY_LM) * 3


def extract_features(image_path, face_mesh):
    """이미지 파일 → 정규화된 랜드마크 벡터"""
    img = cv2.imread(image_path)
    if img is None:
        return None
    rgb = cv2.cvtColor(img, cv2.COLOR_BGR2RGB)
    res = face_mesh.process(rgb)
    if not res.multi_face_landmarks:
        return None
    lm = res.multi_face_landmarks[0].landmark

    raw = []
    for idx in KEY_LM:
        if idx >= len(lm):
            return None
        raw.extend([lm[idx].x, lm[idx].y, lm[idx].z])

    # 코 끝(인덱스 0) 기준 상대 좌표로 정규화
    nx, ny, nz = raw[0], raw[1], raw[2]
    normed = []
    for i in range(0, len(raw), 3):
        normed.extend([raw[i] - nx, raw[i + 1] - ny, raw[i + 2] - nz])
    return np.array(normed, dtype=np.float32)


def load_dataset():
    X, y = [], []
    with mp.solutions.face_mesh.FaceMesh(
        static_image_mode=True,
        max_num_faces=1,
        min_detection_confidence=0.3,
    ) as face_mesh:
        for label in LABELS:
            label_dir = os.path.join(DATA_DIR, label)
            if not os.path.isdir(label_dir):
                continue
            files = [f for f in os.listdir(label_dir) if f.lower().endswith(".jpg")]
            ok, skip = 0, 0
            for fname in files:
                feat = extract_features(os.path.join(label_dir, fname), face_mesh)
                if feat is not None:
                    X.append(feat)
                    y.append(label)
                    ok += 1
                else:
                    skip += 1
            print(f"  {label:8s}: {ok}개 사용  ({skip}개 스킵)")
    return np.array(X), np.array(y)


def plot_confusion(cm, classes, model_name, acc):
    fig, ax = plt.subplots(figsize=(6, 5))
    im = ax.imshow(cm, cmap="Blues")
    ax.set_xticks(range(len(classes)))
    ax.set_yticks(range(len(classes)))
    ax.set_xticklabels(classes)
    ax.set_yticklabels(classes)
    ax.set_xlabel("예측")
    ax.set_ylabel("실제")
    ax.set_title(f"혼동 행렬 — {model_name}  (Test 정확도: {acc:.1%})")
    plt.colorbar(im, ax=ax)
    for i in range(len(classes)):
        for j in range(len(classes)):
            ax.text(j, i, cm[i, j], ha="center", va="center",
                    color="white" if cm[i, j] > cm.max() / 2 else "black",
                    fontsize=12)
    plt.tight_layout()
    plt.savefig(PLOT_PATH, dpi=120)
    plt.show()
    print(f"혼동 행렬 저장: {PLOT_PATH}")


def main():
    print("=== I-Study 방향 인식 — 모델 학습 ===\n")
    print("데이터 로드 중...")
    X, y = load_dataset()

    if len(X) == 0:
        print("\n데이터가 없습니다. collect_data.py로 먼저 이미지를 수집하세요.")
        return

    print(f"\n총 샘플: {len(X)}")
    unique, counts = np.unique(y, return_counts=True)
    for u, c in zip(unique, counts):
        bar = "█" * (c // 2)
        print(f"  {u:8s}: {c:3d}  {bar}")

    if len(unique) < 2:
        print("클래스가 2개 이상 필요합니다.")
        return

    le = LabelEncoder()
    y_enc = le.fit_transform(y)

    X_train, X_test, y_train, y_test = train_test_split(
        X, y_enc, test_size=0.2, random_state=42, stratify=y_enc
    )

    candidates = {
        "RandomForest": RandomForestClassifier(n_estimators=200, random_state=42),
        "SVM (RBF)":    SVC(kernel="rbf", C=10, probability=True, random_state=42),
        "MLP":          MLPClassifier(hidden_layer_sizes=(128, 64), max_iter=500,
                                      early_stopping=True, random_state=42),
    }

    print("\n┌─────────────────────────────────────────────────────┐")
    print("│  모델        │  CV 5-Fold (평균±표준편차)  │  Test   │")
    print("├─────────────────────────────────────────────────────┤")

    best_name, best_model, best_acc = None, None, 0.0
    for name, clf in candidates.items():
        cv = cross_val_score(clf, X, y_enc, cv=5, n_jobs=-1)
        clf.fit(X_train, y_train)
        test_acc = clf.score(X_test, y_test)
        print(f"│  {name:12s}│  {cv.mean():.3f} ± {cv.std():.3f}           │  {test_acc:.3f}  │")
        if test_acc > best_acc:
            best_acc = test_acc
            best_name = name
            best_model = clf

    print("└─────────────────────────────────────────────────────┘")
    print(f"\n✅ 최우수 모델: {best_name}  (Test 정확도: {best_acc:.1%})")

    # 분류 리포트
    y_pred = best_model.predict(X_test)
    print("\n=== 분류 리포트 ===")
    print(classification_report(y_test, y_pred, target_names=le.classes_))

    # 모델 저장
    payload = {
        "model": best_model,
        "label_encoder": le,
        "key_landmarks": KEY_LM,
        "model_name": best_name,
        "test_accuracy": best_acc,
    }
    with open(MODEL_PATH, "wb") as f:
        pickle.dump(payload, f)
    print(f"모델 저장: {MODEL_PATH}")

    # 혼동 행렬
    cm = confusion_matrix(y_test, y_pred)
    plot_confusion(cm, le.classes_, best_name, best_acc)


if __name__ == "__main__":
    main()
