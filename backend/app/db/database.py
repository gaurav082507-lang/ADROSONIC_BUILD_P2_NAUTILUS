import sqlite3
import os

DB_PATH = os.path.join(os.path.dirname(__file__), "../../../data/runtime/lucen.db")

def get_db_path():
    return DB_PATH

def get_connection():
    """Return a SQLite connection with WAL mode enabled."""
    os.makedirs(os.path.dirname(DB_PATH), exist_ok=True)
    conn = sqlite3.connect(DB_PATH, timeout=5.0, isolation_level=None)
    conn.execute('PRAGMA journal_mode=WAL')
    conn.execute('PRAGMA busy_timeout=5000')
    conn.row_factory = sqlite3.Row
    return conn

from contextlib import contextmanager

@contextmanager
def get_db():
    conn = get_connection()
    try:
        yield conn
    finally:
        conn.close()
