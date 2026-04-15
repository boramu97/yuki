#!/usr/bin/env python3
"""boramu kullanıcısına Jaden Yuki destesindeki tüm kartları ver."""
import sqlite3
import sys
import os

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from server.decks import JADEN_DECK

DB_PATH = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "data", "users.db")

conn = sqlite3.connect(DB_PATH)
cur = conn.cursor()

# Kullanıcıyı bul
cur.execute("SELECT id FROM users WHERE username = ?", ("boramu",))
row = cur.fetchone()
if not row:
    print("HATA: 'boramu' kullanıcısı bulunamadı!")
    conn.close()
    sys.exit(1)

user_id = row[0]
print(f"boramu user_id = {user_id}")

# Tüm Jaden kartlarını ekle
added = 0
for code in set(JADEN_DECK):
    try:
        cur.execute("INSERT OR IGNORE INTO collections (user_id, card_code) VALUES (?, ?)", (user_id, code))
        if cur.rowcount > 0:
            added += 1
    except Exception as e:
        print(f"  Hata {code}: {e}")

conn.commit()
conn.close()
print(f"Toplam {added} yeni kart eklendi (zaten varsa atlandı).")
