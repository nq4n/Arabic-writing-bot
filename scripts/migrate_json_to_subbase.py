"""Migrate JSON files in ./data into the subbase database.

Usage:
  python scripts/migrate_json_to_subbase.py

It will read `data/users.json`, `data/messages.json`, `data/submissions.json`, `data/ratings.json`
and insert into the subbase tables (users, messages, submissions, ratings).
"""
import os
import sys
import json
# make sure project root is on path
sys.path.append(os.path.dirname(os.path.dirname(__file__)))
from utils import subbase_adapter

DATA_DIR = os.path.join(os.path.dirname(__file__), '..', 'data')


def load_json(name):
    path = os.path.join(DATA_DIR, name)
    if not os.path.exists(path):
        return []
    with open(path, encoding='utf-8') as f:
        return json.load(f)


def transform_submission(s):
    # Map the existing submission JSON into DB columns, keep extra fields in meta
    base = {
        'id': s.get('id'),
        'student_id': s.get('student_id'),
        'text': s.get('text'),
        'ai_fixed_text': s.get('ai_fixed_text'),
        'ai_grade': s.get('ai_grade'),
        'created_at': s.get('created_at'),
    }
    meta_keys = set(s.keys()) - set(base.keys())
    meta = {k: s.get(k) for k in meta_keys}
    base['meta'] = meta
    return base


def transform_rating(r):
    base = {
        'id': r.get('id'),
        'submission_id': r.get('submission_id'),
        'student_id': r.get('student_id'),
        'rating_value': r.get('rating_value'),
        'feedback_type': r.get('feedback_type'),
        'created_at': r.get('created_at'),
    }
    meta_keys = set(r.keys()) - set(base.keys())
    base['meta'] = {k: r.get(k) for k in meta_keys}
    return base


def migrate():
    ok = subbase_adapter.ensure_tables()
    if not ok:
        print('Subbase not configured; set SUBBASE_PG_URL or SUBBASE_SQLITE_PATH')
        return

    users = load_json('users.json')
    messages = load_json('messages.json')
    submissions = load_json('submissions.json')
    ratings = load_json('ratings.json')

    # Overwrite users/messages/submissions/ratings in DB
    print(f'Migrating {len(users)} users...')
    subbase_adapter.overwrite_table('users', users)
    print(f'Migrating {len(messages)} messages...')
    subbase_adapter.overwrite_table('messages', messages)
    print(f'Migrating {len(submissions)} submissions...')
    subs = [transform_submission(s) for s in submissions]
    subbase_adapter.overwrite_table('submissions', subs)
    print(f'Migrating {len(ratings)} ratings...')
    rts = [transform_rating(r) for r in ratings]
    subbase_adapter.overwrite_table('ratings', rts)

    print('Migration complete.')


if __name__ == '__main__':
    migrate()
