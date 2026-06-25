"""
시선 이탈 탐지 테스트 도구 (추론 전용 / 재학습·파인튜닝 없음)
================================================================
명세 구현:
  - OpenCV         : 웹캠 캡처 / 이미지 처리
  - mediapipe      : FaceLandmarker(Tasks API)로 얼굴·478 랜드마크 검출
  - headpose       : solvePnP 로 yaw/pitch/roll(도) 추정
  - gaze           : 홍채(iris) 랜드마크로 시선 방향 추정
  - eye(눈 감음)   : 양눈 세로 거리로 졸음/눈감음 감지 (메인 앱 gaze_tracker 로직 차용)
  - 한글 오버레이  : PIL(Pillow) + 한글 폰트(.ttf)  ← OpenCV putText 는 한글 불가

※ 이 PC 의 mediapipe(0.10.33)는 레거시 mp.solutions(FaceMesh) 가 없어 Tasks API 를 쓴다.
  gaze/headpose 는 별도 pip 모듈 대신, 검증된 MediaPipe 추론 결과로부터 계산한다.
  (어떤 모델도 재학습하지 않고 추론만 한다.)

사용법:
  python model_test/gaze_deviation_test.py                       # 웹캠 루프(창 표시)
  python model_test/gaze_deviation_test.py --max-frames 30       # 30프레임 후 종료
  python model_test/gaze_deviation_test.py --no-show --max-frames 5   # 창 없이(헤드리스)
  python model_test/gaze_deviation_test.py --image 사진.jpg       # 사진 한 장만 판정
"""

import os
import sys
import csv
import time
import argparse
from datetime import datetime

import cv2
import numpy as np

# Windows 콘솔/백그라운드 리다이렉트 시 한글·기호(—, °) 출력 깨짐·크래시 방지
try:
    sys.stdout.reconfigure(encoding="utf-8")
except Exception:
    pass

# ─────────────────────────────────────────────────────────────
# 전역 설정 (임계값·주기·결합규칙·폰트경로 모두 여기서 변경)
# ─────────────────────────────────────────────────────────────
CAPTURE_INTERVAL_SEC  = 0.1      # 캡처 주기(초) — 0.1초마다 1장(약 10fps)
HEADPOSE_YAW_THRESH   = 25.0     # yaw 임계값(도)  — 좌우 고개 돌림
HEADPOSE_PITCH_THRESH = 15.0     # pitch 임계값(도) — 상하 고개 들기/숙임 (재현율↑ 위해 20→15)
GAZE_CENTER_MARGIN    = 0.12     # 화면 중앙 허용 범위(0~1, 0.5±margin 벗어나면 이탈) (재현율↑ 위해 0.30→0.12)
EYE_CLOSURE_THRESH    = 0.010    # (폴백) 양눈 세로거리 평균이 이 값 미만이면 '눈 감음'
EYE_BLINK_THRESH      = 0.50     # blendshape eyeBlink 평균 ≥ 이 값이면 '눈 감음'(더 견고, 권장)
USE_BLENDSHAPES       = True     # True면 눈 감음을 MediaPipe blendshape(eyeBlink)로 판정(추론 전용)
SUSTAIN_SEC           = 1.0      # 웹캠 루프: 이 시간 이상 같은 상태 지속돼야 최종 라벨 확정(떨림 제거)
CALIBRATE             = True     # 시작 시 개인 '정면' 기준자세 보정(권장; 카메라각·체계적 오차 흡수)
CALIBRATION_SEC       = 3.0      # 보정 샘플 수집 시간(초). 이후 이 기준에서의 편차(Δ)로 판정
COMBINE_RULE          = "OR"     # "OR"(둘 중 하나라도 이탈→이탈) / "AND"(둘 다 이탈→이탈)
OUTPUT_DIR            = "./gaze_test_output"
KOREAN_FONT_PATH      = None     # None 이면 아래 후보에서 자동 탐색(맑은 고딕 등)
MAX_FRAMES            = 1000     # 이 장수 도달 시 자동 종료(0이면 무제한, 'q'로 종료)
CAMERA_INDEX          = 0
FLIP_HORIZONTAL       = True     # 셀카처럼 좌우 반전(앱과 동일). |yaw| 판정엔 영향 없음

# 폰트 자동 탐색 후보 (Windows 기본 한글 폰트)
_FONT_CANDIDATES = [
    r"C:\Windows\Fonts\malgun.ttf",     # 맑은 고딕
    r"C:\Windows\Fonts\malgunbd.ttf",
    r"C:\Windows\Fonts\gulim.ttc",
    r"C:\Windows\Fonts\batang.ttc",
    "/usr/share/fonts/truetype/nanum/NanumGothic.ttf",
]

# face_landmarker.task 탐색 위치 (ai_core/gaze_tracker.py 와 동일)
_BASE = os.path.dirname(os.path.abspath(__file__))
_PROJ = os.path.dirname(_BASE)
_TASK_CANDIDATES = [
    os.path.join(_PROJ, "models", "face_landmarker.task"),
    os.path.join(_PROJ, "ai_core", "models", "face_landmarker.task"),
    os.path.join(_BASE, "face_landmarker.task"),
]

# ─────────────────────────────────────────────────────────────
# headpose: solvePnP 용 3D 표준 얼굴 모델 + 대응 랜드마크 인덱스
# ─────────────────────────────────────────────────────────────
_MODEL_3D = np.array([
    [0.0,    0.0,    0.0],     # 코끝
    [0.0, -330.0,  -65.0],     # 턱
    [-225.0, 170.0, -135.0],   # 왼눈 바깥쪽
    [225.0,  170.0, -135.0],   # 오른눈 바깥쪽
    [-150.0, -150.0, -125.0],  # 왼쪽 입꼬리
    [150.0,  -150.0, -125.0],  # 오른쪽 입꼬리
], dtype=np.float64)
_PNP_IDX = [1, 152, 33, 263, 61, 291]

# gaze/eye: 홍채(iris) + 눈 코너/상하 랜드마크 (478 모델)
#   (iris_center, corner_a, corner_b, lid_top, lid_bottom)
_EYES = [
    (468, 33, 133, 159, 145),    # 한쪽 눈
    (473, 263, 362, 386, 374),   # 반대쪽 눈
]


def log(*a):
    print(*a, flush=True)


def _f(v):
    """수치 포맷(없으면 '-')."""
    return f"{v:.1f}" if isinstance(v, (int, float)) else "-"


_FONT_PATH = None
_FONT_CACHE = {}


def _font(size):
    """폰트 크기별 캐시 로드 (이미지 폭에 맞춰 크기 조절용)."""
    from PIL import ImageFont
    size = int(size)
    if size not in _FONT_CACHE:
        _FONT_CACHE[size] = ImageFont.truetype(_FONT_PATH, size)
    return _FONT_CACHE[size]


# ─────────────────────────────────────────────────────────────
# 1) 모델/모듈 로드
# ─────────────────────────────────────────────────────────────
def resolve_font():
    """한글 폰트 경로 탐색 + 로드 검증. 성공 시 경로(전역에도 저장), 실패 시 None."""
    from PIL import ImageFont
    global _FONT_PATH
    path = KOREAN_FONT_PATH
    cands = ([path] if path and path != "<한글 폰트 경로.ttf>" else []) + _FONT_CANDIDATES
    for p in cands:
        if p and os.path.exists(p):
            try:
                ImageFont.truetype(p, 24)   # 로드 가능 검증
                _FONT_PATH = p
                return p
            except Exception:
                continue
    return None


def find_task_model():
    for p in _TASK_CANDIDATES:
        if os.path.exists(p):
            return p
    return None


def load_landmarker():
    """MediaPipe FaceLandmarker(Tasks API) 로드 — iris 포함 478 랜드마크."""
    from mediapipe.tasks import python
    from mediapipe.tasks.python import vision
    task = find_task_model()
    if task is None:
        return None, "face_landmarker.task 를 찾을 수 없습니다. 프로젝트를 한 번 실행하면 models/ 에 자동 다운로드됩니다."
    try:
        base = python.BaseOptions(model_asset_path=task)
        opts = vision.FaceLandmarkerOptions(
            base_options=base,
            output_face_blendshapes=True,                  # 눈 감음(eyeBlink) 신호용
            output_facial_transformation_matrixes=False,  # headpose 는 solvePnP 사용
            num_faces=1,
        )
        return vision.FaceLandmarker.create_from_options(opts), None
    except Exception as e:
        return None, f"FaceLandmarker 생성 실패: {e}"


# ─────────────────────────────────────────────────────────────
# 3) 추정 함수들
# ─────────────────────────────────────────────────────────────
def _norm_angle(a):
    """solvePnP 분해 각도(±180 wrap) 정규화."""
    if a > 90:
        a -= 180
    elif a < -90:
        a += 180
    return a


def estimate_headpose(lm, w, h):
    """solvePnP 로 (yaw, pitch, roll) 도 단위 추정. 실패 시 None."""
    try:
        pts = np.array([(lm[i].x * w, lm[i].y * h) for i in _PNP_IDX], dtype=np.float64)
    except IndexError:
        return None
    f = float(w)
    cam = np.array([[f, 0, w / 2.0], [0, f, h / 2.0], [0, 0, 1]], dtype=np.float64)
    ok, rvec, _ = cv2.solvePnP(_MODEL_3D, pts, cam, np.zeros((4, 1)),
                               flags=cv2.SOLVEPNP_ITERATIVE)
    if not ok:
        return None
    rmat, _ = cv2.Rodrigues(rvec)
    ang = cv2.RQDecomp3x3(rmat)[0]
    pitch, yaw, roll = _norm_angle(ang[0]), _norm_angle(ang[1]), _norm_angle(ang[2])
    return yaw, pitch, roll


def estimate_gaze(lm):
    """홍채 위치로 (gaze_h, gaze_v) 추정. 0.5,0.5 = 정중앙. 478 미만이면 None."""
    if len(lm) < 478:
        return None
    hs, vs = [], []
    for iris, ca, cb, top, bot in _EYES:
        ix, iy = lm[iris].x, lm[iris].y
        xa, xb = lm[ca].x, lm[cb].x
        yt, yb = lm[top].y, lm[bot].y
        xmin, xmax = min(xa, xb), max(xa, xb)
        ymin, ymax = min(yt, yb), max(yt, yb)
        if xmax - xmin > 1e-6:
            hs.append((ix - xmin) / (xmax - xmin))
        if ymax - ymin > 1e-6:
            vs.append((iy - ymin) / (ymax - ymin))
    if not hs or not vs:
        return None
    return float(np.mean(hs)), float(np.mean(vs))


def estimate_eye_closure(lm):
    """눈 감음 감지 (메인 앱 gaze_tracker._detect_eye_closure 차용):
    양눈 세로 거리(정규화) 평균이 EYE_CLOSURE_THRESH 미만이면 True."""
    heights = []
    for _, _, _, top, bot in _EYES:
        try:
            heights.append(abs(lm[top].y - lm[bot].y))
        except IndexError:
            pass
    if not heights:
        return False
    return (sum(heights) / len(heights)) < EYE_CLOSURE_THRESH


def blink_score_from_blendshapes(res):
    """MediaPipe blendshape 의 eyeBlinkLeft/Right 평균(0~1). 없으면 None."""
    if not getattr(res, "face_blendshapes", None):
        return None
    d = {c.category_name: c.score for c in res.face_blendshapes[0]}
    return (d.get("eyeBlinkLeft", 0.0) + d.get("eyeBlinkRight", 0.0)) / 2.0


def process_frame(landmarker, frame, baseline=None):
    """프레임 한 장 → 판정 결과 dict. baseline 이 있으면 기준자세 대비 편차(Δ)로 판정."""
    import mediapipe as mp
    h, w = frame.shape[:2]
    rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
    res = landmarker.detect(mp.Image(image_format=mp.ImageFormat.SRGB, data=rgb))

    result = {
        "face": False, "yaw": None, "pitch": None, "roll": None,
        "gaze_h": None, "gaze_v": None,
        "headpose_away": False, "gaze_away": False, "eye_closed": False, "eye_score": None,
        "gaze_state": "판단불가", "label": "판단 불가",
    }
    if not res.face_landmarks:
        return result

    lm = res.face_landmarks[0]
    result["face"] = True

    # 기준자세(보정값). 없으면 절대 기준(yaw0=pitch0=0, gaze 중앙 0.5)
    y0 = baseline.get("yaw", 0.0) if baseline else 0.0
    p0 = baseline.get("pitch", 0.0) if baseline else 0.0
    gh0 = baseline.get("gaze_h", 0.5) if baseline else 0.5
    gv0 = baseline.get("gaze_v", 0.5) if baseline else 0.5

    hp = estimate_headpose(lm, w, h)
    if hp is not None:
        yaw, pitch, roll = hp
        result["yaw"], result["pitch"], result["roll"] = yaw, pitch, roll
        result["headpose_away"] = (abs(yaw - y0) > HEADPOSE_YAW_THRESH or
                                   abs(pitch - p0) > HEADPOSE_PITCH_THRESH)

    gz = estimate_gaze(lm)
    if gz is not None:
        gh, gv = gz
        result["gaze_h"], result["gaze_v"] = gh, gv
        result["gaze_away"] = (abs(gh - gh0) > GAZE_CENTER_MARGIN or
                               abs(gv - gv0) > GAZE_CENTER_MARGIN)
    result["gaze_state"] = "이탈" if result["gaze_away"] else "정상"

    # 눈 감음: blendshape(eyeBlink) 우선, 없으면 세로거리 폴백
    if USE_BLENDSHAPES:
        bscore = blink_score_from_blendshapes(res)
        if bscore is not None:
            result["eye_score"] = round(bscore, 3)
            result["eye_closed"] = bscore >= EYE_BLINK_THRESH
        else:
            result["eye_closed"] = estimate_eye_closure(lm)
    else:
        result["eye_closed"] = estimate_eye_closure(lm)

    # 결합 규칙: headpose↔gaze 는 COMBINE_RULE 로, 눈 감음(졸음)은 항상 이탈로 OR
    hp_away, gz_away = result["headpose_away"], result["gaze_away"]
    if COMBINE_RULE.upper() == "AND":
        hg_away = hp_away and gz_away
    else:  # OR (기본)
        hg_away = hp_away or gz_away
    away = hg_away or result["eye_closed"]
    result["label"] = "이탈" if away else "정상"
    return result


# ─────────────────────────────────────────────────────────────
# 4) 한글 오버레이
# ─────────────────────────────────────────────────────────────
def draw_overlay(frame, result):
    """이미지 하단에 배경 띠 + 한글 판정 결과를 PIL 로 그린다 (폭에 맞춰 폰트 자동 크기)."""
    from PIL import Image, ImageDraw
    pil = Image.fromarray(cv2.cvtColor(frame, cv2.COLOR_BGR2RGB))
    draw = ImageDraw.Draw(pil)
    W, H = pil.size
    font_main = _font(max(18, W / 18))
    font_sub = _font(max(13, W / 30))
    band = max(int(H * 0.20), 70)
    draw.rectangle([0, H - band, W, H], fill=(18, 18, 26))

    label = result["label"]
    color = {"이탈": (255, 80, 80), "정상": (90, 230, 130)}.get(label, (185, 185, 185))

    if result["face"]:
        line1 = f"시선 이탈: {label}"
        yaw = result["yaw"] if result["yaw"] is not None else float("nan")
        pitch = result["pitch"] if result["pitch"] is not None else float("nan")
        eye = "감음" if result["eye_closed"] else "열림"
        line2 = f"yaw: {yaw:.1f}  pitch: {pitch:.1f}  gaze: {result['gaze_state']}  eye: {eye}"
    else:
        line1 = "판단 불가"
        line2 = "얼굴 미검출"

    y0 = H - band + int(band * 0.12)
    draw.text((16, y0), line1, font=font_main, fill=color)
    draw.text((16, y0 + int(band * 0.46)), line2, font=font_sub, fill=(225, 225, 225))
    return cv2.cvtColor(np.array(pil), cv2.COLOR_RGB2BGR)


def calibrate(cap, landmarker, flip, seconds, show):
    """시작 시 사용자의 '정면' 기준 자세를 측정(중앙값)해 baseline dict 반환.
    카메라 각도·모델의 체계적 각도 오차를 흡수한다. 실패 시 None."""
    import statistics as st
    ys, ps, ghs, gvs = [], [], [], []
    win = "Gaze Deviation Test"
    t0 = time.time()
    while time.time() - t0 < seconds:
        ret, frame = cap.read()
        if not ret:
            continue
        if flip:
            frame = cv2.flip(frame, 1)
        r = process_frame(landmarker, frame)   # baseline 없이 raw 측정
        if r["face"] and r["yaw"] is not None:
            ys.append(r["yaw"]); ps.append(r["pitch"])
            if r["gaze_h"] is not None:
                ghs.append(r["gaze_h"]); gvs.append(r["gaze_v"])
        if show:
            from PIL import Image, ImageDraw
            pil = Image.fromarray(cv2.cvtColor(frame, cv2.COLOR_BGR2RGB))
            d = ImageDraw.Draw(pil); W, H = pil.size
            band = max(int(H * 0.20), 70)
            d.rectangle([0, H - band, W, H], fill=(18, 18, 26))
            d.text((16, H - band + int(band * 0.12)), "보정 중: 정면(화면)을 보세요",
                   font=_font(max(18, W / 18)), fill=(255, 210, 90))
            d.text((16, H - band + int(band * 0.58)),
                   f"{max(0.0, seconds - (time.time() - t0)):.1f}s   샘플 {len(ys)}",
                   font=_font(max(13, W / 30)), fill=(225, 225, 225))
            cv2.imshow(win, cv2.cvtColor(np.array(pil), cv2.COLOR_RGB2BGR))
            cv2.waitKey(1)
    if len(ys) < 3:
        return None
    base = {"yaw": st.median(ys), "pitch": st.median(ps)}
    if ghs:
        base["gaze_h"] = st.median(ghs)
        base["gaze_v"] = st.median(gvs)
    return base


def verify_overlay(out_dir):
    """루프 전에 한글 오버레이가 정상 출력되는지 샘플 1장으로 검증."""
    sample = np.full((220, 560, 3), 60, dtype=np.uint8)
    demo = {"face": True, "label": "이탈", "yaw": 31.2, "pitch": -8.5,
            "gaze_state": "이탈", "gaze_h": 0.5, "gaze_v": 0.5, "eye_closed": False}
    out = draw_overlay(sample, demo)
    path = os.path.join(out_dir, "_overlay_check.jpg")
    cv2.imwrite(path, out)
    return path


# ─────────────────────────────────────────────────────────────
# 2) 메인: 웹캠 루프 / 단일 이미지
# ─────────────────────────────────────────────────────────────
def open_camera(idx):
    cap = cv2.VideoCapture(idx, cv2.CAP_DSHOW)
    if not cap.isOpened():
        cap = cv2.VideoCapture(idx)
    if not cap.isOpened():
        return None
    cap.set(cv2.CAP_PROP_FRAME_WIDTH, 640)
    cap.set(cv2.CAP_PROP_FRAME_HEIGHT, 480)
    return cap


def ts_now():
    t = datetime.now()
    return t.strftime("%Y%m%d_%H%M%S_") + f"{t.microsecond // 1000:03d}"


CSV_HEADER = ["timestamp", "yaw", "pitch", "gaze_상태", "headpose_이탈",
              "gaze_이탈", "최종_라벨", "즉시_라벨", "눈감음", "roll", "gaze_h", "gaze_v", "image"]


def row_from(result, ts, image_name, instant_label=None):
    def r(v, n=1):
        return "" if v is None else round(v, n)
    return [ts, r(result["yaw"]), r(result["pitch"]), result["gaze_state"],
            result["headpose_away"], result["gaze_away"], result["label"],
            instant_label if instant_label is not None else result["label"],
            result.get("eye_closed", False),
            r(result.get("roll")), r(result["gaze_h"], 3), r(result["gaze_v"], 3),
            image_name]


def main():
    global COMBINE_RULE
    ap = argparse.ArgumentParser(description="시선 이탈 탐지 테스트 도구 (추론 전용)")
    ap.add_argument("--cam", type=int, default=CAMERA_INDEX)
    ap.add_argument("--interval", type=float, default=CAPTURE_INTERVAL_SEC)
    ap.add_argument("--max-frames", type=int, default=MAX_FRAMES)
    ap.add_argument("--combine", choices=["OR", "AND"], default=COMBINE_RULE)
    ap.add_argument("--out", default=OUTPUT_DIR)
    ap.add_argument("--no-show", action="store_true", help="창 표시 없이 저장만(헤드리스)")
    ap.add_argument("--no-flip", action="store_true", help="좌우 반전 끄기")
    ap.add_argument("--no-calibrate", action="store_true", help="시작 보정 건너뛰기(절대 기준 사용)")
    ap.add_argument("--image", default=None, help="웹캠 대신 사진 1장을 판정")
    args = ap.parse_args()

    COMBINE_RULE = args.combine
    out_dir = os.path.abspath(args.out)
    os.makedirs(out_dir, exist_ok=True)

    # ── 1) 모듈/폰트 로드 (실패 시 명확한 에러 후 종료) ──
    font_path = resolve_font()
    if font_path is None:
        log("[에러] 한글 폰트를 찾지 못했습니다. KOREAN_FONT_PATH 에 .ttf 경로를 지정하세요.")
        log("       (확인한 후보: " + ", ".join(_FONT_CANDIDATES) + ")")
        sys.exit(1)
    log(f"[로드] 한글 폰트: {font_path}")

    landmarker, err = load_landmarker()
    if landmarker is None:
        log(f"[에러] MediaPipe 모델 로드 실패: {err}")
        sys.exit(1)
    log("[로드] MediaPipe FaceLandmarker(Tasks API) 준비 완료")

    # ── 한글 오버레이 사전 검증 ──
    check = verify_overlay(out_dir)
    log(f"[검증] 한글 오버레이 샘플 저장: {check}  (육안 확인 후 루프 진행)")

    eye_mode = f"blink≥{EYE_BLINK_THRESH}" if USE_BLENDSHAPES else f"raw<{EYE_CLOSURE_THRESH}"
    log(f"[설정] yaw>{HEADPOSE_YAW_THRESH} | pitch>{HEADPOSE_PITCH_THRESH} | "
        f"gaze margin±{GAZE_CENTER_MARGIN} | eye={eye_mode} | "
        f"결합={COMBINE_RULE} | 지속={SUSTAIN_SEC}s | 주기={args.interval}s")

    # ── 단일 이미지 모드 ──
    if args.image:
        frame = cv2.imread(args.image)
        if frame is None:
            log(f"[에러] 이미지를 읽을 수 없습니다: {args.image}")
            sys.exit(1)
        result = process_frame(landmarker, frame)
        ts = ts_now()
        annotated = draw_overlay(frame.copy(), result)
        save_path = os.path.join(out_dir, f"{ts}_{os.path.basename(args.image)}")
        cv2.imwrite(save_path, annotated)
        csv_path = os.path.join(out_dir, "gaze_log.csv")
        with open(csv_path, "w", newline="", encoding="utf-8-sig") as f:
            w = csv.writer(f); w.writerow(CSV_HEADER)
            w.writerow(row_from(result, ts, os.path.basename(save_path)))
        eye = "감음" if result["eye_closed"] else "열림"
        log(f"[결과] {result['label']}  (yaw={_f(result['yaw'])}, pitch={_f(result['pitch'])}, "
            f"gaze={result['gaze_state']}, eye={eye})  → {save_path}")
        landmarker.close()
        return

    # ── 웹캠 루프 모드 ──
    cap = open_camera(args.cam)
    if cap is None:
        log("[에러] 카메라를 열 수 없습니다. 다른 프로그램이 카메라를 점유 중인지 확인하세요.")
        sys.exit(1)

    flip = FLIP_HORIZONTAL and not args.no_flip

    # ── 개인별 기준자세 보정 ──
    baseline = None
    if CALIBRATE and not args.no_calibrate:
        log(f"[보정] {CALIBRATION_SEC:.0f}초 동안 화면(정면)을 봐주세요...")
        baseline = calibrate(cap, landmarker, flip, CALIBRATION_SEC, not args.no_show)
        if baseline:
            log(f"[보정] 완료 — 기준 yaw={baseline['yaw']:.1f}° pitch={baseline['pitch']:.1f}° "
                f"(이 자세를 '정면'으로 봄, 이후 편차로 판정)")
        else:
            log("[보정] 얼굴 미검출로 실패 → 절대 기준으로 진행")

    csv_path = os.path.join(out_dir, "gaze_log.csv")
    csv_file = open(csv_path, "w", newline="", encoding="utf-8-sig")
    writer = csv.writer(csv_file); writer.writerow(CSV_HEADER)

    n_total = n_normal = n_away = n_unknown = 0
    last_proc = 0.0
    last_annotated = None
    confirmed_label = "정상"        # 히스테리시스로 확정된 라벨
    instant_prev = None             # 직전 즉시 라벨
    instant_since = 0.0             # 현재 즉시 라벨이 시작된 시각
    win = "Gaze Deviation Test"
    log("\n=== 시작 ===  ('q' 종료)")

    try:
        while True:
            ret, frame = cap.read()
            if not ret:
                time.sleep(0.01)
                continue
            if flip:
                frame = cv2.flip(frame, 1)

            now = time.time()
            if now - last_proc >= args.interval:
                last_proc = now
                ts = ts_now()
                result = process_frame(landmarker, frame, baseline)
                instant_label = result["label"]

                # 시간 지속(히스테리시스): 즉시 라벨이 SUSTAIN_SEC 이상 유지돼야 확정 라벨 변경
                if instant_label != instant_prev:
                    instant_prev = instant_label
                    instant_since = now
                if instant_label != confirmed_label and (now - instant_since) >= SUSTAIN_SEC:
                    confirmed_label = instant_label

                result["label"] = confirmed_label   # 화면/저장/집계는 '확정' 라벨 기준
                last_annotated = draw_overlay(frame.copy(), result)
                fname = f"{ts}.jpg"
                cv2.imwrite(os.path.join(out_dir, fname), last_annotated)
                writer.writerow(row_from(result, ts, fname, instant_label)); csv_file.flush()

                n_total += 1
                if confirmed_label == "정상":
                    n_normal += 1
                elif confirmed_label == "이탈":
                    n_away += 1
                else:
                    n_unknown += 1
                eye = "감음" if result["eye_closed"] else "열림"
                log(f"  [{n_total}] {ts}  확정={confirmed_label:6s} 즉시={instant_label:6s}  "
                    f"yaw={_f(result['yaw'])} pitch={_f(result['pitch'])} "
                    f"gaze={result['gaze_state']} eye={eye}")

                if args.max_frames and n_total >= args.max_frames:
                    break

            if not args.no_show:
                try:
                    cv2.imshow(win, last_annotated if last_annotated is not None else frame)
                    if (cv2.waitKey(1) & 0xFF) == ord("q"):
                        break
                except cv2.error:
                    # 디스플레이 없음 → 헤드리스로 강등
                    args.no_show = True
    finally:
        cap.release()
        cv2.destroyAllWindows()
        csv_file.close()
        landmarker.close()

    # ── 종료 요약 ──
    log("\n=== 요약 ===")
    log(f"  총 프레임 : {n_total}")
    log(f"  정상      : {n_normal}")
    log(f"  이탈      : {n_away}")
    log(f"  판단 불가 : {n_unknown}")
    log(f"  로그 CSV  : {csv_path}")
    log(f"  이미지    : {out_dir}")


if __name__ == "__main__":
    main()
