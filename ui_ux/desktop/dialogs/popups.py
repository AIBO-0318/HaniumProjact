"""
I-Study - 알림 팝업 모듈
시선 이탈, 눈 감음, 차단 사이트 경고 팝업을 관리합니다.
"""

import customtkinter as ctk
from shared.config import CARD_BG, GREEN, BLUE, RED, TEXT_SECONDARY


def show_gaze_lost_popup(app):
    """시선 이탈 경고 팝업 표시"""
    if app.gaze_popup is not None:
        try:
            app.gaze_popup.destroy()
        except Exception:
            pass
    _create_alert_popup(app, "👀", "화면을 보고 있지 않습니다", "#FF3B30")


def show_eye_closed_popup(app):
    """눈 감음 경고 팝업 표시"""
    if app.gaze_popup is not None:
        try:
            app.gaze_popup.destroy()
        except Exception:
            pass
    _create_alert_popup(app, "😴", "눈을 감고 있습니다", "#FF9500")


def _create_alert_popup(app, emoji, message, color):
    """알림 팝업 생성 (공통)"""
    app.gaze_popup = ctk.CTkToplevel(app)
    app.gaze_popup.title("")
    app.gaze_popup.geometry("340x210")
    app.gaze_popup.transient(app)
    app.gaze_popup.attributes('-topmost', True)
    app.gaze_popup.configure(fg_color=CARD_BG)
    app.gaze_popup.overrideredirect(True)
    app.gaze_popup.update_idletasks()
    sw = app.gaze_popup.winfo_screenwidth()
    sh = app.gaze_popup.winfo_screenheight()
    app.gaze_popup.geometry(f"+{(sw - 340) // 2}+{(sh - 210) // 2}")

    f = ctk.CTkFrame(app.gaze_popup, fg_color=CARD_BG, corner_radius=20)
    f.pack(expand=True, fill="both", padx=2, pady=2)
    ctk.CTkLabel(f, text=emoji, font=ctk.CTkFont(size=40)).pack(pady=(20, 8))
    ctk.CTkLabel(f, text=message, font=ctk.CTkFont(size=16, weight="bold"), text_color=color).pack()
    bf = ctk.CTkFrame(f, fg_color="transparent")
    bf.pack(pady=18)
    ctk.CTkButton(bf, text="▶ 재생", width=120, height=42, font=ctk.CTkFont(size=14, weight="bold"), fg_color=GREEN, hover_color="#2DA44E", corner_radius=10, command=lambda: app._on_popup_play()).pack(side="left", padx=6)
    ctk.CTkButton(bf, text="⏪ -10초", width=120, height=42, font=ctk.CTkFont(size=14, weight="bold"), fg_color=BLUE, hover_color="#0056CC", corner_radius=10, command=lambda: app._on_popup_rewind()).pack(side="left", padx=6)


def show_blocked_site_popup(app, window_title):
    """차단 사이트 경고 팝업 표시"""
    if app.blocked_popup is not None:
        try:
            app.blocked_popup.destroy()
        except Exception:
            pass
    app.blocked_popup = ctk.CTkToplevel(app)
    app.blocked_popup.title("")
    app.blocked_popup.geometry("360x220")
    app.blocked_popup.transient(app)
    app.blocked_popup.attributes('-topmost', True)
    app.blocked_popup.configure(fg_color=CARD_BG)
    app.blocked_popup.overrideredirect(True)
    app.blocked_popup.update_idletasks()
    sw = app.blocked_popup.winfo_screenwidth()
    sh = app.blocked_popup.winfo_screenheight()
    app.blocked_popup.geometry(f"+{(sw - 360) // 2}+{(sh - 220) // 2}")

    f = ctk.CTkFrame(app.blocked_popup, fg_color=CARD_BG, corner_radius=20)
    f.pack(expand=True, fill="both", padx=2, pady=2)
    ctk.CTkLabel(f, text="🚫", font=ctk.CTkFont(size=40)).pack(pady=(20, 8))
    ctk.CTkLabel(f, text="허용되지 않은 사이트입니다!", font=ctk.CTkFont(size=16, weight="bold"), text_color=RED).pack()
    ctk.CTkLabel(f, text="학습 중에는 등록된 사이트만\n이용할 수 있습니다.", font=ctk.CTkFont(size=12), text_color=TEXT_SECONDARY).pack(pady=(5, 10))
    ctk.CTkButton(f, text="확인", width=120, height=38, font=ctk.CTkFont(size=14, weight="bold"), fg_color=BLUE, hover_color="#0056CC", corner_radius=10, command=lambda: _close_blocked_popup(app)).pack(pady=(0, 15))


def _close_blocked_popup(app):
    """차단 팝업 닫기"""
    if app.blocked_popup:
        try:
            app.blocked_popup.destroy()
        except Exception:
            pass
        app.blocked_popup = None
