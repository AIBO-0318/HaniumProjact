"""
I-Study - Database Module
PostgreSQL 데이터베이스 관리 클래스
"""

import psycopg2
from psycopg2.extras import RealDictCursor
from datetime import datetime
from typing import List, Tuple, Optional

DATABASE_URL = "postgresql://postgres:aisw2026@localhost:5432/istudy"


def _ensure_database_exists():
    """istudy 데이터베이스가 없으면 자동 생성"""
    try:
        conn = psycopg2.connect(
            host="localhost", port=5432,
            user="postgres", password="aisw2026",
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
                CREATE TABLE IF NOT EXISTS study_log (
                    id SERIAL PRIMARY KEY,
                    study_date DATE NOT NULL,
                    start_time TIMESTAMP NOT NULL,
                    end_time TIMESTAMP NOT NULL,
                    total_time_seconds INTEGER NOT NULL,
                    focus_time_seconds INTEGER NOT NULL,
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
        focus_time_seconds: int
    ) -> int:
        with self.conn.cursor() as cur:
            cur.execute(
                '''INSERT INTO study_log 
                   (study_date, start_time, end_time, total_time_seconds, focus_time_seconds)
                   VALUES (%s, %s, %s, %s, %s)
                   RETURNING id''',
                (
                    start_time.date().isoformat(),
                    start_time.isoformat(),
                    end_time.isoformat(),
                    total_time_seconds,
                    focus_time_seconds
                )
            )
            row_id = cur.fetchone()[0]
        self.conn.commit()
        return row_id
    
    def get_study_logs(self, limit: int = 30) -> List[dict]:
        with self.conn.cursor(cursor_factory=RealDictCursor) as cur:
            cur.execute(
                '''SELECT id, study_date::TEXT as study_date, start_time, end_time, 
                          total_time_seconds, focus_time_seconds, created_at
                   FROM study_log 
                   ORDER BY created_at DESC 
                   LIMIT %s''',
                (limit,)
            )
            return [dict(row) for row in cur.fetchall()]
    
    def get_today_total_focus_time(self) -> int:
        with self.conn.cursor(cursor_factory=RealDictCursor) as cur:
            cur.execute(
                "SELECT COALESCE(SUM(focus_time_seconds), 0) as total FROM study_log WHERE study_date = CURRENT_DATE"
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
