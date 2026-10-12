"""
I-Study DB 초기 구성 (최초 1회)

- .env 의 접속 정보로 PostgreSQL 에 접속해 DB(DB_NAME)가 없으면 만들고
- backend_spring/src/main/resources/schema.sql 로 테이블을 만든다.
- 이미 있는 DB·테이블은 건드리지 않으므로 여러 번 실행해도 안전하다.

사용:
    venv\\Scripts\\python.exe init_db.py
"""
import os
import sys

import psycopg2
from psycopg2 import sql

ROOT = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, ROOT)
from shared.env_config import DB_HOST, DB_PORT, DB_NAME, DB_USER, DB_PASSWORD  # noqa: E402

SCHEMA = os.path.join(ROOT, "backend_spring", "src", "main", "resources", "schema.sql")


def main():
    if not os.path.exists(os.path.join(ROOT, ".env")):
        sys.exit("[오류] .env 파일이 없습니다. .env.example 을 .env 로 복사하고 DB_PASSWORD 를 채우세요.")

    conn_info = dict(host=DB_HOST, port=DB_PORT, user=DB_USER, password=DB_PASSWORD)
    try:
        conn = psycopg2.connect(dbname="postgres", **conn_info)
    except psycopg2.OperationalError as e:
        sys.exit(f"[오류] PostgreSQL 에 접속하지 못했습니다. 서비스가 켜져 있는지, "
                 f".env 의 DB_PASSWORD 가 맞는지 확인하세요.\n{e}")
    conn.autocommit = True
    with conn.cursor() as cur:
        cur.execute("SELECT 1 FROM pg_database WHERE datname = %s", (DB_NAME,))
        if cur.fetchone():
            print(f"DB '{DB_NAME}' 이미 있음")
        else:
            cur.execute(sql.SQL("CREATE DATABASE {}").format(sql.Identifier(DB_NAME)))
            print(f"DB '{DB_NAME}' 생성")
    conn.close()

    with open(SCHEMA, encoding="utf-8") as f:
        ddl = f.read()
    conn = psycopg2.connect(dbname=DB_NAME, **conn_info)
    with conn, conn.cursor() as cur:
        cur.execute(ddl)
        cur.execute("SELECT table_name FROM information_schema.tables "
                    "WHERE table_schema = 'public' ORDER BY table_name")
        tables = [r[0] for r in cur.fetchall()]
    conn.close()
    print(f"테이블 {len(tables)}개: {', '.join(tables)}")
    print("완료. 이제 run_all.bat 으로 서버를 실행하세요.")


if __name__ == "__main__":
    main()
