# Yuki — Browser-Based Duel Game
# Copyright (C) 2026 Yuki Contributors
# SPDX-License-Identifier: AGPL-3.0-or-later
#
# user_database.py — Kullanıcı veritabanı (kayıt, giriş, oturum)

import hashlib
import json
import os
import random
import secrets
import sqlite3
from dataclasses import dataclass

from server.config import USER_DB_PATH, CARD_DB_PATH


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
                dust INTEGER NOT NULL DEFAULT 100,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)
        self._conn.execute("""
            CREATE TABLE IF NOT EXISTS collections (
                user_id INTEGER NOT NULL,
                card_code INTEGER NOT NULL,
                FOREIGN KEY (user_id) REFERENCES users(id),
                UNIQUE(user_id, card_code)
            )
        """)
        self._conn.execute("""
            CREATE TABLE IF NOT EXISTS user_decks (
                user_id INTEGER NOT NULL,
                slot INTEGER NOT NULL CHECK(slot >= 0 AND slot <= 2),
                name TEXT NOT NULL DEFAULT 'Deste',
                cards TEXT NOT NULL DEFAULT '[]',
                FOREIGN KEY (user_id) REFERENCES users(id),
                UNIQUE(user_id, slot)
            )
        """)
        self._conn.commit()

    def _load_card_pool(self):
        """Tüm destelerdeki kartları tipine göre gruplar (başlangıç koleksiyonu için)."""
        from server.decks import (
            YUGI_DECK, BASTION_DECK, KAIBA_DECK, ANCIENT_GEAR_DECK,
            JOEY_DECK, MAI_DECK, SYRUS_DECK, DINO_DECK,
            INSECT_DECK, REX_RAPTOR_DECK,
        )
        all_decks = [
            YUGI_DECK, BASTION_DECK, KAIBA_DECK, ANCIENT_GEAR_DECK,
            JOEY_DECK, MAI_DECK, SYRUS_DECK, DINO_DECK,
            INSECT_DECK, REX_RAPTOR_DECK,
        ]
        all_codes = set()
        for d in all_decks:
            all_codes.update(d)

        card_db = sqlite3.connect(str(CARD_DB_PATH))
        TYPE_SPELL = 0x2
        TYPE_TRAP = 0x4
        TYPE_FUSION = 0x40

        monsters, spells, traps = [], [], []
        for code in all_codes:
            row = card_db.execute(
                "SELECT type FROM datas WHERE id = ?", (code,)
            ).fetchone()
            if not row:
                continue
            ctype = row[0]
            if ctype & TYPE_FUSION:
                continue  # Extra deck — koleksiyona dahil değil
            elif ctype & TYPE_TRAP:
                traps.append(code)
            elif ctype & TYPE_SPELL:
                spells.append(code)
            else:
                monsters.append(code)
        card_db.close()
        return monsters, spells, traps

    def _generate_starter_collection(self, user_id: int):
        """Yeni kullanıcıya 60 rastgele kart verir (25 monster, 20 spell, 15 trap)."""
        monsters, spells, traps = self._load_card_pool()
        selected = (
            random.sample(monsters, min(25, len(monsters)))
            + random.sample(spells, min(20, len(spells)))
            + random.sample(traps, min(15, len(traps)))
        )
        for code in selected:
            self._conn.execute(
                "INSERT OR IGNORE INTO collections (user_id, card_code) VALUES (?, ?)",
                (user_id, code),
            )
        # 3 boş deste slotu oluştur
        for slot in range(3):
            self._conn.execute(
                "INSERT OR IGNORE INTO user_decks (user_id, slot, name, cards) VALUES (?, ?, ?, '[]')",
                (user_id, slot, f"Deste {slot + 1}"),
            )
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
            cursor = self._conn.execute(
                "INSERT INTO users (username, password_hash, salt) VALUES (?, ?, ?)",
                (username, pw_hash, salt),
            )
            self._conn.commit()
            self._generate_starter_collection(cursor.lastrowid)
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

    # --- Dust (Toz) Sistemi ---

    # Tier: S (ATK>=2500), A (ATK>=1800), B (spell/trap/orta), C (ATK<1000)
    DUST_TABLE = {
        "S": {"disenchant": 25, "craft": 100},
        "A": {"disenchant": 15, "craft": 60},
        "B": {"disenchant": 8,  "craft": 30},
        "C": {"disenchant": 3,  "craft": 10},
    }

    def card_tier(self, code: int) -> str:
        """Kart kodundan tier hesaplar."""
        card_db = sqlite3.connect(str(CARD_DB_PATH))
        row = card_db.execute(
            "SELECT type, atk FROM datas WHERE id = ?", (code,)
        ).fetchone()
        card_db.close()
        if not row:
            return "B"
        ctype, atk = row
        TYPE_SPELL, TYPE_TRAP = 0x2, 0x4
        if ctype & (TYPE_SPELL | TYPE_TRAP):
            return "B"
        # Monster — ATK bazlı
        if atk >= 2500:
            return "S"
        if atk >= 1800:
            return "A"
        if atk < 1000:
            return "C"
        return "B"

    def get_dust(self, user_id: int) -> int:
        """Kullanıcının toz miktarını döndürür."""
        row = self._conn.execute(
            "SELECT dust FROM users WHERE id = ?", (user_id,)
        ).fetchone()
        return row["dust"] if row else 0

    def craft_card(self, user_id: int, code: int) -> tuple[bool, str, int]:
        """Kartı toz ile açar. (başarılı, mesaj, kalan_toz) döner."""
        # Zaten koleksiyonda mı?
        exists = self._conn.execute(
            "SELECT 1 FROM collections WHERE user_id=? AND card_code=?",
            (user_id, code),
        ).fetchone()
        if exists:
            return False, "Bu kart zaten koleksiyonunda", self.get_dust(user_id)

        tier = self.card_tier(code)
        cost = self.DUST_TABLE[tier]["craft"]
        dust = self.get_dust(user_id)

        if dust < cost:
            return False, f"Yetersiz toz ({dust}/{cost})", dust

        # Tozu düş, kartı ekle
        self._conn.execute(
            "UPDATE users SET dust = dust - ? WHERE id = ?", (cost, user_id)
        )
        self._conn.execute(
            "INSERT OR IGNORE INTO collections (user_id, card_code) VALUES (?, ?)",
            (user_id, code),
        )
        self._conn.commit()
        new_dust = self.get_dust(user_id)
        return True, "Kart acildi", new_dust

    def disenchant_card(self, user_id: int, code: int) -> tuple[bool, str, int]:
        """Kartı bozdurur, toz kazanır. (başarılı, mesaj, kalan_toz) döner."""
        # Koleksiyonda mı?
        exists = self._conn.execute(
            "SELECT 1 FROM collections WHERE user_id=? AND card_code=?",
            (user_id, code),
        ).fetchone()
        if not exists:
            return False, "Bu kart koleksiyonunda yok", self.get_dust(user_id)

        # Herhangi bir destede mi?
        decks = self._conn.execute(
            "SELECT cards FROM user_decks WHERE user_id=?", (user_id,)
        ).fetchall()
        for row in decks:
            deck_cards = json.loads(row["cards"])
            if code in deck_cards:
                return False, "Bu kart bir destede kullaniliyor, once desteden cikar", self.get_dust(user_id)

        tier = self.card_tier(code)
        gain = self.DUST_TABLE[tier]["disenchant"]

        # Kartı sil, tozu ekle
        self._conn.execute(
            "DELETE FROM collections WHERE user_id=? AND card_code=?",
            (user_id, code),
        )
        self._conn.execute(
            "UPDATE users SET dust = dust + ? WHERE id = ?", (gain, user_id)
        )
        self._conn.commit()
        new_dust = self.get_dust(user_id)
        return True, f"+{gain} toz", new_dust

    # --- Kart Havuzu (tüm destelerden) ---

    def get_card_pool(self) -> list[dict]:
        """Tüm destelerdeki benzersiz kartları tip bilgisiyle döndürür."""
        monsters, spells, traps = self._load_card_pool()
        card_db = sqlite3.connect(str(CARD_DB_PATH))

        pool = []
        for code in sorted(set(monsters + spells + traps)):
            row = card_db.execute(
                "SELECT d.type, d.atk, d.def, d.level, t.name "
                "FROM datas d JOIN texts t ON d.id=t.id WHERE d.id=?",
                (code,),
            ).fetchone()
            if not row:
                continue
            ctype, atk, defn, level_raw, name = row
            TYPE_SPELL, TYPE_TRAP = 0x2, 0x4
            if ctype & TYPE_TRAP:
                kind = "trap"
            elif ctype & TYPE_SPELL:
                kind = "spell"
            else:
                kind = "monster"
            pool.append({
                "c": code, "n": name, "t": kind,
                "a": atk, "d": defn, "l": level_raw & 0xFF,
            })
        card_db.close()
        return pool

    def get_preset_decks(self) -> dict:
        """Hazır desteleri {isim: [kodlar]} olarak döndürür."""
        from server.decks import (
            YUGI_DECK, BASTION_DECK, KAIBA_DECK, ANCIENT_GEAR_DECK,
            JOEY_DECK, MAI_DECK, SYRUS_DECK, DINO_DECK,
            INSECT_DECK, REX_RAPTOR_DECK,
        )
        return {
            "Yugi Muto": sorted(set(YUGI_DECK)),
            "Bastion Misawa": sorted(set(BASTION_DECK)),
            "Seto Kaiba": sorted(set(KAIBA_DECK)),
            "Ancient Gear": sorted(set(ANCIENT_GEAR_DECK)),
            "Joey Wheeler": sorted(set(JOEY_DECK)),
            "Mai Valentine": sorted(set(MAI_DECK)),
            "Syrus Truesdale": sorted(set(SYRUS_DECK)),
            "Dino (Hassleberry)": sorted(set(DINO_DECK)),
            "Weevil Underwood": sorted(set(INSECT_DECK)),
            "Rex Raptor": sorted(set(REX_RAPTOR_DECK)),
        }

    # --- Koleksiyon ---

    def get_collection(self, user_id: int) -> list[int]:
        """Kullanıcının koleksiyonundaki kart kodlarını döndürür."""
        rows = self._conn.execute(
            "SELECT card_code FROM collections WHERE user_id = ?", (user_id,)
        ).fetchall()
        return [row["card_code"] for row in rows]

    # --- Desteler ---

    def get_decks(self, user_id: int) -> list[dict]:
        """Kullanıcının 3 deste slotunu döndürür."""
        rows = self._conn.execute(
            "SELECT slot, name, cards FROM user_decks WHERE user_id = ? ORDER BY slot",
            (user_id,),
        ).fetchall()
        result = []
        for row in rows:
            result.append({
                "slot": row["slot"],
                "name": row["name"],
                "cards": json.loads(row["cards"]),
            })
        # Eksik slotları doldur
        existing = {r["slot"] for r in result}
        for slot in range(3):
            if slot not in existing:
                result.append({"slot": slot, "name": f"Deste {slot + 1}", "cards": []})
        result.sort(key=lambda r: r["slot"])
        return result

    def save_deck(self, user_id: int, slot: int, name: str, cards: list[int]) -> bool:
        """Bir deste slotunu kaydeder. Kartlar koleksiyonda olmalı."""
        if slot < 0 or slot > 2:
            return False
        if len(cards) > 40:
            return False
        self._conn.execute(
            """INSERT INTO user_decks (user_id, slot, name, cards)
               VALUES (?, ?, ?, ?)
               ON CONFLICT(user_id, slot) DO UPDATE SET name=?, cards=?""",
            (user_id, slot, name, json.dumps(cards), name, json.dumps(cards)),
        )
        self._conn.commit()
        return True
