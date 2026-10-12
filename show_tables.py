import psycopg2

from shared.env_config import DB_HOST, DB_PORT, DB_NAME, DB_USER, DB_PASSWORD

conn = psycopg2.connect(host=DB_HOST, port=DB_PORT, dbname=DB_NAME, user=DB_USER, password=DB_PASSWORD)
cur = conn.cursor()

cur.execute("SELECT table_name FROM information_schema.tables WHERE table_schema='public' ORDER BY table_name")
tables = [r[0] for r in cur.fetchall()]

for t in tables:
    cur.execute("SELECT column_name, data_type, is_nullable FROM information_schema.columns WHERE table_name=%s ORDER BY ordinal_position", (t,))
    cols = cur.fetchall()
    cur.execute(f"SELECT COUNT(*) FROM {t}")
    cnt = cur.fetchone()[0]
    print(f"\n┌─ {t}  ({cnt}건)")
    for c in cols:
        nullable = "" if c[2] == "YES" else " NOT NULL"
        print(f"│  {c[0]:<28} {c[1]}{nullable}")

conn.close()
