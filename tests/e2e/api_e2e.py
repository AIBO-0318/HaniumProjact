"""
I-Study 서버 API·DB·AI WebSocket 통합 테스트 (E2E)

- 실행 중인 Spring(8000) / FastAPI AI(8001) / PostgreSQL 을 대상으로 한다.
- 매 실행마다 qa_e2e_ 접두사의 학생·교사·관리자 테스트 계정을 새로 만들고
  e2e_accounts.json 에 기록한다(데스크톱 GUI 테스트가 같은 계정을 사용).
- 결과는 results/api_results.json 에 저장된다.
- 테스트 데이터 정리는 cleanup.py 로 한다.

실행: venv\\Scripts\\python.exe tests\\e2e\\api_e2e.py
"""

import base64
import json
import os
import secrets
import socket
import string
import sys
import time
from datetime import datetime, timedelta

import psycopg2
import requests

HERE = os.path.dirname(os.path.abspath(__file__))
BASE = os.getenv("E2E_API", "http://127.0.0.1:8000")
AI = os.getenv("E2E_AI", "127.0.0.1:8001")
DB = dict(host="localhost", port=5432, dbname="istudy", user="postgres",
          password=os.getenv("DB_PASSWORD", "aisw2026"))

RESULTS = []


def check(tc, name, ok, detail=""):
    RESULTS.append({"tc": tc, "name": name, "pass": bool(ok), "detail": str(detail)[:300]})
    mark = "PASS" if ok else "FAIL"
    print(f"[{mark}] {tc:<7} {name}" + (f"  — {detail}" if detail and not ok else ""))
    return ok


def _pw(n=14):
    alphabet = string.ascii_letters + string.digits
    return "".join(secrets.choice(alphabet) for _ in range(n))


def H(token):
    return {"Authorization": f"Bearer {token}"}


def db_exec(sql, args=()):
    with psycopg2.connect(**DB) as c, c.cursor() as cur:
        cur.execute(sql, args)


def db_one(sql, args=()):
    with psycopg2.connect(**DB) as c, c.cursor() as cur:
        cur.execute(sql, args)
        return cur.fetchone()


# ─── 최소 WebSocket 클라이언트 (외부 패키지 없이 /ws/gaze 검증용) ───
def ws_connect(host_port, path):
    host, port = host_port.split(":")
    s = socket.create_connection((host, int(port)), timeout=10)
    key = base64.b64encode(os.urandom(16)).decode()
    s.sendall((f"GET {path} HTTP/1.1\r\nHost: {host_port}\r\nUpgrade: websocket\r\n"
               f"Connection: Upgrade\r\nSec-WebSocket-Key: {key}\r\n"
               f"Sec-WebSocket-Version: 13\r\n\r\n").encode())
    resp = b""
    while b"\r\n\r\n" not in resp:
        chunk = s.recv(4096)
        if not chunk:
            break
        resp += chunk
    status = resp.split(b"\r\n", 1)[0].decode(errors="replace")
    return s, status


def ws_send(s, text):
    data = text.encode()
    mask = os.urandom(4)
    hdr = bytearray([0x81])
    n = len(data)
    if n < 126:
        hdr.append(0x80 | n)
    elif n < 65536:
        hdr.append(0x80 | 126); hdr += n.to_bytes(2, "big")
    else:
        hdr.append(0x80 | 127); hdr += n.to_bytes(8, "big")
    s.sendall(bytes(hdr) + mask + bytes(b ^ mask[i % 4] for i, b in enumerate(data)))


def _recv_exact(s, n):
    buf = b""
    while len(buf) < n:
        chunk = s.recv(n - len(buf))
        if not chunk:
            raise ConnectionError("closed")
        buf += chunk
    return buf


def ws_recv(s):
    b1, b2 = _recv_exact(s, 2)
    op, n = b1 & 0x0F, b2 & 0x7F
    if n == 126:
        n = int.from_bytes(_recv_exact(s, 2), "big")
    elif n == 127:
        n = int.from_bytes(_recv_exact(s, 8), "big")
    payload = _recv_exact(s, n)
    if op == 0x8:
        code = int.from_bytes(payload[:2], "big") if len(payload) >= 2 else None
        return ("close", code)
    return ("text", payload.decode(errors="replace"))


def main():
    tag = datetime.now().strftime("%m%d%H%M")
    acc = {
        "student": {"login_id": f"qa_e2e_s{tag}", "password": _pw(), "name": "QA학생"},
        "teacher": {"login_id": f"qa_e2e_t{tag}", "password": _pw(), "name": "QA교사"},
        "admin":   {"admin_id": f"qa_e2e_a{tag}", "password": _pw(), "name": "QA관리자"},
        "created_at": datetime.now().isoformat(timespec="seconds"),
        "base_url": BASE,
    }
    S, T, A = acc["student"], acc["teacher"], acc["admin"]

    # ── 0. 서버 기동 ──
    r = requests.get(f"{BASE}/", timeout=5)
    check("SYS-01", "Spring 8000 웹 루트 응답", r.status_code == 200, r.status_code)
    r = requests.get(f"http://{AI}/health", timeout=5)
    check("SYS-02", "AI 8001 /health", r.status_code == 200 and r.json().get("status") == "ok", r.text)
    check("SYS-03", "PostgreSQL 연결", db_one("select 1")[0] == 1)

    pages = ["/", "/signup", "/main", "/calibration", "/whitelist", "/stats", "/schedule",
             "/mypage", "/dashboard", "/gaze-settings", "/teacher-whitelist", "/auto-login",
             "/admin-users", "/admin-stats", "/focus-mode", "/teacher-schedule"]
    bad = [p for p in pages if requests.get(BASE + p, timeout=5).status_code != 200]
    check("WEB-01", f"웹 페이지 {len(pages)}종 200 응답", not bad, bad)

    # ── 1. 회원가입 ──
    r = requests.post(f"{BASE}/users/signup", json={**S, "role": "STUDENT"}, timeout=5)
    check("AUTH-01", "학생 회원가입 201", r.status_code == 201, r.text)
    S["id"] = r.json().get("id") if r.ok else None
    r = requests.post(f"{BASE}/users/signup", json={**S, "role": "STUDENT"}, timeout=5)
    check("AUTH-02", "중복 아이디 가입 거부 400", r.status_code == 400, r.status_code)
    r = requests.post(f"{BASE}/users/signup",
                      json={"login_id": f"qa_e2e_x{tag}", "password": "123", "name": "x"}, timeout=5)
    check("AUTH-03", "짧은 비밀번호(3자) 가입 거부 400/422", r.status_code in (400, 422), r.status_code)
    r = requests.post(f"{BASE}/users/signup",
                      json={**T, "role": "TEACHER", "login_id": f"qa_e2e_y{tag}"}, timeout=5)
    check("AUTH-04", "교사 가입 시 학생 아이디 누락 거부 400", r.status_code == 400, r.status_code)
    r = requests.post(f"{BASE}/users/signup",
                      json={**T, "role": "TEACHER", "student_login_id": S["login_id"]}, timeout=5)
    check("AUTH-05", "교사 회원가입(담당 학생 연결) 201", r.status_code == 201, r.text)
    T["id"] = r.json().get("id") if r.ok else None
    row = db_one("select teacher_id from users where id=%s", (S["id"],))
    check("DB-01", "DB: 학생 teacher_id 가 교사 id 로 연결", row and row[0] == T["id"], row)
    row = db_one("select password_hash from users where id=%s", (S["id"],))
    check("DB-02", "DB: 비밀번호 평문 저장 안 함(BCrypt 해시)",
          row and row[0] != S["password"] and row[0].startswith("$2"), "hash prefix=" + (row[0][:4] if row else "?"))

    # ── 2. 로그인 ──
    r = requests.post(f"{BASE}/users/login", json={"login_id": S["login_id"], "password": S["password"]}, timeout=5)
    ok = check("AUTH-06", "학생 로그인(JSON) 200 + 토큰", r.status_code == 200 and r.json().get("access_token"), r.status_code)
    st = r.json()["access_token"] if ok else None
    check("AUTH-07", "로그인 응답 role/name", ok and r.json().get("role") == "STUDENT" and r.json().get("name") == S["name"], r.text[:200])
    r = requests.post(f"{BASE}/users/login", json={"login_id": S["login_id"], "password": "wrong-pass"}, timeout=5)
    check("AUTH-08", "틀린 비밀번호 401", r.status_code == 401, r.status_code)
    r = requests.post(f"{BASE}/users/login", json={"login_id": "qa_e2e_nouser", "password": "whatever1"}, timeout=5)
    check("AUTH-09", "없는 아이디 401", r.status_code == 401, r.status_code)
    r = requests.post(f"{BASE}/users/login", data={"username": S["login_id"], "password": S["password"]}, timeout=5)
    check("AUTH-10", "학생 로그인(form-urlencoded) 200", r.status_code == 200, r.status_code)
    r = requests.post(f"{BASE}/users/login", json={"login_id": T["login_id"], "password": T["password"]}, timeout=5)
    tt = r.json().get("access_token") if r.ok else None
    check("AUTH-11", "교사 로그인 200", bool(tt), r.status_code)

    r = requests.get(f"{BASE}/users/me", headers=H(st), timeout=5)
    check("AUTH-12", "GET /users/me (토큰) 200", r.status_code == 200 and r.json().get("login_id") == S["login_id"], r.status_code)
    r = requests.get(f"{BASE}/users/me", timeout=5)
    check("AUTH-13", "GET /users/me (토큰 없음) 401", r.status_code == 401, r.status_code)
    r = requests.get(f"{BASE}/users/me", headers=H(st[:-4] + "abcd"), timeout=5)
    check("AUTH-14", "변조 토큰 401", r.status_code == 401, r.status_code)

    # ── 3. 학습 통계 ──
    now = datetime.now()
    payload = {"date": now.date().isoformat(),
               "start_time": (now - timedelta(minutes=25)).isoformat(),
               "end_time": now.isoformat(),
               "total_time_seconds": 1500, "focus_time_seconds": 1200, "duration_min": 25,
               "focus_score": 80.0, "focused_min": 20, "dazed_min": 3, "distracted_min": 2}
    r = requests.post(f"{BASE}/stats/sessions", json=payload, headers=H(st), timeout=5)
    check("STAT-01", "학습 세션 저장 200", r.status_code == 200 and r.json().get("id"), r.text)
    sid = r.json().get("id") if r.ok else None
    row = db_one("select user_id, total_time_seconds, focus_time_seconds, focus_score from study_sessions where id=%s", (sid,))
    check("DB-03", "DB: study_sessions 행 저장값 일치", row and row[0] == S["id"] and row[1] == 1500 and row[2] == 1200, row)
    r = requests.post(f"{BASE}/stats/sessions", json=payload, timeout=5)
    check("STAT-02", "세션 저장 토큰 없음 401", r.status_code == 401, r.status_code)
    r = requests.get(f"{BASE}/stats/logs", headers=H(st), timeout=5)
    items = r.json().get("items", []) if r.ok else []
    check("STAT-03", "GET /stats/logs 본인 기록 1건", r.ok and len(items) == 1 and items[0]["id"] == sid, len(items))
    r = requests.get(f"{BASE}/stats/today", headers=H(st), timeout=5)
    check("STAT-04", "GET /stats/today = 1200초", r.ok and r.json().get("focus_time_seconds") == 1200, r.text)
    today = now.date().isoformat()
    for i, ep in enumerate(["daily", f"hourly?date={today}", f"week-days?date={today}", "weekly", "monthly"], start=5):
        r = requests.get(f"{BASE}/stats/{ep}", headers=H(st), timeout=5)
        check(f"STAT-{i:02d}", f"GET /stats/{ep.split('?')[0]} 200", r.status_code == 200, f"{r.status_code} {r.text[:120]}")
    r = requests.get(f"{BASE}/stats/hourly", headers=H(st), timeout=5)
    check("STAT-11", "필수 파라미터(date) 누락 시 400 응답", r.status_code == 400, f"실제 {r.status_code} (서버 오류로 처리됨)")
    r = requests.get(f"{BASE}/users/student/sessions", headers=H(st), timeout=5)
    check("STAT-10", "GET /users/student/sessions 200", r.status_code == 200, r.status_code)

    # ── 4. 일정 ──
    sched = {"date": now.date().isoformat(), "start_time": "19:00", "end_time": "20:00",
             "title": "QA 수학 복습", "memo": "e2e", "color": "#3D7EF8"}
    r = requests.post(f"{BASE}/schedules", json=sched, headers=H(st), timeout=5)
    check("SCH-01", "일정 생성", r.status_code in (200, 201) and r.json().get("id"), r.text[:200])
    sch_id = r.json().get("id") if r.ok else None
    r = requests.post(f"{BASE}/schedules", json={**sched, "date": "2026/10/02"}, headers=H(st), timeout=5)
    check("SCH-02", "잘못된 날짜 형식 거부 400/422", r.status_code in (400, 422), r.status_code)
    r = requests.get(f"{BASE}/schedules", headers=H(st), timeout=5)
    check("SCH-03", "일정 목록에 생성 항목 포함", r.ok and any(x.get("id") == sch_id for x in r.json()), r.status_code)
    r = requests.patch(f"{BASE}/schedules/{sch_id}", json={"is_done": 1}, headers=H(st), timeout=5)
    check("SCH-04", "일정 완료 처리(PATCH is_done=1)", r.ok and r.json().get("is_done") == 1, r.text[:200])
    r = requests.get(f"{BASE}/schedules/student/{S['id']}", headers=H(tt), timeout=5)
    check("SCH-05", "교사: 담당 학생 일정 조회", r.ok and any(x.get("id") == sch_id for x in r.json()), r.status_code)
    r = requests.delete(f"{BASE}/schedules/{sch_id}", headers=H(tt), timeout=5)
    check("SCH-06", "교사가 학생 일정 삭제 시도 거부(403/404)", r.status_code in (403, 404), r.status_code)
    r = requests.delete(f"{BASE}/schedules/{sch_id}", headers=H(st), timeout=5)
    check("SCH-07", "본인 일정 삭제", r.status_code in (200, 204), r.status_code)

    # ── 5. 화이트리스트 ──
    r = requests.get(f"{BASE}/api/whitelist", timeout=5)
    base_wl = r.json() if r.ok else []
    check("WL-01", "기본 화이트리스트 조회(데스크톱용)", r.ok and len(base_wl) > 0, len(base_wl))
    r = requests.post(f"{BASE}/whitelist/student/{S['id']}",
                      json={"name": "QA 강의", "url": "https://qa-e2e.example.com"}, headers=H(tt), timeout=5)
    check("WL-02", "교사: 학생 전용 허용 사이트 추가", r.status_code in (200, 201), r.text[:200])
    wl_id = r.json().get("id") if r.ok else None
    r = requests.get(f"{BASE}/whitelist/effective", headers=H(st), timeout=5)
    eff = r.json() if r.ok else []
    eff_list = eff if isinstance(eff, list) else eff.get("items", [])
    check("WL-03", "학생 유효 화이트리스트 = 기본 + 전용",
          r.ok and any(x.get("id") == wl_id for x in eff_list) and len(eff_list) >= len(base_wl) + 1, len(eff_list))
    r = requests.post(f"{BASE}/whitelist/student/{S['id']}",
                      json={"name": "자가추가", "url": "https://self.example.com"}, headers=H(st), timeout=5)
    check("WL-04", "학생 본인이 허용 사이트 추가 시도 거부(403)", r.status_code == 403, r.status_code)
    r = requests.delete(f"{BASE}/whitelist/{wl_id}", headers=H(st), timeout=5)
    check("WL-05", "학생이 교사 지정 사이트 삭제 시도 거부(403)", r.status_code == 403, r.status_code)
    r = requests.delete(f"{BASE}/whitelist/{wl_id}", headers=H(tt), timeout=5)
    check("WL-06", "교사: 학생 전용 사이트 삭제", r.status_code in (200, 204), r.status_code)

    # ── 6. 시선 설정 / 캘리브레이션 ──
    r = requests.get(f"{BASE}/gaze-settings/me", headers=H(st), timeout=5)
    check("GZ-01", "시선 설정 조회", r.status_code == 200, r.status_code)
    r = requests.put(f"{BASE}/gaze-settings/me", json={"ear_threshold": 0.21, "yaw_threshold": 25.0}, headers=H(st), timeout=5)
    check("GZ-02", "시선 설정 수정", r.ok and abs(r.json().get("ear_threshold", 0) - 0.21) < 1e-6, r.text[:200])
    r = requests.put(f"{BASE}/gaze-settings/me", json={"ear_threshold": 0.9}, headers=H(st), timeout=5)
    check("GZ-03", "범위 밖 값(ear 0.9) 거부 400/422", r.status_code in (400, 422), r.status_code)
    r = requests.get(f"{BASE}/gaze-settings/student/{S['id']}", headers=H(tt), timeout=5)
    check("GZ-04", "교사: 담당 학생 시선 설정 조회", r.status_code == 200, r.status_code)
    r = requests.put(f"{BASE}/calibration/me", json={"center_ratio": 0.52, "h_left_threshold": 0.25,
                                                     "h_right_threshold": 0.78, "gaze_lost_threshold": 2.5},
                     headers=H(st), timeout=5)
    check("CAL-01", "캘리브레이션 저장", r.ok and r.json().get("calibrated") == 1, r.text[:200])
    r = requests.get(f"{BASE}/calibration/me", headers=H(st), timeout=5)
    check("CAL-02", "캘리브레이션 조회 값 반영", r.ok and abs(r.json().get("center_ratio", 0) - 0.52) < 1e-6, r.text[:200])
    r = requests.get(f"{BASE}/api/calibration", timeout=5)
    check("CAL-03", "데스크톱용 /api/calibration 최근 보정값", r.ok and abs(r.json().get("center_ratio", 0) - 0.52) < 1e-6, r.text[:200])
    r = requests.post(f"{BASE}/calibration/me/reset", headers=H(st), timeout=5)
    check("CAL-04", "캘리브레이션 초기화", r.ok and r.json().get("calibrated") == 0, r.text[:200])

    # ── 7. 교사 기능 ──
    r = requests.get(f"{BASE}/users/teacher/students", headers=H(tt), timeout=5)
    lst = r.json() if r.ok else []
    lst = lst if isinstance(lst, list) else lst.get("items", lst.get("students", []))
    check("TCH-01", "교사: 담당 학생 목록에 학생 포함", r.ok and any(x.get("login_id") == S["login_id"] for x in lst), r.text[:200])
    r = requests.get(f"{BASE}/users/teacher/students", headers=H(st), timeout=5)
    check("TCH-02", "학생이 교사 API 접근 거부(403)", r.status_code == 403, r.status_code)
    r = requests.get(f"{BASE}/gaze-settings/student/1", headers=H(tt), timeout=5)
    check("TCH-03", "교사가 남의 학생(id=1) 설정 조회 거부(403)", r.status_code == 403, r.status_code)

    # ── 8. 관리자 ──
    r = requests.get(f"{BASE}/admins/users", headers=H(st), timeout=5)
    check("ADM-01", "학생이 관리자 API 접근 거부(403)", r.status_code == 403, r.status_code)
    r = requests.post(f"{BASE}/admins/signup", json={**A, "level": 9}, timeout=5)
    check("SEC-01", "[보안] 인증 없이 관리자 가입 차단(401)", r.status_code == 401,
          f"실제 {r.status_code} — 누구나 관리자 계정 생성 가능" if r.status_code in (200, 201) else r.status_code)
    r = requests.post(f"{BASE}/admins/signup", json={**A, "level": 1}, headers=H(st), timeout=5)
    check("SEC-06", "[보안] 학생 토큰으로 관리자 가입 차단(403)", r.status_code == 403, r.status_code)
    # 테스트용 관리자(등급 2)는 DB 에 직접 만든다 — 가입 API 는 기존 관리자만 쓸 수 있으므로
    import bcrypt
    db_exec("insert into admins (admin_id, password_hash, name, level) values (%s, %s, %s, 2)",
            (A["admin_id"], bcrypt.hashpw(A["password"].encode(), bcrypt.gensalt()).decode(), A["name"]))
    r = requests.post(f"{BASE}/admins/login", json={"admin_id": A["admin_id"], "password": A["password"]}, timeout=5)
    at = r.json().get("access_token") if r.ok else None
    if at:
        r = requests.get(f"{BASE}/admins/me", headers=H(at), timeout=5)
        check("ADM-02", "관리자 /admins/me", r.ok, r.status_code)
        sub = {"admin_id": A["admin_id"] + "x", "password": _pw(), "name": "QA하위관리자"}
        r = requests.post(f"{BASE}/admins/signup", json={**sub, "level": 9}, headers=H(at), timeout=5)
        check("SEC-07", "[보안] 자신(2)보다 높은 등급(9) 관리자 생성 거부(403)", r.status_code == 403, r.status_code)
        r = requests.post(f"{BASE}/admins/signup", json={**sub, "level": 1}, headers=H(at), timeout=5)
        check("ADM-11", "관리자가 하위 등급 관리자 생성(201)", r.status_code == 201 and r.json().get("level") == 1, r.status_code)
        r = requests.get(f"{BASE}/admins/users", headers=H(at), timeout=5)
        users = r.json() if r.ok else []
        users = users if isinstance(users, list) else users.get("items", [])
        check("ADM-03", "관리자: 전체 사용자 목록", r.ok and any(u.get("login_id") == S["login_id"] for u in users), r.status_code)
        r = requests.post(f"{BASE}/admins/users/{S['id']}/reject", headers=H(at), timeout=5)
        check("ADM-04", "관리자: 학생 비활성화(reject)", r.ok, r.status_code)
        r = requests.post(f"{BASE}/users/login", json={"login_id": S["login_id"], "password": S["password"]}, timeout=5)
        check("ADM-05", "비활성 계정 로그인 403(승인 대기)", r.status_code == 403, r.status_code)
        r = requests.get(f"{BASE}/users/me", headers=H(st), timeout=5)
        check("ADM-06", "비활성화 후 기존 토큰 차단(401)", r.status_code == 401, r.status_code)
        r = requests.post(f"{BASE}/admins/users/{S['id']}/approve", headers=H(at), timeout=5)
        check("ADM-07", "관리자: 학생 승인(approve)", r.ok, r.status_code)
        r = requests.post(f"{BASE}/users/login", json={"login_id": S["login_id"], "password": S["password"]}, timeout=5)
        check("ADM-08", "승인 후 로그인 복구 200", r.status_code == 200, r.status_code)
        st = r.json().get("access_token", st) if r.ok else st
        r = requests.get(f"{BASE}/admins/stats", headers=H(at), timeout=5)
        check("ADM-09", "관리자 통계", r.status_code == 200, r.status_code)
        r = requests.get(f"{BASE}/whitelist/admin/all", headers=H(at), timeout=5)
        check("ADM-10", "관리자: 전체 화이트리스트", r.status_code == 200, r.status_code)

    # ── 9. 레거시/공개 API ──
    leg = {"name": "QA-legacy", "url": "https://qa-legacy.example.com"}
    r = requests.post(f"{BASE}/api/whitelist", json=leg, timeout=5)
    check("SEC-02", "[보안] 인증 없이 기본 화이트리스트 추가 차단(401)", r.status_code == 401,
          f"실제 {r.status_code} — 비로그인 추가 가능" if r.ok else r.status_code)
    r = requests.post(f"{BASE}/api/whitelist", json=leg, headers=H(st), timeout=5)
    check("SEC-04", "[보안] 학생 토큰으로 기본 화이트리스트 추가 차단(403)", r.status_code == 403, r.status_code)
    victim = base_wl[0]["id"] if base_wl else 0
    r = requests.delete(f"{BASE}/api/whitelist/{victim}", timeout=5)
    check("SEC-03", "[보안] 인증 없이 기본 화이트리스트 삭제 차단(401)", r.status_code == 401,
          f"실제 {r.status_code} — 비로그인 삭제 가능" if r.ok else r.status_code)
    r = requests.delete(f"{BASE}/api/whitelist/{victim}", headers=H(st), timeout=5)
    check("SEC-05", "[보안] 학생 토큰으로 기본 화이트리스트 삭제 차단(403)", r.status_code == 403, r.status_code)
    if at:
        r = requests.post(f"{BASE}/api/whitelist", json=leg, headers=H(at), timeout=5)
        leg_id = r.json().get("id") if r.status_code == 201 else None
        check("WL-07", "관리자 토큰으로 기본 화이트리스트 추가(201)", leg_id is not None, r.status_code)
        r = requests.post(f"{BASE}/api/whitelist", json={**leg, "url": leg["url"] + "/"}, headers=H(at), timeout=5)
        check("WL-08", "끝 '/' 만 다른 URL 중복 추가 거부(400)", r.status_code == 400, r.status_code)
        r = requests.post(f"{BASE}/whitelist/admin/default", json={"name": "dup", "url": leg["url"] + "/"}, headers=H(at), timeout=5)
        check("WL-09", "관리자 기본 사이트 API도 끝 '/' 중복 거부(400)", r.status_code == 400, r.status_code)
        if leg_id:
            r = requests.delete(f"{BASE}/api/whitelist/{leg_id}", headers=H(at), timeout=5)
            check("WL-10", "관리자 토큰으로 기본 화이트리스트 삭제", r.status_code == 200, r.status_code)
    r = requests.post(f"{BASE}/whitelist/student/{S['id']}", json={"name": "QA", "url": "https://qa-dup.example.com"}, headers=H(tt), timeout=5)
    dup_id = r.json().get("id") if r.ok else None
    r = requests.post(f"{BASE}/whitelist/student/{S['id']}", json={"name": "QA", "url": "https://qa-dup.example.com/"}, headers=H(tt), timeout=5)
    check("WL-11", "학생 전용 사이트도 끝 '/' 중복 거부(400)", r.status_code == 400, r.status_code)
    if dup_id:
        requests.delete(f"{BASE}/whitelist/{dup_id}", headers=H(tt), timeout=5)
    names = [w["url"].rstrip("/") for w in requests.get(f"{BASE}/api/whitelist", timeout=5).json()]
    check("DB-04", "기본 화이트리스트에 끝 '/' 중복 없음", len(names) == len(set(names)), names)
    r = requests.post(f"{BASE}/headpose", json={"student_id": S["login_id"], "x": 0.1, "y": 0.2}, timeout=5)
    check("API-01", "POST /headpose 저장", r.status_code == 200, f"{r.status_code} {r.text[:150]}")
    row = db_one("select count(*) from head_pose_data where student_id=%s", (S["login_id"],))
    check("DB-05", "DB: head_pose_data 행 저장", row and row[0] == 1, row)

    # ── 10. AI WebSocket ──
    try:
        s, status = ws_connect(AI, "/ws/gaze")
        try:
            kind, val = ws_recv(s)
        except Exception as e:
            kind, val = "err", e
        check("AI-01", "토큰 없는 WS 연결 거부(1008)", (kind == "close" and val == 1008) or "403" in status, f"{status} {kind} {val}")
        s.close()
        s, status = ws_connect(AI, f"/ws/gaze?token={st}")
        ok = check("AI-02", "Spring 발급 토큰으로 WS 연결(JWT 공유 확인)", "101" in status, status + (" — venv에 websockets/wsproto 미설치로 WS 업그레이드 불가" if "404" in status else ""))
        if ok:
            ws_send(s, json.dumps({"type": "ping"}))
            kind, val = ws_recv(s)
            check("AI-03", "ping → pong", kind == "text" and json.loads(val).get("type") == "pong", val)
            import cv2, numpy as np
            blank = np.full((240, 320, 3), 200, np.uint8)
            jpg = base64.b64encode(cv2.imencode(".jpg", blank)[1].tobytes()).decode()
            ws_send(s, json.dumps({"type": "frame", "image": "data:image/jpeg;base64," + jpg, "screen": [1920, 1080]}))
            kind, val = ws_recv(s)
            check("AI-04", "얼굴 없는 프레임 → face_detected=false", kind == "text" and json.loads(val).get("face_detected") is False, val[:150])
            import glob
            # 얼굴 표본은 model_test/data (git 미포함) — 없으면 건너뜀
            face_imgs = sorted(glob.glob(os.path.join(HERE, "..", "..", "model_test", "data", "front", "*.jpg")))
            if not face_imgs:
                print("[SKIP] AI-05  얼굴 표본 이미지 없음 (model_test/data/front)")
        if ok and face_imgs:
            face = cv2.imdecode(np.fromfile(face_imgs[0], np.uint8), cv2.IMREAD_COLOR)
            jpg = base64.b64encode(cv2.imencode(".jpg", face)[1].tobytes()).decode()
            ws_send(s, json.dumps({"type": "frame", "image": "data:image/jpeg;base64," + jpg, "screen": [1920, 1080]}))
            kind, val = ws_recv(s)
            res = json.loads(val) if kind == "text" else {}
            check("AI-05", "얼굴 프레임 → 시선·고개 각도·EAR·집중 상태 응답",
                  res.get("face_detected") is True and len(res.get("gaze", [])) == 2
                  and {"yaw", "pitch"} <= set(res.get("head", {})) and res.get("ear", 0) > 0
                  and res.get("focus_state") in ("Focused", "Dazed", "Distracted") and 0 <= res.get("focus_score", -1) <= 100,
                  val[:200])
        s.close()
    except Exception as e:
        check("AI-03", "WS 세션 처리(ping/frame)", False, e)

    with open(os.path.join(HERE, "e2e_accounts.json"), "w", encoding="utf-8") as f:
        json.dump(acc, f, ensure_ascii=False, indent=2)
    os.makedirs(os.path.join(HERE, "results"), exist_ok=True)
    with open(os.path.join(HERE, "results", "api_results.json"), "w", encoding="utf-8") as f:
        json.dump(RESULTS, f, ensure_ascii=False, indent=2)

    passed = sum(r["pass"] for r in RESULTS)
    print(f"\n총 {len(RESULTS)}건 — PASS {passed} / FAIL {len(RESULTS) - passed}")


if __name__ == "__main__":
    sys.stdout.reconfigure(encoding="utf-8")
    main()
