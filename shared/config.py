"""
I-Study 애플리케이션 설정
색상 상수, UI 테마, 앱 구성 값을 관리합니다.
"""

import customtkinter as ctk

# ─── 앱 기본 설정 ───
APP_TITLE = "I-Study"
APP_GEOMETRY = "1200x750"
APP_MINSIZE = (1000, 650)

# ─── 테마 설정 ───
ctk.set_appearance_mode("light")
ctk.set_default_color_theme("blue")

# ─── 색상 상수 (토스 스타일) ───
BG_COLOR = "#F4F6FA"              # 연한 블루-그레이 배경 (토스 메인)
SIDEBAR_BG = "#FFFFFF"            # 사이드바 흰색
CARD_BG = "#FFFFFF"               # 카드 흰색
ACCENT_YELLOW = "#3182F6"         # 토스 블루 (집중 모드 OFF 버튼)
ACCENT_ORANGE = "#FF7043"         # 부드러운 오렌지
TEXT_PRIMARY = "#191F28"          # 진한 차콜
TEXT_SECONDARY = "#4E5968"        # 중간 그레이
TEXT_MUTED = "#8B95A1"            # 연한 그레이
GREEN = "#3CC57F"                 # 토스풍 그린 (활성/성공)
RED = "#F04452"                   # 부드러운 레드
BLUE = "#3182F6"                  # 토스 블루
PURPLE = "#9F70FF"                # 부드러운 퍼플
ORANGE = "#FF7043"                # 부드러운 오렌지
SIDEBAR_ACTIVE = "#E8F0FE"        # 연한 블루 (사이드바 선택)
BANNER_START = "#3182F6"          # 블루 그라데이션 시작
BANNER_END = "#1E6CD9"            # 블루 그라데이션 끝

# ─── 카드 색상 팔레트 (토스풍 파스텔) ───
CARD_COLORS = ["#5B8DEF", "#3CC57F", "#FFB547", "#9F70FF", "#FF7E5F", "#5BC4DE", "#FF6B9D"]

# ─── 시선 추적 설정 ───
GAZE_LOST_THRESHOLD = 3.0       # 시선 이탈 판정 시간 (초)
EYE_CLOSURE_THRESHOLD = 5.0     # 눈 감음 판정 시간 (초)
CAMERA_UPDATE_INTERVAL = 33     # 카메라 업데이트 주기 (ms, ~30fps)
TIMER_UPDATE_INTERVAL = 1000    # 타이머 업데이트 주기 (ms)

# ─── 모니터링 설정 ───
MONITOR_CHECK_INTERVAL = 1.5    # URL 모니터링 주기 (초)

# ─── matplotlib 한글 폰트 설정 ───
import matplotlib.pyplot as plt
plt.rcParams['font.family'] = 'Malgun Gothic'
plt.rcParams['axes.unicode_minus'] = False
