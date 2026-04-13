# Yuki — Browser-Based Duel Game
# Copyright (C) 2026 Yuki Contributors
# SPDX-License-Identifier: AGPL-3.0-or-later
#
# test_duel.py — Konsol tabanlı düello simülasyonu
#
# Bu test, Faz 2'nin tüm bileşenlerini doğrular:
#   1. Sistem Lua scriptleri düzgün yükleniyor
#   2. Mesaj parser binary mesajları doğru ayrıştırıyor
#   3. Response builder düzgün yanıtlar üretiyor
#   4. Motor tam bir düello döngüsünü çalıştırabiliyor
#
# İki AI oyuncu basit stratejilerle oynuyor:
#   - Çağrılabilecek en güçlü canavarı çağır
#   - Saldırabilecek bir canavar varsa saldır
#   - Zincire yanıt verme (pas geç)
#   - Efektlere hayır de

import sys
import io
import ctypes
from pathlib import Path

sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8")

project_root = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(project_root))

from server.ocg_binding import (
    OCGCore,
    LOCATION_DECK, LOCATION_EXTRA, LOCATION_HAND, LOCATION_MZONE,
    POS_FACEDOWN_DEFENSE, POS_FACEUP_ATTACK,
    DUEL_MODE_MR2, DUEL_STATUS_END, DUEL_STATUS_AWAITING, DUEL_STATUS_CONTINUE,
    MSG_SELECT_IDLECMD, MSG_SELECT_BATTLECMD, MSG_SELECT_CHAIN,
    MSG_SELECT_EFFECTYN, MSG_SELECT_YESNO, MSG_SELECT_OPTION,
    MSG_SELECT_CARD, MSG_SELECT_PLACE, MSG_SELECT_POSITION,
    MSG_SELECT_TRIBUTE, MSG_SELECT_SUM, MSG_SELECT_UNSELECT_CARD,
    MSG_SELECT_COUNTER,
    MSG_ANNOUNCE_RACE, MSG_ANNOUNCE_ATTRIB, MSG_ANNOUNCE_NUMBER,
    MSG_ROCK_PAPER_SCISSORS, MSG_SORT_CHAIN,
    MSG_WIN, MSG_NEW_TURN, MSG_NEW_PHASE, MSG_DRAW, MSG_DAMAGE,
    MSG_RECOVER, MSG_ATTACK, MSG_BATTLE,
    MSG_SUMMONING, MSG_SPSUMMONING, MSG_FLIPSUMMONING,
    MSG_SUMMONED, MSG_SPSUMMONED, MSG_FLIPSUMMONED,
    MSG_RETRY,
)
from server.card_database import CardDatabase
from server.message_parser import split_messages, parse_message
from server.response_builder import (
    build_idle_cmd_response,
    build_battle_cmd_response,
    build_chain_response,
    build_effectyn_response,
    build_yesno_response,
    build_option_response,
    build_card_response,
    build_place_response,
    build_position_response,
    build_tribute_response,
    build_sum_response,
    build_unselect_card_response,
    build_counter_response,
    build_announce_race_response,
    build_announce_attrib_response,
    build_rps_response,
    build_sort_response,
)
from server.config import CARD_DB_PATH, SCRIPT_DIR


# ---------------------------------------------------------------------------
# Callback fonksiyonları (düzeltilmiş — sistem scriptleri destekli)
# ---------------------------------------------------------------------------

_setcode_buffers = []  # GC koruması

def make_card_reader(db: CardDatabase):
    """Kart verisi callback'i oluşturur."""

    def card_reader(payload, code, data_ptr):
        card = db.get_card(code)
        if card is None:
            data_ptr.contents.code = code
            empty = (ctypes.c_uint16 * 1)(0)
            _setcode_buffers.append(empty)
            data_ptr.contents.setcodes = ctypes.cast(empty, ctypes.POINTER(ctypes.c_uint16))
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

        sc_list = card.setcodes + [0]
        sc_arr = (ctypes.c_uint16 * len(sc_list))(*sc_list)
        _setcode_buffers.append(sc_arr)
        data_ptr.contents.setcodes = ctypes.cast(sc_arr, ctypes.POINTER(ctypes.c_uint16))

    return card_reader


def make_script_reader(core: OCGCore):
    """Script yükleme callback'i oluşturur.

    Motor bir script istediğinde bu fonksiyon çağrılır.
    Arama sırası:
      1. data/script/{name}          — sistem scriptleri (utility.lua vs.)
      2. data/script/official/{name}  — kart scriptleri (c89631139.lua vs.)
    """

    def script_reader(payload, duel, name):
        name_str = name.decode("utf-8") if isinstance(name, bytes) else name

        # Arama yolları
        candidates = [
            SCRIPT_DIR / name_str,
            SCRIPT_DIR / "official" / name_str,
        ]

        for path in candidates:
            if path.exists():
                try:
                    content = path.read_text(encoding="utf-8")
                    content_bytes = content.encode("utf-8")
                    name_bytes = name_str.encode("utf-8")
                    core._lib.OCG_LoadScript(
                        duel, content_bytes, len(content_bytes), name_bytes
                    )
                    return 1
                except Exception:
                    return 0

        return 0

    return script_reader


# ---------------------------------------------------------------------------
# Basit AI — seçim mesajlarına otomatik yanıt verir
# ---------------------------------------------------------------------------

def ai_respond(msg: dict, db: CardDatabase) -> bytes | None:
    """Bir seçim mesajına basit AI yanıtı oluşturur.

    Strateji:
      - Ana Faz: Çağrılabilecek en güçlü canavarı çağır, yoksa savaş/bitiş
      - Savaş: İlk saldırabilir canavar ile saldır, yoksa main2/end
      - Zincir: Pas geç (-1)
      - Efekt/Evet-Hayır: Hayır
      - Kart/Pozisyon: İlk seçeneği seç
    """
    mt = msg["type"]

    if mt == MSG_SELECT_IDLECMD:
        # Çağrılabilir canavar varsa çağır
        if msg.get("summonable"):
            # En yüksek ATK'lı olanı bul
            best_idx = 0
            best_atk = 0
            for i, card in enumerate(msg["summonable"]):
                c = db.get_card(card["code"])
                if c and c.attack > best_atk:
                    best_atk = c.attack
                    best_idx = i
            return build_idle_cmd_response("summon", best_idx)

        # Savaş fazına geçebiliyorsak geç
        if msg.get("can_battle_phase"):
            return build_idle_cmd_response("battle")

        # Bitiş fazına geç
        return build_idle_cmd_response("end")

    if mt == MSG_SELECT_BATTLECMD:
        # Saldırabilir canavar varsa saldır
        if msg.get("attackable"):
            return build_battle_cmd_response("attack", 0)
        # Main Phase 2 veya end
        if msg.get("can_main2"):
            return build_battle_cmd_response("main2")
        return build_battle_cmd_response("end")

    if mt == MSG_SELECT_CHAIN:
        # Pas geç
        return build_chain_response(-1)

    if mt == MSG_SELECT_EFFECTYN:
        return build_effectyn_response(False)

    if mt == MSG_SELECT_YESNO:
        return build_yesno_response(False)

    if mt == MSG_SELECT_OPTION:
        return build_option_response(0)

    if mt == MSG_SELECT_CARD:
        # Min kadar kart seç (ilk N tanesini)
        n = msg.get("min", 1)
        indices = list(range(min(n, len(msg.get("cards", [])))))
        return build_card_response(indices)

    if mt == MSG_SELECT_PLACE:
        # İlk uygun bölgeyi seç
        return build_place_response(msg["player"], 0x04, 0)  # MZONE seq 0

    if mt == MSG_SELECT_POSITION:
        # Saldırı pozisyonu tercih et
        positions = msg.get("positions", 0x1)
        if positions & POS_FACEUP_ATTACK:
            return build_position_response(POS_FACEUP_ATTACK)
        return build_position_response(positions & -positions)  # En düşük bit

    if mt == MSG_SELECT_TRIBUTE:
        n = msg.get("min", 1)
        indices = list(range(min(n, len(msg.get("cards", [])))))
        return build_tribute_response(indices)

    if mt == MSG_SELECT_SUM:
        # Zorunlu + ilk seçilebilir
        n = len(msg.get("must_cards", []))
        sel = list(range(min(1, len(msg.get("selectable_cards", [])))))
        return build_sum_response(list(range(n)) + [n + i for i in sel])

    if mt == MSG_SELECT_UNSELECT_CARD:
        if msg.get("selectable"):
            return build_unselect_card_response(0)
        return build_unselect_card_response(-1)

    if mt == MSG_SELECT_COUNTER:
        # Her karta 0 sayaç
        cards = msg.get("cards", [])
        return build_counter_response([0] * len(cards))

    if mt == MSG_ANNOUNCE_RACE:
        # İlk uygun ırkı seç
        available = msg.get("available", 1)
        return build_announce_race_response(available & -available)

    if mt == MSG_ANNOUNCE_ATTRIB:
        available = msg.get("available", 1)
        return build_announce_attrib_response(available & -available)

    if mt == MSG_ANNOUNCE_NUMBER:
        return build_announce_race_response(1)

    if mt == MSG_ROCK_PAPER_SCISSORS:
        return build_rps_response(1)  # Taş

    if mt == MSG_SORT_CHAIN:
        return build_sort_response([])  # Varsayılan sıra

    return None


# ---------------------------------------------------------------------------
# Ana düello döngüsü
# ---------------------------------------------------------------------------

def main():
    print("=" * 60)
    print("  Yuki — Faz 2 Konsol Duello Simulasyonu")
    print("=" * 60)

    # Hazırlık
    core = OCGCore()
    db = CardDatabase(CARD_DB_PATH)
    print(f"Motor: v{core.get_version()[0]}.{core.get_version()[1]}")
    print(f"Veritabani: {db.count()} kart")

    # Callback'ler
    card_reader = make_card_reader(db)
    script_reader = make_script_reader(core)

    log_errors = []
    def log_handler(payload, string, log_type):
        if string and log_type == 0:  # sadece hatalar
            log_errors.append(string.decode("utf-8", errors="replace"))

    # Test destesi — Saf Normal Monster'lar (type=17, efektsiz, script sorunsuz)
    # Sadece Level 4 ve alti (kurbansiz cagri yapilabilsin)
    deck_codes = [
        43096270,   # Alexandrite Dragon (2000/100 Lvl 4)
        69247929,   # Gene-Warped Warwolf (2000/100 Lvl 4)
        81823360,   # Megalosmasher X (2000/0 Lvl 4)
        84754430,   # Mekk-Knight Avram (2000/0 Lvl 4)
        77542832,   # Evilswarm Heliotrope (1950/650 Lvl 4)
        11091375,   # Luster Dragon (1900/1600 Lvl 4)
        14898066,   # Vorse Raider (1900/1200 Lvl 4)
        35052053,   # Insect Knight (1900/1500 Lvl 4)
        49881766,   # Archfiend Soldier (1900/1500 Lvl 4)
        69140098,   # Gemini Elf (1900/900 Lvl 4)
        37265642,   # Sabersaurus (1900/500 Lvl 4)
        4148264,    # Shiny Black C Squadder (2000/0 Lvl 4)
        47226949,   # Leotron (2000/0 Lvl 4)
        74852097,   # Phantom Gryphon (2000/0 Lvl 4)
    ]

    # Desteyi 40 karta tamamla
    full_deck = []
    while len(full_deck) < 40:
        for code in deck_codes:
            full_deck.append(code)
            if len(full_deck) >= 40:
                break

    # Düello oluştur
    duel = core.create_duel(
        card_reader=card_reader,
        script_reader=script_reader,
        log_handler=log_handler,
        starting_lp=8000,
        flags=DUEL_MODE_MR2,
    )

    # Kartları ekle
    for code in full_deck:
        core.add_card(duel, team=0, code=code, loc=LOCATION_DECK)
        core.add_card(duel, team=1, code=code, loc=LOCATION_DECK)

    core.start_duel(duel)

    # Düello döngüsü
    lp = [8000, 8000]
    turn = 0
    total_steps = 0
    max_steps = 500
    retry_count = 0
    max_retries = 5
    last_interactive = None

    print("\n--- Duello Basliyor ---\n")

    while total_steps < max_steps:
        status = core.process(duel)
        total_steps += 1

        raw = core.get_message(duel)
        if not raw:
            if status == DUEL_STATUS_END:
                break
            continue

        messages = split_messages(raw)
        for msg_type, msg_data in messages:
            msg = parse_message(msg_type, msg_data)

            # Bilgi mesajlarını göster
            if msg_type == MSG_NEW_TURN:
                turn += 1
                print(f"\n===== TUR {turn} (Oyuncu {msg['player']}) =====")
                print(f"  LP: P0={lp[0]}  P1={lp[1]}")

            elif msg_type == MSG_NEW_PHASE:
                phase_names = {
                    0x01: "Draw", 0x02: "Standby", 0x04: "Main1",
                    0x08: "Battle Start", 0x10: "Battle Step",
                    0x20: "Damage", 0x40: "Damage Cal",
                    0x80: "Battle", 0x100: "Main2", 0x200: "End",
                }
                pname = phase_names.get(msg.get("phase", 0), f"0x{msg.get('phase', 0):x}")
                print(f"  Faz: {pname}")

            elif msg_type == MSG_DRAW:
                count = msg.get("count", 0)
                codes = [c["code"] for c in msg.get("cards", [])]
                names = []
                for c in codes:
                    card = db.get_card(c)
                    names.append(card.name if card else f"#{c}")
                print(f"  P{msg.get('player', '?')} {count} kart cekti: {', '.join(names)}")

            elif msg_type in (MSG_SUMMONING, MSG_SPSUMMONING, MSG_FLIPSUMMONING):
                card = db.get_card(msg.get("code", 0))
                name = card.name if card else f"#{msg.get('code', 0)}"
                summon_type = {MSG_SUMMONING: "Normal", MSG_SPSUMMONING: "Ozel", MSG_FLIPSUMMONING: "Flip"}
                print(f"  {summon_type.get(msg_type, '')} Cagri: {name}")

            elif msg_type == MSG_ATTACK:
                print(f"  Saldiri! P{msg.get('attacker_controller', '?')} "
                      f"seq={msg.get('attacker_sequence', '?')} -> "
                      f"P{msg.get('target_controller', '?')} seq={msg.get('target_sequence', '?')}")

            elif msg_type == MSG_BATTLE:
                print(f"  Savas: ATK {msg.get('attacker_atk', '?')} vs "
                      f"ATK/DEF {msg.get('target_atk', '?')}/{msg.get('target_def', '?')}")

            elif msg_type == MSG_DAMAGE:
                p = msg.get("player", 0)
                amount = msg.get("amount", 0)
                lp[p] -= amount
                print(f"  P{p} {amount} hasar aldi! (LP: {lp[p]})")

            elif msg_type == MSG_RECOVER:
                p = msg.get("player", 0)
                amount = msg.get("amount", 0)
                lp[p] += amount
                print(f"  P{p} {amount} LP kazandi! (LP: {lp[p]})")

            elif msg_type == MSG_WIN:
                winner = msg.get("player", -1)
                if winner == 2:
                    print(f"\n  BERABERE!")
                else:
                    print(f"\n  KAZANAN: Oyuncu {winner}!")
                print(f"  Son LP: P0={lp[0]}  P1={lp[1]}")

            elif msg_type == MSG_RETRY:
                retry_count += 1
                if retry_count >= max_retries:
                    print(f"\n  [HATA] {max_retries} ardisik RETRY — durduruluyor")
                    print(f"  Son mesaj: {last_interactive}")
                    total_steps = max_steps
                    break
                continue

            # Seçim mesajlarına yanıt ver
            if msg.get("interactive"):
                retry_count = 0
                last_interactive = msg
                response = ai_respond(msg, db)
                if response:
                    core.set_response(duel, response)

        if status == DUEL_STATUS_END:
            break

    # Özet
    print(f"\n--- Duello Bitti ---")
    print(f"  Toplam tur: {turn}")
    print(f"  Toplam adim: {total_steps}")
    print(f"  Son LP: P0={lp[0]}  P1={lp[1]}")

    if log_errors:
        print(f"\n  Script hatalari ({len(log_errors)} adet):")
        # Sadece benzersiz hataları göster
        unique = list(dict.fromkeys(log_errors))
        for err in unique[:5]:
            print(f"    {err}")
        if len(unique) > 5:
            print(f"    ... ve {len(unique) - 5} daha")

    # Temizlik
    core.destroy_duel(duel)
    db.close()

    print("\n" + "=" * 60)
    print("  Faz 2 Testi Tamamlandi!")
    print("=" * 60)


if __name__ == "__main__":
    main()
