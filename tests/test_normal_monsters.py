# Yuki — Browser-Based Duel Game
# Copyright (C) 2026 Yuki Contributors
# SPDX-License-Identifier: AGPL-3.0-or-later
#
# test_normal_monsters.py — Normal canavar mekanik testleri
#
# Test edilen kartlar:
#   67724379  Koumori Dragon     (Lv4 ATK 1500 DEF 1200)
#   15025844  Mystical Elf       (Lv4 ATK  800 DEF 2000)
#   87796900  Winged Dragon GotF (Lv4 ATK 1400 DEF 1200)
#   70781052  Summoned Skull     (Lv6 ATK 2500 DEF 1200 — 1 kurban)
#   46986414  Dark Magician      (Lv7 ATK 2500 DEF 2100 — 2 kurban)
#   78193831  Buster Blader      (Lv7 ATK 2600 DEF 2300 — 2 kurban)

import sys
sys.path.insert(0, ".")
from tests.helpers import *

# Kart kodlari
KOUMORI       = 67724379   # Lv4 ATK 1500 DEF 1200
MYSTICAL_ELF  = 15025844   # Lv4 ATK  800 DEF 2000
WINGED_DRAGON = 87796900   # Lv4 ATK 1400 DEF 1200
SUMMONED_SKULL = 70781052  # Lv6 ATK 2500 DEF 1200
DARK_MAGICIAN = 46986414   # Lv7 ATK 2500 DEF 2100
BUSTER_BLADER = 78193831   # Lv7 ATK 2600 DEF 2300
FILLER        = 43096270   # Alexandrite Dragon (dolgu)


# =========================================================================
# 1) Normal Summon Lv4
# =========================================================================

def test_normal_summon_lv4():
    d = DuelHelper()
    d.add_to_hand(0, KOUMORI)
    for _ in range(40):
        d.add_card(0, FILLER, LOCATION_DECK)
    d.add_deck(1, WOLF_40)
    d.start()

    activated = False

    def on_idle(msg, duel):
        nonlocal activated
        if msg.get("player") != 0:
            core.set_response(duel, build_idle_cmd_response("end"))
            return
        if not activated:
            summ = msg.get("summonable", [])
            idx = next((j for j, c in enumerate(summ) if c["code"] == KOUMORI), -1)
            if idx >= 0:
                core.set_response(duel, build_idle_cmd_response("summon", idx))
                activated = True
                return
        core.set_response(duel, build_idle_cmd_response("end"))

    d.run_auto(on_idle=on_idle)

    found_summoning = d.has_message("MSG_SUMMONING", code=KOUMORI)
    found_summoned = d.has_message("MSG_SUMMONED")
    ok = found_summoning and found_summoned
    d.destroy()
    return (ok,
            "Koumori Dragon basariyla sahaya cagrildi"
            if ok else
            f"Summon mesaji bulunamadi (SUMMONING={found_summoning}, SUMMONED={found_summoned})")


# =========================================================================
# 2) Tribute Summon Lv6 (1 kurban)
# =========================================================================

def test_tribute_summon_lv6():
    d = DuelHelper()
    # P0: Summoned Skull elde, 1 fodder sahada
    d.add_to_hand(0, SUMMONED_SKULL)
    d.add_to_field(0, FILLER, seq=0, pos=POS_FACEUP_ATTACK)
    for _ in range(40):
        d.add_card(0, FILLER, LOCATION_DECK)
    d.add_deck(1, WOLF_40)
    d.start()

    activated = False

    def on_idle(msg, duel):
        nonlocal activated
        if msg.get("player") != 0:
            core.set_response(duel, build_idle_cmd_response("end"))
            return

        summ = msg.get("summonable", [])

        if not activated:
            skull_idx = next((j for j, c in enumerate(summ)
                              if c["code"] == SUMMONED_SKULL), -1)
            if skull_idx >= 0:
                core.set_response(duel, build_idle_cmd_response("summon", skull_idx))
                activated = True
                return

        core.set_response(duel, build_idle_cmd_response("end"))

    d.run_auto(on_idle=on_idle)

    found = d.has_message("MSG_SUMMONING", code=SUMMONED_SKULL)
    d.destroy()
    return (found,
            "Summoned Skull 1 kurbanla basariyla cagrildi"
            if found else
            "Tribute summon mesaji bulunamadi")


# =========================================================================
# 3) Tribute Summon Lv7 (2 kurban)
# =========================================================================

def test_tribute_summon_lv7():
    d = DuelHelper()
    # P0: Dark Magician elde, 2 fodder sahada
    d.add_to_hand(0, DARK_MAGICIAN)
    d.add_to_field(0, FILLER, seq=0, pos=POS_FACEUP_ATTACK)
    d.add_to_field(0, FILLER, seq=1, pos=POS_FACEUP_ATTACK)
    for _ in range(40):
        d.add_card(0, FILLER, LOCATION_DECK)
    d.add_deck(1, WOLF_40)
    d.start()

    activated = False

    def on_idle(msg, duel):
        nonlocal activated
        if msg.get("player") != 0:
            core.set_response(duel, build_idle_cmd_response("end"))
            return

        summ = msg.get("summonable", [])

        if not activated:
            dm_idx = next((j for j, c in enumerate(summ)
                           if c["code"] == DARK_MAGICIAN), -1)
            if dm_idx >= 0:
                core.set_response(duel, build_idle_cmd_response("summon", dm_idx))
                activated = True
                return

        core.set_response(duel, build_idle_cmd_response("end"))

    d.run_auto(on_idle=on_idle)

    found = d.has_message("MSG_SUMMONING", code=DARK_MAGICIAN)
    d.destroy()
    return (found,
            "Dark Magician 2 kurbanla basariyla cagrildi"
            if found else
            "2-kurban tribute summon mesaji bulunamadi")


# =========================================================================
# 4) Set monster (yuz-asagi savunma)
# =========================================================================

def test_set_monster():
    d = DuelHelper()
    d.add_to_hand(0, KOUMORI)
    for _ in range(40):
        d.add_card(0, FILLER, LOCATION_DECK)
    d.add_deck(1, WOLF_40)
    d.start()

    activated = False

    def on_idle(msg, duel):
        nonlocal activated
        if msg.get("player") != 0:
            core.set_response(duel, build_idle_cmd_response("end"))
            return
        if not activated:
            mset = msg.get("monster_setable", [])
            idx = next((j for j, c in enumerate(mset)
                        if c["code"] == KOUMORI), -1)
            if idx >= 0:
                core.set_response(duel, build_idle_cmd_response("mset", idx))
                activated = True
                return
        core.set_response(duel, build_idle_cmd_response("end"))

    d.run_auto(on_idle=on_idle)

    found = d.has_message("MSG_SET", code=KOUMORI)
    d.destroy()
    return (found,
            "Koumori Dragon yuz-asagi savunmaya set edildi"
            if found else
            "SET mesaji bulunamadi")


# =========================================================================
# 5) Battle damage: ATK 1500 vs ATK 1400 => 100 hasar savunana
# =========================================================================

def test_battle_damage():
    d = DuelHelper()
    # P0: Koumori Dragon sahada (ATK 1500)
    d.add_to_field(0, KOUMORI, seq=0, pos=POS_FACEUP_ATTACK)
    for _ in range(40):
        d.add_card(0, FILLER, LOCATION_DECK)
    # P1: Winged Dragon sahada (ATK 1400)
    d.add_to_field(1, WINGED_DRAGON, seq=0, pos=POS_FACEUP_ATTACK)
    for _ in range(40):
        d.add_card(1, FILLER, LOCATION_DECK)
    d.start()

    attacked = False

    def on_idle(msg, duel):
        nonlocal attacked
        if msg.get("player") != 0:
            core.set_response(duel, build_idle_cmd_response("end"))
            return
        if not attacked and msg.get("can_battle_phase"):
            core.set_response(duel, build_idle_cmd_response("battle"))
            return
        core.set_response(duel, build_idle_cmd_response("end"))

    def on_battle(msg, duel):
        nonlocal attacked
        if msg.get("player") != 0:
            core.set_response(duel, build_battle_cmd_response("end"))
            return
        atks = msg.get("attackable", [])
        if atks and not attacked:
            core.set_response(duel, build_battle_cmd_response("attack", 0))
            attacked = True
            return
        core.set_response(duel, build_battle_cmd_response("end"))

    d.run_auto(on_idle=on_idle, on_battle=on_battle)

    # P1'e 100 hasar gelmeli (1500 - 1400 = 100)
    damage_msgs = d.get_messages_by_type("MSG_DAMAGE")
    found_100 = any(m.get("player") == 1 and m.get("amount") == 100
                    for m in damage_msgs)
    d.destroy()
    return (found_100,
            "ATK 1500 vs ATK 1400 => P1'e 100 hasar verildi"
            if found_100 else
            f"100 hasar bulunamadi, damage mesajlari: {[(m.get('player'), m.get('amount')) for m in damage_msgs[:5]]}")


# =========================================================================
# 6) Battle: ATK vs DEF — ATK 1400 saldirir, DEF 2000 => 600 hasar saldirana
# =========================================================================

def test_battle_atk_vs_def():
    d = DuelHelper()
    # P0: Winged Dragon sahada (ATK 1400)
    d.add_to_field(0, WINGED_DRAGON, seq=0, pos=POS_FACEUP_ATTACK)
    for _ in range(40):
        d.add_card(0, FILLER, LOCATION_DECK)
    # P1: Mystical Elf savunmada (DEF 2000)
    d.add_to_field(1, MYSTICAL_ELF, seq=0, pos=POS_FACEUP_DEFENSE)
    for _ in range(40):
        d.add_card(1, FILLER, LOCATION_DECK)
    d.start()

    attacked = False

    def on_idle(msg, duel):
        nonlocal attacked
        if msg.get("player") != 0:
            core.set_response(duel, build_idle_cmd_response("end"))
            return
        if not attacked and msg.get("can_battle_phase"):
            core.set_response(duel, build_idle_cmd_response("battle"))
            return
        core.set_response(duel, build_idle_cmd_response("end"))

    def on_battle(msg, duel):
        nonlocal attacked
        if msg.get("player") != 0:
            core.set_response(duel, build_battle_cmd_response("end"))
            return
        atks = msg.get("attackable", [])
        if atks and not attacked:
            core.set_response(duel, build_battle_cmd_response("attack", 0))
            attacked = True
            return
        core.set_response(duel, build_battle_cmd_response("end"))

    d.run_auto(on_idle=on_idle, on_battle=on_battle)

    # P0'a 600 hasar gelmeli (2000 - 1400 = 600)
    damage_msgs = d.get_messages_by_type("MSG_DAMAGE")
    found_600 = any(m.get("player") == 0 and m.get("amount") == 600
                    for m in damage_msgs)
    d.destroy()
    return (found_600,
            "ATK 1400 vs DEF 2000 => P0'a 600 hasar verildi"
            if found_600 else
            f"600 hasar bulunamadi, damage mesajlari: {[(m.get('player'), m.get('amount')) for m in damage_msgs[:5]]}")


# =========================================================================
# 7) Battle: equal ATK — ATK 1500 vs ATK 1500 => 0 hasar, ikisi de yok
# =========================================================================

def test_battle_equal_atk():
    d = DuelHelper()
    # P0: Koumori Dragon (ATK 1500)
    d.add_to_field(0, KOUMORI, seq=0, pos=POS_FACEUP_ATTACK)
    for _ in range(40):
        d.add_card(0, FILLER, LOCATION_DECK)
    # P1: Koumori Dragon (ATK 1500)
    d.add_to_field(1, KOUMORI, seq=0, pos=POS_FACEUP_ATTACK)
    for _ in range(40):
        d.add_card(1, FILLER, LOCATION_DECK)
    d.start()

    attacked = False

    def on_idle(msg, duel):
        nonlocal attacked
        if msg.get("player") != 0:
            core.set_response(duel, build_idle_cmd_response("end"))
            return
        if not attacked and msg.get("can_battle_phase"):
            core.set_response(duel, build_idle_cmd_response("battle"))
            return
        core.set_response(duel, build_idle_cmd_response("end"))

    def on_battle(msg, duel):
        nonlocal attacked
        if msg.get("player") != 0:
            core.set_response(duel, build_battle_cmd_response("end"))
            return
        atks = msg.get("attackable", [])
        if atks and not attacked:
            core.set_response(duel, build_battle_cmd_response("attack", 0))
            attacked = True
            return
        core.set_response(duel, build_battle_cmd_response("end"))

    d.run_auto(on_idle=on_idle, on_battle=on_battle)

    # Hasar mesaji olmamali (esit ATK => 0 hasar)
    # Ama MSG_BATTLE mesajinda ikisi de yok edilmeli
    battle_msgs = d.get_messages_by_type("MSG_BATTLE")
    damage_msgs = d.get_messages_by_type("MSG_DAMAGE")

    # Esit ATK durumunda hasar olmaz, ama ikisi de yok olur
    # Hasar 0 oldugundan MSG_DAMAGE gelmeyebilir
    no_damage = not any(m.get("amount", 0) > 0 for m in damage_msgs)

    # MSG_BATTLE mesajinda her iki taraf da destroyed olmali
    both_destroyed = any(
        m.get("attacker_destroyed") and m.get("target_destroyed")
        for m in battle_msgs
    )

    ok = no_damage and both_destroyed
    d.destroy()
    return (ok,
            "ATK 1500 vs ATK 1500 => 0 hasar, her iki canavar yok edildi"
            if ok else
            f"Beklenen sonuc bulunamadi (no_damage={no_damage}, both_destroyed={both_destroyed}, "
            f"damages={[(m.get('player'), m.get('amount')) for m in damage_msgs[:5]]}, "
            f"battles={[(m.get('attacker_destroyed'), m.get('target_destroyed')) for m in battle_msgs[:3]]})")


# =========================================================================
# Test Runner
# =========================================================================

if __name__ == "__main__":
    runner = TestRunner("Normal Monster Mekanik Testleri")

    runner.test("Normal Summon Lv4 (Koumori Dragon)", test_normal_summon_lv4)
    runner.test("Tribute Summon Lv6 — 1 kurban (Summoned Skull)", test_tribute_summon_lv6)
    runner.test("Tribute Summon Lv7 — 2 kurban (Dark Magician)", test_tribute_summon_lv7)
    runner.test("Set Monster yuz-asagi savunma (Koumori Dragon)", test_set_monster)
    runner.test("Battle damage: ATK 1500 vs ATK 1400", test_battle_damage)
    runner.test("Battle: ATK 1400 vs DEF 2000", test_battle_atk_vs_def)
    runner.test("Battle: esit ATK 1500 vs ATK 1500", test_battle_equal_atk)

    runner.report()
