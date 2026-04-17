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

import struct
import random

def _pack_i32(v): return struct.pack("<i", v)


def ai_respond(msg_type: int, msg: dict) -> bytes:
    """SELECT mesajına kural bazlı binary yanıt üretir."""

    if msg_type == MSG_SELECT_IDLECMD:
        return _idle_cmd(msg)

    if msg_type == MSG_SELECT_BATTLECMD:
        return _battle_cmd(msg)

    if msg_type == MSG_SELECT_CHAIN:
        return _chain(msg)

    if msg_type == MSG_SELECT_EFFECTYN:
        return build_effectyn_response(True)

    if msg_type == MSG_SELECT_YESNO:
        return build_yesno_response(True)

    if msg_type == MSG_SELECT_OPTION:
        return build_option_response(0)

    if msg_type == MSG_SELECT_CARD:
        return _select_card(msg)

    if msg_type in (MSG_SELECT_PLACE, MSG_SELECT_DISFIELD):
        return _select_place(msg)

    if msg_type == MSG_SELECT_POSITION:
        return _select_position(msg)

    if msg_type == MSG_SELECT_TRIBUTE:
        return _select_tribute(msg)

    if msg_type == MSG_SELECT_COUNTER:
        return _select_counter(msg)

    if msg_type == MSG_SELECT_SUM:
        return _select_sum(msg)

    if msg_type == MSG_SELECT_UNSELECT_CARD:
        return _select_unselect(msg)

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
        return build_announce_card_response(0)

    if msg_type == MSG_ANNOUNCE_NUMBER:
        return build_announce_number_response(0)

    if msg_type == MSG_ROCK_PAPER_SCISSORS:
        return build_rps_response(random.randint(1, 3))

    if msg_type in (MSG_SORT_CHAIN, MSG_SORT_CARD):
        return build_sort_response([])

    # Bilinmeyen — pas/iptal yanıtı
    print(f"[BOT] Bilinmeyen mesaj tipi: {msg_type:#x} — fallback -1")
    return _pack_i32(-1)


def _idle_cmd(msg: dict) -> bytes:
    """Ana Faz kararları — öncelik sırası ile."""

    summonable = msg.get("summonable", [])
    special = msg.get("special_summonable", [])
    activatable = msg.get("activatable", [])
    spell_setable = msg.get("spell_setable", [])
    monster_setable = msg.get("monster_setable", [])
    can_battle = msg.get("can_battle_phase", False)

    # 1) Spell/trap aktifle (eldeki spell'ler — güçlü hamle)
    for i, card in enumerate(activatable):
        loc = card.get("location", 0)
        if loc == 0x02:  # El — spell aktifle
            return build_idle_cmd_response("activate", i)

    # 2) En güçlü canavarı çağır
    if summonable:
        best_idx = _best_atk_index(summonable)
        return build_idle_cmd_response("summon", best_idx)

    # 3) Özel çağrı
    if special:
        best_idx = _best_atk_index(special)
        return build_idle_cmd_response("spsummon", best_idx)

    # 4) Sahadan efekt aktifle (MZONE/SZONE)
    for i, card in enumerate(activatable):
        loc = card.get("location", 0)
        if loc in (0x04, 0x08):
            return build_idle_cmd_response("activate", i)

    # 5) Spell/trap set et
    if spell_setable:
        return build_idle_cmd_response("sset", 0)

    # 6) Canavar set et (çağıramadıysa)
    if monster_setable:
        return build_idle_cmd_response("mset", 0)

    # 7) Savaş fazına geç (sahada canavar varsa)
    if can_battle:
        return build_idle_cmd_response("battle")

    # 8) Turu bitir
    return build_idle_cmd_response("end")


def _battle_cmd(msg: dict) -> bytes:
    """Savaş Fazı kararları — rakip sahası kontrol edilerek."""
    attackable = msg.get("attackable", [])
    activatable = msg.get("activatable", [])
    opp_monsters = msg.get("opponent_monsters", [])

    if attackable:
        for i, card in enumerate(attackable):
            my_atk = card.get("card_atk", 0) or 0
            direct = card.get("direct_attackable", False)

            # Direkt saldırı (rakipte canavar yok) — her zaman saldır
            if direct:
                return build_battle_cmd_response("attack", i)

            if my_atk <= 0:
                continue

            # Rakipte yenebileceğim bir canavar var mı?
            can_win = False
            for m in opp_monsters:
                pos = m.get("position", 0)
                if pos & 0x1:  # Yüz yukarı saldırı — ATK karşılaştır
                    if my_atk > (m.get("atk", 0) or 0):
                        can_win = True
                        break
                elif pos & 0x4:  # Yüz yukarı savunma — DEF karşılaştır
                    if my_atk > (m.get("def", 0) or 0):
                        can_win = True
                        break
                elif pos & 0x8:  # Yüz aşağı savunma — stat bilinmiyor, makul ATK'yla dene
                    if my_atk >= 1500:
                        can_win = True
                        break

            if can_win:
                return build_battle_cmd_response("attack", i)

    # Efekt aktifleştir
    if activatable:
        return build_battle_cmd_response("activate", 0)

    # Saldırmaya değmez — savaşı bitir
    return build_battle_cmd_response("end")


def _chain(msg: dict) -> bytes:
    """Zincir fırsatı — trap/spell aktifle veya pas."""
    chains = msg.get("chains", [])
    forced = msg.get("forced", False)

    if forced and chains:
        return build_chain_response(0)

    # Trap varsa aktifle (SZONE'dan)
    for i, ch in enumerate(chains):
        loc = ch.get("location", 0)
        if loc == 0x08:  # SZONE — muhtemelen trap
            return build_chain_response(i)

    # Elden aktivasyon (Kuriboh gibi)
    for i, ch in enumerate(chains):
        loc = ch.get("location", 0)
        if loc == 0x02:  # El
            return build_chain_response(i)

    # Pas
    return build_chain_response(-1)


def _select_card(msg: dict) -> bytes:
    """Kart seçimi — min adet, en güçlüleri seç."""
    cards = msg.get("cards", [])
    min_count = msg.get("min", 1)
    max_count = msg.get("max", 1)

    if not cards:
        return build_card_response([0])

    # ATK'ya göre sırala, en güçlüleri seç
    indexed = list(enumerate(cards))
    indexed.sort(key=lambda x: x[1].get("card_atk", 0) or 0, reverse=True)

    count = min(min_count, len(cards))
    indices = [idx for idx, _ in indexed[:count]]
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


def _select_tribute(msg: dict) -> bytes:
    """Kurban seçimi — en düşük ATK'lıları seç."""
    cards = msg.get("cards", [])
    min_count = msg.get("min", 1)

    if not cards:
        return build_tribute_response([0])

    # En düşük ATK'lıları seç (kurban için)
    indexed = list(enumerate(cards))
    indexed.sort(key=lambda x: x[1].get("card_atk", 0) or 0)

    count = min(min_count, len(cards))
    indices = [idx for idx, _ in indexed[:count]]
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


def _select_sum(msg: dict) -> bytes:
    """Toplam seçimi — minimum kartla hedef toplamı tuttur."""
    cards = msg.get("must_cards", []) + msg.get("selectable_cards", [])
    min_count = msg.get("min", 1)

    if not cards:
        return build_sum_response([0])

    # Basit: minimum sayıda kart seç
    count = min(min_count, len(cards))
    return build_sum_response(list(range(count)))


def _select_unselect(msg: dict) -> bytes:
    """Seç/kaldır — ilk seçilebilir kartı seç veya bitir."""
    selectable = msg.get("selectable", []) or msg.get("selectable_cards", [])
    finishable = msg.get("finishable", False)
    min_count = msg.get("min", 0)

    if selectable and min_count > 0:
        return build_unselect_card_response(0)

    if finishable:
        return build_unselect_card_response(-1)

    # Secilebilir kart varsa sec
    if selectable:
        return build_unselect_card_response(0)

    # Bitir
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
