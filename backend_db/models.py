"""
I-Study Beta - Server Models
SQLAlchemy ORM 모델

- Users 테이블: 일반 사용자 (Student / Teacher)
- Admins 테이블: 시스템 관리자 (물리적으로 분리)
"""

import enum

from sqlalchemy import (
    Column, Integer, String, Float, DateTime, Enum, ForeignKey, Text, BigInteger
)
from sqlalchemy.sql import func
from sqlalchemy.orm import relationship
from database import Base


# ─────────────────────────────────────────────────────────
# Auth: 사용자 / 관리자 (물리적으로 분리된 테이블)
# ─────────────────────────────────────────────────────────

class UserRole(str, enum.Enum):
    """일반 사용자 역할"""
    STUDENT = "STUDENT"   # 학생
    TEACHER = "TEACHER"   # 학습지도자


class User(Base):
    """
    일반 사용자 테이블 (학생, 학습지도자)
    - login_id: 사용자가 직접 정하는 고유 아이디 (이메일 X)
    """
    __tablename__ = "users"

    id = Column(Integer, primary_key=True, index=True)
    login_id = Column(String(64), unique=True, nullable=False, index=True)
    password_hash = Column(String(255), nullable=False)
    name = Column(String(100), nullable=False)
    role = Column(Enum(UserRole, name="user_role"), nullable=False, default=UserRole.STUDENT)
    is_active = Column(Integer, default=1)              # 관리자 승인 여부 (1=활성)
    teacher_id = Column(Integer, ForeignKey("users.id"), nullable=True)  # 소속 지도자 (학생만)
    created_at = Column(DateTime, server_default=func.now())

    # self-referential: teacher → students
    students = relationship("User", remote_side=[id], backref="teacher", uselist=True)


class Admin(Base):
    """
    시스템 관리자 테이블 (물리적으로 분리)
    - admin_id: 관리자 전용 아이디
    """
    __tablename__ = "admins"

    id = Column(Integer, primary_key=True, index=True)
    admin_id = Column(String(64), unique=True, nullable=False, index=True)
    password_hash = Column(String(255), nullable=False)
    name = Column(String(100), nullable=False)
    level = Column(Integer, nullable=False, default=1)   # 1=일반 관리자, 9=최고 관리자
    created_at = Column(DateTime, server_default=func.now())


# ─────────────────────────────────────────────────────────
# 기존 도메인 테이블
# ─────────────────────────────────────────────────────────

class HeadPoseData(Base):
    """학습 세션 중 머리/시선 좌표 기록"""
    __tablename__ = "head_pose_data"

    id = Column(Integer, primary_key=True, index=True)
    student_id = Column(String, index=True)             # User.login_id
    x = Column(Float)
    y = Column(Float)
    timestamp = Column(DateTime, server_default=func.now())


class WhitelistUrl(Base):
    """
    학습 허용 사이트 화이트리스트.
    user_id NULL  → 시스템 기본 (모든 학생에게 공통 적용)
    user_id 값 있음 → 해당 학생 전용 (지도자/관리자가 관리)
    """
    __tablename__ = "whitelist_urls"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String, nullable=False)
    url = Column(String, nullable=False)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=True, index=True)
    created_at = Column(DateTime, server_default=func.now())


class Schedule(Base):
    """사용자 학습 일정 (일정표)"""
    __tablename__ = "schedules"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False, index=True)
    date = Column(String(10), nullable=False, index=True)   # YYYY-MM-DD
    start_time = Column(String(5), nullable=True)           # HH:MM
    end_time = Column(String(5), nullable=True)             # HH:MM
    title = Column(String(200), nullable=False)
    memo = Column(Text, nullable=True)
    color = Column(String(20), nullable=True, default="blue")
    is_done = Column(Integer, default=0, nullable=False)  # 0=미완료, 1=완료
    created_at = Column(DateTime, server_default=func.now())


class GazeSettings(Base):
    """
    사용자별 시선/집중도 임계치 설정.
    데스크톱 앱이 학습 시작 시 이 값을 불러와 적용.
    user_id 1:1 (UNIQUE).
    """
    __tablename__ = "gaze_settings"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False, unique=True, index=True)

    # 눈 감음
    ear_threshold = Column(Float, default=0.18)            # EAR 임계값
    eye_closure_threshold = Column(Float, default=5.0)     # 눈 감음 판정 시간(초)

    # Head Pose 이탈
    yaw_threshold = Column(Float, default=20.0)            # 좌우 이탈(도)
    pitch_threshold = Column(Float, default=15.0)          # 상하 이탈(도)
    pose_lost_threshold = Column(Float, default=3.0)       # 이탈 판정 시간(초)

    # 멍때리기
    daze_variance_thr = Column(Float, default=300.0)       # 시선 분산 임계(px²)
    daze_duration_sec = Column(Float, default=2.0)         # 멍때리기 판정 시간(초)

    # 가중치
    alpha_iris = Column(Float, default=0.85)               # Iris 가중치 (0~1)

    # ─── 데스크톱 앱 시야각 캘리브레이션 (시선 초점 잡기) ───
    # 학생이 웹에서 30샘플 측정 → 데스크톱 앱이 학습 시작 시 그대로 적용
    center_ratio        = Column(Float, default=0.50)      # 중앙 응시 시 head_ratio 평균
    h_left_threshold    = Column(Float, default=0.20)      # 좌 이탈 임계 (0~1)
    h_right_threshold   = Column(Float, default=0.80)      # 우 이탈 임계
    v_up_threshold      = Column(Float, default=0.38)      # 상 이탈 임계
    v_down_threshold    = Column(Float, default=0.62)      # 하 이탈 임계
    gaze_lost_threshold = Column(Float, default=2.0)       # 시선 이탈 판정 시간(초)
    calibrated          = Column(Integer, default=0)       # 0=미보정, 1=보정 완료

    updated_at = Column(DateTime, server_default=func.now(), onupdate=func.now())


class StudySession(Base):
    """
    학습 세션 요약 (통계용)
    - 웹: user_id로 식별
    - 데스크톱 앱: login_id로 식별 (user_id=NULL 가능)
    """
    __tablename__ = "study_sessions"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=True, index=True)  # 웹 기반
    login_id = Column(String(64), nullable=True, index=True)                      # 데스크톱 앱 기반
    date = Column(String(10), nullable=False, index=True)    # YYYY-MM-DD
    start_time = Column(DateTime, nullable=True)             # 학습 시작 시각
    end_time = Column(DateTime, nullable=True)               # 학습 종료 시각
    total_time_seconds = Column(Integer, nullable=True)      # 총 학습 시간(초)
    focus_time_seconds = Column(Integer, nullable=True)      # 집중 시간(초)
    duration_min = Column(Integer, default=0)                # 학습 시간(분)
    focus_score = Column(Float, default=0.0)                 # 평균 집중도 (0~100)
    focused_min = Column(Integer, default=0)
    dazed_min = Column(Integer, default=0)
    distracted_min = Column(Integer, default=0)
    created_at = Column(DateTime, server_default=func.now())
