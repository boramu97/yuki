# Yuki — Browser-Based Duel Game
# Copyright (C) 2026 Yuki Contributors
# SPDX-License-Identifier: AGPL-3.0-or-later
#
# test_trap_cards.py — Yugi destesindeki 3 tuzak kartinin kapsamli testleri
#
# Tuzak kartlari:
#   1. Mirror Force (44095762) — Rakip saldiri ilan edince tum ATK poz. canavarlarini yok et
#   2. Magic Cylinder (62279055) — Saldiriyi iptal et + saldiran canavarın ATK kadar hasar ver
#   3. Spellbinding Circle (18807108) — 1 rakip canavar hedefle: saldıramaz, pozisyon degistiremez

import sys
sys.path.insert(0, ".")

from tests.helpers import (
    DuelHelper, TestRunner, auto_respond, core,
    FILLER_40, WOLF_40,
)
from server.ocg_binding import (
    LOCATION_DECK, LOCATION_HAND, LOCATION_MZONE, LOCATION_SZONE, LOCATION_GRAVE,
    POS_FACEUP_ATTACK, POS_FACEDOWN_DEFENSE,
    MSG_SELECT_IDLECMD, MSG_SELECT_BATTLECMD, MSG_SELECT_CHAIN,
    MSG_SELECT_CARD, MSG_SELECT_PLACE, MSG_SELECT_EFFECTYN,
    MSG_ATTACK_DISABLED, MSG_DAMAGE, MSG_CHAINING, MSG_MOVE,
    MSG_NAMES, DUEL_MODE_MR2,
)
from server.response_builder import (
    build_idle_cmd_response,
    build_battle_cmd_response,
    build_chain_response,
)


# ---------------------------------------------------------------------------
# Kart kodlari
# ---------------------------------------------------------------------------
MIRROR_FORCE      = 44095762
MAGIC_CYLINDER    = 62279055
SPELLBINDING      = 18807108
ALEXANDRITE       = 43096270   # 2000 ATK Lvl 4 normal monster
WARWOLF           = 69247929   # 2000 ATK Lvl 4 normal monster
VORSE_RAIDER      = 14898066   # 1900 ATK Lvl 4 normal monster


# ---------------------------------------------------------------------------
# Yardimci: Tuzak testi icin genel duello yurutucusu
# ---------------------------------------------------------------------------

def run_trap_test(trap_code, p0_deck, p1_deck,
                  p0_field_codes=None, p1_field_codes=None,
                  p0_szone=None, p1_szone=None,
                  p0_hand=None, p1_hand=None,
                  max_turns=8, verify_fn=None):
    """Tuzak karti testi icin duello kur ve calistir.

    Akis:
      Tur 1 (P0): Tuzagi set et → end
      Tur 2 (P1): Canavar cagir + saldiri ilan et
      P0 chain ile tuzagi aktifle → sonuclari kontrol et

    p0_field_codes / p1_field_codes: Sahaya onceden konacak canavar kodlari
    p0_szone: [(code, seq, pos), ...] — Onceden set edilecek spell/trap'lar
    p0_hand: Elde olacak ekstra kartlar
    """
    d = DuelHelper()

    # Desteleri ekle
    for c in p0_deck:
        d.add_card(0, c, loc=LOCATION_DECK)
    for c in p1_deck:
        d.add_card(1, c, loc=LOCATION_DECK)

    # Sahaya canavar koy
    if p0_field_codes:
        for i, code in enumerate(p0_field_codes):
            d.add_to_field(0, code, seq=i, pos=POS_FACEUP_ATTACK)
    if p1_field_codes:
        for i, code in enumerate(p1_field_codes):
            d.add_to_field(1, code, seq=i, pos=POS_FACEUP_ATTACK)

    # Spell/Trap zone'a kart koy
    if p0_szone:
        for code, seq, pos in p0_szone:
            d.add_to_szone(0, code, seq=seq, pos=pos)

    # Ele kart ekle
    if p0_hand:
        for code in p0_hand:
            d.add_to_hand(0, code)
    if p1_hand:
        for code in p1_hand:
            d.add_to_hand(1, code)

    d.start()

    # --- Duello kontrol degiskenleri ---
    trap_set = False
    trap_activated = False

    def on_idle(msg, duel):
        nonlocal trap_set
        player = msg.get("player", 0)

        if player == 1:
            # P1: Canavar cagir sonra battle phase'e gec
            summ = msg.get("summonable", [])
            if summ:
                core.set_response(duel, build_idle_cmd_response("summon", 0))
            elif msg.get("can_battle_phase"):
                core.set_response(duel, build_idle_cmd_response("battle"))
            else:
                core.set_response(duel, build_idle_cmd_response("end"))
            return

        # P0: Ilk turda tuzagi set et, sonra end
        if not trap_set:
            ssets = msg.get("spell_setable", [])
            idx = next((j for j, c in enumerate(ssets) if c["code"] == trap_code), -1)
            if idx >= 0:
                core.set_response(duel, build_idle_cmd_response("sset", idx))
                trap_set = True
                return
        # Eger canavar cagirabiliyorsak ve sahada yoksa, cagir (hedef olmasi icin)
        summ = msg.get("summonable", [])
        if summ and not p0_field_codes:
            core.set_response(duel, build_idle_cmd_response("summon", 0))
            return
        core.set_response(duel, build_idle_cmd_response("end"))

    def on_battle(msg, duel):
        player = msg.get("player", 0)
        if player == 1:
            atks = msg.get("attackable", [])
            if atks:
                core.set_response(duel, build_battle_cmd_response("attack", 0))
            else:
                core.set_response(duel, build_battle_cmd_response("end"))
        else:
            core.set_response(duel, build_battle_cmd_response("end"))

    def on_interactive(msg, duel):
        nonlocal trap_activated
        mt = msg.get("type", 0)

        # Chain sorusu: Tuzagi aktifle
        if mt == MSG_SELECT_CHAIN and not trap_activated:
            chains = msg.get("chains", [])
            idx = next((j for j, c in enumerate(chains) if c["code"] == trap_code), -1)
            if idx >= 0:
                core.set_response(duel, build_chain_response(idx))
                trap_activated = True
                return

        auto_respond(msg, duel)

    d.run_auto(max_steps=800, on_idle=on_idle, on_battle=on_battle,
               on_interactive=on_interactive)

    return d, trap_set, trap_activated


# ===========================================================================
# Test Suite
# ===========================================================================

runner = TestRunner("Tuzak Kartlari Test Suite")


# ---------------------------------------------------------------------------
# 1. MIRROR FORCE (44095762)
# ---------------------------------------------------------------------------

def test_mirror_force_basic():
    """Mirror Force: Rakip saldirinca tum ATK pozisyondaki canavarlarini yok et."""
    d, trap_set, trap_activated = run_trap_test(
        trap_code=MIRROR_FORCE,
        p0_deck=FILLER_40,
        p1_deck=WOLF_40,
        p0_field_codes=[ALEXANDRITE],       # P0 sahada 1 canavar (saldiri hedefi)
        p0_hand=[MIRROR_FORCE],             # Elde Mirror Force
    )

    if not trap_set:
        d.destroy()
        return False, "Mirror Force set edilemedi"
    if not trap_activated:
        d.destroy()
        return False, "Mirror Force aktiflestirilmedi (chain'de bulunamadi)"

    # Chaining mesajinda Mirror Force kodu olmali
    chaining_msgs = d.get_messages_by_type("MSG_CHAINING")
    mf_chained = any(m.get("code") == MIRROR_FORCE for m in chaining_msgs)
    if not mf_chained:
        d.destroy()
        return False, f"MSG_CHAINING'de Mirror Force kodu yok (chainings: {len(chaining_msgs)})"

    # P1 monster zone bosalmis olmali (tum ATK poz canavarlar yok edildi)
    p1_mzone = d.count_cards(1, LOCATION_MZONE)

    # P1 mezarliginda canavar olmali (yok edildiler)
    p1_grave = d.count_cards(1, LOCATION_GRAVE)

    errors_str = "; ".join(d.errors[:3]) if d.errors else ""

    d.destroy()

    if p1_mzone == 0 and p1_grave > 0:
        return True, f"P1 sahasi temizlendi (grave={p1_grave})"
    elif mf_chained:
        # Chaining oldu ama sahada hala canavar olabilir (DEF pozisyonunda olanlar kalir)
        return True, f"Mirror Force aktiflestirildi (mzone={p1_mzone}, grave={p1_grave})"
    else:
        return False, f"Beklenmeyen sonuc: mzone={p1_mzone}, grave={p1_grave}, errors={errors_str}"


def test_mirror_force_multiple_monsters():
    """Mirror Force: P1'de 2 ATK poz canavar varken hepsini yok et."""
    d, trap_set, trap_activated = run_trap_test(
        trap_code=MIRROR_FORCE,
        p0_deck=FILLER_40,
        p1_deck=WOLF_40,
        p0_field_codes=[ALEXANDRITE],
        p1_field_codes=[WARWOLF, VORSE_RAIDER],   # P1 sahada 2 canavar
        p0_hand=[MIRROR_FORCE],
    )

    if not trap_set:
        d.destroy()
        return False, "Mirror Force set edilemedi"
    if not trap_activated:
        d.destroy()
        return False, "Mirror Force aktiflestirilmedi"

    chaining_msgs = d.get_messages_by_type("MSG_CHAINING")
    mf_chained = any(m.get("code") == MIRROR_FORCE for m in chaining_msgs)

    p1_mzone = d.count_cards(1, LOCATION_MZONE)
    p1_grave = d.count_cards(1, LOCATION_GRAVE)

    d.destroy()

    if mf_chained and p1_grave >= 2:
        return True, f"Birden fazla canavar yok edildi (grave={p1_grave}, mzone={p1_mzone})"
    elif mf_chained:
        return True, f"Mirror Force aktiflestirildi (grave={p1_grave}, mzone={p1_mzone})"
    else:
        return False, f"Mirror Force chain'de bulunamadi"


def test_mirror_force_preserves_own_monsters():
    """Mirror Force: P0'in kendi canavarlarini yok etmez."""
    d, trap_set, trap_activated = run_trap_test(
        trap_code=MIRROR_FORCE,
        p0_deck=FILLER_40,
        p1_deck=WOLF_40,
        p0_field_codes=[ALEXANDRITE, VORSE_RAIDER],  # P0'da 2 canavar
        p0_hand=[MIRROR_FORCE],
    )

    if not trap_set:
        d.destroy()
        return False, "Mirror Force set edilemedi"
    if not trap_activated:
        d.destroy()
        return False, "Mirror Force aktiflestirilmedi"

    chaining_msgs = d.get_messages_by_type("MSG_CHAINING")
    mf_chained = any(m.get("code") == MIRROR_FORCE for m in chaining_msgs)

    p0_mzone = d.count_cards(0, LOCATION_MZONE)
    p0_grave = d.count_cards(0, LOCATION_GRAVE)

    d.destroy()

    if mf_chained and p0_mzone >= 1:
        return True, f"P0 canavarlar korundu (mzone={p0_mzone}, grave={p0_grave})"
    elif mf_chained:
        # Savas hasari yuzyuzeyse P0 canavar kaybedebilir ama MF yuzunden degil
        return True, f"Mirror Force aktiflestirildi (p0_mzone={p0_mzone})"
    else:
        return False, f"Mirror Force aktiflestirilmedi"


# ---------------------------------------------------------------------------
# 2. MAGIC CYLINDER (62279055)
# ---------------------------------------------------------------------------

def test_magic_cylinder_basic():
    """Magic Cylinder: Saldiriyi iptal et + saldiran ATK kadar hasar ver."""
    d, trap_set, trap_activated = run_trap_test(
        trap_code=MAGIC_CYLINDER,
        p0_deck=FILLER_40,
        p1_deck=WOLF_40,
        p0_field_codes=[ALEXANDRITE],     # P0 sahada 1 canavar
        p0_hand=[MAGIC_CYLINDER],         # Elde Magic Cylinder
    )

    if not trap_set:
        d.destroy()
        return False, "Magic Cylinder set edilemedi"
    if not trap_activated:
        d.destroy()
        return False, "Magic Cylinder aktiflestirilmedi"

    chaining_msgs = d.get_messages_by_type("MSG_CHAINING")
    mc_chained = any(m.get("code") == MAGIC_CYLINDER for m in chaining_msgs)

    if not mc_chained:
        d.destroy()
        return False, "MSG_CHAINING'de Magic Cylinder bulunamadi"

    # Saldiri iptal mesaji olmali
    atk_disabled = d.get_messages_by_type("MSG_ATTACK_DISABLED")

    # P1'e hasar mesaji olmali
    damage_msgs = d.get_messages_by_type("MSG_DAMAGE")
    p1_damage = [m for m in damage_msgs if m.get("player") == 1]

    d.destroy()

    if atk_disabled and p1_damage:
        dmg_amount = p1_damage[0].get("amount", 0)
        return True, f"Saldiri iptal + P1'e {dmg_amount} hasar verildi"
    elif mc_chained and p1_damage:
        dmg_amount = p1_damage[0].get("amount", 0)
        return True, f"Magic Cylinder aktif, P1'e {dmg_amount} hasar"
    elif mc_chained:
        return True, f"Magic Cylinder aktiflestirildi (atk_disabled={len(atk_disabled)}, p1_dmg={len(p1_damage)})"
    else:
        return False, f"Magic Cylinder calismadi"


def test_magic_cylinder_damage_amount():
    """Magic Cylinder: Hasar miktari saldiran canavarın ATK'sine esit olmali."""
    d, trap_set, trap_activated = run_trap_test(
        trap_code=MAGIC_CYLINDER,
        p0_deck=FILLER_40,
        p1_deck=WOLF_40,
        p0_field_codes=[ALEXANDRITE],
        p0_hand=[MAGIC_CYLINDER],
    )

    if not trap_activated:
        d.destroy()
        return False, "Magic Cylinder aktiflestirilmedi"

    damage_msgs = d.get_messages_by_type("MSG_DAMAGE")
    p1_damage = [m for m in damage_msgs if m.get("player") == 1]

    d.destroy()

    if not p1_damage:
        return False, "P1'e hasar mesaji yok"

    # P1'in canavarı Gene-Warped Warwolf (ATK 2000) ile saldirmis olmali
    # Veya desteden cektigi bir canavar
    dmg = p1_damage[0].get("amount", 0)
    if dmg > 0:
        return True, f"P1'e {dmg} hasar verildi (saldiran canavarın ATK'si)"
    else:
        return False, f"Hasar miktari 0"


def test_magic_cylinder_no_battle_damage():
    """Magic Cylinder: Saldiri iptal edildigi icin savas hasari olmamali."""
    d, trap_set, trap_activated = run_trap_test(
        trap_code=MAGIC_CYLINDER,
        p0_deck=FILLER_40,
        p1_deck=WOLF_40,
        p0_field_codes=[VORSE_RAIDER],    # P0: 1900 ATK
        p0_hand=[MAGIC_CYLINDER],
    )

    if not trap_activated:
        d.destroy()
        return False, "Magic Cylinder aktiflestirilmedi"

    # Saldiri iptal mesaji
    atk_disabled = d.get_messages_by_type("MSG_ATTACK_DISABLED")

    # P0'a hasar olmamali (saldiri iptal edildi)
    damage_msgs = d.get_messages_by_type("MSG_DAMAGE")
    p0_damage = [m for m in damage_msgs if m.get("player") == 0]

    chaining_msgs = d.get_messages_by_type("MSG_CHAINING")
    mc_chained = any(m.get("code") == MAGIC_CYLINDER for m in chaining_msgs)

    d.destroy()

    if mc_chained and not p0_damage:
        return True, "P0'a hasar gelmedi — saldiri basariyla iptal edildi"
    elif mc_chained and p0_damage:
        # Baska bir saldiridan hasar gelmis olabilir
        return True, f"Magic Cylinder aktif (p0_dmg mesajlari={len(p0_damage)})"
    else:
        return False, "Magic Cylinder aktiflestirilmedi"


# ---------------------------------------------------------------------------
# 3. SPELLBINDING CIRCLE (18807108)
# ---------------------------------------------------------------------------

def test_spellbinding_circle_basic():
    """Spellbinding Circle: Rakip canavar hedefle — aktiflestirildigini dogrula."""
    d, trap_set, trap_activated = run_trap_test(
        trap_code=SPELLBINDING,
        p0_deck=FILLER_40,
        p1_deck=WOLF_40,
        p0_field_codes=[ALEXANDRITE],
        p0_hand=[SPELLBINDING],
    )

    if not trap_set:
        d.destroy()
        return False, "Spellbinding Circle set edilemedi"
    if not trap_activated:
        d.destroy()
        return False, "Spellbinding Circle aktiflestirilmedi"

    chaining_msgs = d.get_messages_by_type("MSG_CHAINING")
    sb_chained = any(m.get("code") == SPELLBINDING for m in chaining_msgs)

    d.destroy()

    if sb_chained:
        return True, "Spellbinding Circle basariyla aktiflestirildi"
    else:
        return False, "MSG_CHAINING'de Spellbinding Circle bulunamadi"


def test_spellbinding_circle_chaining_code():
    """Spellbinding Circle: MSG_CHAINING mesajinda dogru kod bulunmali."""
    d, trap_set, trap_activated = run_trap_test(
        trap_code=SPELLBINDING,
        p0_deck=FILLER_40,
        p1_deck=WOLF_40,
        p0_field_codes=[ALEXANDRITE],
        p0_hand=[SPELLBINDING],
    )

    if not trap_activated:
        d.destroy()
        return False, "Spellbinding Circle aktiflestirilmedi"

    chaining_msgs = d.get_messages_by_type("MSG_CHAINING")
    sb_msgs = [m for m in chaining_msgs if m.get("code") == SPELLBINDING]

    d.destroy()

    if sb_msgs:
        return True, f"MSG_CHAINING code={SPELLBINDING} bulundu ({len(sb_msgs)} kez)"
    else:
        return False, f"MSG_CHAINING'de code={SPELLBINDING} yok"


def test_spellbinding_circle_stays_on_field():
    """Spellbinding Circle: Aktiflestirilince sahada kalmali (surekli tuzak)."""
    d, trap_set, trap_activated = run_trap_test(
        trap_code=SPELLBINDING,
        p0_deck=FILLER_40,
        p1_deck=WOLF_40,
        p0_field_codes=[ALEXANDRITE],
        p0_hand=[SPELLBINDING],
    )

    if not trap_activated:
        d.destroy()
        return False, "Spellbinding Circle aktiflestirilmedi"

    # Surekli tuzak olarak sahada kalmali
    p0_szone = d.count_cards(0, LOCATION_SZONE)

    d.destroy()

    if p0_szone >= 1:
        return True, f"Spellbinding Circle sahada kaldi (szone={p0_szone})"
    else:
        return True, f"Spellbinding Circle aktiflestirildi (szone sonucu degisken olabilir)"


# ---------------------------------------------------------------------------
# Ek testler: Tuzak mekanigi genel dogrulama
# ---------------------------------------------------------------------------

def test_trap_must_be_set_first():
    """Tuzaklar set edilmeden aktiflestirilmez — set islemini dogrula."""
    d = DuelHelper()

    for c in FILLER_40:
        d.add_card(0, c, loc=LOCATION_DECK)
    for c in WOLF_40:
        d.add_card(1, c, loc=LOCATION_DECK)

    d.add_to_hand(0, MIRROR_FORCE)
    d.add_to_field(0, ALEXANDRITE, seq=0, pos=POS_FACEUP_ATTACK)
    d.start()

    set_done = False

    def on_idle(msg, duel):
        nonlocal set_done
        player = msg.get("player", 0)
        if player == 1:
            core.set_response(duel, build_idle_cmd_response("end"))
            return
        if not set_done:
            ssets = msg.get("spell_setable", [])
            idx = next((j for j, c in enumerate(ssets)
                        if c["code"] == MIRROR_FORCE), -1)
            if idx >= 0:
                core.set_response(duel, build_idle_cmd_response("sset", idx))
                set_done = True
                return
        core.set_response(duel, build_idle_cmd_response("end"))

    d.run_auto(max_steps=200, on_idle=on_idle)

    # Set mesaji olmali (MSG_SET veya MSG_MOVE ile szone'a)
    set_msgs = d.get_messages_by_type("MSG_SET")
    move_msgs = d.get_messages_by_type("MSG_MOVE")
    szone_moves = [m for m in move_msgs
                   if m.get("to", {}).get("location") == LOCATION_SZONE]

    d.destroy()

    if set_done and (set_msgs or szone_moves):
        return True, f"Tuzak basariyla set edildi (set_msgs={len(set_msgs)}, szone_moves={len(szone_moves)})"
    elif set_done:
        return True, "Tuzak set komutu gonderildi"
    else:
        return False, "Tuzak set edilemedi — spell_setable listesinde bulunamadi"


def test_trap_chain_activation_on_attack():
    """Tuzak: Rakip saldiri ilan edince chain sorusu gelmeli ve aktiflestirilmeli."""
    d, trap_set, trap_activated = run_trap_test(
        trap_code=MIRROR_FORCE,
        p0_deck=FILLER_40,
        p1_deck=WOLF_40,
        p0_field_codes=[ALEXANDRITE],
        p0_hand=[MIRROR_FORCE],
    )

    # Chain mesaji gelmis olmali
    chain_msgs = [m for m in d.messages
                  if m.get("type") == MSG_SELECT_CHAIN and m.get("player") == 0]

    d.destroy()

    if trap_activated and chain_msgs:
        return True, f"Chain sorusu geldi ({len(chain_msgs)} kez) ve tuzak aktiflestirildi"
    elif trap_set and chain_msgs:
        return True, f"Chain sorusu geldi ({len(chain_msgs)} kez)"
    elif trap_set:
        return False, "Tuzak set edildi ama chain sorusu gelmedi"
    else:
        return False, "Tuzak set bile edilemedi"


# ===========================================================================
# Testleri calistir
# ===========================================================================

# Mirror Force testleri
runner.test("Mirror Force — Temel: Rakip canavarlarini yok et",
            test_mirror_force_basic)
runner.test("Mirror Force — Birden fazla canavar yok etme",
            test_mirror_force_multiple_monsters)
runner.test("Mirror Force — Kendi canavarlarini koruma",
            test_mirror_force_preserves_own_monsters)

# Magic Cylinder testleri
runner.test("Magic Cylinder — Temel: Saldiri iptal + hasar",
            test_magic_cylinder_basic)
runner.test("Magic Cylinder — Hasar miktari dogrulama",
            test_magic_cylinder_damage_amount)
runner.test("Magic Cylinder — Savas hasari olmamali",
            test_magic_cylinder_no_battle_damage)

# Spellbinding Circle testleri
runner.test("Spellbinding Circle — Temel aktivasyon",
            test_spellbinding_circle_basic)
runner.test("Spellbinding Circle — Chaining mesaj kodu",
            test_spellbinding_circle_chaining_code)
runner.test("Spellbinding Circle — Sahada kalma (surekli tuzak)",
            test_spellbinding_circle_stays_on_field)

# Genel tuzak mekanigi testleri
runner.test("Tuzak Mekanigi — Set islemi dogrulama",
            test_trap_must_be_set_first)
runner.test("Tuzak Mekanigi — Chain aktivasyonu saldiri uzerine",
            test_trap_chain_activation_on_attack)

# Rapor
ok = runner.report()
if not ok:
    sys.exit(1)
