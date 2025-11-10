import os
import json
import sqlite3
from urllib.parse import urlparse

try:
    import psycopg2
    import psycopg2.extras
except Exception:
    psycopg2 = None

SQL_DIR = os.path.join(os.path.dirname(__file__), '..', 'sql')


def _get_sqlite_conn(path):
    conn = sqlite3.connect(path, detect_types=sqlite3.PARSE_DECLTYPES | sqlite3.PARSE_COLNAMES)
    conn.row_factory = sqlite3.Row
    return conn


def _get_postgres_conn(dsn):
    if psycopg2 is None:
        raise RuntimeError('psycopg2 not installed')
    conn = psycopg2.connect(dsn)
    return conn


def get_conn_from_env():
    """Return a tuple (type, conn) where type is 'sqlite' or 'postgres', or (None, None)."""
    pg = os.getenv('SUBBASE_PG_URL')
    sqlite_path = os.getenv('SUBBASE_SQLITE_PATH')
    if pg:
        return 'postgres', _get_postgres_conn(pg)
    if sqlite_path:
        return 'sqlite', _get_sqlite_conn(sqlite_path)
    return None, None


def ensure_tables():
    typ, conn = get_conn_from_env()
    if not conn:
        return False
    cur = conn.cursor()
    if typ == 'sqlite':
        sql_file = os.path.join(SQL_DIR, 'subbase_schema.sql')
        with open(sql_file, encoding='utf-8') as f:
            s = f.read()
        cur.executescript(s)
        conn.commit()
    else:
        sql_file = os.path.join(SQL_DIR, 'subbase_schema_postgres.sql')
        with open(sql_file, encoding='utf-8') as f:
            s = f.read()
        cur.execute(s)
        conn.commit()
    cur.close()
    conn.close()
    return True


def read_table(table_name):
    typ, conn = get_conn_from_env()
    if not conn:
        return None
    rows = []
    if typ == 'sqlite':
        cur = conn.cursor()
        cur.execute(f'SELECT * FROM {table_name} ORDER BY id')
        rows = [dict(row) for row in cur.fetchall()]
        cur.close()
        conn.close()
    else:
        cur = conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor)
        cur.execute(f'SELECT * FROM {table_name} ORDER BY id')
        rows = cur.fetchall()
        cur.close()
        conn.close()

    # normalize: convert meta JSON string to objects when present
    for r in rows:
        if 'meta' in r and r['meta']:
            try:
                r['meta'] = json.loads(r['meta']) if isinstance(r['meta'], str) else r['meta']
            except Exception:
                r['meta'] = r['meta']
    return rows


def overwrite_table(table_name, records):
    """Replace the contents of table_name with given records (list of dicts).
    Assumes each record has an 'id' key for primary key.
    """
    typ, conn = get_conn_from_env()
    if not conn:
        return False
    cur = conn.cursor()
    if typ == 'sqlite':
        # delete all
        cur.execute(f'DELETE FROM {table_name}')
        # insert
        for r in records:
            cols = [k for k in r.keys() if k != 'meta']
            placeholders = ','.join('?' for _ in cols)
            cols_sql = ','.join(cols)
            values = [r[c] for c in cols]
            # handle meta
            meta = r.get('meta')
            if 'meta' in r:
                cols_sql += ',meta'
                placeholders += ',?'
                values.append(json.dumps(meta, ensure_ascii=False))
            cur.execute(f'INSERT INTO {table_name} ({cols_sql}) VALUES ({placeholders})', values)
        conn.commit()
        cur.close()
        conn.close()
        return True
    else:
        # Postgres: use jsonb for meta
        cur.execute(f'TRUNCATE TABLE {table_name} RESTART IDENTITY CASCADE')
        for r in records:
            cols = [k for k in r.keys() if k != 'meta']
            cols_sql = ','.join(cols)
            placeholders = ','.join(['%s'] * len(cols))
            values = [r[c] for c in cols]
            if 'meta' in r:
                cols_sql += ',meta'
                placeholders += ',%s'
                values.append(json.dumps(r.get('meta', {}), ensure_ascii=False))
            cur.execute(f'INSERT INTO {table_name} ({cols_sql}) VALUES ({placeholders})', values)
        conn.commit()
        cur.close()
        conn.close()
        return True


def append_record(table_name, record):
    typ, conn = get_conn_from_env()
    if not conn:
        return False
    cur = conn.cursor()
    if typ == 'sqlite':
        cols = list(record.keys())
        cols_sql = ','.join(cols)
        placeholders = ','.join('?' for _ in cols)
        values = [record[c] for c in cols]
        if 'meta' in record:
            # ensure meta stored as text
            idx = cols.index('meta')
            values[idx] = json.dumps(record['meta'], ensure_ascii=False)
        cur.execute(f'INSERT INTO {table_name} ({cols_sql}) VALUES ({placeholders})', values)
        conn.commit()
        cur.close()
        conn.close()
        return True
    else:
        cols = list(record.keys())
        cols_sql = ','.join(cols)
        placeholders = ','.join(['%s'] * len(cols))
        values = [record[c] for c in cols]
        if 'meta' in record:
            idx = cols.index('meta')
            values[idx] = json.dumps(record['meta'], ensure_ascii=False)
        cur.execute(f'INSERT INTO {table_name} ({cols_sql}) VALUES ({placeholders})', values)
        conn.commit()
        cur.close()
        conn.close()
        return True
