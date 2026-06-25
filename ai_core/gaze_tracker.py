"""
I-Study - Gaze Tracker Module
MediaPipe 기반 시선 추적 모듈
"""

import cv2
import numpy as np
from typing import Callable, Optional
import threading
import time
import os
import sys
import urllib.request

import mediapipe as mp
from mediapipe.tasks import python
from mediapipe.tasks.python import vision
from mediapipe import Image, ImageFormat

try:
    from shared.logger import get_logger, LoggerConfig
    logger = get_logger("gaze_tracker", "gaze.log")
except ImportError:
    import logging
    logger = logging.getLogger("gaze_tracker")


class GazeTracker:
    """MediaPipe Tasks API를 이용한 시선 추적 클래스 - 얼굴 방향 기반"""
    
    NOSE_TIP = 1
    LEFT_EYE_OUTER = 33
    RIGHT_EYE_OUTER = 263
    LEFT_FACE_EDGE = 234
    RIGHT_FACE_EDGE = 454
    
    # 눈 랜드마크 포인트
    LEFT_EYE_TOP = 159
    LEFT_EYE_BOTTOM = 145
    RIGHT_EYE_TOP = 386
    RIGHT_EYE_BOTTOM = 374
    
    # 얼굴 상하 기준점
    FOREHEAD = 10
    CHIN = 152
    
    MODEL_URL = "https://storage.googleapis.com/mediapipe-models/face_landmarker/face_landmarker/float16/1/face_landmarker.task"
    
    def __init__(
        self,
        gaze_lost_threshold: float = 2.0,
        eye_closure_threshold: float = 5.0,
        on_gaze_lost: Optional[Callable] = None,
        on_gaze_restored: Optional[Callable] = None,
        on_eye_closed: Optional[Callable] = None
    ):
        """
        시선 추적기 초기화
        
        Args:
            gaze_lost_threshold: 시선 이탈 판정 시간 (초)
            eye_closure_threshold: 눈 감음 판정 시간 (초)
            on_gaze_lost: 시선 이탈 시 콜백 함수
            on_gaze_restored: 시선 복귀 시 콜백 함수
            on_eye_closed: 눈 감음 시 콜백 함수
        """
        self.gaze_lost_threshold = gaze_lost_threshold
        self.eye_closure_threshold = eye_closure_threshold
        self.on_gaze_lost = on_gaze_lost
        self.on_gaze_restored = on_gaze_restored
        self.on_eye_closed = on_eye_closed
        
        self.model_path = self._ensure_model()
        self.landmarker = None
        
        self.cap = None
        self.is_running = False
        self.thread = None
        
        self.gaze_lost_start_time = None
        self.is_gaze_lost = False
        self.total_gaze_lost_time = 0.0
        self.session_start_time = None
        
        # 눈 감음 감지 관련
        self.eye_closed_start_time = None
        self.is_eye_closed = False
        self.eyes_closed = False
        
        self._lock = threading.Lock()
        
        self.current_frame = None
        self.face_detected = False
        self.gaze_direction = "center"
        self.current_gaze_ratio = 0.5
        self.vertical_gaze_ratio = 0.5
        
        self.calibrated = False
        self.center_ratio = 0.5
        self.left_threshold = 0.20
        self.right_threshold = 0.80
        self.up_threshold = 0.38
        self.down_threshold = 0.62
        self.calibration_samples = []
        self.vertical_calibration_samples = []
    
    def _get_base_path(self) -> str:
        """PyInstaller 패키징 여부에 따른 기본 경로 반환"""
        if getattr(sys, 'frozen', False):
            return sys._MEIPASS
        return os.path.dirname(os.path.abspath(__file__))
    
    def _ensure_model(self) -> str:
        """모델 파일 위치 탐색 (없으면 다운로드)"""
        base_path = self._get_base_path()
        project_root = os.path.dirname(base_path)

        # 환경별 모델 후보 경로 (EXE 번들 포함)
        candidates = [
            # PyInstaller 번들: <_MEIPASS>/ai_core/models/face_landmarker.task
            os.path.join(base_path, "ai_core", "models", "face_landmarker.task"),
            # 개발 환경: ai_core/models/face_landmarker.task
            os.path.join(base_path, "models", "face_landmarker.task"),
            # 프로젝트 루트/models
            os.path.join(project_root, "models", "face_landmarker.task"),
            os.path.join(project_root, "face_landmarker.task"),
            os.path.join(base_path, "face_landmarker.task"),
        ]
        for path in candidates:
            if os.path.exists(path):
                logger.info(f"Model found: {path}")
                return path

        # 마지막 수단: 다운로드 (네트워크 필요)
        download_path = os.path.join(project_root, "models", "face_landmarker.task")
        logger.warning(f"Model not found in bundle, downloading to {download_path}")
        print("모델 다운로드 중...")
        os.makedirs(os.path.dirname(download_path), exist_ok=True)
        urllib.request.urlretrieve(self.MODEL_URL, download_path)
        print("모델 다운로드 완료")

        return download_path
    
    def _create_landmarker(self):
        """FaceLandmarker 생성"""
        # 모델을 바이트로 읽어 buffer로 전달한다.
        # MediaPipe의 C++ 파일 로더는 한글 등 비-ASCII 경로를 열지 못하므로
        # (예: '배포_다른PC용') Python에서 직접 읽어 우회한다.
        with open(self.model_path, "rb") as f:
            model_buffer = f.read()
        base_options = python.BaseOptions(model_asset_buffer=model_buffer)
        options = vision.FaceLandmarkerOptions(
            base_options=base_options,
            output_face_blendshapes=False,
            output_facial_transformation_matrixes=False,
            num_faces=1
        )
        self.landmarker = vision.FaceLandmarker.create_from_options(options)
    
    def _calculate_head_direction(self, landmarks):
        """얼굴 방향 계산 - 코 위치와 얼굴 중심 비교"""
        nose = landmarks[self.NOSE_TIP]
        left_edge = landmarks[self.LEFT_FACE_EDGE]
        right_edge = landmarks[self.RIGHT_FACE_EDGE]
        
        face_center_x = (left_edge.x + right_edge.x) / 2
        face_width = abs(right_edge.x - left_edge.x)
        
        if face_width < 0.001:
            return 0.5
        
        offset = (nose.x - face_center_x) / face_width
        ratio = 0.5 + offset
        return max(0.0, min(1.0, ratio))
    
    def _calculate_vertical_direction(self, landmarks):
        """얼굴 수직 방향 계산 - 코 위치와 얼굴 상하 중심 비교"""
        nose = landmarks[self.NOSE_TIP]
        forehead = landmarks[self.FOREHEAD]
        chin = landmarks[self.CHIN]
        
        face_center_y = (forehead.y + chin.y) / 2
        face_height = abs(chin.y - forehead.y)
        
        if face_height < 0.001:
            return 0.5
        
        offset = (nose.y - face_center_y) / face_height
        ratio = 0.5 + offset
        return max(0.0, min(1.0, ratio))
    
    def _detect_eye_closure(self, landmarks):
        """눈 감음 감지 - 눈의 세로 거리 비율로 판단"""
        left_eye_top = landmarks[self.LEFT_EYE_TOP]
        left_eye_bottom = landmarks[self.LEFT_EYE_BOTTOM]
        left_eye_height = abs(left_eye_top.y - left_eye_bottom.y)
        
        right_eye_top = landmarks[self.RIGHT_EYE_TOP]
        right_eye_bottom = landmarks[self.RIGHT_EYE_BOTTOM]
        right_eye_height = abs(right_eye_top.y - right_eye_bottom.y)
        
        avg_eye_height = (left_eye_height + right_eye_height) / 2
        eye_closure_threshold = 0.010
        
        return avg_eye_height < eye_closure_threshold
    
    def _detect_gaze(self, frame) -> tuple:
        """시선 방향 감지"""
        rgb_frame = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
        mp_image = Image(image_format=ImageFormat.SRGB, data=rgb_frame)
        
        try:
            results = self.landmarker.detect(mp_image)
        except Exception:
            return False, "no_face"
        
        if not results.face_landmarks:
            return False, "no_face"
        
        landmarks = results.face_landmarks[0]
        
        head_ratio = self._calculate_head_direction(landmarks)
        vertical_ratio = self._calculate_vertical_direction(landmarks)
        eyes_closed = self._detect_eye_closure(landmarks)
        
        with self._lock:
            self.current_gaze_ratio = head_ratio
            self.vertical_gaze_ratio = vertical_ratio
            self.eyes_closed = eyes_closed
        
        if vertical_ratio < self.up_threshold:
            return True, "up"
        elif vertical_ratio > self.down_threshold:
            return True, "down"
        elif head_ratio < self.left_threshold:
            return True, "left"
        elif head_ratio > self.right_threshold:
            return True, "right"
        else:
            return True, "center"
    
    def _tracking_loop(self):
        """시선 추적 메인 루프"""
        while self.is_running:
            ret, frame = self.cap.read()
            if not ret:
                time.sleep(0.01)
                continue
            
            frame = cv2.flip(frame, 1)
            face_detected, gaze_direction = self._detect_gaze(frame)
            
            with self._lock:
                self.current_frame = frame.copy()
                self.face_detected = face_detected
                self.gaze_direction = gaze_direction
            
            current_time = time.time()
            is_looking_away = not face_detected or gaze_direction in ["left", "right", "up", "down"]
            
            with self._lock:
                eyes_currently_closed = self.eyes_closed
            
            # 시선 이탈 처리
            if is_looking_away:
                if self.gaze_lost_start_time is None:
                    self.gaze_lost_start_time = current_time
                
                elapsed = current_time - self.gaze_lost_start_time
                if not self.is_gaze_lost and elapsed >= self.gaze_lost_threshold:
                    self.is_gaze_lost = True
                    if self.on_gaze_lost:
                        self.on_gaze_lost()
            else:
                if self.gaze_lost_start_time is not None:
                    lost_duration = current_time - self.gaze_lost_start_time
                    self.total_gaze_lost_time += lost_duration
                    self.gaze_lost_start_time = None
                
                if self.is_gaze_lost:
                    self.is_gaze_lost = False
                    if self.on_gaze_restored:
                        self.on_gaze_restored()
            
            # 눈 감음 처리
            if eyes_currently_closed:
                if self.eye_closed_start_time is None:
                    self.eye_closed_start_time = current_time
                
                eye_closed_elapsed = current_time - self.eye_closed_start_time
                if not self.is_eye_closed and eye_closed_elapsed >= self.eye_closure_threshold:
                    self.is_eye_closed = True
                    if self.on_eye_closed:
                        self.on_eye_closed()
            else:
                self.eye_closed_start_time = None
                self.is_eye_closed = False
            
            time.sleep(0.033)
    
    def start(self, camera_index: int = 0):
        """시선 추적 시작"""
        logger.info(f"Starting gaze tracker (camera_index={camera_index})")
        
        if self.is_running:
            logger.warning("Gaze tracker already running")
            return
        
        try:
            self.cap = cv2.VideoCapture(camera_index, cv2.CAP_DSHOW)
            if not self.cap.isOpened():
                logger.warning("Failed to open camera with DSHOW, trying default backend")
                self.cap = cv2.VideoCapture(camera_index)
            if not self.cap.isOpened():
                logger.error(f"Failed to open camera {camera_index}")
                raise RuntimeError("카메라를 열 수 없습니다.")
            
            logger.info("Camera opened successfully")
            
            self.cap.set(cv2.CAP_PROP_FRAME_WIDTH, 640)
            self.cap.set(cv2.CAP_PROP_FRAME_HEIGHT, 480)
            
            self._create_landmarker()
            
            self.is_running = True
            self.session_start_time = time.time()
            self.total_gaze_lost_time = 0.0
            self.gaze_lost_start_time = None
            self.is_gaze_lost = False
            
            self.thread = threading.Thread(target=self._tracking_loop, daemon=True)
            self.thread.start()
            
            LoggerConfig.log_state_change(logger, "GazeTracker", "STOPPED", "RUNNING")
            logger.info("Gaze tracking started successfully")
        except Exception as e:
            LoggerConfig.log_error(logger, "start", e)
            raise
    
    def stop(self) -> dict:
        """시선 추적 중지 및 통계 반환"""
        logger.info("Stopping gaze tracker")
        
        if not self.is_running:
            logger.warning("Gaze tracker not running")
            return {}
        
        self.is_running = False
        LoggerConfig.log_state_change(logger, "GazeTracker", "RUNNING", "STOPPED")
        
        if self.thread:
            self.thread.join(timeout=2.0)
            self.thread = None
        
        if self.cap:
            self.cap.release()
            self.cap = None
        
        end_time = time.time()
        
        final_gaze_lost_time = self.total_gaze_lost_time
        if self.gaze_lost_start_time is not None:
            final_gaze_lost_time += end_time - self.gaze_lost_start_time
        
        total_time = end_time - self.session_start_time if self.session_start_time else 0
        focus_time = max(0, total_time - final_gaze_lost_time)
        
        stats = {
            "total_time_seconds": round(total_time),
            "focus_time_seconds": round(focus_time),
            "gaze_lost_time_seconds": round(final_gaze_lost_time)
        }
        
        logger.info(f"Session stats: total={stats['total_time_seconds']}s, focus={stats['focus_time_seconds']}s")
        LoggerConfig.log_metric(logger, "focus_rate", round(focus_time / total_time * 100, 1) if total_time > 0 else 0, "%")
        
        return stats
    
    def get_current_frame(self):
        """현재 프레임 반환"""
        with self._lock:
            return self.current_frame.copy() if self.current_frame is not None else None
    
    def get_status(self) -> dict:
        """현재 상태 반환"""
        with self._lock:
            return {
                "face_detected": self.face_detected,
                "gaze_direction": self.gaze_direction,
                "is_gaze_lost": self.is_gaze_lost
            }
    
    def reset_session_stats(self):
        """세션 통계 초기화"""
        self.session_start_time = time.time()
        self.total_gaze_lost_time = 0.0
        self.gaze_lost_start_time = None
        self.is_gaze_lost = False
    
    def get_current_gaze_ratio(self) -> float:
        """현재 시선 비율 반환"""
        with self._lock:
            return self.current_gaze_ratio
    
    def add_calibration_sample(self) -> bool:
        """캘리브레이션 샘플 추가"""
        with self._lock:
            if self.face_detected:
                self.calibration_samples.append(self.current_gaze_ratio)
                return True
        return False
    
    def complete_calibration(self, margin: float = 0.15) -> bool:
        """캘리브레이션 완료 및 임계값 설정"""
        if len(self.calibration_samples) < 5:
            return False
        
        self.center_ratio = np.mean(self.calibration_samples)
        self.left_threshold = max(0.1, self.center_ratio - margin)
        self.right_threshold = min(0.9, self.center_ratio + margin)
        
        self.calibrated = True
        self.calibration_samples = []
        
        return True
    
    def reset_calibration(self):
        """캘리브레이션 초기화"""
        self.calibrated = False
        self.center_ratio = 0.5
        self.left_threshold = 0.25
        self.right_threshold = 0.75
        self.calibration_samples = []
    
    def get_calibration_info(self) -> dict:
        """캘리브레이션 정보 반환"""
        return {
            "calibrated": self.calibrated,
            "center_ratio": self.center_ratio,
            "left_threshold": self.left_threshold,
            "right_threshold": self.right_threshold,
            "sample_count": len(self.calibration_samples)
        }
    
    def __del__(self):
        self.stop()
        if self.landmarker:
            self.landmarker.close()
