# I-Study — 방향 인식률 테스트

> **독립 테스트 모듈** — 기존 프로젝트 코드를 건드리지 않음

현재 시스템(임계값 방식)과 ML 모델의 방향 인식 정확도를 비교합니다.

---

## 분류 대상

| 키 | 방향 | 설명 |
|----|------|------|
| 1 | front | 정면 응시 |
| 2 | left  | 좌측으로 고개 돌림 |
| 3 | right | 우측으로 고개 돌림 |
| 4 | up    | 고개를 위로 듦 |
| 5 | down  | 고개를 아래로 내림 |

---

## 사용 순서

### 0. 추가 패키지 설치 (최초 1회)
```bash
pip install scikit-learn
```
> mediapipe, opencv-python, numpy, matplotlib은 이미 설치됨

---

### 1. 데이터 수집 (`collect_data.py`)
```bash
cd I-Study
python model_test/collect_data.py
```

| 조작 | 기능 |
|------|------|
| `1`~`5` | 저장할 방향 선택 |
| `SPACE` | 현재 프레임 저장 (얼굴 감지 시만) |
| `Q` | 종료 |

- **권장 수량**: 방향당 **30장 이상** (많을수록 정확)
- 저장 위치: `model_test/data/{방향}/img_XXXX.jpg`

---

### 2. 모델 학습 (`train.py`)
```bash
python model_test/train.py
```

- RandomForest / SVM / MLP 3가지 모델 비교
- 5-Fold 교차 검증 + Test 정확도 출력
- 최우수 모델 → `model_test/model.pkl` 저장
- 혼동 행렬 → `model_test/confusion_matrix.png` 저장

---

### 3. 실시간 평가 (`evaluate.py`)
```bash
python model_test/evaluate.py
```

| 조작 | 기능 |
|------|------|
| `1`~`5` | 현재 정답 방향 설정 |
| `SPACE` | 현재 프레임 채점 (ML + 임계값 모두) |
| `R` | 점수 초기화 |
| `Q` | 종료 + 최종 결과 출력 |

화면에 다음이 표시됩니다:
- **[ML 모델]** — 학습된 분류기 예측 + 신뢰도
- **[임계값]** — 현재 시스템(Yaw/Pitch 기반) 예측
- 누적 정확도 막대

---

## 결과 해석

```
=== 최종 결과 (100회 평가) ===
  ML 모델 (SVM): 89.0%  (89/100)
  임계값 방식:   72.0%  (72/100)

  🏆 승자: ML 모델
```

---

## 파일 구조

```
model_test/
├── collect_data.py   # 1단계: 데이터 수집
├── train.py          # 2단계: 모델 학습
├── evaluate.py       # 3단계: 실시간 비교
├── requirements.txt  # scikit-learn
├── README.md
├── model.pkl         # (학습 후 생성)
├── confusion_matrix.png  # (학습 후 생성)
└── data/             # (수집 후 생성)
    ├── front/
    ├── left/
    ├── right/
    ├── up/
    └── down/
```

---

> 이 폴더는 테스트 전용입니다. 기존 프로젝트의 어떤 파일도 수정하지 않습니다.
