# Yuki — Bot vs Bot Simulator
# Her iki team icin ai_respond'la motor surer; regression metriklerini toplar.
#
# Kullanim:
#   from tests.ai_sim.simulator import simulate_match
#   result = simulate_match(YUGI_DECK, "Yugi", KAIBA_DECK, "Kaiba")
#   print(result)  # {winner, turn_count, retry_total, max_retry_streak, deadlock, steps}

from __future__ import annotations

import ctypes
import os
import struct
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

from server.ocg_binding import (
    OCGCore,
    DUEL_MODE_MR2,
    LOCATION_DECK, LOCATION_EXTRA, LOCATION_MZONE,
    POS_FACEDOWN_DEFENSE,
    TYPE_FUSION, TYPE_SYNCHRO, TYPE_XYZ, TYPE_LINK,
    QUERY_CODE, QUERY_ATTACK, QUERY_DEFENSE, QUERY_POSITION,
    MSG_NEW_TURN, MSG_WIN, MSG_RETRY,
    MSG_SELECT_BATTLECMD,
    MSG_NAMES,
)
from server.message_parser import split_messages, parse_message
from server.card_database import CardDatabase
from server.config import SCRIPT_DIR, CARD_DB_PATH
from server.ai_player import ai_respond

EXTRA_TYPE_MASK = TYPE_FUSION | TYPE_SYNCHRO | TYPE_XYZ | TYPE_LINK
SYSTEM_SCRIPTS = ["constant.lua", "utility.lua", "archetype_setcode_constants.lua"]

# ---------------------------------------------------------------------------
# Global motor + DB (process'de tek instance, multiple duel)
# ---------------------------------------------------------------------------
_db = CardDatabase(CARD_DB_PATH)
_core = OCGCore()
_buffers: list = []


def _card_reader(payload, code, dp):
    c = _db.get_card(code)
    if not c:
        dp.contents.code = code
        e = (ctypes.c_uint16 * 1)(0)
        _buffers.append(e)
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
    _buffers.append(a)
    dp.contents.setcodes = ctypes.cast(a, ctypes.POINTER(ctypes.c_uint16))


def _script_reader(payload, duel_handle, name):
    n = name.decode("utf-8") if isinstance(name, bytes) else name
    for pa in [SCRIPT_DIR / n, SCRIPT_DIR / "official" / n]:
        if pa.exists():
            c = pa.read_text(encoding="utf-8")
            cb = c.encode("utf-8")
            _core._lib.OCG_LoadScript(duel_handle, cb, len(cb), n.encode("utf-8"))
            return 1
    return 0


def _split_deck(deck: list[int]) -> tuple[list[int], list[int]]:
    """Extra deck'e gidecek kartlari (fusion/synchro/xyz/link) ayir."""
    main, extra = [], []
    for code in deck:
        c = _db.get_card(code)
        if c and c.type & EXTRA_TYPE_MASK:
            extra.append(code)
        else:
            main.append(code)
    return main, extra


def _query_opp_monsters(duel, team: int) -> list[dict]:
    """Rakip mzone'daki canavarlari query eder; _battle_cmd icin gerekli."""
    monsters = []
    flags = QUERY_CODE | QUERY_POSITION | QUERY_ATTACK | QUERY_DEFENSE
    for seq in range(7):
        try:
            raw = _core.query(duel, con=team, loc=LOCATION_MZONE, seq=seq, flags=flags)
        except Exception:
            continue
        if not raw or len(raw) < 8:
            continue
        # Raw parse: u32 total_len + {[u16 sz][u32 flag][data]}*
        info = {"position": 0, "atk": 0, "def": 0, "code": 0}
        off = 4
        while off + 2 <= len(raw):
            sz = struct.unpack_from("<H", raw, off)[0]
            off += 2
            if sz < 4:
                continue
            if off + 4 > len(raw):
                break
            flag = struct.unpack_from("<I", raw, off)[0]
            off += 4
            data_size = sz - 4
            if flag == QUERY_CODE and data_size >= 4:
                info["code"] = struct.unpack_from("<I", raw, off)[0]
            elif flag == QUERY_POSITION and data_size >= 4:
                info["position"] = struct.unpack_from("<I", raw, off)[0]
            elif flag == QUERY_ATTACK and data_size >= 4:
                info["atk"] = struct.unpack_from("<i", raw, off)[0]
            elif flag == QUERY_DEFENSE and data_size >= 4:
                info["def"] = struct.unpack_from("<i", raw, off)[0]
            elif flag == 0x80000000:
                break
            off += data_size
        if info["code"]:
            monsters.append(info)
    return monsters


def simulate_match(
    deck_a: list[int], bot_name_a: str,
    deck_b: list[int], bot_name_b: str,
    *,
    max_steps: int = 5000,
    max_retry_streak: int = 15,
    verbose: bool = False,
) -> dict:
    """Iki bot arasinda duello oynat, regression metriklerini dondur.

    deck_a: team 0 destesi (flat, main+extra karisik — otomatik split)
    deck_b: team 1 destesi
    bot_name_a/b: ai_profiles.PROFILES key'i (Yugi, Kaiba, ...)

    return: {
        winner: -1 | 0 | 1,
        turn_count: int,
        retry_total: int,
        max_retry_streak: int,
        deadlock: bool,  # True = max_retry_streak asildi
        steps: int,
        timeout: bool,  # True = max_steps asildi, kazanan belirlenmedi
        error: str | None,
    }
    """
    duel = _core.create_duel(_card_reader, _script_reader, starting_lp=8000, flags=DUEL_MODE_MR2)
    for n in SYSTEM_SCRIPTS:
        p = SCRIPT_DIR / n
        if p.exists():
            _core.load_script(duel, p.read_text(encoding="utf-8"), n)

    main_a, extra_a = _split_deck(deck_a)
    main_b, extra_b = _split_deck(deck_b)
    for code in main_a:
        _core.add_card(duel, team=0, code=code, loc=LOCATION_DECK, seq=0, pos=POS_FACEDOWN_DEFENSE)
    for code in extra_a:
        _core.add_card(duel, team=0, code=code, loc=LOCATION_EXTRA, seq=0, pos=POS_FACEDOWN_DEFENSE)
    for code in main_b:
        _core.add_card(duel, team=1, code=code, loc=LOCATION_DECK, seq=0, pos=POS_FACEDOWN_DEFENSE)
    for code in extra_b:
        _core.add_card(duel, team=1, code=code, loc=LOCATION_EXTRA, seq=0, pos=POS_FACEDOWN_DEFENSE)
    _core.start_duel(duel)

    bot_names = [bot_name_a, bot_name_b]
    winner = -1
    turn_count = 0
    retry_total = 0
    retry_streak = 0
    max_streak_observed = 0
    deadlock = False
    timeout = False
    error_str = None
    last_msg_type = None
    last_msg: dict | None = None
    last_player = 0
    steps_done = 0

    try:
        for step in range(max_steps):
            steps_done = step
            _core.process(duel)
            raw = _core.get_message(duel)
            if not raw:
                # Motor cevap bekliyor — son mesaja zaten response verdik; devam
                continue

            end_loop = False
            for mt, md in split_messages(raw):
                if mt == MSG_NEW_TURN:
                    turn_count += 1
                    if verbose:
                        print(f"  [turn {turn_count}]")
                    continue
                if mt == MSG_WIN:
                    try:
                        m = parse_message(mt, md)
                        winner = m.get("player", -1)
                    except Exception:
                        pass
                    end_loop = True
                    break
                if mt == MSG_RETRY:
                    retry_total += 1
                    retry_streak += 1
                    if retry_streak > max_streak_observed:
                        max_streak_observed = retry_streak
                    if retry_streak >= max_retry_streak:
                        deadlock = True
                        if verbose:
                            mn = MSG_NAMES.get(last_msg_type or 0, "?")
                            print(f"  [DEADLOCK] last_msg={mn} player={last_player} streak={retry_streak}")
                            if last_msg:
                                keys = [k for k in ("forced", "min", "max", "count", "cancelable") if k in last_msg]
                                snippet = {k: last_msg[k] for k in keys}
                                print(f"           last_msg summary={snippet}")
                        end_loop = True
                        break
                    if last_msg_type is not None and last_msg is not None:
                        try:
                            resp = ai_respond(
                                last_msg_type, last_msg,
                                retry_attempt=retry_streak,
                                bot_name=bot_names[last_player],
                            )
                        except Exception as e:
                            if verbose:
                                print(f"  [retry AI err] {e}")
                            resp = b"\xff\xff\xff\xff"
                        _core.set_response(duel, resp)
                    continue

                # Diger mesajlari parse et
                try:
                    m = parse_message(mt, md)
                except Exception:
                    continue
                if not m.get("interactive"):
                    continue
                # Yeni interaktif — streak sifir
                retry_streak = 0
                p = m.get("player", 0)
                last_player = p
                if mt == MSG_SELECT_BATTLECMD:
                    m["opponent_monsters"] = _query_opp_monsters(duel, 1 - p)
                last_msg_type = mt
                last_msg = m
                try:
                    resp = ai_respond(
                        mt, m, retry_attempt=0, bot_name=bot_names[p],
                    )
                except Exception as e:
                    if verbose:
                        mn = MSG_NAMES.get(mt, "?")
                        print(f"  [ai err] {mn}: {e}")
                    resp = b"\xff\xff\xff\xff"
                _core.set_response(duel, resp)

            if end_loop:
                break
        else:
            # max_steps asildi
            timeout = True
    except Exception as e:
        error_str = str(e)
    finally:
        try:
            _core.destroy_duel(duel)
        except Exception:
            pass

    deadlock_msg_name = MSG_NAMES.get(last_msg_type, "?") if (deadlock and last_msg_type is not None) else None
    return {
        "winner": winner,
        "turn_count": turn_count,
        "retry_total": retry_total,
        "max_retry_streak": max_streak_observed,
        "deadlock": deadlock,
        "deadlock_msg": deadlock_msg_name,
        "deadlock_player": last_player if deadlock else None,
        "timeout": timeout,
        "steps": steps_done,
        "bot_a": bot_name_a,
        "bot_b": bot_name_b,
        "error": error_str,
    }


if __name__ == "__main__":
    # Hizli manuel test — Yugi vs Kaiba tek match
    from server.decks import YUGI_DECK, KAIBA_DECK
    result = simulate_match(YUGI_DECK, "Yugi", KAIBA_DECK, "Kaiba", verbose=True)
    print(result)
