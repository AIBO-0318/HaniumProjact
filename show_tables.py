import psycopg2

conn = psycopg2.connect(host='localhost', dbname='istudy', user='postgres', password='aisw2026')
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
