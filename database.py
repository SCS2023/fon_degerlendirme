import sqlite3
import hashlib
import os
from pathlib import Path

DB_DIR = Path("data")
DB_DIR.mkdir(exist_ok=True)
DB_PATH = DB_DIR / "bes_fon_app.db"


def get_connection():
    return sqlite3.connect(DB_PATH, check_same_thread=False)


def hash_password(password: str) -> str:
    salt = os.environ.get("APP_PASSWORD_SALT", "bes-fon-local-salt")
    raw = f"{salt}:{password}".encode("utf-8")
    return hashlib.sha256(raw).hexdigest()


def init_db():
    conn = get_connection()
    cur = conn.cursor()

    cur.execute("""
        CREATE TABLE IF NOT EXISTS users (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            username TEXT NOT NULL UNIQUE,
            password_hash TEXT NOT NULL,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    """)

    cur.execute("""
        CREATE TABLE IF NOT EXISTS portfolios (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER NOT NULL,
            fund_code TEXT NOT NULL,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            UNIQUE(user_id, fund_code),
            FOREIGN KEY(user_id) REFERENCES users(id)
        )
    """)

    conn.commit()
    conn.close()


def create_user(username: str, password: str):
    username = username.strip().lower()
    password = password.strip()

    if not username or not password:
        return False, "Kullanıcı adı ve şifre boş olamaz."

    conn = get_connection()
    cur = conn.cursor()

    try:
        cur.execute(
            "INSERT INTO users (username, password_hash) VALUES (?, ?)",
            (username, hash_password(password))
        )
        conn.commit()
        return True, "Kullanıcı oluşturuldu."
    except sqlite3.IntegrityError:
        return False, "Bu kullanıcı adı zaten var."
    finally:
        conn.close()


def verify_user(username: str, password: str):
    username = username.strip().lower()
    password_hash = hash_password(password.strip())

    conn = get_connection()
    cur = conn.cursor()

    cur.execute(
        "SELECT id FROM users WHERE username = ? AND password_hash = ?",
        (username, password_hash)
    )
    row = cur.fetchone()
    conn.close()

    if row:
        return row[0]
    return None


def get_user_portfolio(user_id: int):
    conn = get_connection()
    cur = conn.cursor()

    cur.execute(
        "SELECT fund_code FROM portfolios WHERE user_id = ? ORDER BY fund_code",
        (user_id,)
    )
    rows = cur.fetchall()
    conn.close()

    return [row[0] for row in rows]


def add_fund_to_user(user_id: int, fund_code: str):
    fund_code = fund_code.strip().upper()

    if not fund_code:
        return False, "Fon kodu boş olamaz."

    conn = get_connection()
    cur = conn.cursor()

    try:
        cur.execute(
            "INSERT INTO portfolios (user_id, fund_code) VALUES (?, ?)",
            (user_id, fund_code)
        )
        conn.commit()
        return True, f"{fund_code} portföyüne eklendi."
    except sqlite3.IntegrityError:
        return False, f"{fund_code} zaten portföyünde var."
    finally:
        conn.close()


def remove_fund_from_user(user_id: int, fund_code: str):
    fund_code = fund_code.strip().upper()

    conn = get_connection()
    cur = conn.cursor()

    cur.execute(
        "DELETE FROM portfolios WHERE user_id = ? AND fund_code = ?",
        (user_id, fund_code)
    )
    conn.commit()
    affected = cur.rowcount
    conn.close()

    if affected:
        return True, f"{fund_code} portföyünden çıkarıldı."
    return False, f"{fund_code} portföyünde bulunamadı."
