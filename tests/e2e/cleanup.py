"""
E2E 테스트 데이터 정리 — qa_e2e_ 접두사 계정과 그 계정이 만든 데이터만 삭제한다.

실행: venv\\Scripts\\python.exe tests\\e2e\\cleanup.py          (삭제 대상만 출력)
      venv\\Scripts\\python.exe tests\\e2e\\cleanup.py --apply  (실제 삭제)
"""

import os
import sys

import psycopg2

DB = dict(host="localhost", port=5432, dbname="istudy", user="postgres",
          password=os.getenv("DB_PASSWORD", "aisw2026"))
PREFIX = r"qa\_e2e\_%"

DEPENDENT = ["study_sessions", "schedules", "gaze_settings", "whitelist_urls"]


def main(apply: bool):
    sys.stdout.reconfigure(encoding="utf-8")
    with psycopg2.connect(**DB) as c, c.cursor() as cur:
        cur.execute("select id, login_id, role from users where login_id like %s order by id", (PREFIX,))
        users = cur.fetchall()
        ids = [u[0] for u in users] or [-1]
        cur.execute("select id, admin_id from admins where admin_id like %s order by id", (PREFIX,))
        admins = cur.fetchall()
        print("users :", users)
        print("admins:", admins)
        for t in DEPENDENT:
            cur.execute(f"select count(*) from {t} where user_id = any(%s)", (ids,))
            print(f"{t:<15}: {cur.fetchone()[0]} rows")
        cur.execute("select count(*) from whitelist_urls where user_id is null and url like %s", ("https://qa-%",))
        print(f"{'legacy wl(qa-*)':<15}: {cur.fetchone()[0]} rows")
        cur.execute("select count(*) from head_pose_data where student_id like %s", (PREFIX,))
        print(f"{'head_pose_data':<15}: {cur.fetchone()[0]} rows")

        if not apply:
            print("\n(dry-run) --apply 로 실행하면 위 항목을 삭제합니다.")
            return
        for t in DEPENDENT:
            cur.execute(f"delete from {t} where user_id = any(%s)", (ids,))
        cur.execute("delete from whitelist_urls where user_id is null and url like %s", ("https://qa-%",))
        cur.execute("delete from head_pose_data where student_id like %s", (PREFIX,))
        cur.execute("update users set teacher_id = null where teacher_id = any(%s)", (ids,))
        cur.execute("delete from users where id = any(%s)", (ids,))
        cur.execute("delete from admins where admin_id like %s", (PREFIX,))
        c.commit()
        print("\n삭제 완료.")


if __name__ == "__main__":
    main("--apply" in sys.argv)
