"""Initialize subbase database (SQLite or Postgres) using env variables.

Usage:
  python scripts/init_subbase.py

Reads SUBBASE_PG_URL or SUBBASE_SQLITE_PATH from environment and runs the
appropriate SQL file from the `sql/` directory.
"""
import os
import sys
# ensure project root on sys.path for imports
sys.path.append(os.path.dirname(os.path.dirname(__file__)))

SQL_DIR = os.path.join(os.path.dirname(__file__), '..', 'sql')

def init_sqlite(path):
    import sqlite3
    sql_file = os.path.join(SQL_DIR, 'subbase_schema.sql')
    if not os.path.exists(sql_file):
        print('SQLite schema file not found:', sql_file)
        return 1
    with open(sql_file, encoding='utf-8') as f:
        s = f.read()
    conn = sqlite3.connect(path)
    conn.executescript(s)
    conn.commit()
    conn.close()
    print('Initialized SQLite DB at', path)
    return 0

def init_postgres(url):
    try:
        import psycopg2
    except Exception as e:
        print('psycopg2 is required to initialize Postgres:', e)
        return 2
    sql_file = os.path.join(SQL_DIR, 'subbase_schema_postgres.sql')
    if not os.path.exists(sql_file):
        print('Postgres schema file not found:', sql_file)
        return 1
    with open(sql_file, encoding='utf-8') as f:
        s = f.read()
    conn = psycopg2.connect(url)
    conn.autocommit = True
    cur = conn.cursor()
    cur.execute(s)
    cur.close()
    conn.close()
    print('Initialized Postgres DB via', url)
    return 0

def main():
    pg = os.getenv('SUBBASE_PG_URL')
    sqlite_path = os.getenv('SUBBASE_SQLITE_PATH')
    if pg:
        return init_postgres(pg)
    if sqlite_path:
        return init_sqlite(sqlite_path)
    print('No SUBBASE_PG_URL or SUBBASE_SQLITE_PATH set in environment.')
    return 3

if __name__ == '__main__':
    sys.exit(main())
