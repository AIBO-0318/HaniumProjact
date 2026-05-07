"""
I-Study - 화이트리스트 페이지
집중 모드에서 허용할 웹사이트를 관리합니다.
"""

import customtkinter as ctk
from tkinter import messagebox
from shared.config import (
    BG_COLOR, CARD_BG, ACCENT_YELLOW, TEXT_PRIMARY, TEXT_SECONDARY, TEXT_MUTED,
    GREEN, RED, BLUE, PURPLE, ORANGE, CARD_COLORS
)
from shared import api_client


class WhitelistPage:
    """화이트리스트 페이지 빌더"""

    def __init__(self, app):
        self.app = app

    def create(self) -> ctk.CTkScrollableFrame:
        """화이트리스트 페이지 프레임 생성 및 반환"""
        app = self.app
        page = ctk.CTkScrollableFrame(app, fg_color=BG_COLOR, corner_radius=0)

        # 헤더
        ctk.CTkLabel(page, text="화이트리스트 설정 ✅", font=ctk.CTkFont(size=22, weight="bold"), text_color=TEXT_PRIMARY).pack(anchor="w", padx=30, pady=(25, 3))
        ctk.CTkLabel(page, text="집중 모드에서 허용할 프로그램과 웹사이트를 관리하세요", font=ctk.CTkFont(size=13), text_color=TEXT_SECONDARY).pack(anchor="w", padx=30, pady=(0, 15))

        # 집중 모드 배너
        banner = ctk.CTkFrame(page, fg_color=ACCENT_YELLOW, corner_radius=20, height=70)
        banner.pack(fill="x", padx=30, pady=10)
        banner.pack_propagate(False)
        banner_inner = ctk.CTkFrame(banner, fg_color="transparent")
        banner_inner.pack(fill="both", expand=True, padx=25)
        ctk.CTkLabel(banner_inner, text="🔒  집중 모드", font=ctk.CTkFont(size=16, weight="bold"), text_color=TEXT_PRIMARY).pack(side="left", pady=15)
        ctk.CTkLabel(banner_inner, text="허용 모드 | 허용된 사이트만 접근 가능 ✅", font=ctk.CTkFont(size=12), text_color="#6B5B00").pack(side="left", padx=15, pady=15)

        app.wl_focus_switch = ctk.CTkSwitch(banner_inner, text="ON", font=ctk.CTkFont(size=13, weight="bold"), command=app._toggle_study)
        app.wl_focus_switch.pack(side="right", pady=15)

        # 통계 행
        stats_row = ctk.CTkFrame(page, fg_color="transparent")
        stats_row.pack(fill="x", padx=30, pady=10)
        for i in range(4):
            stats_row.grid_columnconfigure(i, weight=1)

        urls = api_client.get_all_whitelist_urls()
        wl_stats = [
            ("🌐", f"{len(urls)}개", "허용 URL", "#E8F9F0", GREEN),
            ("⏱", "0h", "오늘 학습", "#FFF4E0", ORANGE),
            ("✅", "0%", "집중 성공률", "#EEF5FF", BLUE),
            ("🔒", "OFF", "집중 모드", "#F3EEFF", PURPLE),
        ]
        app.wl_stat_labels = {}
        for idx, (icon, val, label, bg, color) in enumerate(wl_stats):
            card = ctk.CTkFrame(stats_row, fg_color=CARD_BG, corner_radius=16)
            card.grid(row=0, column=idx, sticky="nsew", padx=5)
            inner = ctk.CTkFrame(card, fg_color="transparent")
            inner.pack(padx=15, pady=15)
            ctk.CTkLabel(inner, text=icon, font=ctk.CTkFont(size=20)).pack(anchor="w")
            v = ctk.CTkLabel(inner, text=val, font=ctk.CTkFont(size=22, weight="bold"), text_color=TEXT_PRIMARY)
            v.pack(anchor="w", pady=(3, 0))
            ctk.CTkLabel(inner, text=label, font=ctk.CTkFont(size=11), text_color=color).pack(anchor="w")
            app.wl_stat_labels[label] = v

        # 허용 웹사이트 섹션
        sites_card = ctk.CTkFrame(page, fg_color=CARD_BG, corner_radius=20)
        sites_card.pack(fill="x", padx=30, pady=10)

        sites_header = ctk.CTkFrame(sites_card, fg_color="transparent")
        sites_header.pack(fill="x", padx=25, pady=(20, 10))
        ctk.CTkLabel(sites_header, text="🌐  허용 웹사이트", font=ctk.CTkFont(size=15, weight="bold"), text_color=TEXT_PRIMARY).pack(side="left")
        app.wl_count_label = ctk.CTkLabel(sites_header, text=f"{len(urls)}개", font=ctk.CTkFont(size=12, weight="bold"), text_color=BLUE, fg_color="#EEF5FF", corner_radius=10)
        app.wl_count_label.pack(side="right", padx=8, pady=2)

        # 추가 입력
        add_frame = ctk.CTkFrame(sites_card, fg_color="transparent")
        add_frame.pack(fill="x", padx=25, pady=(5, 10))

        app.wl_name_entry = ctk.CTkEntry(add_frame, placeholder_text="사이트 이름", height=38, font=ctk.CTkFont(size=13), fg_color="#F5F5F5", border_width=0, corner_radius=10, width=150)
        app.wl_name_entry.pack(side="left", padx=(0, 8))

        app.wl_url_entry = ctk.CTkEntry(add_frame, placeholder_text="예: https://example.com", height=38, font=ctk.CTkFont(size=13), fg_color="#F5F5F5", border_width=0, corner_radius=10)
        app.wl_url_entry.pack(side="left", fill="x", expand=True, padx=(0, 8))

        ctk.CTkButton(add_frame, text="+ 추가", width=80, height=38, font=ctk.CTkFont(size=13, weight="bold"), fg_color=GREEN, hover_color="#2DA44E", corner_radius=10, command=lambda: self._add_whitelist_url()).pack(side="right")

        # URL 리스트
        app.wl_list_frame = ctk.CTkScrollableFrame(sites_card, fg_color="transparent", height=280)
        app.wl_list_frame.pack(fill="both", padx=15, pady=(0, 15), expand=True)

        self.refresh_ui()

        return page

    def _add_whitelist_url(self):
        """URL 추가"""
        app = self.app
        name = app.wl_name_entry.get().strip()
        url = app.wl_url_entry.get().strip()
        if not name or not url:
            messagebox.showwarning("입력 오류", "이름과 URL을 모두 입력해주세요.")
            return
        if not url.startswith("http"):
            url = "https://" + url
        if api_client.add_whitelist_url(name, url):
            app.wl_name_entry.delete(0, "end")
            app.wl_url_entry.delete(0, "end")
            self.refresh_ui()
            app.home_page._refresh_link_buttons()
        else:
            messagebox.showwarning("중복", "이미 등록된 URL입니다.")

    def _delete_whitelist_url(self, url_id):
        """URL 삭제"""
        api_client.remove_whitelist_url(url_id)
        self.refresh_ui()
        self.app.home_page._refresh_link_buttons()

    def refresh_ui(self):
        """화이트리스트 UI 새로고침"""
        app = self.app
        for w in app.wl_list_frame.winfo_children():
            w.destroy()

        urls = api_client.get_all_whitelist_urls()
        app.wl_count_label.configure(text=f"{len(urls)}개")
        if hasattr(app, 'wl_stat_labels') and "허용 URL" in app.wl_stat_labels:
            app.wl_stat_labels["허용 URL"].configure(text=f"{len(urls)}개")

        for idx, (url_id, name, url) in enumerate(urls):
            row = ctk.CTkFrame(app.wl_list_frame, fg_color="transparent")
            row.pack(fill="x", pady=3)

            color = CARD_COLORS[idx % len(CARD_COLORS)]
            icon_frame = ctk.CTkFrame(row, fg_color=color, corner_radius=8, width=32, height=32)
            icon_frame.pack(side="left", padx=(5, 10))
            icon_frame.pack_propagate(False)
            ctk.CTkLabel(icon_frame, text="🌐", font=ctk.CTkFont(size=14)).pack(expand=True)

            info = ctk.CTkFrame(row, fg_color="transparent")
            info.pack(side="left", fill="x", expand=True)
            ctk.CTkLabel(info, text=name, font=ctk.CTkFont(size=13, weight="bold"), text_color=TEXT_PRIMARY, anchor="w").pack(anchor="w")

            domain = url.replace("https://", "").replace("http://", "").replace("www.", "").split("/")[0]
            ctk.CTkLabel(info, text=domain, font=ctk.CTkFont(size=11), text_color=TEXT_MUTED, anchor="w").pack(anchor="w")

            switch = ctk.CTkSwitch(row, text="", width=40)
            switch.pack(side="right", padx=10)
            switch.select()

            ctk.CTkButton(row, text="삭제", width=50, height=28, font=ctk.CTkFont(size=11), fg_color="#FFEBEE", hover_color="#FFCDD2", text_color=RED, corner_radius=8, command=lambda i=url_id: self._delete_whitelist_url(i)).pack(side="right", padx=5)

            sep = ctk.CTkFrame(app.wl_list_frame, height=1, fg_color="#F0F0F0")
            sep.pack(fill="x", padx=10, pady=2)
