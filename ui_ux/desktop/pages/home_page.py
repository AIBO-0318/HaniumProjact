"""
I-Study - 홈 페이지
학습 타이머, 카메라 프리뷰, 빠른 링크, 최근 현황, 알림을 표시합니다.
"""

import customtkinter as ctk
import webbrowser
from shared.config import (
    BG_COLOR, CARD_BG, TEXT_PRIMARY, TEXT_SECONDARY, TEXT_MUTED,
    GREEN, RED, PURPLE, CARD_COLORS
)
from shared.helpers import darken_color
from shared import api_client


class HomePage:
    """홈 페이지 빌더"""

    def __init__(self, app):
        """
        Args:
            app: FocusEyePro 메인 앱 인스턴스
        """
        self.app = app

    def create(self) -> ctk.CTkScrollableFrame:
        """홈 페이지 프레임 생성 및 반환"""
        app = self.app
        page = ctk.CTkScrollableFrame(app, fg_color=BG_COLOR, corner_radius=0)

        # 헤더
        header = ctk.CTkFrame(page, fg_color="transparent")
        header.pack(fill="x", padx=30, pady=(25, 5))
        ctk.CTkLabel(header, text="안녕하세요! 👋 오늘도 화이팅", font=ctk.CTkFont(size=22, weight="bold"), text_color=TEXT_PRIMARY).pack(side="left")

        ctk.CTkLabel(page, text="학습 진행을 확인해보세요", font=ctk.CTkFont(size=13), text_color=TEXT_SECONDARY).pack(anchor="w", padx=30, pady=(0, 15))

        # 메인 콘텐츠 (2열)
        content = ctk.CTkFrame(page, fg_color="transparent")
        content.pack(fill="both", padx=30, pady=5)
        content.grid_columnconfigure(0, weight=3)
        content.grid_columnconfigure(1, weight=2)

        # ── 왼쪽: 학습 타이머 카드 ──
        timer_card = ctk.CTkFrame(content, fg_color=CARD_BG, corner_radius=20)
        timer_card.grid(row=0, column=0, sticky="nsew", padx=(0, 10), pady=5)

        timer_header = ctk.CTkFrame(timer_card, fg_color="transparent")
        timer_header.pack(fill="x", padx=25, pady=(20, 5))
        ctk.CTkLabel(timer_header, text="⏱ 학습 타이머", font=ctk.CTkFont(size=15, weight="bold"), text_color=TEXT_PRIMARY).pack(side="left")
        app.status_dot = ctk.CTkLabel(timer_header, text="●", font=ctk.CTkFont(size=14), text_color=TEXT_MUTED)
        app.status_dot.pack(side="right")

        # 카메라
        app.camera_frame = ctk.CTkFrame(timer_card, fg_color="#1A1A1A", corner_radius=16, height=160)
        app.camera_frame.pack(fill="x", padx=25, pady=(10, 5))
        app.camera_frame.pack_propagate(False)
        app.camera_label = ctk.CTkLabel(app.camera_frame, text="📷 카메라 대기 중", font=ctk.CTkFont(size=13), text_color="#666666")
        app.camera_label.pack(expand=True)

        # 타이머
        timer_display = ctk.CTkFrame(timer_card, fg_color="#F5F5F0", corner_radius=16)
        timer_display.pack(fill="x", padx=25, pady=10)
        app.timer_label = ctk.CTkLabel(timer_display, text="00 : 00 : 00", font=ctk.CTkFont(size=44, weight="bold"), text_color=TEXT_PRIMARY)
        app.timer_label.pack(pady=20)

        # 시선 상태
        gaze_frame = ctk.CTkFrame(timer_card, fg_color="transparent")
        gaze_frame.pack(fill="x", padx=25, pady=(0, 10))
        app.status_indicator = ctk.CTkLabel(gaze_frame, text="🔵 열심히 공부 중!", font=ctk.CTkFont(size=13), text_color=TEXT_SECONDARY)
        app.status_indicator.pack(side="left")
        app.gaze_status_badge = ctk.CTkLabel(gaze_frame, text="-", font=ctk.CTkFont(size=12, weight="bold"), text_color="#4E5968", fg_color="#F2F4F6", corner_radius=8)
        app.gaze_status_badge.pack(side="right", padx=8, pady=2)

        # 시야각 초점 설정 버튼
        calibration_btn = ctk.CTkButton(
            timer_card, text="👁️ 시야각 초점 설정", height=38,
            font=ctk.CTkFont(size=13, weight="bold"),
            fg_color="#007AFF", hover_color="#0056CC",
            text_color="#FFFFFF", corner_radius=12,
            command=app._open_calibration
        )
        calibration_btn.pack(fill="x", padx=25, pady=(0, 20))

        # ── 오른쪽: 화이트리스트 링크 바로가기 ──
        links_container = ctk.CTkFrame(content, fg_color=CARD_BG, corner_radius=20)
        links_container.grid(row=0, column=1, sticky="nsew", padx=(10, 0), pady=5)

        links_header = ctk.CTkFrame(links_container, fg_color="transparent")
        links_header.pack(fill="x", padx=20, pady=(20, 10))
        ctk.CTkLabel(links_header, text="🔗 빠른 링크", font=ctk.CTkFont(size=15, weight="bold"), text_color=TEXT_PRIMARY).pack(side="left")

        app.link_buttons_frame = ctk.CTkScrollableFrame(links_container, fg_color="transparent")
        app.link_buttons_frame.pack(fill="both", padx=15, pady=(0, 15), expand=True)

        self._refresh_link_buttons()

        app.stat_cards = {}

        # ── 하단 행: 최근 현황 + 최근 알림 ──
        bottom = ctk.CTkFrame(page, fg_color="transparent")
        bottom.pack(fill="x", padx=30, pady=10)
        bottom.grid_columnconfigure(0, weight=1)
        bottom.grid_columnconfigure(1, weight=1)

        # 최근 현황
        activity_card = ctk.CTkFrame(bottom, fg_color=CARD_BG, corner_radius=20)
        activity_card.grid(row=0, column=0, sticky="nsew", padx=(0, 10), pady=5)
        ctk.CTkLabel(activity_card, text="📊 최근 현황", font=ctk.CTkFont(size=15, weight="bold"), text_color=TEXT_PRIMARY).pack(anchor="w", padx=25, pady=(20, 15))

        act_row = ctk.CTkFrame(activity_card, fg_color="transparent")
        act_row.pack(fill="x", padx=15, pady=(0, 20))
        act_row.grid_columnconfigure(0, weight=1)
        act_row.grid_columnconfigure(1, weight=1)
        act_row.grid_columnconfigure(2, weight=1)

        act_data = [
            ("허용됨", "✅", "#E8F9F0", GREEN),
            ("차단됨", "🚫", "#FFEBEE", RED),
            ("총 감지", "📋", "#EDE7F6", PURPLE),
        ]
        app.act_labels = {}
        for idx, (label, icon, bg, color) in enumerate(act_data):
            box = ctk.CTkFrame(act_row, fg_color=bg, corner_radius=14)
            box.grid(row=0, column=idx, sticky="nsew", padx=5)
            ctk.CTkLabel(box, text=icon, font=ctk.CTkFont(size=20)).pack(pady=(15, 5))
            val = ctk.CTkLabel(box, text="0", font=ctk.CTkFont(size=28, weight="bold"), text_color=color)
            val.pack()
            ctk.CTkLabel(box, text=label, font=ctk.CTkFont(size=11), text_color=TEXT_SECONDARY).pack(pady=(2, 15))
            app.act_labels[label] = val

        # 최근 알림
        alert_card = ctk.CTkFrame(bottom, fg_color=CARD_BG, corner_radius=20)
        alert_card.grid(row=0, column=1, sticky="nsew", padx=(10, 0), pady=5)

        alert_header = ctk.CTkFrame(alert_card, fg_color="transparent")
        alert_header.pack(fill="x", padx=25, pady=(20, 10))
        ctk.CTkLabel(alert_header, text="🔔 최근 알림", font=ctk.CTkFont(size=15, weight="bold"), text_color=TEXT_PRIMARY).pack(side="left")

        app.alert_list_frame = ctk.CTkScrollableFrame(alert_card, fg_color="transparent", height=130)
        app.alert_list_frame.pack(fill="both", padx=15, pady=(0, 15), expand=True)
        ctk.CTkLabel(app.alert_list_frame, text="아직 알림이 없습니다", font=ctk.CTkFont(size=12), text_color=TEXT_MUTED).pack(pady=20)

        return page

    def _refresh_link_buttons(self):
        """화이트리스트 링크 바로가기 버튼 업데이트"""
        app = self.app
        if not hasattr(app, 'link_buttons_frame'):
            return

        for w in app.link_buttons_frame.winfo_children():
            w.destroy()

        urls = api_client.get_all_whitelist_urls()

        if not urls:
            ctk.CTkLabel(
                app.link_buttons_frame,
                text="화이트리스트에 링크를 추가하세요",
                font=ctk.CTkFont(size=12),
                text_color=TEXT_MUTED
            ).pack(pady=30)
            return

        for idx, (url_id, name, url) in enumerate(urls):
            color = CARD_COLORS[idx % len(CARD_COLORS)]

            btn = ctk.CTkButton(
                app.link_buttons_frame,
                text=f"🌐  {name}",
                height=45,
                font=ctk.CTkFont(size=13, weight="bold"),
                fg_color=color,
                hover_color=darken_color(color),
                text_color="#FFFFFF",
                corner_radius=12,
                anchor="w",
                command=lambda u=url: webbrowser.open(u)
            )
            btn.pack(fill="x", padx=5, pady=4)
