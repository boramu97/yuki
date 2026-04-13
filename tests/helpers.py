# Yuki — Browser-Based Duel Game
# Copyright (C) 2026 Yuki Contributors
# SPDX-License-Identifier: AGPL-3.0-or-later
#
# helpers.py — Test altyapısı: duel oluşturma, kart yerleştirme, mesaj okuma

import sys
import io
import ctypes
import struct

sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8")
sys.path.insert(0, ".")

from server.ocg_binding import *
from server.card_database import CardDatabase
from server.message_parser import split_messages, parse_message, MSG_NAMES
from server.response_builder import *
from server.config import SCRIPT_DIR, CARD_DB_PATH

# ---------------------------------------------------------------------------
# Global Motor & Veritabanı
# ---------------------------------------------------------------------------

db = CardDatabase(CARD_DB_PATH)
core = OCGCore()
_bufs = []  # ctypes buffer referansları (GC koruması)


# ---------------------------------------------------------------------------
# Callback'ler
# ---------------------------------------------------------------------------

def card_reader(payload, code, dp):
    """Motorun istediği kart verisini veritabanından okur."""
    c = db.get_card(code)
    if not c:
        dp.contents.code = code
        e = (ctypes.c_uint16 * 1)(0)
        _bufs.append(e)
        dp.contents.setcodes = ctypes.cast(e, ctypes.POINTER(ctypes.c_uint16))
        return
    dp.contents.code = c.code
    dp.contents.alias = c.alias
    dp.contents.type = c.type
    dp.contents.level = c.level
    dp.contents.attribute = c.attribute
    dp.contents.race = c.race
    dp.contents.attack = c.attack
    dp.contents.defense = c.defense
    dp.contents.lscale = c.lscale
    dp.contents.rscale = c.rscale
    dp.contents.link_marker = c.link_marker
    sc = c.setcodes + [0]
    a = (ctypes.c_uint16 * len(sc))(*sc)
    _bufs.append(a)
    dp.contents.setcodes = ctypes.cast(a, ctypes.POINTER(ctypes.c_uint16))


def script_reader(payload, duel_handle, name):
    """Lua script dosyalarını yükler."""
    n = name.decode("utf-8") if isinstance(name, bytes) else name
    for pa in [SCRIPT_DIR / n, SCRIPT_DIR / "official" / n]:
        if pa.exists():
            c = pa.read_text(encoding="utf-8")
            cb = c.encode("utf-8")
            core._lib.OCG_LoadScript(duel_handle, cb, len(cb), n.encode("utf-8"))
            return 1
    return 0


# ---------------------------------------------------------------------------
# Otomatik Yanıt Sistemi
# ---------------------------------------------------------------------------

def auto_respond(msg, duel):
    """Herhangi bir interaktif mesaja otomatik (varsayılan) yanıt ver."""
    mt = msg.get("type", 0)
    if mt == MSG_SELECT_CHAIN:
        core.set_response(duel, build_chain_response(-1))
    elif mt == MSG_SELECT_IDLECMD:
        core.set_response(duel, build_idle_cmd_response("end"))
    elif mt == MSG_SELECT_BATTLECMD:
        core.set_response(duel, build_battle_cmd_response("end"))
    elif mt == MSG_SELECT_CARD:
        n = msg.get("min", 1)
        cards = msg.get("cards", [])
        core.set_response(duel, build_card_response(list(range(min(n, len(cards))))))
    elif mt == MSG_SELECT_PLACE:
        flag = msg.get("selectable", 0)
        for s in range(7):
            if not (flag & (1 << s)):
                core.set_response(duel, build_place_response(msg["player"], 0x04, s))
                return
        for s in range(8):
            if not (flag & (1 << (s + 8))):
                core.set_response(duel, build_place_response(msg["player"], 0x08, s))
                return
        core.set_response(duel, build_place_response(msg["player"], 0x04, 0))
    elif mt == MSG_SELECT_POSITION:
        core.set_response(duel, build_position_response(0x1))
    elif mt == MSG_SELECT_TRIBUTE:
        n = msg.get("min", 1)
        cards = msg.get("cards", [])
        core.set_response(duel, build_tribute_response(list(range(min(n, len(cards))))))
    elif mt == MSG_SELECT_EFFECTYN:
        core.set_response(duel, build_effectyn_response(True))
    elif mt == MSG_SELECT_YESNO:
        core.set_response(duel, build_yesno_response(True))
    elif mt == MSG_SELECT_OPTION:
        core.set_response(duel, build_option_response(0))
    elif mt == MSG_SELECT_SUM:
        must = msg.get("must_cards", [])
        sel = msg.get("selectable_cards", [])
        indices = list(range(len(must)))
        if sel:
            indices.append(len(must))
        core.set_response(duel, build_sum_response(indices))
    elif mt == MSG_SELECT_UNSELECT_CARD:
        sel = msg.get("selectable", [])
        core.set_response(duel, build_unselect_card_response(0 if sel else -1))
    elif mt == MSG_SELECT_COUNTER:
        cards = msg.get("cards", [])
        n = msg.get("count", 0)
        counts = [min(n, c.get("counter_count", 0)) if i == 0 else 0
                  for i, c in enumerate(cards)]
        core.set_response(duel, build_counter_response(counts))
    elif mt == MSG_ANNOUNCE_RACE:
        avail = msg.get("available", 1)
        core.set_response(duel, build_announce_race_response(avail & -avail))
    elif mt == MSG_ANNOUNCE_ATTRIB:
        avail = msg.get("available", 1)
        core.set_response(duel, build_announce_attrib_response(avail & -avail))
    else:
        core.set_response(duel, b"\x00\x00\x00\x00")


# ---------------------------------------------------------------------------
# Duel Yönetim Sınıfı
# ---------------------------------------------------------------------------

class DuelHelper:
    """Tek bir test düellosu oluşturup yönetir."""

    def __init__(self, lp=8000, flags=DUEL_MODE_MR2):
        self.duel = core.create_duel(
            card_reader=card_reader,
            script_reader=script_reader,
            starting_lp=lp,
            flags=flags,
        )
        # Lua standart scriptlerini yükle
        for n in ["constant.lua", "utility.lua"]:
            p = SCRIPT_DIR / n
            core.load_script(self.duel, p.read_text(encoding="utf-8"), n)

        self.messages = []     # Tüm parse edilmiş mesajlar
        self.errors = []       # Hatalar
        self.turn = 0
        self._destroyed = False

    def add_card(self, team, code, loc=LOCATION_DECK, seq=0,
                 pos=POS_FACEDOWN_DEFENSE):
        """Düelloya bir kart ekle."""
        core.add_card(self.duel, team=team, code=code, loc=loc, seq=seq, pos=pos)

    def add_deck(self, team, deck):
        """Tüm desteyi ekle."""
        for code in deck:
            self.add_card(team, code, loc=LOCATION_DECK)

    def add_to_hand(self, team, code):
        """Ele kart ekle."""
        self.add_card(team, code, loc=LOCATION_HAND)

    def add_to_field(self, team, code, seq=0, pos=POS_FACEUP_ATTACK):
        """Monster Zone'a kart koy."""
        self.add_card(team, code, loc=LOCATION_MZONE, seq=seq, pos=pos)

    def add_to_szone(self, team, code, seq=0, pos=POS_FACEDOWN_DEFENSE):
        """Spell/Trap Zone'a kart koy."""
        self.add_card(team, code, loc=LOCATION_SZONE, seq=seq, pos=pos)

    def add_to_grave(self, team, code):
        """Mezarlığa kart koy."""
        self.add_card(team, code, loc=LOCATION_GRAVE)

    def add_to_extra(self, team, code):
        """Extra Deck'e kart koy."""
        self.add_card(team, code, loc=LOCATION_EXTRA)

    def start(self):
        """Düelloyu başlat."""
        core.start_duel(self.duel)

    def process_step(self):
        """Motoru bir adım ilerlet, mesajları topla."""
        status = core.process(self.duel)
        raw = core.get_message(self.duel)
        parsed = []
        if raw:
            for mt, md in split_messages(raw):
                try:
                    msg = parse_message(mt, md)
                except Exception as e:
                    mn = MSG_NAMES.get(mt, "?")
                    self.errors.append(f"PARSE ERROR {mn}: {e}")
                    continue
                if mt == MSG_NEW_TURN:
                    self.turn += 1
                if mt == MSG_RETRY:
                    self.errors.append("RETRY")
                self.messages.append(msg)
                parsed.append(msg)
        return status, parsed

    def run_until_interactive(self, max_steps=200):
        """İnteraktif mesaj gelene kadar motoru çalıştır.
        Bilgi mesajlarına otomatik devam eder."""
        for _ in range(max_steps):
            status, msgs = self.process_step()
            for msg in msgs:
                if msg.get("interactive"):
                    return msg
            if status == DUEL_STATUS_END:
                return None
        return None

    def run_auto(self, max_steps=500, on_idle=None, on_battle=None,
                 on_interactive=None):
        """Düelloyu otomatik çalıştır.

        on_idle(msg, duel) → idle cmd handler (None = end)
        on_battle(msg, duel) → battle cmd handler (None = end)
        on_interactive(msg, duel) → diğer interaktif handler (None = auto_respond)
        """
        for _ in range(max_steps):
            status, msgs = self.process_step()
            for msg in msgs:
                if not msg.get("interactive"):
                    continue
                mt = msg.get("type", 0)
                if mt == MSG_SELECT_IDLECMD and on_idle:
                    on_idle(msg, self.duel)
                elif mt == MSG_SELECT_BATTLECMD and on_battle:
                    on_battle(msg, self.duel)
                elif msg.get("interactive"):
                    if on_interactive:
                        on_interactive(msg, self.duel)
                    else:
                        auto_respond(msg, self.duel)
            if status == DUEL_STATUS_END:
                break
            if len(self.errors) > 30:
                break
        return self

    def query_card(self, con, loc, seq, flags=None):
        """Tek bir kartı sorgula, dict olarak döndür."""
        if flags is None:
            flags = (QUERY_CODE | QUERY_POSITION | QUERY_ATTACK |
                     QUERY_DEFENSE | QUERY_LEVEL)
        raw = core.query(self.duel, con=con, loc=loc, seq=seq, flags=flags)
        if not raw or len(raw) < 8:
            return None
        return self._parse_query(raw, flags)

    def query_field_cards(self, con, loc):
        """Bir bölgedeki tüm kartları sorgula."""
        flags = QUERY_CODE | QUERY_POSITION | QUERY_ATTACK | QUERY_DEFENSE
        raw = core.query_location(self.duel, con=con, loc=loc, flags=flags)
        if not raw:
            return []
        return self._parse_query_location(raw, flags)

    def count_cards(self, con, loc):
        """Bir bölgedeki kart sayısını döndür."""
        return core.query_count(self.duel, con, loc)

    def get_messages_by_type(self, type_name):
        """Belirli tipteki mesajları filtrele."""
        return [m for m in self.messages
                if MSG_NAMES.get(m.get("type", 0)) == type_name]

    def has_message(self, type_name, **filters):
        """Belirli tipte ve filtrelerle eşleşen mesaj var mı?"""
        for m in self.messages:
            if MSG_NAMES.get(m.get("type", 0)) != type_name:
                continue
            if all(m.get(k) == v for k, v in filters.items()):
                return True
        return False

    def destroy(self):
        """Düelloyu temizle."""
        if not self._destroyed:
            core.destroy_duel(self.duel)
            self._destroyed = True

    def __del__(self):
        self.destroy()

    # --- Query parsing ---

    def _parse_query(self, raw, flags):
        """Tek kart query sonucunu parse et."""
        result = {}
        pos = 0
        # İlk 4 byte: toplam uzunluk
        if len(raw) < 4:
            return None
        total_len = struct.unpack_from("<I", raw, 0)[0]
        pos = 4
        # Sonraki 4 byte: flags
        if pos + 4 > len(raw):
            return result
        qflags = struct.unpack_from("<I", raw, pos)[0]
        pos += 4

        if qflags & QUERY_CODE and pos + 4 <= len(raw):
            result["code"] = struct.unpack_from("<I", raw, pos)[0]
            pos += 4
        if qflags & QUERY_POSITION and pos + 4 <= len(raw):
            result["position"] = struct.unpack_from("<I", raw, pos)[0]
            pos += 4
        if qflags & QUERY_ALIAS and pos + 4 <= len(raw):
            result["alias"] = struct.unpack_from("<I", raw, pos)[0]
            pos += 4
        if qflags & QUERY_TYPE and pos + 4 <= len(raw):
            result["card_type"] = struct.unpack_from("<I", raw, pos)[0]
            pos += 4
        if qflags & QUERY_LEVEL and pos + 4 <= len(raw):
            result["level"] = struct.unpack_from("<I", raw, pos)[0]
            pos += 4
        if qflags & QUERY_RANK and pos + 4 <= len(raw):
            result["rank"] = struct.unpack_from("<I", raw, pos)[0]
            pos += 4
        if qflags & QUERY_ATTRIBUTE and pos + 4 <= len(raw):
            result["attribute"] = struct.unpack_from("<I", raw, pos)[0]
            pos += 4
        if qflags & QUERY_RACE and pos + 8 <= len(raw):
            result["race"] = struct.unpack_from("<Q", raw, pos)[0]
            pos += 8
        if qflags & QUERY_ATTACK and pos + 4 <= len(raw):
            result["attack"] = struct.unpack_from("<i", raw, pos)[0]
            pos += 4
        if qflags & QUERY_DEFENSE and pos + 4 <= len(raw):
            result["defense"] = struct.unpack_from("<i", raw, pos)[0]
            pos += 4
        return result

    def _parse_query_location(self, raw, flags):
        """Bölge query sonucunu parse et — birden fazla kart."""
        cards = []
        pos = 0
        while pos + 4 <= len(raw):
            entry_len = struct.unpack_from("<I", raw, pos)[0]
            if entry_len <= 4:
                pos += 4
                continue
            entry = raw[pos:pos + entry_len]
            card = self._parse_query(entry, flags)
            if card:
                cards.append(card)
            pos += entry_len
        return cards


# ---------------------------------------------------------------------------
# Yaygın Desteler
# ---------------------------------------------------------------------------

FILLER_40 = [43096270] * 40   # Alexandrite Dragon x40
WOLF_40 = [69247929] * 40     # Gene-Warped Warwolf x40


# ---------------------------------------------------------------------------
# Test Runner
# ---------------------------------------------------------------------------

class TestRunner:
    """Basit test koşucusu — sonuçları toplar ve rapor eder."""

    def __init__(self, suite_name="Test Suite"):
        self.suite_name = suite_name
        self.passed = 0
        self.failed = 0
        self.results = []

    def test(self, name, fn):
        """Bir test fonksiyonunu çalıştır.
        fn() → (ok: bool, reason: str) döndürmeli.
        """
        print(f"\n{'─' * 50}")
        print(f"TEST: {name}")
        try:
            ok, reason = fn()
            if ok:
                print(f"  ✓ GEÇTİ — {reason}")
                self.passed += 1
                self.results.append((name, True, reason))
            else:
                print(f"  ✗ BAŞARISIZ — {reason}")
                self.failed += 1
                self.results.append((name, False, reason))
        except Exception as e:
            print(f"  ✗ HATA — {e}")
            self.failed += 1
            self.results.append((name, False, str(e)))

    def report(self):
        """Sonuç raporu yazdır."""
        total = self.passed + self.failed
        print(f"\n{'=' * 70}")
        print(f"  {self.suite_name}")
        print(f"  SONUÇ: {self.passed} GEÇTİ / {self.failed} BAŞARISIZ / {total} TOPLAM")
        print(f"{'=' * 70}")
        return self.failed == 0
