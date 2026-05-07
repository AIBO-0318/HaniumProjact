"""
I-Study - 학습 리포트 다이얼로그
학습 종료 후 결과를 표시합니다.
"""

import customtkinter as ctk
from shared.config import CARD_BG, TEXT_PRIMARY, GREEN, BLUE, TEXT_SECONDARY


def show_report(app, total_sec, focus_sec):
    """
    학습 리포트 다이얼로그 표시
    
    Args:
        app: 메인 앱 인스턴스
        total_sec: 총 학습 시간 (초)
        focus_sec: 집중 시간 (초)
    """
    report = ctk.CTkToplevel(app)
    report.title("")
    report.geometry("380x320")
    report.transient(app)
    report.grab_set()
    report.configure(fg_color="#FFFFFF")
    report.update_idletasks()
    x = app.winfo_x() + (app.winfo_width() - 380) // 2
    y = app.winfo_y() + (app.winfo_height() - 320) // 2
    report.geometry(f"+{x}+{y}")

    ctk.CTkLabel(report, text="🎉", font=ctk.CTkFont(size=50)).pack(pady=(25, 8))
    ctk.CTkLabel(report, text="수고하셨습니다!", font=ctk.CTkFont(size=22, weight="bold"), text_color=TEXT_PRIMARY).pack()

    total_h, total_r = divmod(total_sec, 3600)
    total_m, total_s = divmod(total_r, 60)
    focus_h, focus_r = divmod(focus_sec, 3600)
    focus_m, focus_s = divmod(focus_r, 60)
    rate = (focus_sec / total_sec * 100) if total_sec > 0 else 0

    sf = ctk.CTkFrame(report, fg_color="#F8F8F8", corner_radius=14)
    sf.pack(padx=30, pady=15, fill="x")
    ctk.CTkLabel(sf, text=f"총 학습: {total_h:02d}:{total_m:02d}:{total_s:02d}", font=ctk.CTkFont(size=15), text_color=TEXT_PRIMARY).pack(pady=(12, 4))
    ctk.CTkLabel(sf, text=f"집중 시간: {focus_h:02d}:{focus_m:02d}:{focus_s:02d}", font=ctk.CTkFont(size=15), text_color=GREEN).pack(pady=4)
    ctk.CTkLabel(sf, text=f"집중률: {rate:.1f}%", font=ctk.CTkFont(size=13), text_color=TEXT_SECONDARY).pack(pady=(4, 12))

    ctk.CTkButton(report, text="확인", height=42, width=120, font=ctk.CTkFont(size=15, weight="bold"), fg_color=BLUE, hover_color="#0056CC", corner_radius=10, command=report.destroy).pack()
