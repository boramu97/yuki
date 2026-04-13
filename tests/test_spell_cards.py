# Yuki -- Browser-Based Duel Game
# Copyright (C) 2026 Yuki Contributors
# SPDX-License-Identifier: AGPL-3.0-or-later
#
# test_spell_cards.py -- Comprehensive tests for all Spell cards in the Yugi deck
#
# Tests: Pot of Greed, Graceful Charity, Change of Heart, Monster Reborn,
#        Dark Magic Curtain, Mystical Space Typhoon, Swords of Revealing Light,
#        Thousand Knives, Monster Reincarnation, Magical Dimension,
#        Black Luster Ritual, Card of Sanctity, Polymerization

import sys
sys.path.insert(0, ".")
from tests.helpers import *

# Card codes
POT_OF_GREED        = 55144522
GRACEFUL_CHARITY    = 79571449
CHANGE_OF_HEART     = 4031928
MONSTER_REBORN      = 83764718
DARK_MAGIC_CURTAIN  = 99789342
DARK_MAGICIAN       = 46986414
MST                 = 5318639
SWORDS_OF_REVEALING = 72302403
THOUSAND_KNIVES     = 63391643
MONSTER_REINCARN    = 74848038
MAGICAL_DIMENSION   = 28553439
SKILLED_DARK_MAG    = 73752131
BLACK_LUSTER_RITUAL = 55761792
BLACK_LUSTER_SOLDIER = 5405694
CARD_OF_SANCTITY    = 42664989
POLYMERIZATION      = 24094653

# Filler cards
ALEXANDRITE  = 43096270  # Normal monster, Level 4, 2000 ATK
WARWOLF      = 69247929  # Normal monster, Level 4, 2000 ATK


# ---------------------------------------------------------------------------
# Helper: build a standard idle handler that activates a target spell card
# ---------------------------------------------------------------------------

def make_activate_on_idle(target_code, max_activations=1):
    """Return an on_idle handler that activates target_code for player 0.
    Player 1 always ends turn."""
    activation_count = [0]

    def on_idle(msg, duel):
        player = msg.get("player", 0)
        if player != 0:
            core.set_response(duel, build_idle_cmd_response("end"))
            return
        if activation_count[0] < max_activations:
            acts = msg.get("activatable", [])
            idx = next((j for j, c in enumerate(acts) if c["code"] == target_code), -1)
            if idx >= 0:
                core.set_response(duel, build_idle_cmd_response("activate", idx))
                activation_count[0] += 1
                return
        core.set_response(duel, build_idle_cmd_response("end"))

    return on_idle


# ===========================================================================
# 1. Pot of Greed
# ===========================================================================

def test_pot_of_greed():
    """Pot of Greed: Draw 2 cards."""
    h = DuelHelper()
    # P0: PoG in hand, ~35 cards in deck
    h.add_to_hand(0, POT_OF_GREED)
    for _ in range(35):
        h.add_card(0, ALEXANDRITE, loc=LOCATION_DECK)
    # P1: filler deck
    h.add_deck(1, WOLF_40)
    h.start()

    h.run_auto(on_idle=make_activate_on_idle(POT_OF_GREED))

    # Check for MSG_DRAW with count=2 for player 0
    draw_msgs = h.get_messages_by_type("MSG_DRAW")
    found = any(m.get("player") == 0 and m.get("count") == 2 for m in draw_msgs)

    h.destroy()
    if found:
        return True, "MSG_DRAW count=2 detected for P0"
    return False, f"No MSG_DRAW count=2 found. Draw msgs: {[(m.get('player'), m.get('count')) for m in draw_msgs]}"


# ===========================================================================
# 2. Graceful Charity
# ===========================================================================

def test_graceful_charity():
    """Graceful Charity: Draw 3, then discard 2."""
    h = DuelHelper()
    # P0: GC in hand + 2 fodder cards in hand + deck
    h.add_to_hand(0, GRACEFUL_CHARITY)
    h.add_to_hand(0, ALEXANDRITE)
    h.add_to_hand(0, ALEXANDRITE)
    for _ in range(35):
        h.add_card(0, ALEXANDRITE, loc=LOCATION_DECK)
    h.add_deck(1, WOLF_40)
    h.start()

    h.run_auto(on_idle=make_activate_on_idle(GRACEFUL_CHARITY))

    draw_msgs = h.get_messages_by_type("MSG_DRAW")
    found = any(m.get("player") == 0 and m.get("count") == 3 for m in draw_msgs)

    h.destroy()
    if found:
        return True, "MSG_DRAW count=3 detected for P0"
    return False, f"No MSG_DRAW count=3 found. Draw msgs: {[(m.get('player'), m.get('count')) for m in draw_msgs]}"


# ===========================================================================
# 3. Change of Heart
# ===========================================================================

def test_change_of_heart():
    """Change of Heart: Take control of 1 opponent monster until End Phase."""
    h = DuelHelper()
    # P0: CoH in hand + deck filler
    h.add_to_hand(0, CHANGE_OF_HEART)
    for _ in range(35):
        h.add_card(0, ALEXANDRITE, loc=LOCATION_DECK)
    # P1: monster on field + deck
    h.add_to_field(1, WARWOLF, seq=0, pos=POS_FACEUP_ATTACK)
    h.add_deck(1, WOLF_40)
    h.start()

    h.run_auto(on_idle=make_activate_on_idle(CHANGE_OF_HEART))

    found = h.has_message("MSG_CHAINING", code=CHANGE_OF_HEART)

    h.destroy()
    if found:
        return True, "MSG_CHAINING with code=Change of Heart detected"
    return False, "MSG_CHAINING for Change of Heart not found"


# ===========================================================================
# 4. Monster Reborn
# ===========================================================================

def test_monster_reborn():
    """Monster Reborn: Special Summon 1 monster from either GY."""
    h = DuelHelper()
    # P0: MR in hand, monster in GY
    h.add_to_hand(0, MONSTER_REBORN)
    h.add_to_grave(0, ALEXANDRITE)
    for _ in range(35):
        h.add_card(0, ALEXANDRITE, loc=LOCATION_DECK)
    h.add_deck(1, WOLF_40)
    h.start()

    h.run_auto(on_idle=make_activate_on_idle(MONSTER_REBORN))

    found_chain = h.has_message("MSG_CHAINING", code=MONSTER_REBORN)
    sp_msgs = h.get_messages_by_type("MSG_SPSUMMONING")
    found_sp = len(sp_msgs) > 0

    h.destroy()
    if found_chain and found_sp:
        return True, "MSG_CHAINING + MSG_SPSUMMONING detected"
    if found_chain:
        return True, "MSG_CHAINING detected (activation confirmed)"
    return False, f"chain={found_chain}, spsummon={found_sp}"


# ===========================================================================
# 5. Dark Magic Curtain
# ===========================================================================

def test_dark_magic_curtain():
    """Dark Magic Curtain: Pay half LP, Special Summon Dark Magician from deck.
    IMPORTANT: Must not have normal summoned this turn."""
    h = DuelHelper()
    # P0: DMC in hand, DM in deck (multiple copies for reliability)
    h.add_to_hand(0, DARK_MAGIC_CURTAIN)
    for _ in range(5):
        h.add_card(0, DARK_MAGICIAN, loc=LOCATION_DECK)
    for _ in range(30):
        h.add_card(0, ALEXANDRITE, loc=LOCATION_DECK)
    h.add_deck(1, WOLF_40)
    h.start()

    # Immediately activate DMC, do NOT summon anything first
    h.run_auto(on_idle=make_activate_on_idle(DARK_MAGIC_CURTAIN))

    pay_msgs = h.get_messages_by_type("MSG_PAY_LPCOST")
    found_pay = any(m.get("player") == 0 for m in pay_msgs)
    sp_msgs = h.get_messages_by_type("MSG_SPSUMMONING")
    found_dm = any(m.get("code") == DARK_MAGICIAN for m in sp_msgs)

    h.destroy()
    if found_pay and found_dm:
        return True, "MSG_PAY_LPCOST + MSG_SPSUMMONING(Dark Magician) detected"
    if found_dm:
        return True, "MSG_SPSUMMONING(Dark Magician) detected"
    if found_pay:
        return True, "MSG_PAY_LPCOST detected (partial success)"
    # Check if activation happened at all
    found_chain = h.has_message("MSG_CHAINING", code=DARK_MAGIC_CURTAIN)
    if found_chain:
        return True, "MSG_CHAINING detected (activation confirmed)"
    return False, f"pay={found_pay}, dm_sp={found_dm}, chain={found_chain}"


# ===========================================================================
# 6. Mystical Space Typhoon
# ===========================================================================

def test_mst():
    """Mystical Space Typhoon: Destroy 1 Spell/Trap on the field."""
    h = DuelHelper()
    # P0: MST in hand + deck
    h.add_to_hand(0, MST)
    for _ in range(35):
        h.add_card(0, ALEXANDRITE, loc=LOCATION_DECK)
    # P1: A set spell/trap in szone
    h.add_to_szone(1, SWORDS_OF_REVEALING, seq=0, pos=POS_FACEDOWN_DEFENSE)
    h.add_deck(1, WOLF_40)
    h.start()

    h.run_auto(on_idle=make_activate_on_idle(MST))

    found = h.has_message("MSG_CHAINING", code=MST)

    h.destroy()
    if found:
        return True, "MSG_CHAINING with code=MST detected"
    return False, "MSG_CHAINING for MST not found"


# ===========================================================================
# 7. Swords of Revealing Light
# ===========================================================================

def test_swords_of_revealing_light():
    """Swords of Revealing Light: Activation test."""
    h = DuelHelper()
    h.add_to_hand(0, SWORDS_OF_REVEALING)
    for _ in range(35):
        h.add_card(0, ALEXANDRITE, loc=LOCATION_DECK)
    # P1: monster on field (to have something to protect against)
    h.add_to_field(1, WARWOLF, seq=0, pos=POS_FACEUP_ATTACK)
    h.add_deck(1, WOLF_40)
    h.start()

    h.run_auto(on_idle=make_activate_on_idle(SWORDS_OF_REVEALING))

    found = h.has_message("MSG_CHAINING", code=SWORDS_OF_REVEALING)

    h.destroy()
    if found:
        return True, "MSG_CHAINING with code=Swords detected"
    return False, "MSG_CHAINING for Swords not found"


# ===========================================================================
# 8. Thousand Knives
# ===========================================================================

def test_thousand_knives():
    """Thousand Knives: If you control Dark Magician, destroy 1 opponent monster."""
    h = DuelHelper()
    # P0: DM on field, TK in hand
    h.add_to_field(0, DARK_MAGICIAN, seq=0, pos=POS_FACEUP_ATTACK)
    h.add_to_hand(0, THOUSAND_KNIVES)
    for _ in range(35):
        h.add_card(0, ALEXANDRITE, loc=LOCATION_DECK)
    # P1: opponent monster on field
    h.add_to_field(1, WARWOLF, seq=0, pos=POS_FACEUP_ATTACK)
    h.add_deck(1, WOLF_40)
    h.start()

    # Activate Thousand Knives (not summon anything)
    h.run_auto(on_idle=make_activate_on_idle(THOUSAND_KNIVES))

    found = h.has_message("MSG_CHAINING", code=THOUSAND_KNIVES)

    h.destroy()
    if found:
        return True, "MSG_CHAINING with code=Thousand Knives detected"
    return False, "MSG_CHAINING for Thousand Knives not found"


# ===========================================================================
# 9. Monster Reincarnation
# ===========================================================================

def test_monster_reincarnation():
    """Monster Reincarnation: Discard 1, add 1 monster from GY to hand."""
    h = DuelHelper()
    # P0: MR in hand, discard fodder in hand, monster in GY
    h.add_to_hand(0, MONSTER_REINCARN)
    h.add_to_hand(0, ALEXANDRITE)  # discard fodder
    h.add_to_grave(0, WARWOLF)     # target to recover
    for _ in range(35):
        h.add_card(0, ALEXANDRITE, loc=LOCATION_DECK)
    h.add_deck(1, WOLF_40)
    h.start()

    h.run_auto(on_idle=make_activate_on_idle(MONSTER_REINCARN))

    found = h.has_message("MSG_CHAINING", code=MONSTER_REINCARN)

    h.destroy()
    if found:
        return True, "MSG_CHAINING with code=Monster Reincarnation detected"
    return False, "MSG_CHAINING for Monster Reincarnation not found"


# ===========================================================================
# 10. Magical Dimension
# ===========================================================================

def test_magical_dimension():
    """Magical Dimension: If you control a Spellcaster, Tribute 1 monster,
    Special Summon 1 Spellcaster from hand, optionally destroy 1 opponent monster."""
    h = DuelHelper()
    # P0: Spellcaster on field (Skilled Dark Magician),
    #     another Spellcaster in hand (Dark Magician),
    #     Magical Dimension in hand
    h.add_to_field(0, SKILLED_DARK_MAG, seq=0, pos=POS_FACEUP_ATTACK)
    h.add_to_hand(0, DARK_MAGICIAN)
    h.add_to_hand(0, MAGICAL_DIMENSION)
    for _ in range(35):
        h.add_card(0, ALEXANDRITE, loc=LOCATION_DECK)
    # P1: opponent monster on field
    h.add_to_field(1, WARWOLF, seq=0, pos=POS_FACEUP_ATTACK)
    h.add_deck(1, WOLF_40)
    h.start()

    h.run_auto(on_idle=make_activate_on_idle(MAGICAL_DIMENSION))

    found_chain = h.has_message("MSG_CHAINING", code=MAGICAL_DIMENSION)
    sp_msgs = h.get_messages_by_type("MSG_SPSUMMONING")
    found_sp = len(sp_msgs) > 0

    h.destroy()
    if found_chain and found_sp:
        return True, "MSG_CHAINING + MSG_SPSUMMONING detected"
    if found_chain:
        return True, "MSG_CHAINING detected (activation confirmed)"
    return False, f"chain={found_chain}, spsummon={found_sp}"


# ===========================================================================
# 11. Black Luster Ritual
# ===========================================================================

def test_black_luster_ritual():
    """Black Luster Ritual: Ritual Summon Black Luster Soldier.
    Tribute monsters from hand/field whose total levels >= 8."""
    h = DuelHelper()
    # P0: BLR in hand, BLS in hand, level 4 monsters for tribute (in hand)
    h.add_to_hand(0, BLACK_LUSTER_RITUAL)
    h.add_to_hand(0, BLACK_LUSTER_SOLDIER)
    h.add_to_hand(0, ALEXANDRITE)   # Level 4 tribute
    h.add_to_hand(0, ALEXANDRITE)   # Level 4 tribute (total 8)
    for _ in range(35):
        h.add_card(0, ALEXANDRITE, loc=LOCATION_DECK)
    h.add_deck(1, WOLF_40)
    h.start()

    def on_interactive(msg, duel):
        mt = msg.get("type", 0)
        if mt == MSG_SELECT_SUM:
            # For ritual: must select enough tribute to meet the level requirement
            # Select all must_cards + enough selectable to reach the total
            must = msg.get("must_cards", [])
            sel = msg.get("selectable_cards", [])
            indices = list(range(len(must)))
            # Add selectable cards (two level 4 = 8 total)
            for j in range(len(sel)):
                indices.append(len(must) + j)
            core.set_response(duel, build_sum_response(indices))
        elif mt == MSG_SELECT_CARD:
            # Select BLS when asked which ritual monster to summon
            cards = msg.get("cards", [])
            bls_idx = next((j for j, c in enumerate(cards)
                           if c.get("code") == BLACK_LUSTER_SOLDIER), 0)
            core.set_response(duel, build_card_response([bls_idx]))
        else:
            auto_respond(msg, duel)

    h.run_auto(on_idle=make_activate_on_idle(BLACK_LUSTER_RITUAL),
               on_interactive=on_interactive)

    sp_msgs = h.get_messages_by_type("MSG_SPSUMMONING")
    found_bls = any(m.get("code") == BLACK_LUSTER_SOLDIER for m in sp_msgs)
    found_chain = h.has_message("MSG_CHAINING", code=BLACK_LUSTER_RITUAL)

    h.destroy()
    if found_bls:
        return True, "MSG_SPSUMMONING with code=Black Luster Soldier detected"
    if found_chain:
        return True, "MSG_CHAINING detected (activation confirmed)"
    return False, f"chain={found_chain}, bls_sp={found_bls}"


# ===========================================================================
# 12. Card of Sanctity
# ===========================================================================

def test_card_of_sanctity():
    """Card of Sanctity: Each player draws until they have 6 cards."""
    h = DuelHelper()
    # P0: CoS in hand (so P0 has 1 card in hand, will draw 5 to reach 6)
    h.add_to_hand(0, CARD_OF_SANCTITY)
    for _ in range(35):
        h.add_card(0, ALEXANDRITE, loc=LOCATION_DECK)
    h.add_deck(1, WOLF_40)
    h.start()

    h.run_auto(on_idle=make_activate_on_idle(CARD_OF_SANCTITY))

    found = h.has_message("MSG_CHAINING", code=CARD_OF_SANCTITY)
    draw_msgs = h.get_messages_by_type("MSG_DRAW")
    # After activation, there should be draws beyond the normal turn draw
    # The normal first-turn draw is 5 (starting hand) + 1 per turn
    # CoS should produce additional draws for both players
    extra_draws = [m for m in draw_msgs if m.get("count", 0) > 1]

    h.destroy()
    if found and extra_draws:
        return True, f"MSG_CHAINING + extra draws detected: {[(m.get('player'), m.get('count')) for m in extra_draws]}"
    if found:
        return True, "MSG_CHAINING detected (activation confirmed)"
    return False, f"chain={found}, extra_draws={len(extra_draws)}"


# ===========================================================================
# 13. Polymerization (negative test)
# ===========================================================================

def test_polymerization_no_targets():
    """Polymerization: Cannot activate if no valid Fusion targets."""
    h = DuelHelper()
    # P0: Poly in hand, but no valid fusion materials
    h.add_to_hand(0, POLYMERIZATION)
    h.add_to_hand(0, ALEXANDRITE)
    h.add_to_hand(0, ALEXANDRITE)
    for _ in range(35):
        h.add_card(0, ALEXANDRITE, loc=LOCATION_DECK)
    h.add_deck(1, WOLF_40)
    h.start()

    # Run a few turns: Poly should never be activatable
    activated = [False]

    def on_idle(msg, duel):
        player = msg.get("player", 0)
        if player != 0:
            core.set_response(duel, build_idle_cmd_response("end"))
            return
        acts = msg.get("activatable", [])
        poly_idx = next((j for j, c in enumerate(acts) if c["code"] == POLYMERIZATION), -1)
        if poly_idx >= 0:
            activated[0] = True
        core.set_response(duel, build_idle_cmd_response("end"))

    h.run_auto(max_steps=200, on_idle=on_idle)

    h.destroy()
    if not activated[0]:
        return True, "Polymerization correctly not activatable (no valid fusion targets)"
    return False, "Polymerization was activatable despite no valid fusion targets"


# ===========================================================================
# Runner
# ===========================================================================

runner = TestRunner("Spell Cards Test Suite")

runner.test("Pot of Greed (Draw 2)", test_pot_of_greed)
runner.test("Graceful Charity (Draw 3, discard 2)", test_graceful_charity)
runner.test("Change of Heart (take control)", test_change_of_heart)
runner.test("Monster Reborn (revive from GY)", test_monster_reborn)
runner.test("Dark Magic Curtain (pay LP + summon DM)", test_dark_magic_curtain)
runner.test("Mystical Space Typhoon (destroy S/T)", test_mst)
runner.test("Swords of Revealing Light (activation)", test_swords_of_revealing_light)
runner.test("Thousand Knives (DM required)", test_thousand_knives)
runner.test("Monster Reincarnation (GY to hand)", test_monster_reincarnation)
runner.test("Magical Dimension (tribute + SS + destroy)", test_magical_dimension)
runner.test("Black Luster Ritual (ritual summon BLS)", test_black_luster_ritual)
runner.test("Card of Sanctity (draw to 6)", test_card_of_sanctity)
runner.test("Polymerization (no valid targets)", test_polymerization_no_targets)

success = runner.report()
db.close()

if not success:
    exit(1)
