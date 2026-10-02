"""
I-Study 데스크톱 앱 GUI E2E 테스트 (화면 시연용)

실제 FocusEyePro 앱을 띄우고 위젯을 순서대로 조작한다.
- 로그인 다이얼로그에 한 글자씩 입력하고 버튼을 누르는 과정이 화면에 그대로 보인다.
- 화면 오른쪽 위 진행 패널에 현재 단계와 PASS/FAIL 이 표시된다.
- 단계별 스크린샷: results/screens/*.png, 결과: results/desktop_results.json

테스트 중 외부 부작용은 기록만 하도록 대체한다:
  영상 일시정지/재생 키 전송(pyautogui), 비허용 창 최소화, 브라우저 열기, 메시지박스

계정: api_e2e.py 가 만든 e2e_accounts.json 의 학생 계정을 사용한다.
실행: venv\\Scripts\\python.exe tests\\e2e\\desktop_gui_e2e.py
"""

import json
import os
import sys
import time
import traceback
import tkinter as tk
import webbrowser

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.abspath(os.path.join(HERE, "..", ".."))
sys.path.insert(0, ROOT)
os.environ.setdefault("API_SERVER_URL", "http://127.0.0.1:8000")

import psycopg2
import requests
from PIL import ImageGrab

import ui_ux.desktop.app as appmod
from ai_core.monitor import WhitelistMonitor
from ui_ux.desktop.dialogs.calibration import CalibrationWindow
from ui_ux.desktop.dialogs.login import LoginDialog
from shared.env_config import API_SERVER_URL

SCREENS = os.path.join(HERE, "results", "screens")
os.makedirs(SCREENS, exist_ok=True)
ACC = json.load(open(os.path.join(HERE, "e2e_accounts.json"), encoding="utf-8"))["student"]
DB = dict(host="localhost", port=5432, dbname="istudy", user="postgres",
          password=os.getenv("DB_PASSWORD", "aisw2026"))

RESULTS, SIDE_EFFECTS, CALLBACK_ERRORS = [], [], []

# ─── 외부 부작용 → 기록만 ───
for _name in ("pause_video", "play_video", "rewind_and_play"):
    setattr(appmod, _name, (lambda n: (lambda: SIDE_EFFECTS.append(n)))(_name))
WhitelistMonitor._minimize_window = lambda self: SIDE_EFFECTS.append("minimize_window")
webbrowser.open = lambda url, *a, **k: SIDE_EFFECTS.append(("browser", url)) or True
for _fn in ("showerror", "showwarning", "showinfo"):
    setattr(appmod.messagebox, _fn, (lambda n: (lambda *a, **k: SIDE_EFFECTS.append((n, a))))(_fn))
appmod.messagebox.askyesno = lambda *a, **k: SIDE_EFFECTS.append(("askyesno", a)) or True


class RecordingLoginDialog(LoginDialog):
    instance = None

    def __init__(self, parent):
        super().__init__(parent)
        RecordingLoginDialog.instance = self


appmod.LoginDialog = RecordingLoginDialog


# ─── 진행 패널 ───
class Panel:
    def __init__(self, root):
        self.win = tk.Toplevel(root)
        self.win.overrideredirect(True)
        self.win.attributes("-topmost", True)
        sw = self.win.winfo_screenwidth()
        self.win.geometry(f"440x560+{sw - 460}+20")
        self.win.configure(bg="#111827")
        tk.Label(self.win, text="🤖 I-Study 자동 GUI 테스트", fg="#FBBF24", bg="#111827",
                 font=("Malgun Gothic", 13, "bold")).pack(anchor="w", padx=14, pady=(12, 2))
        self.now = tk.Label(self.win, text="준비 중…", fg="#E5E7EB", bg="#111827", wraplength=410,
                            justify="left", font=("Malgun Gothic", 11))
        self.now.pack(anchor="w", padx=14, pady=(0, 8))
        self.score = tk.Label(self.win, text="PASS 0 · FAIL 0", fg="#9CA3AF", bg="#111827",
                              font=("Malgun Gothic", 10, "bold"))
        self.score.pack(anchor="w", padx=14)
        self.log = tk.Text(self.win, bg="#1F2937", fg="#E5E7EB", bd=0, font=("Malgun Gothic", 9),
                           wrap="word", height=26)
        self.log.pack(fill="both", expand=True, padx=10, pady=10)
        self.log.tag_config("pass", foreground="#34D399")
        self.log.tag_config("fail", foreground="#F87171")

    def step(self, text):
        self.now.configure(text="▶ " + text)
        self.win.lift()

    def add(self, tc, name, ok, detail):
        line = f"{'✅' if ok else '❌'} {tc} {name}" + (f"\n     → {detail}" if detail and not ok else "") + "\n"
        self.log.insert("end", line, "pass" if ok else "fail")
        self.log.see("end")
        p = sum(r["pass"] for r in RESULTS)
        self.score.configure(text=f"PASS {p} · FAIL {len(RESULTS) - p}")


PANEL = None


def check(tc, name, ok, detail=""):
    RESULTS.append({"tc": tc, "name": name, "pass": bool(ok), "detail": str(detail)[:300]})
    print(f"[{'PASS' if ok else 'FAIL'}] {tc:<5} {name}" + (f"  — {detail}" if detail and not ok else ""), flush=True)
    try:
        if PANEL:
            PANEL.add(tc, name, ok, str(detail)[:120])
    except tk.TclError:
        pass
    return ok


def shot(widget, name):
    try:
        widget.update_idletasks()
        x, y = widget.winfo_rootx(), widget.winfo_rooty()
        w, h = widget.winfo_width(), widget.winfo_height()
        ImageGrab.grab(bbox=(x, y, x + w, y + h), all_screens=True).save(os.path.join(SCREENS, name + ".png"))
    except Exception as e:
        print("screenshot failed:", name, e)


def wait_until(cond, timeout_ms, poll=200):
    t0 = time.time()
    while (time.time() - t0) * 1000 < timeout_ms:
        try:
            if cond():
                return True
        except Exception:
            pass
        yield poll
    return False


def type_into(entry, text, delay=110):
    entry.focus_set()
    for ch in text:
        entry.insert("end", ch)
        yield delay


def press(button, hold=450):
    """버튼을 잠깐 강조한 뒤 누른다(화면에서 어떤 버튼이 눌리는지 보이도록)."""
    old = button.cget("fg_color")
    button.configure(fg_color="#F59E0B")
    yield hold
    try:
        button.configure(fg_color=old)
    except Exception:
        pass
    try:
        button.invoke()
    except Exception:
        # 실제 클릭이었다면 Tk 가 콜백 예외를 report_callback_exception 으로 넘기고 앱은 계속 돈다
        CALLBACK_ERRORS.append(traceback.format_exc())
        print("[callback exception]", traceback.format_exc().splitlines()[-1], flush=True)
    yield 300


def find_buttons(widget, text_part):
    import customtkinter as ctk
    out = []
    for w in widget.winfo_children():
        if isinstance(w, ctk.CTkButton) and text_part in str(w.cget("text")):
            out.append(w)
        out += find_buttons(w, text_part)
    return out


def find_labels_text(widget):
    import customtkinter as ctk
    out = []
    for w in widget.winfo_children():
        if isinstance(w, ctk.CTkLabel):
            out.append(str(w.cget("text")))
        out += find_labels_text(w)
    return out


def effective_whitelist(token):
    r = requests.get(f"{API_SERVER_URL}/whitelist/effective", headers={"Authorization": f"Bearer {token}"}, timeout=5)
    return r.json() if r.ok else []


def toplevels(app, cls=None):
    return [w for w in app.winfo_children()
            if isinstance(w, tk.Toplevel) and w.winfo_exists() and (cls is None or isinstance(w, cls))]


def db_rows_for(login_id):
    with psycopg2.connect(**DB) as c, c.cursor() as cur:
        cur.execute("select count(*) from study_sessions s join users u on u.id=s.user_id where u.login_id=%s", (login_id,))
        return cur.fetchone()[0]


# ─── 시나리오 ───
def scenario(app):
    global PANEL
    PANEL = Panel(app)
    yield 1200

    # 로그인
    ok = yield from wait_until(lambda: RecordingLoginDialog.instance and RecordingLoginDialog.instance.winfo_viewable(), 8000)
    dlg = RecordingLoginDialog.instance
    PANEL.step("D-01 로그인 창 표시 확인")
    check("D-01", "앱 실행 시 로그인 창 표시", ok and dlg.title() == "I-Study 로그인", dlg.title() if dlg else None)
    dlg.geometry("+380+160")
    yield 1200
    shot(dlg, "01_login")

    PANEL.step("D-02 빈 칸으로 로그인 → 입력 요구 메시지")
    yield from press(dlg._btn)
    msg = dlg._err_label.cget("text")
    check("D-02", "빈 입력 로그인 시 오류 안내", msg == "아이디와 비밀번호를 입력하세요.", msg)
    yield 1200

    PANEL.step("D-03 틀린 비밀번호로 로그인 시도")
    yield from type_into(dlg._id_entry, ACC["login_id"])
    yield from type_into(dlg._pw_entry, "wrongpass")
    yield 400
    yield from press(dlg._btn)
    msg = dlg._err_label.cget("text")
    check("D-03", "틀린 비밀번호 → 인증 실패 안내", msg == "아이디 또는 비밀번호가 올바르지 않습니다.", msg)
    shot(dlg, "02_login_fail")
    yield 1500

    PANEL.step("D-04 올바른 비밀번호로 로그인")
    dlg._pw_entry.delete(0, "end")
    yield 300
    yield from type_into(dlg._pw_entry, ACC["password"], delay=70)
    yield 400
    yield from press(dlg._btn)
    ok = yield from wait_until(lambda: hasattr(app, "focus_btn") and app.current_name, 8000)
    check("D-04", "로그인 성공 → 메인 화면 진입", ok and app.title() == f"I-Study — {ACC['name']}", app.title())
    app.geometry("1200x750+20+20")
    yield 1800
    shot(app, "03_home")

    # 홈
    PANEL.step("D-05 빠른 링크 = 서버 화이트리스트")
    server_wl = effective_whitelist(app.current_token)
    link_btns = [w for w in app.link_buttons_frame.winfo_children() if hasattr(w, "invoke")]
    names = [str(b.cget("text")).replace("🌐", "").strip() for b in link_btns]
    check("D-05", f"빠른 링크 {len(link_btns)}개 = 서버 화이트리스트 {len(server_wl)}개",
          len(link_btns) == len(server_wl) and names == [w["name"] for w in server_wl], names)
    yield 1000

    PANEL.step("D-06 빠른 링크 클릭 → 해당 URL 열기")
    before = len(SIDE_EFFECTS)
    if link_btns:
        yield from press(link_btns[0])
    opened = [e for e in SIDE_EFFECTS[before:] if isinstance(e, tuple) and e[0] == "browser"]
    check("D-06", "빠른 링크 클릭 시 등록 URL 열기", opened and opened[0][1] == server_wl[0]["url"], opened)
    yield 900

    PANEL.step("D-07 🌐 웹 바로가기 → 자동 로그인 URL")
    before = len(SIDE_EFFECTS)
    web_btn = find_buttons(app, "웹 바로가기")[0]
    yield from press(web_btn)
    opened = [e for e in SIDE_EFFECTS[before:] if isinstance(e, tuple) and e[0] == "browser"]
    url = opened[0][1] if opened else ""
    tok = url.split("token=", 1)[1] if "token=" in url else ""
    me = requests.get(f"{API_SERVER_URL}/users/me", headers={"Authorization": f"Bearer {tok}"}, timeout=5)
    check("D-07", "웹 바로가기 URL·토큰 유효(/users/me 200)",
          url.startswith(f"{API_SERVER_URL}/auto-login?token=") and me.status_code == 200, me.status_code)
    yield 1000

    # 사이드바: 화이트리스트·학습 통계는 웹 전용 → 앱은 홈만
    PANEL.step("P-01 사이드바 메뉴 = 홈")
    menu = [str(b.cget("text")).strip() for b in app.nav_buttons.values()]
    check("P-01", "앱 사이드바에 화이트리스트·학습 통계 메뉴 없음(웹 전용)",
          list(app.nav_buttons) == ["home"] and list(app.pages) == ["home"]
          and not find_buttons(app, "화이트리스트") and not find_buttons(app, "학습 통계"), menu)
    yield 800

    # 캘리브레이션
    PANEL.step("D-08 👁️ 시야각 초점 설정 (웹캠 켜짐 — 화면 중앙을 봐 주세요)")
    cal_btn = find_buttons(app, "시야각 초점 설정")[0]
    yield from press(cal_btn)
    ok = yield from wait_until(lambda: toplevels(app, CalibrationWindow), 10000)
    cal = toplevels(app, CalibrationWindow)[0] if ok else None
    check("D-08", "캘리브레이션 창 열림", bool(cal))
    if cal:
        got_frame = yield from wait_until(lambda: getattr(cal.camera_label, "image", None) is not None, 10000)
        check("D-09", "캘리브레이션 창에 웹캠 영상 표시", got_frame)
        yield 2500
        shot(cal, "04_calibration")
        done = yield from wait_until(lambda: not cal.winfo_exists(), 12000)
        if done:
            check("D-10", "얼굴 인식 샘플 30개 수집 → 자동 완료", app.is_calibrated is True, app.is_calibrated)
        else:
            n = cal.sample_count
            PANEL.step(f"D-10 샘플 {n}/30 — 얼굴 인식 부족, 건너뛰기")
            yield from press(find_buttons(cal, "건너뛰기")[0])
            check("D-10", f"캘리브레이션 건너뛰기(수집 {n}/30)", not cal.winfo_exists() and app.is_calibrated, n)
    yield 1200

    # 집중 모드
    PANEL.step("D-11 ⚡ 집중 모드 ON (웹캠 시선추적 시작)")
    logs_before = len(requests.get(f"{API_SERVER_URL}/stats/logs", headers={"Authorization": f"Bearer {app.current_token}"}, timeout=5).json()["items"])
    db_before = db_rows_for(ACC["login_id"])
    yield from press(app.focus_btn)
    check("D-11", "집중 모드 ON 표시·세션 상태 변경",
          app.is_studying and "ON" in app.focus_btn.cget("text") and "학습 진행 중" in app.session_label.cget("text"),
          app.focus_btn.cget("text"))
    ok = yield from wait_until(lambda: getattr(app.camera_label, "image", None) is not None, 10000)
    check("D-12", "홈 카메라 영역에 실시간 영상 표시", ok)
    ok = yield from wait_until(lambda: app.gaze_status_badge.cget("text") not in ("-", ""), 10000)
    check("D-13", "시선 방향 배지 갱신", ok, app.gaze_status_badge.cget("text"))
    check("D-14", "화이트리스트 모니터 동작",
          app.whitelist_monitor is not None and len(app.whitelist_monitor.whitelist_urls) == len(server_wl),
          len(app.whitelist_monitor.whitelist_urls) if app.whitelist_monitor else None)
    t1 = app.timer_label.cget("text")
    yield 3000
    t2 = app.timer_label.cget("text")
    check("D-15", "학습 타이머 증가", t1 != t2 and t2 != "00 : 00 : 00", f"{t1} → {t2}")
    shot(app, "05_focus_on")

    PANEL.step("D-16 시선 이탈 이벤트 → 경고 팝업 → ▶ 재생")
    if not app.gaze_popup:
        app.video_paused = False
        app._on_gaze_lost()
    ok = yield from wait_until(lambda: app.gaze_popup and app.gaze_popup.winfo_exists(), 3000)
    yield 1200
    texts = find_labels_text(app.gaze_popup) if ok else []
    check("D-16", "시선 이탈/눈 감음 경고 팝업 표시", ok and any("화면을 보고" in t or "눈을 감고" in t for t in texts), texts)
    shot(app.gaze_popup, "06_gaze_popup") if ok else None
    check("D-17", "경고 시 영상 일시정지 호출", "pause_video" in SIDE_EFFECTS, SIDE_EFFECTS[-3:])
    if ok:
        pop = app.gaze_popup
        yield from press(find_buttons(pop, "재생")[0])
        check("D-18", "▶ 재생 → 팝업 닫힘·재생 호출", not pop.winfo_exists() and "play_video" in SIDE_EFFECTS and not app.video_paused)
    yield 1200

    PANEL.step("D-19 눈 감음 이벤트 → 경고 팝업 → ⏪ -10초")
    app.video_paused = False
    app._on_eye_closed()
    ok = yield from wait_until(lambda: app.gaze_popup and app.gaze_popup.winfo_exists(), 3000)
    yield 1200
    texts = find_labels_text(app.gaze_popup) if ok else []
    check("D-19", "눈 감음 경고 팝업 표시", ok and any("눈을 감고" in t for t in texts), texts)
    if ok:
        pop = app.gaze_popup
        yield from press(find_buttons(pop, "-10초")[0])
        check("D-20", "⏪ -10초 → 팝업 닫힘·되감기 호출", not pop.winfo_exists() and "rewind_and_play" in SIDE_EFFECTS)
    yield 1200

    PANEL.step("D-21 비허용 사이트 감지 → 차단 팝업 → 확인")
    app._on_blocked_site_detected("재미있는 쇼츠 - YouTube - Chrome")
    ok = yield from wait_until(lambda: app.blocked_popup and app.blocked_popup.winfo_exists(), 3000)
    yield 1200
    check("D-21", "비허용 사이트 차단 팝업 표시", ok and any("허용되지 않은" in t for t in find_labels_text(app.blocked_popup)))
    shot(app.blocked_popup, "07_blocked_popup") if ok else None
    if ok:
        pop = app.blocked_popup
        yield from press(find_buttons(pop, "확인")[0])
        check("D-22", "확인 → 차단 팝업 닫힘", not pop.winfo_exists())
    yield 800
    blocked = app.act_labels["차단됨"].cget("text")
    total = app.act_labels["총 감지"].cget("text")
    allowed = app.act_labels["허용됨"].cget("text")
    check("D-23", "최근 현황 카운트 갱신(허용/차단/총 감지)",
          allowed == str(len(server_wl)) and int(blocked) >= 1 and int(total) >= 3, f"허용 {allowed} 차단 {blocked} 총 {total}")
    alerts = [t for t in find_labels_text(app.alert_list_frame) if "감지" in t or "차단" in t]
    check("D-24", "최근 알림 목록에 이벤트 기록", len(alerts) >= 3, alerts)
    shot(app, "08_home_after_events")

    PANEL.step("D-25 실제 시선추적 계속 진행 중… (8초)")
    yield 8000

    PANEL.step("D-25 ⚡ 집중 모드 OFF → 학습 리포트")
    errs_before = len(CALLBACK_ERRORS)
    yield from press(app.focus_btn)
    ok = yield from wait_until(lambda: any("수고하셨습니다" in " ".join(find_labels_text(t)) for t in toplevels(app)), 5000)
    report = next((t for t in toplevels(app) if "수고하셨습니다" in " ".join(find_labels_text(t))), None)
    check("D-25", "집중 모드 OFF → 학습 리포트 표시", ok, find_labels_text(report) if report else None)
    if report:
        yield 1500
        shot(report, "09_report")
    check("D-26", "집중 모드 종료 처리 중 예외 없음", len(CALLBACK_ERRORS) == errs_before,
          CALLBACK_ERRORS[-1].splitlines()[-1] if len(CALLBACK_ERRORS) > errs_before else "")
    check("D-27", "UI 대기 상태 복귀(OFF·타이머 0)",
          not app.is_studying and "OFF" in app.focus_btn.cget("text") and app.timer_label.cget("text") == "00 : 00 : 00")
    logs_after = requests.get(f"{API_SERVER_URL}/stats/logs", headers={"Authorization": f"Bearer {app.current_token}"}, timeout=5).json()["items"]
    check("D-28", "학습 세션 서버 저장(/stats/logs +1)", len(logs_after) == logs_before + 1, f"{logs_before} → {len(logs_after)}")
    check("D-29", "DB study_sessions 행 +1", db_rows_for(ACC["login_id"]) == db_before + 1)
    if report:
        PANEL.step("D-30 리포트 확인 버튼")
        yield from press(find_buttons(report, "확인")[0])
        check("D-30", "리포트 확인 → 닫힘", not report.winfo_exists())
    yield 1000

    yield 500

    PANEL.step("D-31 앱 종료")
    p = sum(r["pass"] for r in RESULTS)
    PANEL.now.configure(text=f"완료 — PASS {p} / FAIL {len(RESULTS) - p}  (5초 후 종료)")
    yield 5000
    app._on_closing()
    check("D-31", "앱 정상 종료", True)


def main():
    sys.stdout.reconfigure(encoding="utf-8")

    class E2EApp(appmod.FocusEyePro):
        def report_callback_exception(self, exc, val, tb):
            CALLBACK_ERRORS.append("".join(traceback.format_exception(exc, val, tb)))
            print("[callback exception]", val, flush=True)

        def _do_login(self):
            self.runner = scenario(self)
            self.after(10, self._tick)
            super()._do_login()

        def _tick(self):
            try:
                delay = next(self.runner)
            except StopIteration:
                return
            except Exception:
                CALLBACK_ERRORS.append(traceback.format_exc())
                check("D-ERR", "시나리오 실행 오류", False, traceback.format_exc().splitlines()[-1])
                try:
                    self._on_closing()
                except Exception:
                    pass
                return
            try:
                self.after(delay or 1, self._tick)
            except Exception:
                pass

    app = E2EApp()
    app.mainloop()

    with open(os.path.join(HERE, "results", "desktop_results.json"), "w", encoding="utf-8") as f:
        json.dump({"results": RESULTS, "side_effects": [str(s) for s in SIDE_EFFECTS],
                   "callback_errors": CALLBACK_ERRORS}, f, ensure_ascii=False, indent=2)
    p = sum(r["pass"] for r in RESULTS)
    print(f"\n총 {len(RESULTS)}건 — PASS {p} / FAIL {len(RESULTS) - p}")
    for e in CALLBACK_ERRORS:
        print("\n[captured exception]\n" + e)


if __name__ == "__main__":
    main()
