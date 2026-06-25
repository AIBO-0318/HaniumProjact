# -*- coding: utf-8 -*-
"""I-Study 데이터베이스 설계 문서 PDF — 라이브 DB(istudy)에서 스키마를 읽어 생성."""
import os
import psycopg2
from reportlab.lib.pagesizes import A4
from reportlab.lib.units import mm
from reportlab.lib import colors
from reportlab.lib.styles import ParagraphStyle
from reportlab.lib.enums import TA_LEFT, TA_CENTER
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont
from reportlab.platypus import (SimpleDocTemplate, Paragraph, Spacer, Table,
                                TableStyle, PageBreak, KeepTogether)

pdfmetrics.registerFont(TTFont("Malgun", r"C:\Windows\Fonts\malgun.ttf"))
pdfmetrics.registerFont(TTFont("MalgunBd", r"C:\Windows\Fonts\malgunbd.ttf"))

NAVY = colors.HexColor("#1F3A5F")
BLUE = colors.HexColor("#2E6FB7")
LBLUE = colors.HexColor("#EAF2FB")
ROW = colors.HexColor("#F6F9FD")
GRAY = colors.HexColor("#555555")
LGRAY = colors.HexColor("#8A8A8A")
GREEN = colors.HexColor("#2E8B57")
AMBER = colors.HexColor("#C78212")
LINEC = colors.HexColor("#D8E2EE")

OUT = os.path.join(os.path.dirname(__file__), "I-Study_DB_설계문서.pdf")

# ── 한글명 / 상태 / 역할 ──
KOR = {
    "users": "사용자 (학생·지도자)", "admins": "관리자",
    "study_sessions": "학습 세션 기록", "schedules": "학습 일정",
    "whitelist_urls": "허용 URL (화이트리스트)", "gaze_settings": "시선 감지 설정·보정",
    "head_pose_data": "머리/시선 좌표 로그",
}
STATUS = {
    "users": ("사용 중", GREEN), "admins": ("사용 중", GREEN),
    "study_sessions": ("사용 중", GREEN), "schedules": ("사용 중", GREEN),
    "whitelist_urls": ("사용 중", GREEN),
    "gaze_settings": ("부분 사용 · 일부 레거시", AMBER),
    "head_pose_data": ("미사용 레거시 (0행)", AMBER),
}
ROLE = {
    "users": "시스템의 중심 테이블. 학생·학습지도자 계정과 로그인·권한·매칭 정보를 보관하며, "
             "대부분의 다른 테이블이 이 테이블을 참조(FK)한다. teacher_id 자기참조로 학생–지도자 매칭을 표현한다.",
    "admins": "시스템 관리자 계정. 사용자 승인·전체 통계 조회를 담당하며 users 와 분리된 별도 인증 테이블이다.",
    "study_sessions": "시선추적으로 측정한 1회 학습 세션의 집중도 결과(집중/멍/이탈 시간, 집중 점수)를 저장한다. "
                      "웹 통계·대시보드의 데이터 소스이며, 웹·앱 공용(user_id 또는 login_id 로 식별)이다.",
    "schedules": "학생의 과목별 학습 일정(계획)을 저장한다. 웹 일정표 화면에서 등록·완료 체크에 사용된다.",
    "whitelist_urls": "학습 중 접속이 허용되는 사이트 목록. user_id 가 NULL 이면 전체 공용, 값이 있으면 해당 학생 전용이며, "
                      "데스크톱 앱의 사이트 모니터링이 이 목록을 참조한다.",
    "gaze_settings": "학생별 시선·졸음·멍 감지 파라미터와 시야각 보정값을 보관한다. 웹(/calibration, /gaze-settings)에서 편집된다. "
                     "단, 현재 실행 엔진은 이 DB 값을 거의 불러오지 않으며(기록용), '감지' 그룹 8개 컬럼은 사용되지 않는 레거시다.",
    "head_pose_data": "학습 중 머리/시선 좌표(x,y)를 남기기 위한 로그 테이블. /headpose 엔드포인트만 존재하고 호출하는 "
                      "클라이언트가 없어 현재 0행·미사용이며, x·y 의 단위/의미도 확정돼 있지 않다.",
}
ROLE_SHORT = {
    "users": "계정·권한·매칭의 중심", "admins": "시스템 관리자 계정",
    "study_sessions": "시선분석 집중도 결과(통계 소스)", "schedules": "학습 일정",
    "whitelist_urls": "학습 중 허용 사이트", "gaze_settings": "사용자별 시선 감지 설정·보정",
    "head_pose_data": "머리/시선 좌표 로그(미사용)",
}

COL = {
    ("users", "id"): "기본 키 (자동 증가)",
    ("users", "login_id"): "로그인 아이디(고유). 앱·통계의 사용자 식별 키",
    ("users", "password_hash"): "bcrypt 로 해싱된 비밀번호",
    ("users", "name"): "화면에 표시되는 이름",
    ("users", "role"): "역할 enum — STUDENT(학생) / TEACHER(학습지도자)",
    ("users", "is_active"): "관리자 승인 상태 (1=활성, 0=대기/비활성)",
    ("users", "teacher_id"): "소속 지도자 id(학생만). 같은 테이블 참조 → 학생–지도자 매칭의 핵심",
    ("users", "created_at"): "가입 시각",
    ("admins", "id"): "기본 키",
    ("admins", "admin_id"): "관리자 로그인 아이디(고유)",
    ("admins", "password_hash"): "bcrypt 비밀번호 해시",
    ("admins", "name"): "관리자 이름",
    ("admins", "level"): "권한 등급(숫자가 클수록 상위 권한)",
    ("admins", "created_at"): "생성 시각",
    ("study_sessions", "id"): "기본 키",
    ("study_sessions", "user_id"): "사용자 id(FK). 앱 기록은 비어 있을 수 있어 login_id 로 대체 식별 → nullable",
    ("study_sessions", "date"): "학습 날짜 (YYYY-MM-DD)",
    ("study_sessions", "duration_min"): "세션 길이(분)",
    ("study_sessions", "focus_score"): "집중도 점수 (시선분석 결과)",
    ("study_sessions", "focused_min"): "집중 상태 시간(분)",
    ("study_sessions", "dazed_min"): "멍때림 상태 시간(분)",
    ("study_sessions", "distracted_min"): "이탈(딴짓) 시간(분)",
    ("study_sessions", "created_at"): "기록 시각",
    ("study_sessions", "login_id"): "앱 세션 식별용 로그인 아이디(user_id 없을 때 사용)",
    ("study_sessions", "start_time"): "세션 시작 시각",
    ("study_sessions", "end_time"): "세션 종료 시각",
    ("study_sessions", "total_time_seconds"): "총 학습 시간(초)",
    ("study_sessions", "focus_time_seconds"): "집중 시간(초)",
    ("schedules", "id"): "기본 키",
    ("schedules", "user_id"): "학생 id(FK)",
    ("schedules", "date"): "일정 날짜 (YYYY-MM-DD)",
    ("schedules", "start_time"): "시작 시각 (HH:MM)",
    ("schedules", "end_time"): "종료 시각 (HH:MM)",
    ("schedules", "title"): "일정 제목(과목 등)",
    ("schedules", "memo"): "메모",
    ("schedules", "color"): "표시 색상",
    ("schedules", "created_at"): "생성 시각",
    ("schedules", "is_done"): "완료 체크 (0=미완, 1=완료)",
    ("whitelist_urls", "id"): "기본 키",
    ("whitelist_urls", "name"): "사이트 이름",
    ("whitelist_urls", "url"): "허용 URL",
    ("whitelist_urls", "created_at"): "생성 시각",
    ("whitelist_urls", "user_id"): "대상 학생 id(FK). NULL 이면 전체 공용 허용 사이트",
    ("gaze_settings", "id"): "기본 키",
    ("gaze_settings", "user_id"): "학생 id(FK, 1인 1행/고유)",
    ("gaze_settings", "ear_threshold"): "[감지] 눈 종횡비(EAR) 임계값 — 이보다 작으면 눈 감음. ※현재 엔진 미사용",
    ("gaze_settings", "eye_closure_threshold"): "[감지] 눈 감음 지속 시 졸음 경고까지 시간(초). ※현재 엔진 미사용",
    ("gaze_settings", "yaw_threshold"): "[감지] 고개 좌우 회전 허용 각도(°). ※현재 엔진 미사용",
    ("gaze_settings", "pitch_threshold"): "[감지] 고개 상하 각도(°). ※현재 엔진 미사용",
    ("gaze_settings", "pose_lost_threshold"): "[감지] 얼굴 자세 인식 실패 지속 시간(초). ※현재 엔진 미사용",
    ("gaze_settings", "daze_variance_thr"): "[감지] 멍때림 판정용 움직임 분산 임계값. ※현재 엔진 미사용",
    ("gaze_settings", "daze_duration_sec"): "[감지] 멍 상태 지속 판정 시간(초). ※현재 엔진 미사용",
    ("gaze_settings", "alpha_iris"): "[감지] 홍채 추적 평활(EMA) 계수(0~1). ※현재 엔진 미사용",
    ("gaze_settings", "updated_at"): "수정 시각",
    ("gaze_settings", "center_ratio"): "[보정] 정면 응시 시 코의 수평 기준점(0.5=중앙)",
    ("gaze_settings", "h_left_threshold"): "[보정] 좌측 이탈 판정 비율(이보다 작으면 좌)",
    ("gaze_settings", "h_right_threshold"): "[보정] 우측 이탈 판정 비율(이보다 크면 우)",
    ("gaze_settings", "v_up_threshold"): "[보정] 상단 이탈 판정 비율",
    ("gaze_settings", "v_down_threshold"): "[보정] 하단 이탈 판정 비율",
    ("gaze_settings", "gaze_lost_threshold"): "[보정] 시선 이탈이 몇 초 지속되면 이탈 판정(초)",
    ("gaze_settings", "calibrated"): "[보정] 보정 완료 여부 (1=보정됨, 0=기본값)",
    ("head_pose_data", "id"): "기본 키",
    ("head_pose_data", "student_id"): "학생 로그인 아이디 (users.login_id 문자열 참조, FK 아님)",
    ("head_pose_data", "x"): "머리/시선 수평 좌표 ※단위·의미 미확정·미사용",
    ("head_pose_data", "y"): "머리/시선 수직 좌표 ※단위·의미 미확정·미사용",
    ("head_pose_data", "timestamp"): "기록 시각",
}

ORDER = ["users", "admins", "study_sessions", "schedules",
         "whitelist_urls", "gaze_settings", "head_pose_data"]


def short_type(dt, clen):
    m = {"character varying": "varchar", "integer": "int", "double precision": "float8",
         "timestamp without time zone": "timestamp", "text": "text", "USER-DEFINED": "user_role (enum)"}
    base = m.get(dt, dt)
    if clen and dt == "character varying":
        base = f"varchar({clen})"
    return base


# ── 라이브 DB 조회 ──
conn = psycopg2.connect(host="localhost", port=5432, dbname="istudy",
                        user="postgres", password="aisw2026")
cur = conn.cursor()
cur.execute("""select table_name, column_name, data_type, character_maximum_length,
               is_nullable, column_default, ordinal_position
               from information_schema.columns where table_schema='public'
               order by table_name, ordinal_position""")
cols = {}
for t, c, dt, clen, nul, dflt, pos in cur.fetchall():
    cols.setdefault(t, []).append((c, short_type(dt, clen), nul, dflt))

cur.execute("""select tc.table_name, tc.constraint_type, kcu.column_name,
               ccu.table_name, ccu.column_name
               from information_schema.table_constraints tc
               join information_schema.key_column_usage kcu on tc.constraint_name=kcu.constraint_name
               left join information_schema.constraint_column_usage ccu
                 on tc.constraint_name=ccu.constraint_name and tc.constraint_type='FOREIGN KEY'
               where tc.table_schema='public'
                 and tc.constraint_type in ('PRIMARY KEY','FOREIGN KEY')""")
pk, fk = {}, {}
for t, ctype, col, rt, rc in cur.fetchall():
    if ctype == "PRIMARY KEY":
        pk.setdefault(t, set()).add(col)
    else:
        fk[(t, col)] = f"{rt}.{rc}"

cur.execute("""select t.relname, a.attname from pg_index i
               join pg_class t on t.oid=i.indrelid
               join pg_class ix on ix.oid=i.indexrelid
               join pg_attribute a on a.attrelid=t.oid and a.attnum = any(i.indkey)
               where i.indisunique and not i.indisprimary
                 and t.relnamespace=(select oid from pg_namespace where nspname='public')""")
uniq = set((t, c) for t, c in cur.fetchall())

counts = {}
for t in ORDER:
    cur.execute(f"select count(*) from {t}")
    counts[t] = cur.fetchone()[0]
cur.close(); conn.close()

# ── 스타일 ──
st_title = ParagraphStyle("t", fontName="MalgunBd", fontSize=26, textColor=NAVY, leading=32)
st_sub = ParagraphStyle("s", fontName="Malgun", fontSize=13, textColor=GRAY, leading=18)
st_meta = ParagraphStyle("m", fontName="Malgun", fontSize=10, textColor=LGRAY, leading=15)
st_h2 = ParagraphStyle("h2", fontName="MalgunBd", fontSize=15, textColor=NAVY, leading=19, spaceBefore=4)
st_role = ParagraphStyle("r", fontName="Malgun", fontSize=9.5, textColor=GRAY, leading=14)
st_cell = ParagraphStyle("c", fontName="Malgun", fontSize=8.2, textColor=GRAY, leading=11)
st_cellb = ParagraphStyle("cb", fontName="MalgunBd", fontSize=8.4, textColor=NAVY, leading=11)
st_mono = ParagraphStyle("mono", fontName="Malgun", fontSize=7.8, textColor=GRAY, leading=10)
st_hd = ParagraphStyle("hd", fontName="MalgunBd", fontSize=8.6, textColor=colors.white, leading=11)
st_note = ParagraphStyle("n", fontName="Malgun", fontSize=8.5, textColor=GRAY, leading=12)

story = []

# ── 표지 ──
story.append(Spacer(1, 60*mm))
story.append(Paragraph("I-Study 데이터베이스 설계 문서", st_title))
story.append(Spacer(1, 6*mm))
story.append(Paragraph("PostgreSQL <font color='#2E6FB7'>istudy</font> · 전체 테이블 구조와 각 컬럼의 역할", st_sub))
story.append(Spacer(1, 4*mm))
story.append(Paragraph("AI 시선추적 학습 집중도 관리 시스템", st_sub))
story.append(Spacer(1, 10*mm))
story.append(Paragraph(f"테이블 7개 · 컬럼 66개 · 생성일 2026-06-22 (라이브 DB 기준)", st_meta))
story.append(PageBreak())

# ── 개요 (요약 표 + 관계) ──
story.append(Paragraph("개요 — 테이블 목록", st_h2))
story.append(Spacer(1, 3*mm))
ov = [[Paragraph(x, st_hd) for x in ["테이블", "한글명", "행 수", "상태", "역할"]]]
for t in ORDER:
    stat, scol = STATUS[t]
    stat_p = Paragraph(stat, ParagraphStyle("stt", fontName="Malgun", fontSize=8.2, textColor=scol, leading=11))
    ov.append([Paragraph(f"<b>{t}</b>", st_cellb), Paragraph(KOR[t], st_cell),
               Paragraph(str(counts[t]), st_cell), stat_p, Paragraph(ROLE_SHORT[t], st_cell)])
ovt = Table(ov, colWidths=[88, 110, 36, 110, 166], repeatRows=1)
ovt.setStyle(TableStyle([
    ("BACKGROUND", (0, 0), (-1, 0), NAVY),
    ("ROWBACKGROUNDS", (0, 1), (-1, -1), [colors.white, ROW]),
    ("LINEBELOW", (0, 0), (-1, -1), 0.4, LINEC),
    ("BOX", (0, 0), (-1, -1), 0.5, LINEC),
    ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
    ("LEFTPADDING", (0, 0), (-1, -1), 5), ("RIGHTPADDING", (0, 0), (-1, -1), 5),
    ("TOPPADDING", (0, 0), (-1, -1), 4), ("BOTTOMPADDING", (0, 0), (-1, -1), 4),
]))
story.append(ovt)
story.append(Spacer(1, 7*mm))

story.append(Paragraph("테이블 관계 (Foreign Key)", st_h2))
story.append(Spacer(1, 3*mm))
rels = [
    ("users → study_sessions", "1 : N", "user_id — 한 사용자의 여러 학습 세션"),
    ("users → schedules", "1 : N", "user_id — 한 학생의 여러 일정"),
    ("users → whitelist_urls", "1 : N", "user_id (NULL=전체 공용)"),
    ("users → gaze_settings", "1 : 1", "user_id (사용자당 1행, 고유)"),
    ("users → users", "1 : N", "teacher_id 자기참조 — 지도자 1명 : 학생 N명 (매칭)"),
    ("admins", "독립", "users 와 무관한 별도 인증 테이블"),
    ("head_pose_data", "독립", "FK 없음. student_id 로 login_id 를 느슨히 참조"),
]
rt = [[Paragraph(x, st_hd) for x in ["관계", "유형", "설명"]]]
for a, b, c in rels:
    rt.append([Paragraph(a, st_cellb), Paragraph(b, st_cell), Paragraph(c, st_cell)])
rtt = Table(rt, colWidths=[150, 60, 300], repeatRows=1)
rtt.setStyle(TableStyle([
    ("BACKGROUND", (0, 0), (-1, 0), BLUE),
    ("ROWBACKGROUNDS", (0, 1), (-1, -1), [colors.white, ROW]),
    ("BOX", (0, 0), (-1, -1), 0.5, LINEC),
    ("LINEBELOW", (0, 0), (-1, -1), 0.4, LINEC),
    ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
    ("LEFTPADDING", (0, 0), (-1, -1), 5), ("RIGHTPADDING", (0, 0), (-1, -1), 5),
    ("TOPPADDING", (0, 0), (-1, -1), 4), ("BOTTOMPADDING", (0, 0), (-1, -1), 4),
]))
story.append(rtt)
story.append(PageBreak())

# ── 테이블별 상세 ──
def key_badge(t, c):
    parts = []
    if c in pk.get(t, set()):
        parts.append("<font color='#1F3A5F' size=7><b>PK</b></font>")
    if (t, c) in fk:
        parts.append(f"<font color='#2E6FB7' size=7>FK→{fk[(t,c)]}</font>")
    if (t, c) in uniq:
        parts.append("<font color='#8A8A8A' size=7>UNIQUE</font>")
    return ("<br/>" + " ".join(parts)) if parts else ""


for t in ORDER:
    stat, scol = STATUS[t]
    head = (f"{t} &nbsp;<font size=11 color='#555555'>· {KOR[t]}</font>"
            f"&nbsp;&nbsp;<font size=9 color='{scol.hexval().replace('0x','#')}'>[{stat}]</font>")
    pkc = ", ".join(sorted(pk.get(t, []))) or "—"
    fkc = "; ".join(f"{c}→{fk[(t,c)]}" for (tt, c) in fk if tt == t) or "없음"

    data = [[Paragraph(x, st_hd) for x in ["컬럼", "타입 · 제약", "기본값", "설명"]]]
    for (c, typ, nul, dflt) in cols[t]:
        name = f"<b>{c}</b>" + key_badge(t, c)
        tcon = typ + ("" if nul == "YES" else "<br/><font size=7 color='#8A8A8A'>NOT NULL</font>")
        dv = "—"
        if dflt:
            d = dflt.split("::")[0].replace("nextval('", "seq").strip()
            dv = "자동증가" if "seq" in d else d
        desc = COL.get((t, c), "")
        data.append([Paragraph(name, st_cell), Paragraph(tcon, st_mono),
                     Paragraph(dv, st_mono), Paragraph(desc, st_cell)])
    # 요약(PK/FK/행수)을 표의 마지막 병합 행으로 → 표와 항상 붙어 다님(고아 방지)
    note = f"<b>PK</b>: {pkc} &nbsp;&nbsp;|&nbsp;&nbsp; <b>FK</b>: {fkc} &nbsp;&nbsp;|&nbsp;&nbsp; <b>행 수</b>: {counts[t]}"
    data.append([Paragraph(note, st_note), "", "", ""])
    nrow = len(data) - 1
    tb = Table(data, colWidths=[120, 110, 65, 215], repeatRows=1)
    tb.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (-1, 0), NAVY),
        ("ROWBACKGROUNDS", (0, 1), (-1, nrow - 1), [colors.white, ROW]),
        ("BOX", (0, 0), (-1, -1), 0.5, LINEC),
        ("INNERGRID", (0, 0), (-1, -1), 0.3, LINEC),
        ("VALIGN", (0, 0), (-1, -1), "TOP"),
        ("LEFTPADDING", (0, 0), (-1, -1), 5), ("RIGHTPADDING", (0, 0), (-1, -1), 5),
        ("TOPPADDING", (0, 0), (-1, -1), 3.5), ("BOTTOMPADDING", (0, 0), (-1, -1), 3.5),
        ("SPAN", (0, nrow), (3, nrow)),
        ("BACKGROUND", (0, nrow), (3, nrow), LBLUE),
        ("TOPPADDING", (0, nrow), (3, nrow), 5), ("BOTTOMPADDING", (0, nrow), (3, nrow), 5),
    ]))
    # 표를 통째로 한 페이지에 유지(모든 표가 한 페이지 높이 안에 들어감) → 분할 단편/고아 방지
    section = [Paragraph(head, st_h2), Spacer(1, 2*mm), Paragraph(ROLE[t], st_role), Spacer(1, 3*mm)]
    story.append(KeepTogether(section + [tb]))
    story.append(Spacer(1, 8*mm))


def footer(canvas, doc):
    canvas.saveState()
    canvas.setFont("Malgun", 8); canvas.setFillColor(LGRAY)
    canvas.drawString(15*mm, 10*mm, "I-Study DB 설계 문서")
    canvas.drawRightString(A4[0]-15*mm, 10*mm, str(doc.page))
    canvas.restoreState()


doc = SimpleDocTemplate(OUT, pagesize=A4, leftMargin=15*mm, rightMargin=15*mm,
                        topMargin=16*mm, bottomMargin=16*mm,
                        title="I-Study DB 설계 문서")
doc.build(story, onLaterPages=footer, onFirstPage=lambda c, d: None)
print("saved:", OUT)
