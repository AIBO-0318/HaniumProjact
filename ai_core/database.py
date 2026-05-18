"""
I-Study - Database Module
PostgreSQL 데이터베이스 관리 클래스
"""

import os
import sys
import psycopg2
from psycopg2.extras import RealDictCursor
from datetime import datetime
from typing import List, Tuple, Optional

# 프로젝트 루트를 path에 추가
_project_root = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..")
if _project_root not in sys.path:
    sys.path.insert(0, _project_root)

from shared.env_config import DATABASE_URL, DB_HOST, DB_PORT, DB_USER, DB_PASSWORD, DB_NAME


def _ensure_database_exists():
    """istudy 데이터베이스가 없으면 자동 생성"""
    try:
        conn = psycopg2.connect(
            host=DB_HOST, port=int(DB_PORT),
            user=DB_USER, password=DB_PASSWORD,
            dbname="postgres"
        )
        conn.autocommit = True
        with conn.cursor() as cur:
            cur.execute("SELECT 1 FROM pg_database WHERE datname = 'istudy'")
            if not cur.fetchone():
                cur.execute("CREATE DATABASE istudy")
        conn.close()
    except Exception:
        pass


class FocusDatabase:
    """I-Study 데이터베이스 관리 클래스"""
    
    def __init__(self, dsn: str = None):
        self.dsn = dsn or DATABASE_URL
        self.conn = None
        _ensure_database_exists()
        self._connect()
        self._create_tables()
    
    def _connect(self):
        self.conn = psycopg2.connect(self.dsn)
    
    def _create_tables(self):
        with self.conn.cursor() as cur:
            cur.execute('''
                CREATE TABLE IF NOT EXISTS study_sessions (
                    id SERIAL PRIMARY KEY,
                    user_id INTEGER,
                    login_id VARCHAR(64),
                    date VARCHAR(10) NOT NULL,
                    start_time TIMESTAMP,
                    end_time TIMESTAMP,
                    total_time_seconds INTEGER,
                    focus_time_seconds INTEGER,
                    duration_min INTEGER DEFAULT 0,
                    focus_score REAL DEFAULT 0.0,
                    focused_min INTEGER DEFAULT 0,
                    dazed_min INTEGER DEFAULT 0,
                    distracted_min INTEGER DEFAULT 0,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            ''')

            cur.execute('''
                CREATE TABLE IF NOT EXISTS whitelist_urls (
                    id SERIAL PRIMARY KEY,
                    name TEXT NOT NULL,
                    url TEXT NOT NULL UNIQUE,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            ''')

        self.conn.commit()
        self._initialize_default_whitelist()
    
    def _initialize_default_whitelist(self):
        default_sites = [
            ("EBSI", "https://www.ebsi.co.kr/ebs/pot/poti/main.ebs"),
            ("네이버 사전", "https://dict.naver.com/"),
            ("대성 마이맥", "https://www.mimacstudy.com/main/main.ds"),
            ("메가 스터디", "https://www.megastudy.net/"),
            ("이투스", "https://www.etoos.com/home/default.asp"),
            ("ChatGPT", "https://chatgpt.com/"),
            ("Gemini", "https://gemini.google.com/u/1/app?hl=ko")
        ]
        
        with self.conn.cursor(cursor_factory=RealDictCursor) as cur:
            cur.execute("SELECT url FROM whitelist_urls")
            existing_urls = {row['url'] for row in cur.fetchall()}
            
            for name, url in default_sites:
                if url not in existing_urls:
                    cur.execute(
                        "INSERT INTO whitelist_urls (name, url) VALUES (%s, %s) ON CONFLICT (url) DO NOTHING",
                        (name, url)
                    )
        
        self.conn.commit()
    
    def reset_whitelist_to_default(self):
        default_sites = [
            ("EBSI", "https://www.ebsi.co.kr/ebs/pot/poti/main.ebs"),
            ("네이버 사전", "https://dict.naver.com/"),
            ("대성 마이맥", "https://www.mimacstudy.com/main/main.ds"),
            ("메가 스터디", "https://www.megastudy.net/"),
            ("이투스", "https://www.etoos.com/home/default.asp"),
            ("ChatGPT", "https://chatgpt.com/"),
            ("Gemini", "https://gemini.google.com/u/1/app?hl=ko")
        ]
        
        with self.conn.cursor() as cur:
            cur.execute("DELETE FROM whitelist_urls")
            for name, url in default_sites:
                cur.execute(
                    "INSERT INTO whitelist_urls (name, url) VALUES (%s, %s)",
                    (name, url)
                )
        
        self.conn.commit()
        return True
    
    def save_study_log(
        self,
        start_time: datetime,
        end_time: datetime,
        total_time_seconds: int,
        focus_time_seconds: int,
        login_id: str = None,
        focus_score: float = None,
        focused_min: int = 0,
        dazed_min: int = 0,
        distracted_min: int = 0,
    ) -> int:
        duration_min = max(1, total_time_seconds // 60)
        if focus_score is None:
            focus_score = round(focus_time_seconds / total_time_seconds * 100, 1) if total_time_seconds > 0 else 0.0
        with self.conn.cursor() as cur:
            cur.execute(
                '''INSERT INTO study_sessions
                   (login_id, date, start_time, end_time,
                    total_time_seconds, focus_time_seconds,
                    duration_min, focus_score, focused_min, dazed_min, distracted_min)
                   VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
                   RETURNING id''',
                (
                    login_id,
                    start_time.date().isoformat(),
                    start_time,
                    end_time,
                    total_time_seconds,
                    focus_time_seconds,
                    duration_min,
                    focus_score,
                    focused_min,
                    dazed_min,
                    distracted_min,
                )
            )
            row_id = cur.fetchone()[0]
        self.conn.commit()
        return row_id
    
    def get_study_logs(self, limit: int = 30, login_id: str = None) -> List[dict]:
        with self.conn.cursor(cursor_factory=RealDictCursor) as cur:
            if login_id:
                cur.execute(
                    '''SELECT id, date as study_date, start_time, end_time,
                              total_time_seconds, focus_time_seconds,
                              duration_min, focus_score, created_at
                       FROM study_sessions
                       WHERE login_id = %s
                       ORDER BY created_at DESC LIMIT %s''',
                    (login_id, limit)
                )
            else:
                cur.execute(
                    '''SELECT id, date as study_date, start_time, end_time,
                              total_time_seconds, focus_time_seconds,
                              duration_min, focus_score, created_at
                       FROM study_sessions
                       ORDER BY created_at DESC LIMIT %s''',
                    (limit,)
                )
            return [dict(row) for row in cur.fetchall()]
    
    def get_today_total_focus_time(self, login_id: str = None) -> int:
        with self.conn.cursor(cursor_factory=RealDictCursor) as cur:
            if login_id:
                cur.execute(
                    "SELECT COALESCE(SUM(focus_time_seconds), 0) as total FROM study_sessions WHERE date = CURRENT_DATE::TEXT AND login_id = %s",
                    (login_id,)
                )
            else:
                cur.execute(
                    "SELECT COALESCE(SUM(focus_time_seconds), 0) as total FROM study_sessions WHERE date = CURRENT_DATE::TEXT"
                )
            result = cur.fetchone()
            return result['total']
    
    def add_whitelist_url(self, name: str, url: str) -> bool:
        try:
            with self.conn.cursor() as cur:
                cur.execute(
                    "INSERT INTO whitelist_urls (name, url) VALUES (%s, %s) ON CONFLICT (url) DO NOTHING",
                    (name.strip(), url.strip())
                )
                inserted = cur.rowcount > 0
            self.conn.commit()
            return inserted
        except Exception:
            self.conn.rollback()
            return False
    
    def remove_whitelist_url(self, url_id: int) -> bool:
        with self.conn.cursor() as cur:
            cur.execute("DELETE FROM whitelist_urls WHERE id = %s", (url_id,))
            deleted = cur.rowcount > 0
        self.conn.commit()
        return deleted
    
    def get_all_whitelist_urls(self) -> List[Tuple[int, str, str]]:
        with self.conn.cursor(cursor_factory=RealDictCursor) as cur:
            cur.execute("SELECT id, name, url FROM whitelist_urls ORDER BY created_at DESC")
            return [(row['id'], row['name'], row['url']) for row in cur.fetchall()]
    
    def close(self):
        if self.conn:
            self.conn.close()
            self.conn = None
    
    def __enter__(self):
        return self
    
    def __exit__(self, exc_type, exc_val, exc_tb):
        self.close()
