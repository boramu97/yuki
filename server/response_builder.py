# Yuki — Browser-Based Duel Game
# Copyright (C) 2026 Yuki Contributors
# SPDX-License-Identifier: AGPL-3.0-or-later
#
# response_builder.py — Oyuncu kararlarını OCGCore binary yanıtına çevirir
#
# Motor bir seçim mesajı gönderdiğinde (MSG_SELECT_*), oyuncunun yanıtı
# binary formatta geri gönderilmelidir. Bu modül her seçim tipi için
# doğru binary yanıtı oluşturur.

import struct


def _pack_u32(value: int) -> bytes:
    return struct.pack("<I", value)


def _pack_i32(value: int) -> bytes:
    return struct.pack("<i", value)


def _pack_u16(value: int) -> bytes:
    return struct.pack("<H", value)


def _pack_u64(value: int) -> bytes:
    return struct.pack("<Q", value)


def _pack_u8(value: int) -> bytes:
    return struct.pack("<B", value)


# --- Ana Faz Komutları ---

def build_idle_cmd_response(action: str, index: int = 0) -> bytes:
    """MSG_SELECT_IDLECMD yanıtı oluşturur.

    Kaynak: playerop.cpp — (index << 16) | action_type formatı, tek i32.
    action:  "summon", "spsummon", "reposition", "mset", "sset",
             "activate", "battle", "end", "shuffle"
    index:   Seçilen kartın/efektin listesindeki sırası (0'dan başlar)
    """
    action_map = {
        "summon": 0,
        "spsummon": 1,
        "reposition": 2,
        "mset": 3,
        "sset": 4,
        "activate": 5,
        "battle": 6,
        "end": 7,
        "shuffle": 8,
    }
    action_code = action_map[action]
    return _pack_i32((index << 16) | action_code)


def build_battle_cmd_response(action: str, index: int = 0) -> bytes:
    """MSG_SELECT_BATTLECMD yanıtı.

    Kaynak: playerop.cpp — (index << 16) | action_type formatı, tek i32.
    Savaş Fazı'nda:
      action: "activate", "attack", "main2", "end"
      index:  Kartın/efektin sırası
    NOT: battlecmd'de sıra farklı: 0=activate, 1=attack, 2=main2, 3=end
    """
    action_map = {
        "activate": 0,
        "attack": 1,
        "main2": 2,
        "end": 3,
    }
    action_code = action_map[action]
    return _pack_i32((index << 16) | action_code)


# --- Evet/Hayır ---

def build_effectyn_response(yes: bool) -> bytes:
    """MSG_SELECT_EFFECTYN yanıtı: Efekti aktifle? Evet=1, Hayır=0."""
    return _pack_u32(1 if yes else 0)


def build_yesno_response(yes: bool) -> bytes:
    """MSG_SELECT_YESNO yanıtı."""
    return _pack_u32(1 if yes else 0)


# --- Seçenek ---

def build_option_response(index: int) -> bytes:
    """MSG_SELECT_OPTION yanıtı: Seçenek indeksi."""
    return _pack_u32(index)


# --- Kart Seçimi ---

def build_card_response(indices: list[int], cancel: bool = False) -> bytes:
    """MSG_SELECT_CARD yanıtı.

    Kaynak: playerop.cpp parse_response_cards
    Format: [type:i32][count:u32][idx0:u32][idx1:u32]...
    type=-1: iptal, type=0: u32 indeksleri
    """
    if cancel:
        return _pack_i32(-1)
    data = _pack_i32(0)  # type = 0 (u32 indices)
    data += _pack_u32(len(indices))
    for idx in indices:
        data += _pack_u32(idx)
    return data


# --- Zincir Seçimi ---

def build_chain_response(index: int) -> bytes:
    """MSG_SELECT_CHAIN yanıtı.

    index = -1: Pas geç (zincire ekleme)
    index >= 0: Seçilen zincir efektinin indeksi
    """
    return _pack_i32(index)


# --- Bölge Seçimi ---

def build_place_response(player: int, location: int, sequence: int) -> bytes:
    """MSG_SELECT_PLACE / MSG_SELECT_DISFIELD yanıtı.

    Seçilen bölgeyi bit maskesi olarak döndürür.
    """
    # Bölge maskesi: player bit 4, location bitleri, sequence
    return _pack_u8(player) + _pack_u8(location) + _pack_u8(sequence)


# --- Pozisyon Seçimi ---

def build_position_response(position: int) -> bytes:
    """MSG_SELECT_POSITION yanıtı.

    position: POS_FACEUP_ATTACK (0x1), POS_FACEDOWN_DEFENSE (0x8), vs.
    """
    return _pack_u32(position)


# --- Kurban Seçimi ---

def build_tribute_response(indices: list[int], cancel: bool = False) -> bytes:
    """MSG_SELECT_TRIBUTE yaniti.

    parse_response_cards formati: [type:i32=0][count:u32][idx0:u32]...
    """
    if cancel:
        return _pack_i32(-1)
    data = _pack_i32(0)
    data += _pack_u32(len(indices))
    for idx in indices:
        data += _pack_u32(idx)
    return data


# --- Sayaç Seçimi ---

def build_counter_response(counts: list[int]) -> bytes:
    """MSG_SELECT_COUNTER yanıtı: Her karttaki sayaç miktarı."""
    data = b""
    for count in counts:
        data += _pack_u16(count)
    return data


# --- Toplam Seçimi ---

def build_sum_response(indices: list[int]) -> bytes:
    """MSG_SELECT_SUM yaniti.

    parse_response_cards formatı: [type:i32=0][count:u32][idx0:u32]...
    """
    data = _pack_i32(0)  # type prefix
    data += _pack_u32(len(indices))
    for idx in indices:
        data += _pack_u32(idx)
    return data


# --- Seç/Seçimi Kaldır ---

def build_unselect_card_response(index: int) -> bytes:
    """MSG_SELECT_UNSELECT_CARD yaniti.

    Kaynak: playerop.cpp — returns.at<i32>(0) = action, returns.at<i32>(1) = index
    action=-1: iptal/bitir, action=1: sec
    """
    if index < 0:
        return _pack_i32(-1)
    return _pack_i32(1) + _pack_i32(index)


# --- İlan ---

def build_announce_race_response(race_mask: int) -> bytes:
    """MSG_ANNOUNCE_RACE yanıtı: İlan edilen ırk bit maskesi (u64 — OCGCore race 64-bit)."""
    return _pack_u64(race_mask)


def build_announce_attrib_response(attrib_mask: int) -> bytes:
    """MSG_ANNOUNCE_ATTRIB yanıtı."""
    return _pack_u32(attrib_mask)


def build_announce_card_response(code: int) -> bytes:
    """MSG_ANNOUNCE_CARD yaniti: Kart kodu."""
    return _pack_u32(code)


def build_announce_number_response(number: int) -> bytes:
    """MSG_ANNOUNCE_NUMBER yaniti: Secilen sayi indeksi."""
    return _pack_u32(number)


# --- Taş Kağıt Makas ---

def build_rps_response(choice: int) -> bytes:
    """MSG_ROCK_PAPER_SCISSORS yanıtı: 1=taş, 2=kağıt, 3=makas."""
    return _pack_u8(choice)


# --- Kart Sıralama ---

def build_sort_response(indices: list[int]) -> bytes:
    """MSG_SORT_CARD / MSG_SORT_CHAIN yanıtı."""
    data = b""
    for idx in indices:
        data += _pack_u32(idx)
    return data
