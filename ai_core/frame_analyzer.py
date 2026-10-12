"""
I-Study - 프레임 단위 시선/집중 분석기 (웹 /ws/gaze 용)

데스크톱 GazeTracker 와 같은 판정 로직(얼굴 방향 비율·눈 감음)을
카메라 없이, 클라이언트가 보낸 프레임 한 장씩 적용한다.
"""

import math
import time

from ai_core.gaze_tracker import GazeTracker


class FrameGazeAnalyzer(GazeTracker):
    """연결(사용자)마다 하나씩 만들어 쓰는 프레임 분석기"""

    # EAR 계산용 눈 안쪽 끝 랜드마크
    LEFT_EYE_INNER = 133
    RIGHT_EYE_INNER = 362

    def __init__(self, gaze_lost_threshold: float = 3.0, eye_closure_threshold: float = 5.0):
        super().__init__(gaze_lost_threshold=gaze_lost_threshold,
                         eye_closure_threshold=eye_closure_threshold)
        self._create_landmarker(with_pose=True)
        self._away_since = None
        self._closed_since = None
        self.focus_state = "Focused"
        self.focus_score = 100.0

    def analyze(self, frame, now: float = None) -> dict:
        """BGR 프레임 → 결과 dict (얼굴이 없으면 {"face_detected": False})"""
        now = time.time() if now is None else now
        face_detected, direction = self._detect_gaze(frame)
        if not face_detected:
            self._update_focus(now, away=True, closed=False)
            return {"face_detected": False}

        detection = self.last_detection
        landmarks = detection.face_landmarks[0]
        yaw, pitch = self._head_pose_degrees(detection)
        self._update_focus(now, away=direction != "center", closed=self.eyes_closed)
        return {
            "face_detected": True,
            "gaze": [round(self.current_gaze_ratio, 4), round(self.vertical_gaze_ratio, 4)],
            "head": {"yaw": yaw, "pitch": pitch},
            "ear": round(self._eye_aspect_ratio(landmarks), 4),
            "direction": direction,
            "focus_state": self.focus_state,
            "focus_score": round(self.focus_score, 1),
        }

    def _update_focus(self, now: float, away: bool, closed: bool):
        """시선 이탈·눈 감음이 임계 시간 이상 이어지면 상태 변경, 점수는 지수이동평균"""
        if not away:
            self._away_since = None
        elif self._away_since is None:
            self._away_since = now
        if not closed:
            self._closed_since = None
        elif self._closed_since is None:
            self._closed_since = now

        if self._closed_since is not None and now - self._closed_since >= self.eye_closure_threshold:
            self.focus_state = "Dazed"
        elif self._away_since is not None and now - self._away_since >= self.gaze_lost_threshold:
            self.focus_state = "Distracted"
        else:
            self.focus_state = "Focused"
        target = 100.0 if self.focus_state == "Focused" else 0.0
        self.focus_score = self.focus_score * 0.9 + target * 0.1

    def __del__(self):
        # 카메라를 쓰지 않으므로 stop() 없이 모델만 닫는다
        if self.landmarker:
            self.landmarker.close()

    @staticmethod
    def _head_pose_degrees(detection) -> tuple:
        """얼굴 변환행렬의 회전 부분 → (yaw, pitch) 도"""
        if not detection.facial_transformation_matrixes:
            return 0.0, 0.0
        r = detection.facial_transformation_matrixes[0]
        pitch = math.degrees(math.atan2(r[2][1], r[2][2]))
        yaw = math.degrees(math.atan2(-r[2][0], math.hypot(r[2][1], r[2][2])))
        return round(yaw, 1), round(pitch, 1)

    def _eye_aspect_ratio(self, landmarks) -> float:
        """양쪽 눈 EAR(세로/가로) 평균"""
        def ear(top, bottom, outer, inner):
            t, b, o, i = (landmarks[k] for k in (top, bottom, outer, inner))
            width = math.hypot(o.x - i.x, o.y - i.y)
            return math.hypot(t.x - b.x, t.y - b.y) / width if width > 1e-6 else 0.0

        left = ear(self.LEFT_EYE_TOP, self.LEFT_EYE_BOTTOM, self.LEFT_EYE_OUTER, self.LEFT_EYE_INNER)
        right = ear(self.RIGHT_EYE_TOP, self.RIGHT_EYE_BOTTOM, self.RIGHT_EYE_OUTER, self.RIGHT_EYE_INNER)
        return (left + right) / 2
