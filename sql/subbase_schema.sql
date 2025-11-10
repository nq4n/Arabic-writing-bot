-- SQLite schema for subbase
PRAGMA foreign_keys = ON;

CREATE TABLE IF NOT EXISTS users (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  username TEXT NOT NULL UNIQUE,
  password_hash TEXT,
  role TEXT DEFAULT 'student'
);

CREATE TABLE IF NOT EXISTS messages (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  user_id INTEGER,
  content TEXT,
  created_at TEXT,
  FOREIGN KEY(user_id) REFERENCES users(id) ON DELETE SET NULL
);

CREATE TABLE IF NOT EXISTS submissions (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  student_id INTEGER,
  text TEXT,
  ai_fixed_text TEXT,
  ai_grade REAL,
  ai_response TEXT,
  meta TEXT,
  created_at TEXT,
  FOREIGN KEY(student_id) REFERENCES users(id) ON DELETE SET NULL
);

CREATE TABLE IF NOT EXISTS ratings (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  submission_id INTEGER,
  user_id INTEGER,
  value REAL,
  feedback_type TEXT,
  meta TEXT,
  created_at TEXT,
  FOREIGN KEY(submission_id) REFERENCES submissions(id) ON DELETE CASCADE,
  FOREIGN KEY(user_id) REFERENCES users(id) ON DELETE SET NULL
);

-- Simple indexes
CREATE INDEX IF NOT EXISTS idx_submissions_student ON submissions(student_id);
CREATE INDEX IF NOT EXISTS idx_messages_user ON messages(user_id);
