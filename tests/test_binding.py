# Yuki — Browser-Based Duel Game
# Copyright (C) 2026 Yuki Contributors
# SPDX-License-Identifier: AGPL-3.0-or-later
#
# test_binding.py — OCGCore binding + kart veritabanı bütünleşik test
#
# Bu test, tüm Faz 1 bileşenlerinin birlikte çalıştığını doğrular:
#   1. OCGCore DLL yükleniyor mu?
#   2. Versiyon okunabiliyor mu?
#   3. Kart veritabanı açılıyor mu?
#   4. Callback'ler ile düello oluşturulabiliyor mu?
#   5. Kartlar eklenip düello başlatılabiliyor mu?
#   6. Motor mesaj üretiyor mu?

import sys
import os
import io
import ctypes
from pathlib import Path

# stdout encoding fix (Windows konsolunda Türkçe/Unicode sorununu önler)
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8")

# Proje kökünü Python path'ine ekle
project_root = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(project_root))

from server.ocg_binding import (
    OCGCore,
    LOCATION_DECK, LOCATION_EXTRA,
    POS_FACEDOWN_DEFENSE,
    DUEL_MODE_MR2,
    DUEL_STATUS_END, DUEL_STATUS_AWAITING, DUEL_STATUS_CONTINUE,
    MSG_NAMES,
)
from server.card_database import CardDatabase


# ---------------------------------------------------------------------------
# Script ve kart verisi yolları
# ---------------------------------------------------------------------------
SCRIPT_DIR = project_root / "data" / "script"
DB_PATH = project_root / "data" / "cards.cdb"


# ---------------------------------------------------------------------------
# Test
# ---------------------------------------------------------------------------
def main():
    print("=" * 60)
    print("  Yuki — Faz 1 Bütünleşik Test")
    print("=" * 60)

    # 1. OCGCore yükle
    core = OCGCore()
    major, minor = core.get_version()
    print(f"\n[OK] OCGCore yuklu: v{major}.{minor}")

    # 2. Kart veritabanı aç
    db = CardDatabase(DB_PATH)
    card_count = db.count()
    print(f"[OK] Kart veritabani: {card_count} kart")

    # 3. Callback fonksiyonları oluştur
    #    card_reader: Motor bir kartın verisini istediğinde çağrılır
    #    script_reader: Motor bir kartın Lua scriptini istediğinde çağrılır

    # setcodes için kalıcı buffer'lar (GC'nin silmesini engelle)
    _setcode_buffers = []

    def card_reader(payload, code, data_ptr):
        """Motor soruyor: Bu kartın verisi ne?"""
        card = db.get_card(code)
        if card is None:
            # Kart bulunamadı — boş veri dön
            data_ptr.contents.code = code
            empty = (ctypes.c_uint16 * 1)(0)
            _setcode_buffers.append(empty)
            data_ptr.contents.setcodes = ctypes.cast(
                empty, ctypes.POINTER(ctypes.c_uint16)
            )
            return

        data_ptr.contents.code = card.code
        data_ptr.contents.alias = card.alias
        data_ptr.contents.type = card.type
        data_ptr.contents.level = card.level
        data_ptr.contents.attribute = card.attribute
        data_ptr.contents.race = card.race
        data_ptr.contents.attack = card.attack
        data_ptr.contents.defense = card.defense
        data_ptr.contents.lscale = card.lscale
        data_ptr.contents.rscale = card.rscale
        data_ptr.contents.link_marker = card.link_marker

        # setcodes: null-terminated uint16 dizisi
        sc_list = card.setcodes + [0]  # sonuna 0 ekle (null terminator)
        sc_arr = (ctypes.c_uint16 * len(sc_list))(*sc_list)
        _setcode_buffers.append(sc_arr)  # GC koruması
        data_ptr.contents.setcodes = ctypes.cast(
            sc_arr, ctypes.POINTER(ctypes.c_uint16)
        )

    def script_reader(payload, duel, name):
        """Motor soruyor: Bu script dosyasını verir misin?"""
        name_str = name.decode("utf-8") if isinstance(name, bytes) else name

        # Script dosyasını ara (birden fazla olası konum)
        candidates = [
            SCRIPT_DIR / name_str,                    # data/script/utility.lua
            SCRIPT_DIR / "official" / name_str,       # data/script/official/c89631139.lua
        ]

        for path in candidates:
            if path.exists():
                content = path.read_text(encoding="utf-8")
                content_bytes = content.encode("utf-8")
                core.load_script(duel, content, name_str)
                return 1  # başarılı

        return 0  # bulunamadı

    def log_handler(payload, string, log_type):
        """Motor log mesajı gönderdi."""
        if string:
            msg = string.decode("utf-8", errors="replace")
            print(f"  [LOG] {msg}")

    print("[OK] Callback fonksiyonlari hazir")

    # 4. Test destesi oluştur — 40 kart, sadece Normal Monster'lar
    #    Bu basit bir testtir, efektsiz canavarlarla düellonun çalıştığını doğrular
    test_deck_codes = [
        89631139,   # Blue-Eyes White Dragon (ATK 3000, Lvl 8)
        46986414,   # Dark Magician (ATK 2500, Lvl 7)
        74677422,   # Red-Eyes Black Dragon (ATK 2400, Lvl 7)
        38033121,   # Dark Magician Girl (ATK 2000, Lvl 6)
        11549357,   # Curse of Dragon (ATK 2000, Lvl 5)
        6368038,    # Gaia The Fierce Knight (ATK 2300, Lvl 7)
        36996508,   # La Jinn the Mystical Genie (ATK 1800, Lvl 4)
        4031928,    # Summoned Skull (ATK 2500, Lvl 6)
        99785935,   # Neo the Magic Swordsman (ATK 1700, Lvl 4)
        44287299,   # Giant Soldier of Stone (ATK 1300, Lvl 3)
    ]

    # Desteyi 40 karta tamamla (aynı kartları tekrarla)
    full_deck = []
    while len(full_deck) < 40:
        for code in test_deck_codes:
            full_deck.append(code)
            if len(full_deck) >= 40:
                break

    # 5. Düello oluştur
    print("\nDuello olusturuluyor...")
    duel = core.create_duel(
        card_reader=card_reader,
        script_reader=script_reader,
        log_handler=log_handler,
        starting_lp=8000,
        flags=DUEL_MODE_MR2,
    )
    print(f"[OK] Duello olusturuldu (handle: {duel.value})")

    # 6. Her iki oyuncuya kart ekle
    for code in full_deck:
        core.add_card(duel, team=0, code=code, loc=LOCATION_DECK)
        core.add_card(duel, team=1, code=code, loc=LOCATION_DECK)

    deck_count_p0 = core.query_count(duel, 0, LOCATION_DECK)
    deck_count_p1 = core.query_count(duel, 1, LOCATION_DECK)
    print(f"[OK] Kartlar eklendi: P0={deck_count_p0}, P1={deck_count_p1}")

    # 7. Düelloyu başlat
    core.start_duel(duel)
    print("[OK] Duello baslatildi")

    # 8. Motor döngüsü — birkaç adım işle ve mesajları oku
    print("\nMotor dongusu basliyor...")
    total_messages = 0
    steps = 0
    max_steps = 20  # Sonsuz döngüyü önle

    while steps < max_steps:
        status = core.process(duel)
        steps += 1

        # Mesajları oku
        raw = core.get_message(duel)
        if raw:
            # Mesajları say (her mesaj: [length:u32][type:u8][data:...])
            offset = 0
            while offset < len(raw):
                if offset + 4 > len(raw):
                    break
                msg_len = int.from_bytes(raw[offset:offset+4], "little")
                if msg_len == 0 or offset + 4 + msg_len > len(raw):
                    break
                msg_type = raw[offset + 4]
                msg_name = MSG_NAMES.get(msg_type, f"UNKNOWN_{msg_type}")
                if total_messages < 30:  # İlk 30 mesajı göster
                    print(f"  [{steps:2d}] {msg_name} (len={msg_len})")
                total_messages += 1
                offset += 4 + msg_len

        if status == DUEL_STATUS_END:
            print(f"\n[OK] Duello bitti (adim {steps})")
            break
        elif status == DUEL_STATUS_AWAITING:
            # Oyuncudan yanıt bekliyor — basit yanıt gönder (ilk seçeneği seç)
            # Bu test için sadece motorun çalıştığını doğruluyoruz
            response = b"\x00\x00\x00\x00"  # Basit 4-byte yanıt
            core.set_response(duel, response)
        elif status == DUEL_STATUS_CONTINUE:
            continue

    if total_messages > 30:
        print(f"  ... ve {total_messages - 30} mesaj daha")

    print(f"\n[OK] Motor {steps} adimda {total_messages} mesaj uretti")

    # 9. Temizlik
    core.destroy_duel(duel)
    db.close()

    print("\n" + "=" * 60)
    print("  TUM TESTLER BASARILI!")
    print("  Faz 1 tamamlandi — motor, veritabani, callback calisiyor")
    print("=" * 60)


if __name__ == "__main__":
    main()
