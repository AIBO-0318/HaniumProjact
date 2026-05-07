"""
I-Study Beta - Server Database
FastAPI 서버용 SQLAlchemy DB 연결
"""

import psycopg2
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, declarative_base

DATABASE_URL = "postgresql://postgres:aisw2026@localhost:5432/istudy"

Base = declarative_base()


def ensure_database():
    """istudy DB가 없으면 자동 생성"""
    try:
        conn = psycopg2.connect(
            host="localhost", port=5432,
            user="postgres", password="aisw2026",
            dbname="postgres"
        )
        conn.autocommit = True
        cur = conn.cursor()
        cur.execute("SELECT 1 FROM pg_database WHERE datname = 'istudy'")
        if not cur.fetchone():
            cur.execute("CREATE DATABASE istudy")
        cur.close()
        conn.close()
    except Exception:
        pass


ensure_database()

engine = create_engine(DATABASE_URL)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)


def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
