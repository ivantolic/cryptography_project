import os
import sqlite3
import hashlib
import hmac
from typing import Optional


DB_NAME = "chat.db"

# Password hashing settings
SALT_SIZE = 16
HASH_NAME = "sha256"
ITERATIONS = 200_000
DKLEN = 32


def init_db(db_name: str = DB_NAME) -> None:
    """
    Creates the SQLite database and users table if they do not already exist.
    """
    conn = sqlite3.connect(db_name)
    cursor = conn.cursor()

    cursor.execute(
        """
        CREATE TABLE IF NOT EXISTS users (
            username TEXT PRIMARY KEY,
            salt BLOB NOT NULL,
            password_hash BLOB NOT NULL
        )
        """
    )

    conn.commit()
    conn.close()


def hash_password(password: str, salt: Optional[bytes] = None) -> tuple[bytes, bytes]:
    """
    Hashes a password using PBKDF2-HMAC-SHA256 with a random salt.

    Returns:
        salt, password_hash
    """
    if salt is None:
        salt = os.urandom(SALT_SIZE)

    password_hash = hashlib.pbkdf2_hmac(
        HASH_NAME,
        password.encode("utf-8"),
        salt,
        ITERATIONS,
        dklen=DKLEN,
    )

    return salt, password_hash


def register_user(username: str, password: str, db_name: str = DB_NAME) -> bool:
    """
    Registers a new user.

    Returns:
        True if registration succeeds.
        False if username already exists or input is invalid.
    """
    username = username.strip()

    if not username or not password:
        return False

    salt, password_hash = hash_password(password)

    try:
        conn = sqlite3.connect(db_name)
        cursor = conn.cursor()

        cursor.execute(
            "INSERT INTO users (username, salt, password_hash) VALUES (?, ?, ?)",
            (username, salt, password_hash),
        )

        conn.commit()
        return True

    except sqlite3.IntegrityError:
        # Username already exists
        return False

    finally:
        conn.close()


def verify_user(username: str, password: str, db_name: str = DB_NAME) -> bool:
    """
    Verifies user credentials.

    Returns:
        True if username/password are correct.
        False otherwise.
    """
    username = username.strip()

    conn = sqlite3.connect(db_name)
    cursor = conn.cursor()

    cursor.execute(
        "SELECT salt, password_hash FROM users WHERE username = ?",
        (username,),
    )

    row = cursor.fetchone()
    conn.close()

    if row is None:
        return False

    salt, stored_hash = row
    _, candidate_hash = hash_password(password, salt)

    return hmac.compare_digest(stored_hash, candidate_hash)


if __name__ == "__main__":
    init_db()
    print("SQLite authentication database initialized successfully.")