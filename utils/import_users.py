import csv
import io
import os
from werkzeug.security import generate_password_hash

try:
    import openpyxl
except Exception:
    openpyxl = None


def parse_csv_stream(stream):
    """Parse a CSV stream (file-like) and return list of dicts with username and password.
    Expected columns: username, password, role (optional)
    """
    # Ensure stream is at start
    try:
        stream.seek(0)
    except Exception:
        pass
    text = stream.read()
    if isinstance(text, bytes):
        text = text.decode('utf-8')
    reader = csv.DictReader(io.StringIO(text))
    users = []
    for row in reader:
        username = (row.get('username') or row.get('user') or '').strip()
        password = (row.get('password') or row.get('pass') or '').strip()
        role = (row.get('role') or 'student').strip() or 'student'
        if not username or not password:
            continue
        users.append({
            'username': username,
            'password_hash': generate_password_hash(password),
            'role': role
        })
    return users


def parse_xlsx_stream(stream):
    """Parse an XLSX stream using openpyxl and return similar list of dicts.
    Expects headers in the first row: username, password, role (optional)
    """
    if openpyxl is None:
        return []
    try:
        stream.seek(0)
    except Exception:
        pass
    wb = openpyxl.load_workbook(stream, read_only=True)
    ws = wb.active
    rows = list(ws.iter_rows(values_only=True))
    if not rows:
        return []
    headers = [str(h).strip().lower() for h in rows[0]]
    users = []
    for row in rows[1:]:
        data = {headers[i]: (row[i] or '') for i in range(len(headers))}
        username = (data.get('username') or data.get('user') or '').strip()
        password = (data.get('password') or data.get('pass') or '').strip()
        role = (data.get('role') or 'student').strip() or 'student'
        if not username or not password:
            continue
        users.append({
            'username': username,
            'password_hash': generate_password_hash(password),
            'role': role
        })
    return users


def import_users_from_file_storage(file_storage):
    """Accepts a Flask FileStorage object and returns list of parsed users.
    Supports CSV and XLSX.
    """
    filename = getattr(file_storage, 'filename', '') or ''
    lower = filename.lower()
    # Reset stream if possible
    try:
        file_storage.stream.seek(0)
    except Exception:
        pass
    if lower.endswith('.csv'):
        return parse_csv_stream(file_storage.stream)
    if lower.endswith('.xlsx') or lower.endswith('.xlsm'):
        return parse_xlsx_stream(file_storage.stream)

    # Try CSV fallback
    try:
        return parse_csv_stream(file_storage.stream)
    except Exception:
        return []
