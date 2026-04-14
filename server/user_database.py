# Yuki — Browser-Based Duel Game
# Copyright (C) 2026 Yuki Contributors
# SPDX-License-Identifier: AGPL-3.0-or-later
#
# user_database.py — Kullanıcı veritabanı (kayıt, giriş, oturum)

import hashlib
import os
import secrets
import sqlite3
from dataclasses import dataclass

from server.config import USER_DB_PATH


@dataclass
class User:
    user_id: int
    username: str


class UserDatabase:
    """SQLite tabanlı kullanıcı veritabanı."""

    def __init__(self, db_path=None):
        self._path = str(db_path or USER_DB_PATH)
        self._conn = sqlite3.connect(self._path)
        self._conn.row_factory = sqlite3.Row
        self._create_tables()
        # token → User eşlemesi (bellekte)
        self._sessions: dict[str, User] = {}

    def _create_tables(self):
        self._conn.execute("""
            CREATE TABLE IF NOT EXISTS users (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                username TEXT UNIQUE NOT NULL,
                password_hash TEXT NOT NULL,
                salt TEXT NOT NULL,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)
        self._conn.commit()

    def _hash_password(self, password: str, salt: str) -> str:
        return hashlib.pbkdf2_hmac(
            "sha256", password.encode(), salt.encode(), 100_000
        ).hex()

    def register(self, username: str, password: str) -> tuple[bool, str]:
        """Yeni kullanıcı kaydı. (başarılı, mesaj) döner."""
        username = username.strip()
        if not username or len(username) < 3:
            return False, "Kullanici adi en az 3 karakter olmali"
        if len(username) > 20:
            return False, "Kullanici adi en fazla 20 karakter olmali"
        if not password or len(password) < 4:
            return False, "Sifre en az 4 karakter olmali"

        salt = os.urandom(16).hex()
        pw_hash = self._hash_password(password, salt)

        try:
            self._conn.execute(
                "INSERT INTO users (username, password_hash, salt) VALUES (?, ?, ?)",
                (username, pw_hash, salt),
            )
            self._conn.commit()
            return True, "Kayit basarili"
        except sqlite3.IntegrityError:
            return False, "Bu kullanici adi zaten alinmis"

    def login(self, username: str, password: str) -> tuple[str | None, str]:
        """Giriş yapar. (token|None, mesaj) döner."""
        row = self._conn.execute(
            "SELECT id, username, password_hash, salt FROM users WHERE username = ?",
            (username,),
        ).fetchone()

        if not row:
            return None, "Kullanici bulunamadi"

        pw_hash = self._hash_password(password, row["salt"])
        if pw_hash != row["password_hash"]:
            return None, "Sifre yanlis"

        token = secrets.token_hex(16)
        self._sessions[token] = User(user_id=row["id"], username=row["username"])
        return token, "Giris basarili"

    def get_user(self, token: str) -> User | None:
        """Token ile kullanıcı döndürür."""
        return self._sessions.get(token)

    def logout(self, token: str):
        """Oturumu sonlandırır."""
        self._sessions.pop(token, None)
