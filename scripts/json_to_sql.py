#!/usr/bin/env python3
"""Generate SQL INSERT statements from data/*.json for SQLite or Postgres.

Usage:
  python scripts/json_to_sql.py --db sqlite   # generates SQL files for sqlite
  python scripts/json_to_sql.py --db postgres # generates SQL files for postgres

Output: files written to sql/imports/*.sql

Notes:
- Extra fields not present in the target table columns are stored in `meta` (TEXT for sqlite, JSONB for postgres).
- IDs and numeric values are preserved; strings are safely quoted.
"""
import os
import sys
import json
import argparse

ROOT = os.path.dirname(os.path.dirname(__file__))
DATA_DIR = os.path.join(ROOT, 'data')
OUT_DIR = os.path.join(ROOT, 'sql', 'imports')
os.makedirs(OUT_DIR, exist_ok=True)

# Known schema columns for each table. meta may be added to hold extras.
SCHEMA = {
    'users': ['id', 'username', 'password_hash', 'role', 'meta'],
    'messages': ['id', 'user_id', 'content', 'created_at', 'meta'],
    'submissions': ['id', 'student_id', 'text', 'ai_fixed_text', 'ai_grade', 'created_at', 'meta'],
    'ratings': ['id', 'submission_id', 'student_id', 'rating_value', 'feedback_type', 'created_at', 'meta'],
}


def quote_sql(value, dbtype='sqlite'):
    """Return SQL literal for value depending on dbtype.
    dbtype: 'sqlite' or 'postgres'
    """
    if value is None:
        return 'NULL'
    if isinstance(value, bool):
        return '1' if value and dbtype == 'sqlite' else ('TRUE' if value else 'FALSE') if dbtype == 'postgres' else '1' if value else '0'
    if isinstance(value, (int, float)):
        return str(value)
    # For other types, convert to JSON-friendly string
    s = str(value)
    # escape single quotes by doubling
    s = s.replace("'", "''")
    # For postgres, we'll often want to cast meta to jsonb separately
    return f"'{s}'"


def build_row(record, table, dbtype='sqlite'):
    cols = []
    vals = []
    schema_cols = SCHEMA[table][:]
    # collect extras into meta
    meta = {}
    for k, v in record.items():
        if k in schema_cols and k != 'meta':
            cols.append(k)
            vals.append(v)
        else:
            # treat as meta
            meta[k] = v

    # if meta has nothing, still include meta=NULL for uniform inserts
    if 'meta' in schema_cols:
        cols.append('meta')
        if meta:
            meta_json = json.dumps(meta, ensure_ascii=False)
            if dbtype == 'postgres':
                # quote and cast to jsonb
                vals.append({'__meta__': meta_json})
            else:
                vals.append(meta_json)
        else:
            vals.append(None)

    return cols, vals


def generate_inserts(table, records, dbtype='sqlite'):
    out_lines = []
    for rec in records:
        cols, vals = build_row(rec, table, dbtype=dbtype)
        col_sql = ','.join(cols)
        val_literals = []
        for v in vals:
            if isinstance(v, dict) and '__meta__' in v:
                # postgres meta marker
                meta_s = v['__meta__'].replace("'", "''")
                val_literals.append(f"'{meta_s}'::jsonb")
            else:
                val_literals.append(quote_sql(v, dbtype=dbtype))
        vals_sql = ','.join(val_literals)
        out_lines.append(f'INSERT INTO {table} ({col_sql}) VALUES ({vals_sql});')
    return out_lines


def load_json_file(fname):
    p = os.path.join(DATA_DIR, fname)
    if not os.path.exists(p):
        return []
    with open(p, encoding='utf-8') as f:
        return json.load(f)


def write_file(path, lines):
    with open(path, 'w', encoding='utf-8') as f:
        f.write('\n'.join(lines))
    print('Wrote', path)


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--db', choices=['sqlite', 'postgres'], default='sqlite')
    args = parser.parse_args()

    dbtype = args.db

    mapping = {
        'users.json': 'users',
        'messages.json': 'messages',
        'submissions.json': 'submissions',
        'ratings.json': 'ratings',
    }

    for jf, table in mapping.items():
        records = load_json_file(jf)
        if not records:
            print('No records for', jf)
            continue
        inserts = generate_inserts(table, records, dbtype=dbtype)
        out_path = os.path.join(OUT_DIR, f'insert_{table}_{dbtype}.sql')
        # add header
        header = [f'-- Inserts for {table} generated from data/{jf} (db={dbtype})']
        write_file(out_path, header + inserts)


if __name__ == '__main__':
    main()
