-- I-Study DB 스키마 (PostgreSQL)
-- 기존 시스템(FastAPI/SQLAlchemy)이 생성한 스키마와 동일.
-- ⚠️ 기본은 자동 실행하지 않음. 신규 DB 를 처음 구성할 때만 수동 실행:
--     psql -U postgres -d istudy -f schema.sql

-- 사용자 역할 enum (이미 있으면 건너뜀)
DO $$
BEGIN
    IF NOT EXISTS (SELECT 1 FROM pg_type WHERE typname = 'user_role') THEN
        CREATE TYPE user_role AS ENUM ('STUDENT', 'TEACHER');
    END IF;
END$$;

CREATE TABLE IF NOT EXISTS users (
    id            SERIAL PRIMARY KEY,
    login_id      VARCHAR(64) UNIQUE NOT NULL,
    password_hash VARCHAR(255) NOT NULL,
    name          VARCHAR(100) NOT NULL,
    role          user_role NOT NULL DEFAULT 'STUDENT',
    is_active     INTEGER DEFAULT 1,
    teacher_id    INTEGER REFERENCES users(id),
    created_at    TIMESTAMP DEFAULT now()
);
CREATE INDEX IF NOT EXISTS ix_users_login_id ON users (login_id);

CREATE TABLE IF NOT EXISTS admins (
    id            SERIAL PRIMARY KEY,
    admin_id      VARCHAR(64) UNIQUE NOT NULL,
    password_hash VARCHAR(255) NOT NULL,
    name          VARCHAR(100) NOT NULL,
    level         INTEGER NOT NULL DEFAULT 1,
    created_at    TIMESTAMP DEFAULT now()
);

CREATE TABLE IF NOT EXISTS head_pose_data (
    id         SERIAL PRIMARY KEY,
    student_id VARCHAR,
    x          DOUBLE PRECISION,
    y          DOUBLE PRECISION,
    timestamp  TIMESTAMP DEFAULT now()
);
CREATE INDEX IF NOT EXISTS ix_head_pose_student ON head_pose_data (student_id);

CREATE TABLE IF NOT EXISTS whitelist_urls (
    id         SERIAL PRIMARY KEY,
    name       VARCHAR NOT NULL,
    url        VARCHAR NOT NULL,
    user_id    INTEGER REFERENCES users(id),
    created_at TIMESTAMP DEFAULT now()
);
CREATE INDEX IF NOT EXISTS ix_whitelist_user ON whitelist_urls (user_id);

CREATE TABLE IF NOT EXISTS schedules (
    id         SERIAL PRIMARY KEY,
    user_id    INTEGER NOT NULL REFERENCES users(id),
    date       VARCHAR(10) NOT NULL,
    start_time VARCHAR(5),
    end_time   VARCHAR(5),
    title      VARCHAR(200) NOT NULL,
    memo       TEXT,
    color      VARCHAR(20) DEFAULT 'blue',
    is_done    INTEGER NOT NULL DEFAULT 0,
    created_at TIMESTAMP DEFAULT now()
);
CREATE INDEX IF NOT EXISTS ix_schedules_user ON schedules (user_id);
CREATE INDEX IF NOT EXISTS ix_schedules_date ON schedules (date);

CREATE TABLE IF NOT EXISTS gaze_settings (
    id                    SERIAL PRIMARY KEY,
    user_id               INTEGER NOT NULL UNIQUE REFERENCES users(id),
    ear_threshold         DOUBLE PRECISION DEFAULT 0.18,
    eye_closure_threshold DOUBLE PRECISION DEFAULT 5.0,
    yaw_threshold         DOUBLE PRECISION DEFAULT 20.0,
    pitch_threshold       DOUBLE PRECISION DEFAULT 15.0,
    pose_lost_threshold   DOUBLE PRECISION DEFAULT 3.0,
    daze_variance_thr     DOUBLE PRECISION DEFAULT 300.0,
    daze_duration_sec     DOUBLE PRECISION DEFAULT 2.0,
    alpha_iris            DOUBLE PRECISION DEFAULT 0.85,
    center_ratio          DOUBLE PRECISION DEFAULT 0.50,
    h_left_threshold      DOUBLE PRECISION DEFAULT 0.20,
    h_right_threshold     DOUBLE PRECISION DEFAULT 0.80,
    v_up_threshold        DOUBLE PRECISION DEFAULT 0.38,
    v_down_threshold      DOUBLE PRECISION DEFAULT 0.62,
    gaze_lost_threshold   DOUBLE PRECISION DEFAULT 2.0,
    calibrated            INTEGER DEFAULT 0,
    updated_at            TIMESTAMP DEFAULT now()
);

CREATE TABLE IF NOT EXISTS study_sessions (
    id                 SERIAL PRIMARY KEY,
    user_id            INTEGER REFERENCES users(id),
    login_id           VARCHAR(64),
    date               VARCHAR(10) NOT NULL,
    start_time         TIMESTAMP,
    end_time           TIMESTAMP,
    total_time_seconds INTEGER,
    focus_time_seconds INTEGER,
    duration_min       INTEGER DEFAULT 0,
    focus_score        DOUBLE PRECISION DEFAULT 0.0,
    focused_min        INTEGER DEFAULT 0,
    dazed_min          INTEGER DEFAULT 0,
    distracted_min     INTEGER DEFAULT 0,
    created_at         TIMESTAMP DEFAULT now()
);
CREATE INDEX IF NOT EXISTS ix_sessions_user ON study_sessions (user_id);
CREATE INDEX IF NOT EXISTS ix_sessions_login ON study_sessions (login_id);
CREATE INDEX IF NOT EXISTS ix_sessions_date ON study_sessions (date);
