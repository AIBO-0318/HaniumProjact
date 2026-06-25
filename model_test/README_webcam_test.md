# I-Study 방향 인식 성능 데모 (웹캠 → 판정)

> 우리 앱이 **실제로 쓰는 엔진**([`ai_core/gaze_tracker.py`](../ai_core/gaze_tracker.py),
> MediaPipe FaceLandmarker + 기하 계산)으로, 웹캠으로 찍은 사진을 어느 방향으로
> 인식하는지 보여주는 데모입니다. 학습 분류기(`model.pkl`, `predict.py`)가 아니라
> **제품에 들어간 그 코드 그대로** 판정하므로 "우리 성능"을 정확히 보여줍니다.
>
> 기존 코드는 전혀 수정하지 않았고, 아래 두 스크립트만 새로 추가했습니다.

## 구성

| 파일 | 역할 |
|------|------|
| `capture_webcam.py` | 웹캠 프레임을 **앱과 동일한 파이프라인**(좌우 반전 등)으로 캡처해 라벨 폴더에 저장 |
| `judge_webcam.py`   | 저장된 사진을 **실제 엔진**으로 판정 → 방향 출력 + 정확도/혼동행렬 + CSV |

## 사용 흐름

### 1) 웹캠으로 사진 모으기

```powershell
python model_test/capture_webcam.py
```

- 창이 뜨면 화면 위에 **지금 AI가 보는 방향(AI now)** 이 실시간 표시됩니다.
- 조작:
  - `1` 정면 · `2` 좌측 · `3` 우측 · `4` 위 · `5` 아래 → **현재 라벨 선택**
  - `SPACE` 현재 프레임 저장 · `A` 자동 저장(0.3초 간격) 토글 · `Q`/`ESC` 종료
- 저장 위치: `model_test/captures/<라벨>/...jpg` (기본값, `--out` 으로 변경 가능)
- 앱과 똑같이 **좌우 반전 후 저장**하므로 판정 결과가 실제 앱과 일치합니다.

> 카메라는 한 번에 한 프로그램만 쓸 수 있어, 본 앱이 카메라를 점유 중이면 이 도구는
> 카메라를 못 엽니다. 데모용으로는 앱 대신 이 캡처 도구를 켜서 사진을 모으세요.

### 2) 모은 사진을 판정하기

```powershell
# 폴더 전체 (하위 라벨 폴더 자동 인식 → 정확도까지 계산)
python model_test/judge_webcam.py model_test/captures

# 결과를 사진 위에 그려 model_test/judge_out/ 에 저장
python model_test/judge_webcam.py model_test/captures --save

# 사진 몇 장만 / 대용량 폴더 일부만
python model_test/judge_webcam.py a.jpg b.png
python model_test/judge_webcam.py model_test/captures --limit 50
```

출력:
- 사진별 판정 방향 + 좌우비율(h) · 상하비율(v)
- 폴더명이 라벨이면 **전체 정확도 · 클래스별 정확도 · 혼동행렬**
- `model_test/judge_results.csv` (엑셀에서 바로 열림)

## 판정 원리 (요약)

1. 사진에서 MediaPipe FaceLandmarker 가 얼굴 특징점 좌표를 추출
2. 코끝 vs 얼굴 좌우/상하 중심을 비교해 비율(h, v) 계산
3. 임계값으로 방향 결정 — 기본값은 앱과 동일:
   `좌 h<0.20 · 우 h>0.80 · 위 v<0.38 · 아래 v>0.62 · 그 외 정면`
   (필요시 `--left/--right/--up/--down` 으로 조정 가능)

## 참고

- 정확도를 제대로 보려면 **본인이 직접 찍은 캡처**(1번)로 판정하세요.
  외부 데이터셋(`data/`)은 좌우/상하 라벨 규칙이 우리 앱과 달라 정확도가 낮게 보일 수 있습니다.
- `captures/`, `judge_out/`, `judge_results.csv` 는 생성물이라 커밋이 필요 없으면
  `.gitignore` 에 추가하셔도 됩니다.
