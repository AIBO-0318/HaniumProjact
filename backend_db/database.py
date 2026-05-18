"""
I-Study Beta - Server Database
FastAPI 서버용 SQLAlchemy DB 연결
"""

import os
import sys
import psycopg2
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, declarative_base

try:
    _project_root = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..")
    if _project_root not in sys.path:
        sys.path.insert(0, _project_root)
    from shared.env_config import DATABASE_URL, DB_HOST, DB_PORT, DB_USER, DB_PASSWORD, DB_NAME
except ImportError:
    # 클라우드 환경 (Render 등) - 환경변수에서 직접 읽기
    DB_HOST = os.getenv("DB_HOST", "localhost")
    DB_PORT = os.getenv("DB_PORT", "5432")
    DB_USER = os.getenv("DB_USER", "postgres")
    DB_PASSWORD = os.getenv("DB_PASSWORD", "")
    DB_NAME = os.getenv("DB_NAME", "istudy")
    DATABASE_URL = os.getenv(
        "DATABASE_URL",
        f"postgresql://{DB_USER}:{DB_PASSWORD}@{DB_HOST}:{DB_PORT}/{DB_NAME}"
    )

Base = declarative_base()


def ensure_database():
    """istudy DB가 없으면 자동 생성"""
    try:
        conn = psycopg2.connect(
            host=DB_HOST, port=int(DB_PORT),
            user=DB_USER, password=DB_PASSWORD,
            dbname="postgres"
        )
        conn.autocommit = True
        cur = conn.cursor()
        cur.execute("SELECT 1 FROM pg_database WHERE datname = %s", (DB_NAME,))
        if not cur.fetchone():
            cur.execute(f'CREATE DATABASE "{DB_NAME}"')
        cur.close()
        conn.close()
    except Exception:
        pass


ensure_database()

# Render.com은 postgres:// 로 제공 → SQLAlchemy는 postgresql:// 필요
_db_url = DATABASE_URL.replace("postgres://", "postgresql://", 1)
engine = create_engine(_db_url)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)


def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
