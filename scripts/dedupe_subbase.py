"""Deduplicate users in the subbase DB.

This script finds users with the same username, keeps the row with the smallest id,
re-assigns foreign keys in messages, submissions, and ratings to the kept id,
and deletes the duplicate user rows.

Usage:
  python scripts/dedupe_subbase.py

It uses the same SUBBASE env vars as the app (SUBBASE_BACKEND, SUBBASE_SQLITE_PATH, SUBBASE_PG_URL).
Be sure to BACKUP your DB before running this.
"""
import os
import sys
from utils.subbase_adapter import get_conn_from_env


def dedupe_sqlite(conn):
    cur = conn.cursor()
    # Find duplicate usernames
    cur.execute("SELECT username, GROUP_CONCAT(id) as ids, MIN(id) as keep_id FROM users GROUP BY username HAVING COUNT(*)>1")
    rows = cur.fetchall()
    for username, ids_csv, keep_id in rows:
        ids = [int(x) for x in ids_csv.split(',') if int(x) != keep_id]
        print(f"Consolidating username={username}, keep={keep_id}, remove={ids}")
        for rid in ids:
            # update messages
            cur.execute('UPDATE messages SET user_id = ? WHERE user_id = ?', (keep_id, rid))
            # update submissions.student_id
            cur.execute('UPDATE submissions SET student_id = ? WHERE student_id = ?', (keep_id, rid))
            # update ratings.user_id
            cur.execute('UPDATE ratings SET user_id = ? WHERE user_id = ?', (keep_id, rid))
            # delete duplicate user
            cur.execute('DELETE FROM users WHERE id = ?', (rid,))
    conn.commit()


def dedupe_postgres(conn):
    cur = conn.cursor()
    cur.execute("SELECT username, array_agg(id) as ids, min(id) as keep_id FROM users GROUP BY username HAVING count(*)>1")
    rows = cur.fetchall()
    for username, ids_arr, keep_id in rows:
        ids = [i for i in ids_arr if i != keep_id]
        print(f"Consolidating username={username}, keep={keep_id}, remove={ids}")
        for rid in ids:
            cur.execute('UPDATE messages SET user_id = %s WHERE user_id = %s', (keep_id, rid))
            cur.execute('UPDATE submissions SET student_id = %s WHERE student_id = %s', (keep_id, rid))
            cur.execute('UPDATE ratings SET user_id = %s WHERE user_id = %s', (keep_id, rid))
            cur.execute('DELETE FROM users WHERE id = %s', (rid,))
    conn.commit()


def main():
    typ, conn = get_conn_from_env()
    if not conn:
        print('Subbase is not configured. Set SUBBASE_SQLITE_PATH or SUBBASE_PG_URL in .env')
        sys.exit(1)

    try:
        if typ == 'sqlite':
            dedupe_sqlite(conn)
        else:
            dedupe_postgres(conn)
        print('Deduplication completed.')
    finally:
        try:
            conn.close()
        except Exception:
            pass


if __name__ == '__main__':
    print('WARNING: Make a backup of your database before running this script!')
    confirm = input('Run dedupe now? (yes/no): ').strip().lower()
    if confirm in ('y','yes'):
        main()
    else:
        print('Aborted.')
