"""
I-Study 데스크톱 앱 - 로그인 다이얼로그
앱 시작 시 웹 백엔드와 인증, login_id를 앱에 저장
"""

import requests
import customtkinter as ctk

try:
    import sys, os
    sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "..", ".."))
    from shared.env_config import API_SERVER_URL as API_URL
except ImportError:
    API_URL = "http://127.0.0.1:8000"

BG      = "#F2F4F6"
WHITE   = "#FFFFFF"
BLUE    = "#3D7EF8"
TEXT    = "#2D3648"
MUTED   = "#8B95A1"
ERR     = "#F04452"
RADIUS  = 16


class LoginDialog(ctk.CTkToplevel):
    """앱 시작 시 표시되는 로그인 창"""

    def __init__(self, parent):
        super().__init__(parent)
        self.title("I-Study 로그인")
        self.geometry("400x460")
        self.resizable(False, False)
        self.configure(fg_color=BG)
        self.grab_set()

        self.result_login_id: str | None = None
        self.result_token: str | None = None
        self.result_name: str | None = None
        self._offline = False

        self._build()
        self.protocol("WM_DELETE_WINDOW", self._on_cancel)

    def _build(self):
        frame = ctk.CTkFrame(self, fg_color=WHITE, corner_radius=RADIUS)
        frame.pack(fill="both", expand=True, padx=24, pady=24)

        ctk.CTkLabel(frame, text="📘", font=ctk.CTkFont(size=36)).pack(pady=(24, 4))
        ctk.CTkLabel(frame, text="I-Study", font=ctk.CTkFont(size=22, weight="bold"),
                     text_color=TEXT).pack()
        ctk.CTkLabel(frame, text="계정으로 로그인하세요", font=ctk.CTkFont(size=13),
                     text_color=MUTED).pack(pady=(2, 20))

        # 아이디
        ctk.CTkLabel(frame, text="아이디", font=ctk.CTkFont(size=12, weight="bold"),
                     text_color=MUTED, anchor="w").pack(fill="x", padx=24)
        self._id_entry = ctk.CTkEntry(frame, placeholder_text="아이디 입력",
                                       fg_color=BG, corner_radius=10, height=42)
        self._id_entry.pack(fill="x", padx=24, pady=(4, 12))

        # 비밀번호
        ctk.CTkLabel(frame, text="비밀번호", font=ctk.CTkFont(size=12, weight="bold"),
                     text_color=MUTED, anchor="w").pack(fill="x", padx=24)
        self._pw_entry = ctk.CTkEntry(frame, placeholder_text="비밀번호 입력", show="●",
                                       fg_color=BG, corner_radius=10, height=42)
        self._pw_entry.pack(fill="x", padx=24, pady=(4, 4))
        self._pw_entry.bind("<Return>", lambda _: self._do_login())

        # 에러 메시지
        self._err_label = ctk.CTkLabel(frame, text="", font=ctk.CTkFont(size=12),
                                        text_color=ERR)
        self._err_label.pack(pady=(0, 8))

        # 로그인 버튼
        self._btn = ctk.CTkButton(
            frame, text="로그인", height=46,
            fg_color=BLUE, hover_color="#1B64DA",
            font=ctk.CTkFont(size=14, weight="bold"),
            corner_radius=50, command=self._do_login
        )
        self._btn.pack(fill="x", padx=24, pady=(0, 8))

        # 오프라인 모드
        ctk.CTkButton(
            frame, text="서버 없이 시작 (오프라인)",
            fg_color="transparent", hover_color=BG,
            text_color=MUTED, font=ctk.CTkFont(size=12),
            command=self._go_offline
        ).pack(pady=(0, 16))

    def _do_login(self):
        login_id = self._id_entry.get().strip()
        password = self._pw_entry.get()
        if not login_id or not password:
            self._err_label.configure(text="아이디와 비밀번호를 입력하세요.")
            return

        self._btn.configure(state="disabled", text="로그인 중…")
        self._err_label.configure(text="")
        self.update()

        try:
            resp = requests.post(
                f"{API_URL}/users/login",
                json={"login_id": login_id, "password": password},
                timeout=5
            )
            if resp.status_code == 200:
                data = resp.json()
                self.result_login_id = login_id
                self.result_token = data.get("access_token")
                self.result_name = data.get("name", login_id)
                self.destroy()
            elif resp.status_code == 403:
                self._err_label.configure(text="관리자 승인 대기 중입니다.")
            else:
                self._err_label.configure(text="아이디 또는 비밀번호가 올바르지 않습니다.")
        except requests.exceptions.ConnectionError:
            self._err_label.configure(text="서버에 연결할 수 없습니다. 오프라인으로 시작하세요.")
        finally:
            try:
                self._btn.configure(state="normal", text="로그인")
            except Exception:
                pass

    def _go_offline(self):
        self._offline = True
        self.destroy()

    def _on_cancel(self):
        self._offline = True
        self.destroy()
