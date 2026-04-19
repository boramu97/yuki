# Yuki — Browser-Based Duel Game
# Copyright (C) 2026 Yuki Contributors
# SPDX-License-Identifier: AGPL-3.0-or-later
#
# ai_profiles.py — Bot bazli "play profile" ve key/fodder heuristikleri.
#
# Her bot icin tanimli bir "style" var; IDLECMD priority listesi ve
# TRIBUTE/SELECT_CARD heuristikleri bu stile gore degisir. Ayrica deste
# icinden auto key/fodder tespiti yapilir (hardcode degil — deste guncellendiginde
# otomatik genisler).

from __future__ import annotations

# ---------------------------------------------------------------------------
# STYLES — IDLECMD priority listesini etkiler
# ---------------------------------------------------------------------------
# "aggressive"  : summon → spsummon → battle → activate → set → end
# "tactical"    : set → activate → summon → spsummon → battle → end
# "combo"       : activate → spsummon → summon → battle → set → end
# "stall"       : set (mset face-down) → activate → battle → summon → end
# "control"     : activate → set → summon → spsummon → battle → end

STYLE_PRIORITIES = {
    "aggressive": [
        "hand_activate", "summon", "spsummon", "field_activate",
        "battle", "sset", "mset", "end",
    ],
    "tactical": [
        "sset", "hand_activate", "field_activate", "summon",
        "spsummon", "battle", "mset", "end",
    ],
    "combo": [
        "hand_activate", "spsummon", "field_activate", "summon",
        "battle", "sset", "mset", "end",
    ],
    "stall": [
        "mset", "sset", "hand_activate", "field_activate",
        "battle", "summon", "spsummon", "end",
    ],
    "control": [
        "hand_activate", "field_activate", "sset", "summon",
        "spsummon", "battle", "mset", "end",
    ],
}

DEFAULT_STYLE = "aggressive"


# ---------------------------------------------------------------------------
# BOT PROFILES — her bot'un stili + özel key cards (opsiyonel manuel override)
# ---------------------------------------------------------------------------
# key_cards: asla tribute/discard etme (boş liste → auto-detect)
# fodder_cards: tribute/discard oncelikli (bos liste → auto-detect)

PROFILES: dict[str, dict] = {
    "Yugi":     {"style": "tactical",   "key_cards": [46986414, 38033121], "fodder_cards": []},
    # Dark Magician, Dark Magician Girl
    "Kaiba":    {"style": "aggressive", "key_cards": [89631139, 10000000], "fodder_cards": []},
    # Blue-Eyes White Dragon, Obelisk
    "Joey":     {"style": "aggressive", "key_cards": [74677422, 77585513], "fodder_cards": []},
    # Red-Eyes Black Dragon, Jinzo (yaklasik)
    "Mai":      {"style": "combo",      "key_cards": [12206212, 76812113], "fodder_cards": []},
    # Harpie Lady Sisters, Cyber Harpie Lady
    "Bastion":  {"style": "combo",      "key_cards": [88264978], "fodder_cards": []},
    # Water Dragon
    "Dino":     {"style": "aggressive", "key_cards": [46718686, 72291078], "fodder_cards": []},
    # Super Conductor Tyranno + ilgili
    "Weevil":   {"style": "stall",      "key_cards": [14735698], "fodder_cards": []},
    # Great Moth family
    "Rex":      {"style": "aggressive", "key_cards": [46718686], "fodder_cards": []},
    # Ultimate Tyranno vb.
    "Pegasus":  {"style": "combo",      "key_cards": [15259703, 42386471], "fodder_cards": []},
    # Toon World + ana Toon
    "Jaden":    {"style": "combo",      "key_cards": [89943723, 24094653], "fodder_cards": []},
    # Elemental HERO Neos + Polymerization
    "Syrus":    {"style": "combo",      "key_cards": [], "fodder_cards": []},
    "Ancient Gear": {"style": "control", "key_cards": [], "fodder_cards": []},

    # --- Battle City macerasi ---
    "Seeker": {
        "style": "stall",
        # Exodia parcalari key — asla tribute/discard etme
        "key_cards": [33396948, 70903634, 7902349, 8124921, 44519536, 58604027],
        "fodder_cards": [13039848, 31812496],  # Giant Soldier of Stone, Stone Statue
    },
    "Strings": {
        "style": "combo",
        "key_cards": [10000020, 31709826],  # Slifer, Revival Jam
        "fodder_cards": [46821314, 73216412],  # Humanoid Slime, Worm Drake (Norm)
    },
    "Arkana": {
        "style": "tactical",
        "key_cards": [46986414, 12686296],  # Dark Magician, Chaos Ruler
        "fodder_cards": [83011277, 97534104],  # Mystic Tomato/Potato
    },
    "UmbraLumis": {
        "style": "combo",
        "key_cards": [48948935, 49064413],  # Des Gardius, The Masked Beast
        "fodder_cards": [13676474, 86569121, 11761845, 14531242],
    },
    "YamiBakura": {
        "style": "stall",
        "key_cards": [31829185, 94212438, 16625614],  # Necrofear, Destiny Board, Dark Sanctuary
        "fodder_cards": [5434080, 32541773, 68049471, 17358176, 4920010, 99030164],
    },
    "KaibaBC": {
        "style": "aggressive",
        "key_cards": [89631139, 10000000, 17444133],  # BEWD, Obelisk, Kaiser Sea Horse
        "fodder_cards": [30113682, 86281779, 14898066, 24611934],
    },
    "YamiMarik": {
        "style": "control",
        "key_cards": [10000010, 102380, 48948935],  # Ra, Lava Golem, Des Gardius
        "fodder_cards": [13676474, 86569121, 38445524, 59546797],
    },
}


def get_profile(bot_name: str | None) -> dict:
    """Bot ismine gore profile dondurur; tanimsiz bot icin default."""
    if not bot_name:
        return {"style": DEFAULT_STYLE, "key_cards": [], "fodder_cards": []}
    return PROFILES.get(bot_name, {"style": DEFAULT_STYLE, "key_cards": [], "fodder_cards": []})


def get_priority(bot_name: str | None) -> list[str]:
    """Bot stiline gore IDLECMD action priority listesi."""
    style = get_profile(bot_name).get("style", DEFAULT_STYLE)
    return STYLE_PRIORITIES.get(style, STYLE_PRIORITIES[DEFAULT_STYLE])


# ---------------------------------------------------------------------------
# KEY / FODDER AUTO-DETECTION
# ---------------------------------------------------------------------------
# Bir kart "key" sayilir: level >= 7 VEYA atk >= 2500 VEYA manuel listede
# Bir kart "fodder" sayilir: atk <= 1000 VE etkili degilse VEYA manuel listede
# (etkili olma kontrolu: card_type NORMAL ise etkisiz sayilir)

TYPE_NORMAL = 0x10
TYPE_EFFECT = 0x20


def is_key_card(card: dict, profile: dict) -> bool:
    """Kart sahipligi: key mi?"""
    code = card.get("code", 0)
    if code and code in profile.get("key_cards", []):
        return True
    atk = card.get("card_atk", 0) or 0
    level = card.get("card_level", 0) or 0
    if atk >= 2500 or level >= 7:
        return True
    return False


def is_fodder(card: dict, profile: dict) -> bool:
    """Kart sahipligi: fodder mi?"""
    code = card.get("code", 0)
    if code and code in profile.get("fodder_cards", []):
        return True
    atk = card.get("card_atk", 0) or 0
    ctype = card.get("card_type", 0) or 0
    # Dusuk ATK Normal monster (efekti yok) en iyi fodder
    if atk <= 1000 and (ctype & TYPE_NORMAL) and not (ctype & TYPE_EFFECT):
        return True
    return False


def rank_tribute_candidates(cards: list[dict], profile: dict) -> list[int]:
    """Tribute oncelik siralamasi: fodder > normal > key (en sonda).

    Doner: tribute edilmeye uygun siraya gore index listesi.
    """
    indexed = list(enumerate(cards))

    def _score(entry: tuple[int, dict]) -> tuple[int, int]:
        _, c = entry
        if is_fodder(c, profile):
            rank = 0
        elif is_key_card(c, profile):
            rank = 2
        else:
            rank = 1
        atk = c.get("card_atk", 0) or 0
        return (rank, atk)  # low rank first, then low atk first

    indexed.sort(key=_score)
    return [idx for idx, _ in indexed]
