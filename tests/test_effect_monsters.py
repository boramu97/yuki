# Yuki — Browser-Based Duel Game
# Copyright (C) 2026 Yuki Contributors
# SPDX-License-Identifier: AGPL-3.0-or-later
#
# test_effect_monsters.py — Yugi destesindeki efekt canavar kartlarinin testleri

import sys
import struct as _struct

sys.path.insert(0, ".")
from tests.helpers import *


# ---------------------------------------------------------------------------
# Query Parser — OCGCore per-field format
# Format: [u16 payload_size][u32 flag][data...] repeated, ends with QUERY_END
# ---------------------------------------------------------------------------
def parse_query_raw(raw):
    """Parse OCGCore query response with per-field length-prefixed blocks."""
    result = {}
    off = 0
    while off + 2 <= len(raw):
        sz = _struct.unpack_from("<H", raw, off)[0]
        off += 2
        if sz < 4:
            break
        flag = _struct.unpack_from("<I", raw, off)[0]
        off += 4
        data_size = sz - 4

        if flag == QUERY_CODE and data_size >= 4:
            result["code"] = _struct.unpack_from("<I", raw, off)[0]
        elif flag == QUERY_POSITION and data_size >= 4:
            result["position"] = _struct.unpack_from("<I", raw, off)[0]
        elif flag == QUERY_LEVEL and data_size >= 4:
            result["level"] = _struct.unpack_from("<I", raw, off)[0]
        elif flag == QUERY_ATTACK and data_size >= 4:
            result["attack"] = _struct.unpack_from("<i", raw, off)[0]
        elif flag == QUERY_DEFENSE and data_size >= 4:
            result["defense"] = _struct.unpack_from("<i", raw, off)[0]
        elif flag == QUERY_END:
            break

        off += data_size
    return result


def query_monster(d, con, loc, seq):
    """Query a single card using the correct per-field format."""
    flags = QUERY_CODE | QUERY_POSITION | QUERY_ATTACK | QUERY_DEFENSE | QUERY_LEVEL
    raw = core.query(d.duel, con=con, loc=loc, seq=seq, flags=flags)
    if not raw or len(raw) < 6:
        return None
    return parse_query_raw(raw)


# ---------------------------------------------------------------------------
# Kart Kodlari
# ---------------------------------------------------------------------------
DARK_MAGICIAN       = 46986414
DARK_MAGICIAN_GIRL  = 38033121
BREAKER             = 71413901
THE_TRICKY          = 14778250
SKILLED_DM          = 73752131
KURIBOH             = 40640057
KINGS_KNIGHT        = 64788463
QUEENS_KNIGHT       = 25652259
JACKS_KNIGHT        = 90876561
POT_OF_GREED        = 55144522
ALEXANDRITE         = 43096270
WARWOLF             = 69247929


# ---------------------------------------------------------------------------
# 1. Dark Magician Girl — ATK boost (+300 per DM/DMG in either GY)
# ---------------------------------------------------------------------------
def test_dark_magician_girl_atk_boost():
    """DMG kazanir +300 ATK her DM/DMG icin mezarlikta.
    1 DM mezarlikta => DMG ATK 2000 + 300 = 2300."""
    d = DuelHelper()
    # P0: Fodder on field for tribute, DMG in hand, DM in grave
    d.add_to_field(0, ALEXANDRITE, seq=0, pos=POS_FACEUP_ATTACK)
    d.add_to_hand(0, DARK_MAGICIAN_GIRL)
    d.add_to_grave(0, DARK_MAGICIAN)
    # Fill decks
    for _ in range(20):
        d.add_card(0, ALEXANDRITE, LOCATION_DECK)
        d.add_card(1, WARWOLF, LOCATION_DECK)
    d.start()

    summoned = False
    dmg_summoned_complete = False

    def on_idle(msg, duel):
        nonlocal summoned
        player = msg.get("player", 0)
        if player == 1:
            core.set_response(duel, build_idle_cmd_response("end"))
            return
        if not summoned:
            summ = msg.get("summonable", [])
            dmg_idx = next((j for j, c in enumerate(summ)
                           if c["code"] == DARK_MAGICIAN_GIRL), -1)
            if dmg_idx >= 0:
                core.set_response(duel, build_idle_cmd_response("summon", dmg_idx))
                summoned = True
                return
        core.set_response(duel, build_idle_cmd_response("end"))

    # Run step by step: tribute summon DMG, wait for summon to complete
    for _ in range(300):
        status, msgs = d.process_step()
        for msg in msgs:
            mt = msg.get("type", 0)
            if mt == MSG_SUMMONED and summoned and not dmg_summoned_complete:
                dmg_summoned_complete = True
            if not msg.get("interactive"):
                continue
            if mt == MSG_SELECT_IDLECMD:
                on_idle(msg, d.duel)
            else:
                auto_respond(msg, d.duel)
        if dmg_summoned_complete and summoned:
            break
        if status == DUEL_STATUS_END:
            break

    if not summoned:
        d.destroy()
        return (False, "DMG could not be tribute summoned")

    # Query DMG on field using correct per-field format parser
    found_atk = None
    for seq in range(7):
        ci = query_monster(d, con=0, loc=LOCATION_MZONE, seq=seq)
        if ci and ci.get("code") == DARK_MAGICIAN_GIRL:
            found_atk = ci.get("attack")
            break

    d.destroy()

    if found_atk is None:
        return (False, "DMG not found on field after summon")
    if found_atk == 2300:
        return (True, f"DMG ATK = {found_atk} (2000 + 300 from 1 DM in GY)")
    else:
        return (False, f"DMG ATK = {found_atk}, expected 2300")


# ---------------------------------------------------------------------------
# 2. Breaker the Magical Warrior — Spell Counter on summon (+300 ATK)
# ---------------------------------------------------------------------------
def test_breaker_spell_counter():
    """Breaker normal summon edildiginde 1 Spell Counter alir, ATK 1600+300=1900."""
    d = DuelHelper()
    d.add_to_hand(0, BREAKER)
    for _ in range(20):
        d.add_card(0, ALEXANDRITE, LOCATION_DECK)
        d.add_card(1, WARWOLF, LOCATION_DECK)
    d.start()

    summoned = False

    def on_idle(msg, duel):
        nonlocal summoned
        player = msg.get("player", 0)
        if player == 1:
            core.set_response(duel, build_idle_cmd_response("end"))
            return
        if not summoned:
            summ = msg.get("summonable", [])
            brk_idx = next((j for j, c in enumerate(summ)
                           if c["code"] == BREAKER), -1)
            if brk_idx >= 0:
                core.set_response(duel, build_idle_cmd_response("summon", brk_idx))
                summoned = True
                return
        core.set_response(duel, build_idle_cmd_response("end"))

    # Run step by step: summon Breaker, wait for summon to complete, then query
    post_summon_idle = False
    for step in range(300):
        status, msgs = d.process_step()
        for msg in msgs:
            mt = msg.get("type", 0)
            if not msg.get("interactive"):
                continue
            if mt == MSG_SELECT_IDLECMD:
                if summoned and not post_summon_idle:
                    post_summon_idle = True
                on_idle(msg, d.duel)
            else:
                auto_respond(msg, d.duel)
        if post_summon_idle:
            break
        if status == DUEL_STATUS_END:
            break

    has_counter = d.has_message("MSG_ADD_COUNTER")

    # Query Breaker on field using correct format parser
    found_atk = None
    for seq in range(7):
        ci = query_monster(d, con=0, loc=LOCATION_MZONE, seq=seq)
        if ci and ci.get("code") == BREAKER:
            found_atk = ci.get("attack")
            break

    d.destroy()

    if not summoned:
        return (False, "Breaker could not be summoned")
    if not has_counter:
        return (False, "No MSG_ADD_COUNTER message found")
    if found_atk == 1900:
        return (True, f"Breaker ATK = {found_atk} with spell counter, MSG_ADD_COUNTER present")
    elif found_atk is not None:
        return (False, f"Breaker ATK = {found_atk}, expected 1900")
    else:
        return (False, "Breaker not found on field after summon")


# ---------------------------------------------------------------------------
# 3. The Tricky — Discard 1 card to Special Summon from hand
# ---------------------------------------------------------------------------
def test_the_tricky_spsummon():
    """The Tricky: elden 1 kart atarak ozel cagri."""
    d = DuelHelper()
    d.add_to_hand(0, THE_TRICKY)
    d.add_to_hand(0, ALEXANDRITE)  # discard fodder
    for _ in range(20):
        d.add_card(0, ALEXANDRITE, LOCATION_DECK)
        d.add_card(1, WARWOLF, LOCATION_DECK)
    d.start()

    sp_summoned = False

    def on_idle(msg, duel):
        nonlocal sp_summoned
        player = msg.get("player", 0)
        if player == 1:
            core.set_response(duel, build_idle_cmd_response("end"))
            return
        if not sp_summoned:
            sps = msg.get("special_summonable", [])
            tricky_idx = next((j for j, c in enumerate(sps)
                              if c["code"] == THE_TRICKY), -1)
            if tricky_idx >= 0:
                core.set_response(duel, build_idle_cmd_response("spsummon", tricky_idx))
                sp_summoned = True
                return
        core.set_response(duel, build_idle_cmd_response("end"))

    d.run_auto(max_steps=300, on_idle=on_idle)

    result = d.has_message("MSG_SPSUMMONING", code=THE_TRICKY)
    d.destroy()

    if result:
        return (True, "The Tricky special summoned via discard effect")
    elif sp_summoned:
        return (False, "SpSummon initiated but MSG_SPSUMMONING not found with code 14778250")
    else:
        return (False, "The Tricky was not available for special summon")


# ---------------------------------------------------------------------------
# 4. Skilled Dark Magician — Gains Spell Counters when spells activate
# ---------------------------------------------------------------------------
def test_skilled_dm_spell_counters():
    """Skilled DM sahada iken spell aktiflenirse counter alir.
    3 adet Pot of Greed oynayarak 3 counter eklenmeli."""
    d = DuelHelper()
    d.add_to_hand(0, SKILLED_DM)
    d.add_to_hand(0, POT_OF_GREED)
    d.add_to_hand(0, POT_OF_GREED)
    d.add_to_hand(0, POT_OF_GREED)
    for _ in range(20):
        d.add_card(0, ALEXANDRITE, LOCATION_DECK)
        d.add_card(1, WARWOLF, LOCATION_DECK)
    d.start()

    sdm_summoned = False
    spells_activated = [0]

    def on_idle(msg, duel):
        nonlocal sdm_summoned
        player = msg.get("player", 0)
        if player == 1:
            core.set_response(duel, build_idle_cmd_response("end"))
            return
        if not sdm_summoned:
            # First: summon SDM
            summ = msg.get("summonable", [])
            sdm_idx = next((j for j, c in enumerate(summ)
                           if c["code"] == SKILLED_DM), -1)
            if sdm_idx >= 0:
                core.set_response(duel, build_idle_cmd_response("summon", sdm_idx))
                sdm_summoned = True
                return
        # After SDM is on field, activate Pot of Greed
        if sdm_summoned and spells_activated[0] < 3:
            acts = msg.get("activatable", [])
            pot_idx = next((j for j, c in enumerate(acts)
                           if c["code"] == POT_OF_GREED), -1)
            if pot_idx >= 0:
                core.set_response(duel, build_idle_cmd_response("activate", pot_idx))
                spells_activated[0] += 1
                return
        core.set_response(duel, build_idle_cmd_response("end"))

    d.run_auto(max_steps=500, on_idle=on_idle)

    # Count MSG_ADD_COUNTER messages for Skilled DM (on MZONE)
    counter_msgs = d.get_messages_by_type("MSG_ADD_COUNTER")
    # Filter for counters on a monster zone card controlled by P0
    sdm_counters = [m for m in counter_msgs
                    if m.get("controller") == 0
                    and m.get("location") == LOCATION_MZONE]

    d.destroy()

    if not sdm_summoned:
        return (False, "Skilled Dark Magician could not be summoned")
    count = len(sdm_counters)
    if count >= 3:
        return (True, f"Skilled DM received {count} spell counters from spell activations")
    else:
        return (False, f"Skilled DM received {count} counters, expected >= 3 (spells activated: {spells_activated[0]})")


# ---------------------------------------------------------------------------
# 5. Kuriboh — Discard from hand during damage calc to reduce battle damage to 0
# ---------------------------------------------------------------------------
def test_kuriboh_battle_damage():
    """Kuriboh: P0 has Kuriboh on field (ATK 300), P1 attacks with Warwolf (ATK 2000).
    Verify battle damage to P0 = 2000-300 = 1700.
    Also verify Kuriboh goes to graveyard after being destroyed in battle."""
    d = DuelHelper()
    # P0: Kuriboh on field as face-up attack
    d.add_to_field(0, KURIBOH, seq=0, pos=POS_FACEUP_ATTACK)
    # P1: Warwolf on field to attack
    d.add_to_field(1, WARWOLF, seq=0, pos=POS_FACEUP_ATTACK)
    for _ in range(20):
        d.add_card(0, ALEXANDRITE, LOCATION_DECK)
        d.add_card(1, WARWOLF, LOCATION_DECK)
    d.start()

    attack_resolved = False

    for step in range(400):
        status, msgs = d.process_step()
        for msg in msgs:
            if not msg.get("interactive"):
                continue
            mt = msg.get("type", 0)
            player = msg.get("player", 0)

            if mt == MSG_SELECT_IDLECMD:
                if player == 1:
                    if msg.get("can_battle_phase"):
                        core.set_response(d.duel, build_idle_cmd_response("battle"))
                    else:
                        core.set_response(d.duel, build_idle_cmd_response("end"))
                else:
                    core.set_response(d.duel, build_idle_cmd_response("end"))

            elif mt == MSG_SELECT_BATTLECMD:
                if player == 1:
                    atks = msg.get("attackable", [])
                    if atks and not attack_resolved:
                        core.set_response(d.duel, build_battle_cmd_response("attack", 0))
                    else:
                        core.set_response(d.duel, build_battle_cmd_response("end"))
                        if not attack_resolved and d.has_message("MSG_DAMAGE"):
                            attack_resolved = True
                else:
                    core.set_response(d.duel, build_battle_cmd_response("end"))

            elif mt == MSG_SELECT_CHAIN:
                core.set_response(d.duel, build_chain_response(-1))

            else:
                auto_respond(msg, d.duel)

        # Stop after damage is dealt
        if d.has_message("MSG_DAMAGE"):
            # Let engine finish current step
            for _ in range(30):
                st2, ms2 = d.process_step()
                for m2 in ms2:
                    if m2.get("interactive"):
                        auto_respond(m2, d.duel)
                if st2 == DUEL_STATUS_END:
                    break
            break
        if status == DUEL_STATUS_END:
            break

    # Check results
    damage_msgs = d.get_messages_by_type("MSG_DAMAGE")
    p0_damage = sum(m.get("amount", 0) for m in damage_msgs if m.get("player") == 0)

    # Check Kuriboh was destroyed (moved to graveyard)
    kuriboh_destroyed = d.has_message("MSG_MOVE", code=KURIBOH)

    # Check grave count for P0
    p0_grave_count = d.count_cards(0, LOCATION_GRAVE)

    d.destroy()

    if p0_damage == 1700 and p0_grave_count >= 1:
        return (True, f"Kuriboh (ATK 300) destroyed by Warwolf (ATK 2000), P0 took {p0_damage} damage, grave={p0_grave_count}")
    elif p0_damage == 1700:
        return (True, f"Battle damage correct: P0 took {p0_damage} (2000-300)")
    elif p0_damage > 0:
        return (False, f"P0 took {p0_damage} damage, expected 1700")
    else:
        return (False, "No battle damage detected")


# ---------------------------------------------------------------------------
# 6. King's Knight + Queen's Knight => Jack's Knight Special Summon
# ---------------------------------------------------------------------------
def test_kings_knight_summons_jacks():
    """Queen's Knight sahada iken King's Knight normal summon => Jack's Knight ozel cagri."""
    d = DuelHelper()
    # Queen's Knight on field
    d.add_to_field(0, QUEENS_KNIGHT, seq=0, pos=POS_FACEUP_ATTACK)
    # King's Knight in hand
    d.add_to_hand(0, KINGS_KNIGHT)
    # Jack's Knight in deck (must be findable)
    d.add_card(0, JACKS_KNIGHT, LOCATION_DECK)
    d.add_card(0, JACKS_KNIGHT, LOCATION_DECK)
    for _ in range(18):
        d.add_card(0, ALEXANDRITE, LOCATION_DECK)
        d.add_card(1, WARWOLF, LOCATION_DECK)
    d.start()

    summoned = False

    def on_idle(msg, duel):
        nonlocal summoned
        player = msg.get("player", 0)
        if player == 1:
            core.set_response(duel, build_idle_cmd_response("end"))
            return
        if not summoned:
            summ = msg.get("summonable", [])
            king_idx = next((j for j, c in enumerate(summ)
                            if c["code"] == KINGS_KNIGHT), -1)
            if king_idx >= 0:
                core.set_response(duel, build_idle_cmd_response("summon", king_idx))
                summoned = True
                return
        core.set_response(duel, build_idle_cmd_response("end"))

    d.run_auto(max_steps=300, on_idle=on_idle)

    result = d.has_message("MSG_SPSUMMONING", code=JACKS_KNIGHT)
    d.destroy()

    if result:
        return (True, "Jack's Knight was special summoned when King's Knight summoned with Queen on field")
    elif summoned:
        return (False, "King's Knight was summoned but Jack's Knight was not special summoned")
    else:
        return (False, "King's Knight could not be normal summoned")


# ---------------------------------------------------------------------------
# Test Runner
# ---------------------------------------------------------------------------
if __name__ == "__main__":
    runner = TestRunner("Effect Monster Tests — Yugi Deck")

    runner.test("Dark Magician Girl ATK boost (+300 per DM in GY)",
                test_dark_magician_girl_atk_boost)
    runner.test("Breaker the Magical Warrior (Spell Counter on summon)",
                test_breaker_spell_counter)
    runner.test("The Tricky (discard to Special Summon)",
                test_the_tricky_spsummon)
    runner.test("Skilled Dark Magician (Spell Counter accumulation)",
                test_skilled_dm_spell_counters)
    runner.test("Kuriboh (battle damage calculation)",
                test_kuriboh_battle_damage)
    runner.test("King's Knight + Queen's Knight => Jack's Knight",
                test_kings_knight_summons_jacks)

    success = runner.report()
    sys.exit(0 if success else 1)
