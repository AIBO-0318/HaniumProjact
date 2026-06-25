# -*- coding: utf-8 -*-
"""I-Study 시선추적 AI(ai_core) — 학습 데이터/모델 발표자료 PDF"""

import os
from reportlab.lib.pagesizes import landscape, A4
from reportlab.lib.units import mm
from reportlab.lib import colors
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont
from reportlab.pdfgen import canvas
from reportlab.lib.utils import ImageReader

# ── 폰트 ──
pdfmetrics.registerFont(TTFont("Malgun", r"C:\Windows\Fonts\malgun.ttf"))
pdfmetrics.registerFont(TTFont("MalgunBd", r"C:\Windows\Fonts\malgunbd.ttf"))

OUT = os.path.join(os.path.dirname(__file__), "I-Study_시선추적AI_발표.pdf")
CM_IMG = os.path.join(os.path.dirname(__file__), "model_test", "confusion_matrix.png")

PAGE_W, PAGE_H = landscape(A4)

NAVY = colors.HexColor("#1F3A5F")
BLUE = colors.HexColor("#2E6FB7")
LBLUE = colors.HexColor("#EAF2FB")
GRAY = colors.HexColor("#555555")
LGRAY = colors.HexColor("#888888")
GREEN = colors.HexColor("#2E8B57")
ORANGE = colors.HexColor("#D08A1E")

c = canvas.Canvas(OUT, pagesize=landscape(A4))


def footer(num):
    c.setFont("Malgun", 9)
    c.setFillColor(LGRAY)
    c.drawString(15 * mm, 10 * mm, "I-Study — 시선추적 AI")
    c.drawRightString(PAGE_W - 15 * mm, 10 * mm, f"{num}")


def header_bar(title, num):
    c.setFillColor(NAVY)
    c.rect(0, PAGE_H - 28 * mm, PAGE_W, 28 * mm, fill=1, stroke=0)
    c.setFillColor(colors.white)
    c.setFont("MalgunBd", 20)
    c.drawString(18 * mm, PAGE_H - 19 * mm, title)
    c.setFillColor(BLUE)
    c.rect(0, PAGE_H - 30 * mm, PAGE_W, 2 * mm, fill=1, stroke=0)
    footer(num)


def bullet(x, y, text, size=13, color=GRAY, font="Malgun"):
    c.setFillColor(BLUE)
    c.circle(x + 1.5 * mm, y + 1.4 * mm, 1.1 * mm, fill=1, stroke=0)
    c.setFillColor(color)
    c.setFont(font, size)
    c.drawString(x + 6 * mm, y, text)


def sub(x, y, text, size=12, color=LGRAY):
    c.setFillColor(color)
    c.setFont("Malgun", size)
    c.drawString(x, y, text)


# ════════════ 표지 ════════════
c.setFillColor(NAVY)
c.rect(0, 0, PAGE_W, PAGE_H, fill=1, stroke=0)
c.setFillColor(BLUE)
c.rect(0, PAGE_H * 0.5 - 1, PAGE_W, 2, fill=1, stroke=0)
c.setFillColor(colors.white)
c.setFont("MalgunBd", 40)
c.drawCentredString(PAGE_W / 2, PAGE_H * 0.60, "I-Study 시선추적 AI")
c.setFont("Malgun", 18)
c.setFillColor(colors.HexColor("#AEC6E4"))
c.drawCentredString(PAGE_W / 2, PAGE_H * 0.50 - 6 * mm, "ai_core/gaze_tracker.py — 어떤 모델과 데이터로 동작하는가")
c.setFont("Malgun", 12)
c.setFillColor(colors.HexColor("#8FAFD0"))
c.drawCentredString(PAGE_W / 2, 22 * mm, "2026-06-05")
c.showPage()

# ════════════ 슬라이드 1 — 개요 ════════════
header_bar("시선추적 AI 개요", 1)
y = PAGE_H - 45 * mm
c.setFont("Malgun", 14); c.setFillColor(GRAY)
c.drawString(18 * mm, y, "I-Study의 핵심 AI는 웹캠 영상에서 사용자가 화면을 보고 있는지 판별하는 시선추적 모듈입니다.")
y -= 16 * mm
for t in [
    "위치: ai_core/gaze_tracker.py (실제 앱이 사용하는 모듈)",
    "입력: 웹캠 영상 (640×480, 약 30 FPS)",
    "출력: 얼굴 감지 여부 · 시선 방향(상·하·좌·우·중앙) · 눈 감음 여부",
    "활용: 시선 이탈/졸음 감지 → 집중 시간 통계 산출",
]:
    bullet(20 * mm, y, t, 13); y -= 13 * mm

# 강조 박스
c.setFillColor(LBLUE)
c.roundRect(18 * mm, 20 * mm, PAGE_W - 36 * mm, 18 * mm, 5, fill=1, stroke=0)
c.setFillColor(NAVY); c.setFont("MalgunBd", 13)
c.drawString(26 * mm, 30 * mm, "핵심 질문: \"이 AI의 학습 데이터는 무엇인가?\"")
c.setFillColor(GRAY); c.setFont("Malgun", 12)
c.drawString(26 * mm, 23 * mm, "→ 직접 수집·학습한 데이터가 아니라, Google이 사전학습한 얼굴 인식 모델을 사용합니다.")
c.showPage()

# ════════════ 슬라이드 2 — 사용 모델 / 학습 데이터 ════════════
header_bar("사용 모델 & 학습 데이터", 2)
y = PAGE_H - 45 * mm
bullet(20 * mm, y, "기반 모델: MediaPipe Face Landmarker (Google 제공)", 14, NAVY, "MalgunBd"); y -= 12 * mm
sub(26 * mm, y, "얼굴에서 468개 랜드마크(특징점)를 검출하는 딥러닝 모델", 12); y -= 12 * mm
bullet(20 * mm, y, "모델 파일: ai_core/models/face_landmarker.task (float16)", 13); y -= 12 * mm
bullet(20 * mm, y, "출처: storage.googleapis.com/mediapipe-models/.../face_landmarker.task", 12); y -= 14 * mm

bullet(20 * mm, y, "학습 데이터는?", 14, ORANGE, "MalgunBd"); y -= 12 * mm
sub(26 * mm, y, "이 모델은 Google이 대규모 얼굴 이미지로 이미 학습(pretrained)을 마친 상태", 12); y -= 10 * mm
sub(26 * mm, y, "→ I-Study는 별도의 학습 데이터를 수집하거나 재학습하지 않음", 12, ORANGE); y -= 10 * mm
sub(26 * mm, y, "→ 사전학습 모델로 좌표를 받고, 방향 판정은 규칙(좌표 계산)으로 처리", 12); y -= 14 * mm

# 다이어그램: 웹캠 -> MediaPipe(사전학습) -> 좌표 -> 규칙판정 -> 방향
steps = ["웹캠 영상", "MediaPipe\n사전학습 모델", "468개\n랜드마크 좌표", "규칙 기반\n방향 판정"]
boxw = 50 * mm; n = len(steps)
gap = (PAGE_W - 36 * mm - n * boxw) / (n - 1)
bx = 18 * mm; by = 22 * mm
for i, s in enumerate(steps):
    x = bx + i * (boxw + gap)
    col = colors.HexColor("#E8F5EC") if i == 1 else LBLUE
    c.setFillColor(col)
    c.roundRect(x, by, boxw, 18 * mm, 4, fill=1, stroke=0)
    c.setFillColor(NAVY); c.setFont("MalgunBd", 11)
    for j, ln in enumerate(s.split("\n")):
        yy = by + 11 * mm if len(s.split("\n")) == 1 else by + 12 * mm - j * 5 * mm
        c.drawCentredString(x + boxw / 2, yy, ln)
    if i < n - 1:
        c.setFillColor(BLUE); c.setFont("MalgunBd", 16)
        c.drawCentredString(x + boxw + gap / 2, by + 7 * mm, "→")
c.setFillColor(GREEN); c.setFont("Malgun", 9)
c.drawCentredString(bx + boxw + gap + boxw / 2, by - 4 * mm, "↑ 유일한 \"학습된\" 부분 (사전학습)")
c.showPage()

# ════════════ 슬라이드 3 — 동작 원리 ════════════
header_bar("동작 원리 — 좌표로 방향 판정", 3)
y = PAGE_H - 45 * mm
bullet(20 * mm, y, "좌우 방향: 코끝이 얼굴 좌우 중심에서 얼마나 치우쳤는지 비율 계산", 13); y -= 12 * mm
bullet(20 * mm, y, "상하 방향: 코끝이 이마–턱 중심에서 얼마나 위/아래인지 비율 계산", 13); y -= 12 * mm
bullet(20 * mm, y, "눈 감음: 위·아래 눈꺼풀 랜드마크 간 세로 거리로 판단", 13); y -= 12 * mm
bullet(20 * mm, y, "캘리브레이션: 정면 응시 샘플로 사용자별 중심·임계값 보정", 13); y -= 12 * mm
bullet(20 * mm, y, "시간 임계값: 2초 이상 이탈 → 시선 이탈, 5초 이상 → 눈 감음 알림", 13); y -= 16 * mm

# 임계값 표
rows = [
    ("좌/우 판정", "비율 < 0.20 → 좌,  > 0.80 → 우"),
    ("상/하 판정", "비율 < 0.38 → 상,  > 0.62 → 하"),
    ("눈 감음", "평균 눈 높이 < 0.010"),
    ("시선 이탈", "이탈 상태 2.0초 지속"),
]
tx = 20 * mm; ty = y
c.setFillColor(NAVY); c.setFont("MalgunBd", 12)
c.drawString(tx, ty, "항목"); c.drawString(tx + 45 * mm, ty, "기준값")
ty -= 3 * mm; c.setStrokeColor(NAVY); c.setLineWidth(1)
c.line(tx, ty, tx + 150 * mm, ty); ty -= 9 * mm
for k, v in rows:
    c.setFillColor(GRAY); c.setFont("Malgun", 12)
    c.drawString(tx, ty, k); c.drawString(tx + 45 * mm, ty, v)
    ty -= 9 * mm
c.showPage()

# ════════════ 슬라이드 4 — 인식률 검증 ════════════
header_bar("인식률 검증 (참고 실험)", 4)
y = PAGE_H - 45 * mm
bullet(20 * mm, y, "방향 판정 정확도를 측정하기 위한 참고 실험: model_test/", 13); y -= 12 * mm
bullet(20 * mm, y, "공개 데이터셋 AFLW2000(얼굴 자세 이미지)로 방향 인식률 평가", 13); y -= 12 * mm
bullet(20 * mm, y, "5개 방향으로 분류된 약 4,000장 → 혼동 행렬로 성능 확인", 13); y -= 14 * mm

# 데이터 분포 미니 표
data = [("front", 1574, GREEN), ("right", 964, BLUE), ("left", 906, BLUE),
        ("up", 426, ORANGE), ("down", 130, colors.HexColor("#C0504D"))]
tx, ty = 20 * mm, y
maxv = 1574
for label, cnt, col in data:
    c.setFillColor(GRAY); c.setFont("Malgun", 12)
    c.drawString(tx, ty, label)
    c.drawRightString(tx + 40 * mm, ty, f"{cnt:,}장")
    c.setFillColor(col)
    c.roundRect(tx + 46 * mm, ty - 1 * mm, (cnt / maxv) * 45 * mm, 5 * mm, 1, fill=1, stroke=0)
    ty -= 10 * mm
c.setFillColor(NAVY); c.setFont("MalgunBd", 12)
c.drawString(tx, ty - 2 * mm, "합계  4,000장")

# 혼동행렬 이미지
if os.path.exists(CM_IMG):
    img = ImageReader(CM_IMG)
    iw, ih = img.getSize()
    disp_h = 100 * mm; disp_w = disp_h * iw / ih
    c.drawImage(img, PAGE_W - 18 * mm - disp_w, 22 * mm, disp_w, disp_h,
                preserveAspectRatio=True, mask='auto')
    c.setFont("Malgun", 10); c.setFillColor(LGRAY)
    c.drawCentredString(PAGE_W - 18 * mm - disp_w / 2, 17 * mm, "혼동 행렬 (confusion_matrix.png)")

c.setFillColor(ORANGE); c.setFont("Malgun", 11)
c.drawString(20 * mm, 20 * mm, "※ 이 실험은 성능 측정용 참고 자료이며, 실제 앱은 사전학습 모델 + 규칙으로 동작합니다.")
c.showPage()

# ════════════ 슬라이드 5 — 혼동 행렬 해석 ════════════
header_bar("혼동 행렬(Confusion Matrix) 읽는 법", 5)
# 왼쪽: 이미지
if os.path.exists(CM_IMG):
    img = ImageReader(CM_IMG)
    iw, ih = img.getSize()
    disp_h = 110 * mm; disp_w = disp_h * iw / ih
    c.drawImage(img, 16 * mm, 28 * mm, disp_w, disp_h,
                preserveAspectRatio=True, mask='auto')
    rx = 16 * mm + disp_w + 6 * mm
else:
    rx = 150 * mm

# 오른쪽: 설명
y = PAGE_H - 44 * mm
bullet(rx, y, "가로축 = 모델의 예측, 세로축 = 실제 정답", 12.5); y -= 11 * mm
bullet(rx, y, "대각선 칸 = 정답을 맞힌 개수 (많을수록 좋음)", 12.5); y -= 11 * mm
bullet(rx, y, "대각선 밖 = 오분류 (무엇을 무엇으로 헷갈렸는지)", 12.5); y -= 14 * mm

c.setFillColor(NAVY); c.setFont("MalgunBd", 12.5)
c.drawString(rx, y, "예시 — front 행 (정면)"); y -= 10 * mm
sub(rx + 4 * mm, y, "총 314개 중 304개 정답 (대각선)", 11.5); y -= 9 * mm
sub(rx + 4 * mm, y, "left·right·up 으로 각각 2~4개 오분류", 11.5); y -= 16 * mm

# 정확도 강조 박스
c.setFillColor(colors.HexColor("#E8F5EC"))
c.roundRect(rx, y - 14 * mm, PAGE_W - rx - 16 * mm, 22 * mm, 5, fill=1, stroke=0)
c.setFillColor(GREEN); c.setFont("MalgunBd", 22)
c.drawString(rx + 6 * mm, y - 2 * mm, "정확도 97.6%")
c.setFillColor(GRAY); c.setFont("Malgun", 11.5)
c.drawString(rx + 6 * mm, y - 10 * mm, "최우수 모델: RandomForest (3개 중 선정)")
c.showPage()

# ════════════ 슬라이드 6 — 방향별 인식률 ════════════
header_bar("방향별 인식률 & 정확도", 6)
y = PAGE_H - 42 * mm
c.setFont("Malgun", 12.5); c.setFillColor(GRAY)
c.drawString(18 * mm, y, "AFLW2000 테스트셋 기준, 5개 방향 각각의 인식 성능입니다. (인식률=실제 그 방향을 맞힌 비율)")
y -= 14 * mm

# 표 헤더
tx = 20 * mm
col_dir = tx
col_rate = tx + 38 * mm     # 인식률 라벨
col_bar = tx + 70 * mm      # 막대 시작
bar_max = 70 * mm
col_prec = tx + 150 * mm    # 정밀도
col_cnt = tx + 190 * mm     # 정답 개수
c.setFillColor(NAVY); c.setFont("MalgunBd", 12)
c.drawString(col_dir, y, "방향")
c.drawString(col_rate, y, "인식률")
c.drawString(col_prec, y, "정밀도")
c.drawString(col_cnt, y, "정답/전체")
y -= 3 * mm
c.setStrokeColor(NAVY); c.setLineWidth(1)
c.line(tx, y, tx + 215 * mm, y)
y -= 11 * mm

rows = [
    ("정면 (front)", 96.8, 98.1, "304 / 314", GREEN),
    ("왼쪽 (left)", 100.0, 97.5, "153 / 153", BLUE),
    ("오른쪽 (right)", 98.8, 97.6, "163 / 165", BLUE),
    ("위 (up)", 97.6, 95.4, "83 / 85", ORANGE),
    ("아래 (down)", 84.0, 100.0, "21 / 25", colors.HexColor("#C0504D")),
]
for name, rate, prec, cnt, col in rows:
    c.setFillColor(GRAY); c.setFont("Malgun", 12.5)
    c.drawString(col_dir, y, name)
    c.setFillColor(NAVY); c.setFont("MalgunBd", 12.5)
    c.drawString(col_rate, y, f"{rate:.1f}%")
    # 막대 (배경 + 값)
    c.setFillColor(colors.HexColor("#E6E6E6"))
    c.roundRect(col_bar, y - 1 * mm, bar_max, 5 * mm, 1, fill=1, stroke=0)
    c.setFillColor(col)
    c.roundRect(col_bar, y - 1 * mm, bar_max * rate / 100, 5 * mm, 1, fill=1, stroke=0)
    c.setFillColor(GRAY); c.setFont("Malgun", 12)
    c.drawString(col_prec, y, f"{prec:.1f}%")
    c.setFillColor(LGRAY); c.setFont("Malgun", 11.5)
    c.drawString(col_cnt, y, cnt)
    y -= 13 * mm

y -= 2 * mm
c.setStrokeColor(LGRAY); c.setLineWidth(0.5)
c.line(tx, y + 5 * mm, tx + 215 * mm, y + 5 * mm)
c.setFillColor(NAVY); c.setFont("MalgunBd", 13)
c.drawString(col_dir, y - 2 * mm, "전체 정확도")
c.setFillColor(GREEN); c.setFont("MalgunBd", 13)
c.drawString(col_rate, y - 2 * mm, "97.6%")

# 해설 박스
c.setFillColor(LBLUE)
c.roundRect(18 * mm, 18 * mm, PAGE_W - 36 * mm, 24 * mm, 5, fill=1, stroke=0)
c.setFillColor(NAVY); c.setFont("MalgunBd", 12)
c.drawString(24 * mm, 34 * mm, "해석 포인트")
c.setFillColor(GRAY); c.setFont("Malgun", 11.5)
c.drawString(24 * mm, 27 * mm, "• 좌·우·정면·위는 96~100%로 매우 안정적  •  아래(down)는 84%로 가장 낮음")
c.drawString(24 * mm, 21 * mm, "• 원인: 아래 방향 학습 샘플(130장)이 가장 적어 데이터 불균형 → 향후 보강 필요")
c.showPage()

# ════════════ 슬라이드 7 — 정리 ════════════
header_bar("정리", 7)
y = PAGE_H - 50 * mm
items = [
    ("기반 모델", "MediaPipe Face Landmarker — Google이 사전학습한 얼굴 검출 딥러닝 모델"),
    ("학습 데이터", "직접 수집·학습한 데이터 없음 (사전학습 모델을 그대로 사용)"),
    ("방향 판정", "468개 랜드마크 좌표로 비율을 계산하는 규칙 기반 방식"),
    ("성능 검증", "AFLW2000 약 4,000장으로 인식률 측정 (model_test, 참고용)"),
]
for i, (k, v) in enumerate(items):
    by = y - i * 26 * mm
    c.setFillColor(BLUE)
    c.roundRect(18 * mm, by - 6 * mm, 6 * mm, 18 * mm, 1, fill=1, stroke=0)
    c.setFillColor(NAVY); c.setFont("MalgunBd", 15)
    c.drawString(30 * mm, by + 4 * mm, k)
    c.setFillColor(GRAY); c.setFont("Malgun", 12.5)
    c.drawString(30 * mm, by - 4 * mm, v)

c.setFillColor(NAVY); c.setFont("MalgunBd", 13)
c.drawCentredString(PAGE_W / 2, 24 * mm,
                    "결론: I-Study 시선추적 AI는 Google 사전학습 모델 기반이라 별도 학습 데이터가 없습니다.")
c.showPage()

c.save()
print("저장 완료:", OUT)
