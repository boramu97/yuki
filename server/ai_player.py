# Yuki — Browser-Based Duel Game
# Copyright (C) 2026 Yuki Contributors
# SPDX-License-Identifier: AGPL-3.0-or-later
#
# ai_player.py — Kural bazlı AI oyuncu
#
# Her SELECT mesajına response_builder fonksiyonlarını kullanarak
# binary yanıt üretir. Basit ama oynanabilir seviyede.

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
    build_announce_card_response,
    build_announce_number_response,
    build_rps_response,
    build_sort_response,
)
from server.ocg_binding import (
    MSG_SELECT_IDLECMD, MSG_SELECT_BATTLECMD, MSG_SELECT_CHAIN,
    MSG_SELECT_EFFECTYN, MSG_SELECT_YESNO, MSG_SELECT_OPTION,
    MSG_SELECT_CARD, MSG_SELECT_PLACE, MSG_SELECT_POSITION,
    MSG_SELECT_TRIBUTE, MSG_SELECT_COUNTER, MSG_SELECT_SUM,
    MSG_SELECT_UNSELECT_CARD, MSG_SELECT_DISFIELD,
    MSG_SORT_CHAIN, MSG_SORT_CARD,
    MSG_ANNOUNCE_RACE, MSG_ANNOUNCE_ATTRIB, MSG_ANNOUNCE_CARD,
    MSG_ANNOUNCE_NUMBER, MSG_ROCK_PAPER_SCISSORS,
    LOCATION_MZONE, LOCATION_SZONE,
)

import os
import struct
import random

from server.ai_profiles import (
    get_priority, get_profile, is_key_card, is_fodder, rank_tribute_candidates,
)

def _pack_i32(v): return struct.pack("<i", v)

# MSG_ANNOUNCE_CARD icin populer Yu-Gi-Oh kart kodlari.
# Retry rotation ile denenir; filter DSL yorumlanmaz — motor reddederse
# sonraki kart denenir, 15+ retry'da deadlock escape devreye girer.
_ANNOUNCE_CARD_CANDIDATES = [
    46986414,   # Dark Magician
    89631139,   # Blue-Eyes White Dragon
    74677422,   # Red-Eyes B. Dragon
    40640057,   # Kuriboh
    83764718,   # Monster Reborn
    24094653,   # Polymerization
    44095762,   # Mirror Force
    55144522,   # Pot of Greed
    5318639,    # Magic Cylinder
    5405694,    # Dark Hole
    12580477,   # Raigeki
    21844576,   # Elemental HERO Avian
    64788463,   # Jinzo
    71413901,   # Summoned Skull
    89943723,   # Elemental HERO Neos
]

# Bot karar logu — YUKI_AI_TRACE=1 ile acilir. Debug amacli;
# production'da kapali tutulmali (ama log satir sayisi kucuk).
_AI_TRACE = os.environ.get("YUKI_AI_TRACE", "0") == "1"


def _trace(msg_type: int, msg: dict, response: bytes, retry: int):
    """Karar trace (journalctl'e duser)."""
    if not _AI_TRACE:
        return
    name_map = {
        0x0A: "BATTLECMD", 0x0B: "IDLECMD", 0x0C: "EFFECTYN", 0x0D: "YESNO",
        0x0E: "OPTION", 0x0F: "CARD", 0x10: "CHAIN", 0x11: "PLACE",
        0x12: "POSITION", 0x13: "TRIBUTE", 0x14: "COUNTER", 0x15: "SUM",
        0x1A: "UNSELECT_CARD", 0x16: "DISFIELD",
    }
    mname = name_map.get(msg_type, f"0x{msg_type:02X}")
    resp_hex = response[:16].hex() if response else ""
    # Onemli field'lari ozetle
    summary_parts = []
    for k in ("forced", "cancelable", "min", "max", "count"):
        if k in msg:
            summary_parts.append(f"{k}={msg[k]}")
    if "chains" in msg:
        summary_parts.append(f"chains={len(msg['chains'])}")
    if "cards" in msg:
        summary_parts.append(f"cards={len(msg['cards'])}")
    if "attackable" in msg:
        summary_parts.append(f"attackable={len(msg['attackable'])}")
    summary = " ".join(summary_parts)
    print(f"[AI] {mname} retry={retry} {summary} => {resp_hex}", flush=True)


def ai_respond(msg_type: int, msg: dict, retry_attempt: int = 0, bot_name: str = "") -> bytes:
    """SELECT mesajına kural bazlı binary yanıt üretir.

    retry_attempt: motor kac kere RETRY istedi. Her retry'da farkli bir
    strateji denemek icin kullanilir — ayni cevabi tekrar gondermek
    sonsuz loop'a sebep olurdu.
    bot_name: profile lookup icin ("Yugi", "Kaiba", ...); bos ise default.
    """
    response = _ai_respond_inner(msg_type, msg, retry_attempt, bot_name)
    _trace(msg_type, msg, response, retry_attempt)
    return response


def _ai_respond_inner(msg_type: int, msg: dict, retry_attempt: int = 0, bot_name: str = "") -> bytes:

    if msg_type == MSG_SELECT_IDLECMD:
        return _idle_cmd(msg, retry_attempt, bot_name)

    if msg_type == MSG_SELECT_BATTLECMD:
        return _battle_cmd(msg, retry_attempt)

    if msg_type == MSG_SELECT_CHAIN:
        return _chain(msg, retry_attempt)

    if msg_type == MSG_SELECT_EFFECTYN:
        # Retry'da efekti iptal et (hayir) — belki efekt tetiklemesi problemliydi
        return build_effectyn_response(retry_attempt == 0)

    if msg_type == MSG_SELECT_YESNO:
        return build_yesno_response(retry_attempt == 0)

    if msg_type == MSG_SELECT_OPTION:
        # Retry'da farkli secenek dene
        options = msg.get("options", [])
        max_idx = max(0, len(options) - 1) if options else 0
        return build_option_response(min(retry_attempt, max_idx))

    if msg_type == MSG_SELECT_CARD:
        return _select_card(msg, retry_attempt, bot_name)

    if msg_type in (MSG_SELECT_PLACE, MSG_SELECT_DISFIELD):
        return _select_place(msg)

    if msg_type == MSG_SELECT_POSITION:
        return _select_position(msg)

    if msg_type == MSG_SELECT_TRIBUTE:
        return _select_tribute(msg, retry_attempt, bot_name)

    if msg_type == MSG_SELECT_COUNTER:
        return _select_counter(msg)

    if msg_type == MSG_SELECT_SUM:
        return _select_sum(msg, retry_attempt)

    if msg_type == MSG_SELECT_UNSELECT_CARD:
        return _select_unselect(msg, retry_attempt, bot_name)

    if msg_type == MSG_ANNOUNCE_RACE:
        races = msg.get("available", 0)
        # İlk geçerli ırkı seç
        for bit in range(25):
            if races & (1 << bit):
                return build_announce_race_response(1 << bit)
        return build_announce_race_response(1)

    if msg_type == MSG_ANNOUNCE_ATTRIB:
        attrs = msg.get("available", 0)
        for bit in range(8):
            if attrs & (1 << bit):
                return build_announce_attrib_response(1 << bit)
        return build_announce_attrib_response(1)

    if msg_type == MSG_ANNOUNCE_CARD:
        # Motor filter DSL (opcodes) gonderir; filter VM karmasik, bypass edilir.
        # Retry rotation ile populer kart kodlarini dene — birisi filter'a uyarsa kabul.
        idx = min(retry_attempt, len(_ANNOUNCE_CARD_CANDIDATES) - 1)
        return build_announce_card_response(_ANNOUNCE_CARD_CANDIDATES[idx])

    if msg_type == MSG_ANNOUNCE_NUMBER:
        return build_announce_number_response(0)

    if msg_type == MSG_ROCK_PAPER_SCISSORS:
        return build_rps_response(random.randint(1, 3))

    if msg_type in (MSG_SORT_CHAIN, MSG_SORT_CARD):
        return build_sort_response([])

    # Bilinmeyen — pas/iptal yanıtı
    print(f"[BOT] Bilinmeyen mesaj tipi: {msg_type:#x} — fallback -1")
    return _pack_i32(-1)


def _idle_cmd(msg: dict, retry_attempt: int = 0, bot_name: str = "") -> bytes:
    """Ana Faz kararları — bot stiline göre priority + retry rotasyonu.

    retry_attempt >= 2: "end" gonder — sonsuz loop'a girmeyelim.
    """

    summonable = msg.get("summonable", [])
    special = msg.get("special_summonable", [])
    activatable = msg.get("activatable", [])
    spell_setable = msg.get("spell_setable", [])
    monster_setable = msg.get("monster_setable", [])
    can_battle = msg.get("can_battle_phase", False)

    # 2+ retry → "end" ile kurtul.
    if retry_attempt >= 2:
        return build_idle_cmd_response("end")

    # Bot stiline gore priority listesi
    style_order = get_priority(bot_name)

    # Mevcut secenekleri (action, arg) pair'leri olarak hazirla, key'le
    options: dict[str, list[tuple[str, int]]] = {
        "hand_activate": [],
        "field_activate": [],
        "summon": [],
        "spsummon": [],
        "sset": [],
        "mset": [],
        "battle": [],
        "end": [("end", 0)],
    }

    # Eldeki spell/trap aktivasyon (location=0x02=HAND)
    for i, card in enumerate(activatable):
        if card.get("location", 0) == 0x02:
            options["hand_activate"].append(("activate", i))

    # Sahadan (mzone/szone) aktivasyon
    for i, card in enumerate(activatable):
        if card.get("location", 0) in (0x04, 0x08):
            options["field_activate"].append(("activate", i))

    # Canavar cagri — en yuksek ATK once
    if summonable:
        options["summon"].append(("summon", _best_atk_index(summonable)))

    # Ozel cagri — en yuksek ATK once
    if special:
        options["spsummon"].append(("spsummon", _best_atk_index(special)))

    # Set (spell/trap)
    if spell_setable:
        options["sset"].append(("sset", 0))

    # Set (monster face-down)
    if monster_setable:
        options["mset"].append(("mset", 0))

    # Savas fazi
    if can_battle:
        options["battle"].append(("battle", 0))

    # Stile gore siralanmis mevcut secenek akisi
    flat: list[tuple[str, int]] = []
    for key in style_order:
        flat.extend(options.get(key, []))

    # Retry offset ile rotasyon
    idx = min(retry_attempt, len(flat) - 1)
    action, arg = flat[idx] if flat else ("end", 0)

    if action in ("battle", "end"):
        return build_idle_cmd_response(action)
    return build_idle_cmd_response(action, arg)


def _battle_cmd(msg: dict, retry_attempt: int = 0) -> bytes:
    """Savaş Fazı kararları — rakip sahası kontrol edilerek.

    Attacker-first policy: en yuksek ATK'li saldirgan + direct saldiri > guvenli hedef.
    Zayif canavar guclu rakibe intihar ettirilmez.
    """
    attackable = msg.get("attackable", [])
    activatable = msg.get("activatable", [])
    opp_monsters = msg.get("opponent_monsters", [])

    # Retry — saldiri/aktivasyon reddedildi, end'e kac
    if retry_attempt >= 1:
        return build_battle_cmd_response("end")

    def _can_win(my_atk: int) -> bool:
        """my_atk bu attacker ile yenilebilir en az bir hedef var mi?"""
        for m in opp_monsters:
            pos = m.get("position", 0)
            if pos & 0x1:  # Yuz yukari ATK — ATK karsilastir
                if my_atk > (m.get("atk", 0) or 0):
                    return True
            elif pos & 0x4:  # Yuz yukari DEF
                if my_atk > (m.get("def", 0) or 0):
                    return True
            elif pos & 0x8:  # Yuz asagi — makul ATK ile dene
                if my_atk >= 1500:
                    return True
        return False

    if attackable:
        # En yuksek ATK'li attacker'dan basla — zayif canavar intihar etmesin
        indexed = sorted(
            enumerate(attackable),
            key=lambda x: x[1].get("card_atk", 0) or 0,
            reverse=True,
        )
        for i, card in indexed:
            my_atk = card.get("card_atk", 0) or 0
            direct = card.get("direct_attackable", False)
            if direct:
                return build_battle_cmd_response("attack", i)
            if my_atk <= 0:
                continue
            if _can_win(my_atk):
                return build_battle_cmd_response("attack", i)

    # Efekt aktifleştir
    if activatable:
        return build_battle_cmd_response("activate", 0)

    # Saldırmaya değmez — savaşı bitir
    return build_battle_cmd_response("end")


def _chain(msg: dict, retry_attempt: int = 0) -> bytes:
    """Zincir fırsatı — trap/spell/monster efekt aktifle veya pas.

    Oncelik: SZONE (trap/continuous spell) > MZONE (monster trigger) >
    HAND (Kuriboh tipi) > GRAVE (dark world vs).
    """
    chains = msg.get("chains", [])
    forced = msg.get("forced", False)

    # Forced + chains var → index 0 zorunlu
    if forced and chains:
        return build_chain_response(min(retry_attempt, len(chains) - 1))

    # Retry — aktivasyon reddedildi, pas gec
    if retry_attempt >= 1:
        return build_chain_response(-1)

    # Lokasyon onceligi ile ara (SZONE > MZONE > HAND > GRAVE)
    for priority_loc in (0x08, 0x04, 0x02, 0x10):
        for i, ch in enumerate(chains):
            if ch.get("location", 0) == priority_loc:
                return build_chain_response(i)

    # Pas
    return build_chain_response(-1)


def _select_card(msg: dict, retry_attempt: int = 0, bot_name: str = "") -> bytes:
    """Kart seçimi — min-max bounds ile en guclu kartlari sec.

    retry'da max_count'a dogru artir, alternatif kartlar dene.
    """
    cards = msg.get("cards", [])
    min_count = max(1, msg.get("min", 1))
    max_count = max(min_count, msg.get("max", min_count))

    if not cards:
        # Bos liste — iptal
        return build_card_response([], cancel=True)

    # Hedef sayi: min'den baslayip retry basina arttir, max'i gecme
    target = min(min_count + retry_attempt, max_count, len(cards))
    target = max(target, 1)

    # Retry'da farkli kart subsetleri dene (en guclulerden rotasyon)
    indexed = list(enumerate(cards))
    indexed.sort(key=lambda x: x[1].get("card_atk", 0) or 0, reverse=True)

    offset = retry_attempt % max(1, len(cards) - target + 1)
    indices = [idx for idx, _ in indexed[offset:offset + target]]
    if len(indices) < min_count:
        indices = [idx for idx, _ in indexed[:min_count]]
    return build_card_response(indices)


def _select_place(msg: dict) -> bytes:
    """Bölge seçimi — bitmask'ten ilk uygun boş slotu bul.

    Bitmask formatı (ters mantık — bit 0 = boş, bit 1 = dolu):
      Bit  0-6:  Kendi MZONE (7 slot)
      Bit  8-15: Kendi SZONE (8 slot)
      Bit 16-22: Rakip MZONE
      Bit 24-31: Rakip SZONE
    """
    flag = msg.get("selectable", 0)
    player = msg.get("player", 0)

    # Kendi MZONE
    for s in range(7):
        if not (flag & (1 << s)):
            return build_place_response(player, 0x04, s)
    # Kendi SZONE
    for s in range(8):
        if not (flag & (1 << (s + 8))):
            return build_place_response(player, 0x08, s)
    # Rakip MZONE
    for s in range(7):
        if not (flag & (1 << (s + 16))):
            return build_place_response(1 - player, 0x04, s)
    # Rakip SZONE
    for s in range(8):
        if not (flag & (1 << (s + 24))):
            return build_place_response(1 - player, 0x08, s)

    return build_place_response(player, 0x04, 0)


def _select_position(msg: dict) -> bytes:
    """Pozisyon seçimi — ATK yüksekse saldırı, değilse savunma."""
    positions = msg.get("positions", 0)
    code = msg.get("code", 0)
    atk = msg.get("card_atk", 0) or 0
    defn = msg.get("card_def", 0) or 0

    # Saldırı pozisyonu tercih (ATK >= DEF)
    if atk >= defn and (positions & 0x1):
        return build_position_response(0x1)  # FACEUP_ATTACK
    if positions & 0x8:
        return build_position_response(0x8)  # FACEDOWN_DEFENSE
    if positions & 0x4:
        return build_position_response(0x4)  # FACEUP_DEFENSE
    if positions & 0x1:
        return build_position_response(0x1)
    return build_position_response(positions & 0xF)


def _select_tribute(msg: dict, retry_attempt: int = 0, bot_name: str = "") -> bytes:
    """Kurban seçimi — profile key/fodder sirasina gore (fodder once, key en sonda).

    Retry'da kademeli olarak daha fazla kart (max'a kadar).
    """
    cards = msg.get("cards", [])
    min_count = max(1, msg.get("min", 1))
    max_count = max(min_count, msg.get("max", min_count))

    if not cards:
        return build_tribute_response([], cancel=True)

    profile = get_profile(bot_name)
    ordered = rank_tribute_candidates(cards, profile)

    target = min(min_count + retry_attempt, max_count, len(cards))
    target = max(target, 1)
    indices = ordered[:target]
    return build_tribute_response(indices)


def _select_counter(msg: dict) -> bytes:
    """Sayaç seçimi — ilk karttan."""
    cards = msg.get("cards", [])
    counter_count = msg.get("count", 1)

    counts = []
    remaining = counter_count
    for card in cards:
        available = card.get("counter", 0)
        take = min(remaining, available)
        counts.append(take)
        remaining -= take
        if remaining <= 0:
            break

    # Kalan kartlar için 0 ekle
    while len(counts) < len(cards):
        counts.append(0)

    return build_counter_response(counts)


def _select_sum(msg: dict, retry_attempt: int = 0) -> bytes:
    """Toplam seçimi — Valkyrion / ritual gibi sum-based fusion icin.

    Param: her kartin "value" (genelde level).
    mode=0: must + selected param'lari toplami == target_sum
    mode=1: must + selected param'lari toplami >= target_sum

    Retry'da kademeli olarak farkli kombinasyonlar dene (n'inci match skip).
    """
    from itertools import combinations
    must = msg.get("must_cards", []) or []
    sel = msg.get("selectable_cards", []) or []
    target = msg.get("target_sum", 0)
    mode = msg.get("mode", 0)
    min_c = max(0, msg.get("min", 1))
    max_c = max(min_c, msg.get("max", len(sel)) or len(sel))

    must_indices = list(range(len(must)))
    must_sum = sum((c.get("param", 0) or 0) for c in must)

    if not sel:
        return build_sum_response(must_indices if must else [0])

    # Target 0 ise min_c kadar kart sec (ritual'de ayni-seviye gereksinimi olmayabilir)
    if target <= 0:
        k = min(max(min_c, 1), len(sel))
        return build_sum_response(must_indices + list(range(len(must), len(must) + k)))

    # Subset-sum arama — target'i karsilayan tum kombinasyonlari topla
    n = len(sel)
    candidates: list[list[int]] = []
    for k in range(max(min_c, 1), min(max_c, n) + 1):
        for combo in combinations(range(n), k):
            s = sum((sel[i].get("param", 0) or 0) for i in combo)
            total = s + must_sum
            if (mode == 0 and total == target) or (mode != 0 and total >= target):
                candidates.append(list(combo))
            if len(candidates) > 30:
                break
        if len(candidates) > 30:
            break

    if candidates:
        # Retry offset ile farkli kombinasyon dene
        pick = candidates[retry_attempt % len(candidates)]
        indices = must_indices + [len(must) + i for i in pick]
        return build_sum_response(indices)

    # Eslestiren kombinasyon yok — fallback: must + minimum selectable
    k = min(max(min_c, 1), n)
    return build_sum_response(must_indices + list(range(len(must), len(must) + k)))


def _select_unselect(msg: dict, retry_attempt: int = 0, bot_name: str = "") -> bytes:
    """Seç/kaldır — ilk seçilebilir kartı seç veya bitir."""
    selectable = msg.get("selectable", []) or msg.get("selectable_cards", [])
    finishable = msg.get("finishable", False)
    min_count = msg.get("min", 0)

    # Retry — bitir (varsa) aksi halde farkli index
    if retry_attempt >= 1 and finishable:
        return build_unselect_card_response(-1)

    if selectable and min_count > 0:
        idx = min(retry_attempt, len(selectable) - 1) if selectable else 0
        return build_unselect_card_response(max(0, idx))

    if finishable:
        return build_unselect_card_response(-1)

    if selectable:
        idx = min(retry_attempt, len(selectable) - 1)
        return build_unselect_card_response(max(0, idx))

    return build_unselect_card_response(-1)


def _best_atk_index(cards: list[dict]) -> int:
    """Listeden en yüksek ATK'lı kartın indeksini döndürür."""
    best_idx = 0
    best_atk = -1
    for i, card in enumerate(cards):
        atk = card.get("card_atk", 0) or 0
        if atk > best_atk:
            best_atk = atk
            best_idx = i
    return best_idx
