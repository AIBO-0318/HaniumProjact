"""
DB 통합 마이그레이션 스크립트
- 불필요 테이블 삭제
- study_sessions 컬럼 확장 (desktop 앱 연동)
- study_log 데이터 이전 후 삭제
"""
import psycopg2

conn = psycopg2.connect(host='localhost', dbname='istudy', user='postgres', password='aisw2026')
conn.autocommit = False
cur = conn.cursor()

try:
    print("1. 불필요한 테이블 삭제...")
    cur.execute("DROP TABLE IF EXISTS gaze_calibration")
    cur.execute("DROP TABLE IF EXISTS gaze_data")
    cur.execute("DROP TABLE IF EXISTS block_list")
    print("   ✓ gaze_calibration, gaze_data, block_list 삭제")

    print("2. study_sessions 컬럼 확장...")
    cur.execute("ALTER TABLE study_sessions ALTER COLUMN user_id DROP NOT NULL")
    cur.execute("ALTER TABLE study_sessions ADD COLUMN IF NOT EXISTS login_id VARCHAR(64)")
    cur.execute("ALTER TABLE study_sessions ADD COLUMN IF NOT EXISTS start_time TIMESTAMP")
    cur.execute("ALTER TABLE study_sessions ADD COLUMN IF NOT EXISTS end_time TIMESTAMP")
    cur.execute("ALTER TABLE study_sessions ADD COLUMN IF NOT EXISTS total_time_seconds INTEGER")
    cur.execute("ALTER TABLE study_sessions ADD COLUMN IF NOT EXISTS focus_time_seconds INTEGER")
    print("   ✓ login_id, start_time, end_time, total_time_seconds, focus_time_seconds 추가")
    print("   ✓ user_id nullable로 변경")

    print("3. study_log → study_sessions 데이터 이전...")
    cur.execute("""
        INSERT INTO study_sessions
            (login_id, date, start_time, end_time,
             total_time_seconds, focus_time_seconds,
             duration_min, focus_score, created_at)
        SELECT
            NULL,
            study_date::TEXT,
            start_time,
            end_time,
            total_time_seconds,
            focus_time_seconds,
            GREATEST(1, total_time_seconds / 60),
            COALESCE(focus_score, 0.0),
            created_at
        FROM study_log
    """)
    migrated = cur.rowcount
    print(f"   ✓ {migrated}건 이전 완료")

    print("4. study_log 테이블 삭제...")
    cur.execute("DROP TABLE study_log")
    print("   ✓ study_log 삭제")

    conn.commit()
    print("\n✅ 마이그레이션 완료!")

except Exception as e:
    conn.rollback()
    print(f"\n❌ 오류 발생, 롤백: {e}")
    raise
finally:
    cur.close()
    conn.close()
