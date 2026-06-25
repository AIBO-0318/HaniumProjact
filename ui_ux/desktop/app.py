"""
I-Study - 메인 애플리케이션 클래스
UI 조정, 학습 세션 관리, 모듈 간 연결을 담당합니다.
"""

import customtkinter as ctk
from tkinter import messagebox
import threading
import time
import webbrowser
import socket
from datetime import datetime
from PIL import Image
import cv2

from shared.config import (
    APP_TITLE, APP_GEOMETRY, APP_MINSIZE,
    BG_COLOR, SIDEBAR_BG, CARD_BG, ACCENT_YELLOW,
    TEXT_PRIMARY, TEXT_SECONDARY, TEXT_MUTED,
    GREEN, RED, BLUE, PURPLE, ORANGE,
    SIDEBAR_ACTIVE,
    GAZE_LOST_THRESHOLD, EYE_CLOSURE_THRESHOLD, MONITOR_CHECK_INTERVAL,
    CAMERA_UPDATE_INTERVAL, TIMER_UPDATE_INTERVAL,
)
from ai_core.gaze_tracker import GazeTracker
from ai_core.monitor import WhitelistMonitor
from shared.remote_db import RemoteStatsDB
from ui_ux.desktop.pages.home_page import HomePage
from ui_ux.desktop.dialogs.calibration import CalibrationWindow
from ui_ux.desktop.dialogs.popups import show_gaze_lost_popup, show_eye_closed_popup, show_blocked_site_popup
from ui_ux.desktop.dialogs.report import show_report
from ui_ux.desktop.dialogs.login import LoginDialog
from shared.helpers import pause_video, play_video, rewind_and_play
from shared import api_client


class FocusEyePro(ctk.CTk):
    """I-Study 메인 애플리케이션"""

    def __init__(self):
        super().__init__()

        self.title(APP_TITLE)
        self.geometry(APP_GEOMETRY)
        self.minsize(*APP_MINSIZE)
        self.configure(fg_color=BG_COLOR)

        # ─── 데이터(원격 서버 통계 API) ───
        self.db = RemoteStatsDB()

        # ─── 로그인 상태 ───
        self.current_login_id: str | None = None
        self.current_token: str | None = None
        self.current_name: str | None = None

        # ─── 상태 변수 ───
        self.gaze_tracker = None
        self.whitelist_monitor = None
        self.is_studying = False
        self.study_start_time = None
        self.video_paused = False
        self.is_calibrated = False
        self.gaze_popup = None
        self.blocked_popup = None
        self.current_page = "home"
        self.alert_count = 0
        self.block_count = 0

        # ─── 로그인 다이얼로그 ───
        self._do_login()

        # ─── 페이지 빌더 ───
        self.home_page = HomePage(self)

        # ─── UI 구성 ───
        self.pages = {}
        self._build_layout()
        self._show_page("home")

        self.protocol("WM_DELETE_WINDOW", self._on_closing)
        self._update_title()

    def _do_login(self):
        """앱 시작 시 로그인 다이얼로그 표시"""
        dlg = LoginDialog(self)
        dlg.lift()
        dlg.focus_force()
        self.wait_window(dlg)
        if not dlg._offline and dlg.result_login_id:
            self.current_login_id = dlg.result_login_id
            self.current_token = dlg.result_token
            self.current_name = dlg.result_name
            # 이후 /stats/* 호출에 쓸 JWT 토큰을 api_client 에 주입
            api_client.set_token(self.current_token)

    def _update_title(self):
        if self.current_name:
            self.title(f"I-Study — {self.current_name}")
        else:
            self.title("I-Study (오프라인)")

    def _open_web(self):
        """브라우저로 웹 UI를 열고 로그인 세션을 이어받음"""
        if not self.current_token:
            messagebox.showwarning("알림", "로그인 상태가 아닙니다.\n오프라인 모드에서는 웹 바로가기를 사용할 수 없습니다.")
            return
        try:
            from shared.env_config import API_SERVER_URL
        except ImportError:
            API_SERVER_URL = "http://127.0.0.1:8000"
        url = f"{API_SERVER_URL}/auto-login?token={self.current_token}"
        webbrowser.open(url)

    # ═══════════════════════════════════════
    #  레이아웃
    # ═══════════════════════════════════════

    def _build_layout(self):
        self.grid_columnconfigure(1, weight=1)
        self.grid_rowconfigure(0, weight=1)
        self._create_sidebar()
        self._create_pages()

    def _create_sidebar(self):
        sidebar = ctk.CTkFrame(self, width=220, fg_color=SIDEBAR_BG, corner_radius=0)
        sidebar.grid(row=0, column=0, sticky="nsw")
        sidebar.grid_propagate(False)

        # 로고
        logo_frame = ctk.CTkFrame(sidebar, fg_color="transparent")
        logo_frame.pack(fill="x", padx=20, pady=(25, 30))

        ctk.CTkLabel(logo_frame, text="📘", font=ctk.CTkFont(size=28)).pack(side="left")
        logo_text = ctk.CTkFrame(logo_frame, fg_color="transparent")
        logo_text.pack(side="left", padx=10)
        ctk.CTkLabel(logo_text, text="I-Study", font=ctk.CTkFont(size=18, weight="bold"), text_color=TEXT_PRIMARY).pack(anchor="w")
        ctk.CTkLabel(logo_text, text="스마트 학습 도우미", font=ctk.CTkFont(size=10), text_color=TEXT_MUTED).pack(anchor="w")

        # 메뉴 라벨
        ctk.CTkLabel(sidebar, text="메뉴", font=ctk.CTkFont(size=11), text_color=TEXT_MUTED).pack(anchor="w", padx=25, pady=(0, 5))

        # 네비게이션 버튼
        self.nav_buttons = {}
        nav_items = [
            ("home", "🏠", "홈"),
        ]
        for page_key, icon, label in nav_items:
            btn = ctk.CTkButton(
                sidebar, text=f"  {icon}  {label}", anchor="w",
                height=42, font=ctk.CTkFont(size=14, weight="bold"),
                fg_color="transparent", hover_color=SIDEBAR_ACTIVE,
                text_color=TEXT_PRIMARY, corner_radius=12,
                command=lambda k=page_key: self._show_page(k)
            )
            btn.pack(fill="x", padx=15, pady=2)
            self.nav_buttons[page_key] = btn

        # 집중 모드 버튼
        self.focus_btn = ctk.CTkButton(
            sidebar, text="⚡ 집중 모드 OFF", height=44,
            font=ctk.CTkFont(size=13, weight="bold"),
            fg_color=ACCENT_YELLOW, hover_color="#E6C200",
            text_color=TEXT_PRIMARY, corner_radius=12,
            command=self._toggle_study
        )
        self.focus_btn.pack(fill="x", padx=15, pady=(15, 8))

        # 하단 영역
        spacer = ctk.CTkFrame(sidebar, fg_color="transparent")
        spacer.pack(fill="both", expand=True)

        # 웹 바로가기 버튼
        web_btn = ctk.CTkButton(
            sidebar, text="🌐 웹 바로가기", height=40,
            font=ctk.CTkFont(size=13, weight="bold"),
            fg_color=BLUE, hover_color="#1B64DA",
            text_color="#FFFFFF", corner_radius=12,
            command=self._open_web
        )
        web_btn.pack(fill="x", padx=15, pady=(0, 8))

        # 세션 상태
        session_frame = ctk.CTkFrame(sidebar, fg_color="transparent")
        session_frame.pack(fill="x", padx=20, pady=(0, 20))
        self.session_dot = ctk.CTkLabel(session_frame, text="⚪", font=ctk.CTkFont(size=12))
        self.session_dot.pack(side="left")
        self.session_label = ctk.CTkLabel(session_frame, text="  대기 중", font=ctk.CTkFont(size=12), text_color=TEXT_SECONDARY)
        self.session_label.pack(side="left")

    def _show_page(self, page_key):
        self.current_page = page_key
        for key, frame in self.pages.items():
            frame.grid_forget()
        self.pages[page_key].grid(row=0, column=1, sticky="nsew", padx=0, pady=0)

        for key, btn in self.nav_buttons.items():
            if key == page_key:
                btn.configure(fg_color=SIDEBAR_ACTIVE)
            else:
                btn.configure(fg_color="transparent")

    def _create_pages(self):
        self.pages["home"] = self.home_page.create()

    # ═══════════════════════════════════════
    #  학습 시작 / 종료
    # ═══════════════════════════════════════

    def _toggle_study(self):
        if self.is_studying:
            self._stop_study()
        else:
            self._start_study()

    def _start_study(self):
        try:
            if self.gaze_tracker is None:
                self.gaze_tracker = GazeTracker(
                    gaze_lost_threshold=GAZE_LOST_THRESHOLD,
                    eye_closure_threshold=EYE_CLOSURE_THRESHOLD,
                    on_gaze_lost=self._on_gaze_lost,
                    on_gaze_restored=self._on_gaze_restored,
                    on_eye_closed=self._on_eye_closed
                )
                self.gaze_tracker.start()
                time.sleep(0.5)
            else:
                self.gaze_tracker.on_gaze_lost = self._on_gaze_lost
                self.gaze_tracker.on_gaze_restored = self._on_gaze_restored
                self.gaze_tracker.on_eye_closed = self._on_eye_closed
                self.gaze_tracker.reset_session_stats()
        except Exception as e:
            messagebox.showerror("오류", f"카메라 시작 실패: {e}")
            return

        self._start_whitelist_monitor()

        self.is_studying = True
        self.study_start_time = datetime.now()
        self.video_paused = False
        self.alert_count = 0
        self.block_count = 0

        # UI 업데이트
        self.focus_btn.configure(text="⚡ 집중 모드 ON", fg_color="#FF6B00")
        self.session_dot.configure(text="🟢")
        self.session_label.configure(text="  학습 진행 중")
        self.status_dot.configure(text_color=GREEN)
        self.status_indicator.configure(text="🔵 열심히 공부 중!")

        if hasattr(self, 'wl_focus_switch'):
            self.wl_focus_switch.select()
        if hasattr(self, 'wl_stat_labels') and "집중 모드" in self.wl_stat_labels:
            self.wl_stat_labels["집중 모드"].configure(text="ON")

        self._update_camera()
        self._update_timer()

    def _stop_study(self):
        if not self.is_studying:
            return

        self.is_studying = False

        if self.whitelist_monitor:
            self.whitelist_monitor.stop()
            self.whitelist_monitor = None

        stats = {}
        if self.gaze_tracker:
            stats = self.gaze_tracker.stop()
            self.gaze_tracker = None

        end_time = datetime.now()
        total_sec = stats.get("total_time_seconds", 0)
        focus_sec = stats.get("focus_time_seconds", 0)

        if total_sec > 0:
            focused_min  = int(stats.get("focused_sec", 0) // 60)
            dazed_min    = int(stats.get("dazed_sec",   0) // 60)
            distract_min = int(stats.get("distracted_sec", 0) // 60)
            self.db.save_study_log(
                start_time=self.study_start_time,
                end_time=end_time,
                total_time_seconds=total_sec,
                focus_time_seconds=focus_sec,
                login_id=self.current_login_id,
                focused_min=focused_min,
                dazed_min=dazed_min,
                distracted_min=distract_min,
            )

        show_report(self, total_sec, focus_sec)

        # UI 리셋
        self.focus_btn.configure(text="⚡ 집중 모드 OFF", fg_color=ACCENT_YELLOW)
        self.session_dot.configure(text="⚪")
        self.session_label.configure(text="  대기 중")
        self.status_dot.configure(text_color=TEXT_MUTED)
        self.status_indicator.configure(text="🔵 열심히 공부 중!")
        self.gaze_status_badge.configure(text="-")
        self.timer_label.configure(text="00 : 00 : 00")
        self.camera_label.configure(text="📷 카메라 대기 중", image=None)

        if hasattr(self, 'wl_focus_switch'):
            self.wl_focus_switch.deselect()
        if hasattr(self, 'wl_stat_labels') and "집중 모드" in self.wl_stat_labels:
            self.wl_stat_labels["집중 모드"].configure(text="OFF")

        self._update_home_stats()

        if self.current_page == "stats":
            self.stats_page.refresh()
        else:
            self.stats_page._refresh_stats_logs()

    # ═══════════════════════════════════════
    #  화이트리스트 모니터
    # ═══════════════════════════════════════

    def _start_whitelist_monitor(self):
        urls = api_client.get_all_whitelist_urls()
        whitelist = [{"name": name, "url": url} for (_, name, url) in urls]
        self.whitelist_monitor = WhitelistMonitor(
            whitelist_urls=whitelist,
            on_blocked_site_detected=self._on_blocked_site_detected,
            check_interval=MONITOR_CHECK_INTERVAL
        )
        self.whitelist_monitor.start()

    # ═══════════════════════════════════════
    #  캘리브레이션
    # ═══════════════════════════════════════

    def _open_calibration(self):
        try:
            if self.gaze_tracker is None or not self.gaze_tracker.is_running:
                self.gaze_tracker = GazeTracker(
                    gaze_lost_threshold=GAZE_LOST_THRESHOLD,
                    eye_closure_threshold=EYE_CLOSURE_THRESHOLD
                )
                self.gaze_tracker.start()
                time.sleep(0.5)
        except Exception as e:
            self.gaze_tracker = None
            messagebox.showerror("오류", f"시야각 초점 설정을 시작할 수 없습니다.\n{e}")
            return
        CalibrationWindow(self, self.gaze_tracker, self._on_calibration_complete)

    def _on_calibration_complete(self, success):
        self.is_calibrated = success
        if not self.is_studying and self.gaze_tracker:
            self.gaze_tracker.stop()
            self.gaze_tracker = None

    # ═══════════════════════════════════════
    #  콜백 핸들러
    # ═══════════════════════════════════════

    def _on_gaze_lost(self):
        if not self.video_paused:
            self.video_paused = True
            self.alert_count += 1
            threading.Thread(target=pause_video, daemon=True).start()
            self.after(0, lambda: self.status_indicator.configure(text="🔴 시선 이탈"))
            self.after(0, lambda: self.status_dot.configure(text_color=RED))
            self.after(0, lambda: self._add_alert("👀", "시선 이탈 감지", RED))
            self.after(0, self._update_activity_counts)
            self.after(100, lambda: show_gaze_lost_popup(self))

    def _on_gaze_restored(self):
        pass

    def _on_eye_closed(self):
        if not self.video_paused:
            self.video_paused = True
            self.alert_count += 1
            threading.Thread(target=pause_video, daemon=True).start()
            self.after(0, lambda: self.status_indicator.configure(text="🟠 눈 감음 감지"))
            self.after(0, lambda: self.status_dot.configure(text_color=ORANGE))
            self.after(0, lambda: self._add_alert("😴", "눈 감음 감지 (5초+)", ORANGE))
            self.after(0, self._update_activity_counts)
            self.after(100, lambda: show_eye_closed_popup(self))

    def _on_blocked_site_detected(self, window_title):
        self.block_count += 1
        self.after(0, lambda: self._add_alert("🚫", "비허용 사이트 차단", PURPLE))
        self.after(0, self._update_activity_counts)
        self.after(0, lambda: show_blocked_site_popup(self, window_title))

    # ═══════════════════════════════════════
    #  팝업 액션
    # ═══════════════════════════════════════

    def _on_popup_play(self):
        if self.gaze_popup:
            try:
                self.gaze_popup.destroy()
            except Exception:
                pass
            self.gaze_popup = None
        self.video_paused = False
        threading.Thread(target=play_video, daemon=True).start()
        self.status_indicator.configure(text="🔵 열심히 공부 중!")
        self.status_dot.configure(text_color=GREEN)

    def _on_popup_rewind(self):
        if self.gaze_popup:
            try:
                self.gaze_popup.destroy()
            except Exception:
                pass
            self.gaze_popup = None
        self.video_paused = False
        threading.Thread(target=rewind_and_play, daemon=True).start()
        self.status_indicator.configure(text="🔵 열심히 공부 중!")
        self.status_dot.configure(text_color=GREEN)

    # ═══════════════════════════════════════
    #  알림 / 활동 카운트
    # ═══════════════════════════════════════

    def _add_alert(self, icon, message, color):
        now = datetime.now().strftime("%H:%M")
        for w in self.alert_list_frame.winfo_children():
            if hasattr(w, 'cget') and 'text' in w.keys():
                try:
                    if "아직" in w.cget("text"):
                        w.destroy()
                except Exception:
                    pass

        row = ctk.CTkFrame(self.alert_list_frame, fg_color="transparent")
        row.pack(fill="x", pady=3, before=self.alert_list_frame.winfo_children()[0] if self.alert_list_frame.winfo_children() else None)
        ctk.CTkLabel(row, text=icon, font=ctk.CTkFont(size=14)).pack(side="left", padx=(5, 8))
        ctk.CTkLabel(row, text=message, font=ctk.CTkFont(size=12), text_color=TEXT_PRIMARY).pack(side="left")
        ctk.CTkLabel(row, text=now, font=ctk.CTkFont(size=10), text_color=TEXT_MUTED).pack(side="right", padx=5)

    def _update_activity_counts(self):
        urls_count = len(api_client.get_all_whitelist_urls())
        if "허용됨" in self.act_labels:
            self.act_labels["허용됨"].configure(text=str(urls_count))
        if "차단됨" in self.act_labels:
            self.act_labels["차단됨"].configure(text=str(self.block_count))
        if "총 감지" in self.act_labels:
            self.act_labels["총 감지"].configure(text=str(self.alert_count + self.block_count))
        if "alert_count" in self.stat_cards:
            self.stat_cards["alert_count"].configure(text=f"{self.alert_count}회")

    # ═══════════════════════════════════════
    #  카메라 / 타이머 업데이트
    # ═══════════════════════════════════════

    def _update_camera(self):
        if not self.is_studying or self.gaze_tracker is None:
            return
        frame = self.gaze_tracker.get_current_frame()
        status = self.gaze_tracker.get_status()

        if frame is not None:
            frame_rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
            h, w = frame_rgb.shape[:2]
            scale = min(500 / w, 160 / h)
            nw, nh = int(w * scale), int(h * scale)
            img = Image.fromarray(frame_rgb).resize((nw, nh), Image.Resampling.LANCZOS)
            photo = ctk.CTkImage(light_image=img, dark_image=img, size=(nw, nh))
            self.camera_label.configure(image=photo, text="")
            self.camera_label.image = photo

        direction = status.get('gaze_direction', '-')
        direction_kr = {
            'center': '정면', 'left': '왼쪽', 'right': '오른쪽',
            'up': '위쪽', 'down': '아래쪽', 'no_face': '얼굴 없음'
        }.get(direction, '-')
        self.gaze_status_badge.configure(text=direction_kr)
        self.after(CAMERA_UPDATE_INTERVAL, self._update_camera)

    def _update_timer(self):
        if not self.is_studying:
            return
        elapsed = datetime.now() - self.study_start_time
        total_seconds = int(elapsed.total_seconds())
        h, r = divmod(total_seconds, 3600)
        m, s = divmod(r, 60)
        self.timer_label.configure(text=f"{h:02d} : {m:02d} : {s:02d}")
        self.after(TIMER_UPDATE_INTERVAL, self._update_timer)

    def _update_home_stats(self):
        today_focus = self.db.get_today_total_focus_time()
        th, tr = divmod(today_focus, 3600)
        tm, _ = divmod(tr, 60)
        if "study_time" in self.stat_cards:
            self.stat_cards["study_time"].configure(text=f"{th}h {tm}m")
        self._update_activity_counts()

    # ═══════════════════════════════════════
    #  앱 종료
    # ═══════════════════════════════════════

    def _on_closing(self):
        if self.is_studying:
            if messagebox.askyesno("종료 확인", "공부 중입니다. 종료하시겠습니까?"):
                self._stop_study()
            else:
                return
        if self.whitelist_monitor:
            self.whitelist_monitor.stop()
        if self.gaze_tracker:
            self.gaze_tracker.stop()
        self.db.close()
        self.destroy()
