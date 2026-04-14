# Yuki — Browser-Based Duel Game
# Copyright (C) 2026 Yuki Contributors
# SPDX-License-Identifier: AGPL-3.0-or-later
#
# message_parser.py — OCGCore binary mesajlarını Python dict'lere çevirir
#
# Motor binary buffer üretiyor. Buffer içinde art arda mesajlar var:
#   [mesaj_uzunluk: uint32][mesaj_tipi: uint8][mesaj_verisi: değişken]
#
# Her mesaj tipinin kendi binary yapısı var. Bu dosya her tipi ayrıştırıp
# okunabilir Python dict'e çevirir.
#
# Mesajlar iki kategoriye ayrılır:
#   - Bilgi mesajları: Oyunculara bildirilir, yanıt gerektirmez
#   - Seçim mesajları: Oyuncudan yanıt (response) gerektirir

import struct
from server.ocg_binding import (
    MSG_RETRY, MSG_HINT, MSG_WAITING, MSG_START, MSG_WIN,
    MSG_SELECT_BATTLECMD, MSG_SELECT_IDLECMD,
    MSG_SELECT_EFFECTYN, MSG_SELECT_YESNO, MSG_SELECT_OPTION,
    MSG_SELECT_CARD, MSG_SELECT_CHAIN, MSG_SELECT_PLACE,
    MSG_SELECT_POSITION, MSG_SELECT_TRIBUTE,
    MSG_SELECT_COUNTER, MSG_SELECT_SUM, MSG_SELECT_UNSELECT_CARD,
    MSG_NEW_TURN, MSG_NEW_PHASE, MSG_DRAW, MSG_DAMAGE, MSG_RECOVER,
    MSG_LPUPDATE, MSG_PAY_LPCOST,
    MSG_MOVE, MSG_POS_CHANGE, MSG_SET, MSG_SWAP,
    MSG_SUMMONING, MSG_SUMMONED, MSG_SPSUMMONING, MSG_SPSUMMONED,
    MSG_FLIPSUMMONING, MSG_FLIPSUMMONED,
    MSG_CHAINING, MSG_CHAINED, MSG_CHAIN_SOLVING, MSG_CHAIN_SOLVED,
    MSG_CHAIN_END, MSG_CHAIN_NEGATED, MSG_CHAIN_DISABLED,
    MSG_ATTACK, MSG_BATTLE, MSG_ATTACK_DISABLED,
    MSG_DAMAGE_STEP_START, MSG_DAMAGE_STEP_END,
    MSG_TOSS_COIN, MSG_TOSS_DICE,
    MSG_SHUFFLE_DECK, MSG_SHUFFLE_HAND, MSG_SHUFFLE_SET_CARD,
    MSG_FIELD_DISABLED,
    MSG_EQUIP, MSG_UNEQUIP, MSG_CARD_TARGET, MSG_CANCEL_TARGET,
    MSG_ADD_COUNTER, MSG_REMOVE_COUNTER,
    MSG_CONFIRM_DECKTOP, MSG_CONFIRM_CARDS,
    MSG_BECOME_TARGET, MSG_CARD_HINT,
    MSG_ROCK_PAPER_SCISSORS, MSG_HAND_RES,
    MSG_ANNOUNCE_RACE, MSG_ANNOUNCE_ATTRIB,
    MSG_ANNOUNCE_CARD, MSG_ANNOUNCE_NUMBER,
    MSG_CARD_SELECTED, MSG_SORT_CHAIN, MSG_SELECT_DISFIELD, MSG_SORT_CARD,
    MSG_NAMES,
)

# Yanıt gerektiren mesaj tipleri
INTERACTIVE_MESSAGES = {
    MSG_SELECT_BATTLECMD, MSG_SELECT_IDLECMD,
    MSG_SELECT_EFFECTYN, MSG_SELECT_YESNO, MSG_SELECT_OPTION,
    MSG_SELECT_CARD, MSG_SELECT_CHAIN, MSG_SELECT_PLACE,
    MSG_SELECT_POSITION, MSG_SELECT_TRIBUTE,
    MSG_SELECT_COUNTER, MSG_SELECT_SUM, MSG_SELECT_UNSELECT_CARD,
    MSG_SELECT_DISFIELD, MSG_SORT_CHAIN, MSG_SORT_CARD,
    MSG_ANNOUNCE_RACE, MSG_ANNOUNCE_ATTRIB,
    MSG_ANNOUNCE_CARD, MSG_ANNOUNCE_NUMBER,
    MSG_ROCK_PAPER_SCISSORS,
}


class BufferReader:
    """Binary buffer'dan veri okumak için yardımcı sınıf.

    OCGCore mesajları little-endian formatta. Bu sınıf sıralı
    okuma yaparak buffer'ı ilerletir.
    """

    def __init__(self, data: bytes):
        self._data = data
        self._pos = 0

    @property
    def remaining(self) -> int:
        return len(self._data) - self._pos

    def read_u8(self) -> int:
        val = self._data[self._pos]
        self._pos += 1
        return val

    def read_u16(self) -> int:
        val = struct.unpack_from("<H", self._data, self._pos)[0]
        self._pos += 2
        return val

    def read_u32(self) -> int:
        val = struct.unpack_from("<I", self._data, self._pos)[0]
        self._pos += 4
        return val

    def read_i32(self) -> int:
        val = struct.unpack_from("<i", self._data, self._pos)[0]
        self._pos += 4
        return val

    def read_u64(self) -> int:
        val = struct.unpack_from("<Q", self._data, self._pos)[0]
        self._pos += 8
        return val

    def read_bytes(self, n: int) -> bytes:
        val = self._data[self._pos:self._pos + n]
        self._pos += n
        return val

    def skip(self, n: int):
        self._pos += n

    def read_loc_info(self) -> dict:
        """Kart konum bilgisi oku: controller, location, sequence, position."""
        return {
            "controller": self.read_u8(),
            "location": self.read_u8(),
            "sequence": self.read_u32(),
            "position": self.read_u32(),
        }

    def read_card_loc(self) -> dict:
        """Kısa kart konum: code, controller, location, sequence, position."""
        return {
            "code": self.read_u32(),
            "controller": self.read_u8(),
            "location": self.read_u8(),
            "sequence": self.read_u8(),
            "position": self.read_u8(),
        }


def split_messages(raw: bytes) -> list[tuple[int, bytes]]:
    """Ham buffer'ı (mesaj_tipi, mesaj_verisi) çiftlerine ayırır.

    Her mesaj: [uzunluk:u32][tip:u8][veri:değişken]
    """
    messages = []
    offset = 0
    while offset + 4 <= len(raw):
        msg_len = struct.unpack_from("<I", raw, offset)[0]
        if msg_len == 0 or offset + 4 + msg_len > len(raw):
            break
        msg_type = raw[offset + 4]
        msg_data = raw[offset + 5:offset + 4 + msg_len]
        messages.append((msg_type, msg_data))
        offset += 4 + msg_len
    return messages


def parse_message(msg_type: int, data: bytes) -> dict:
    """Tek bir mesajı Python dict'e çevirir.

    Returns:
        {
            "type": int,           # Mesaj tipi kodu
            "name": str,           # Mesaj adı (ör. "MSG_DRAW")
            "interactive": bool,   # Yanıt gerektiriyor mu
            "player": int | None,  # Hangi oyuncuya ait (varsa)
            ...                    # Mesaja özel alanlar
        }
    """
    r = BufferReader(data)
    msg = {
        "type": msg_type,
        "name": MSG_NAMES.get(msg_type, f"UNKNOWN_{msg_type}"),
        "interactive": msg_type in INTERACTIVE_MESSAGES,
    }

    parser = _PARSERS.get(msg_type)
    if parser:
        parser(r, msg)
    else:
        msg["raw"] = data

    return msg


# ---------------------------------------------------------------------------
# Bilgi Mesajı Ayrıştırıcıları
# ---------------------------------------------------------------------------

def _parse_start(r: BufferReader, msg: dict):
    """MSG_START: Düello başladı."""
    msg["player"] = r.read_u8()
    # İki oyuncunun LP'si
    msg["lp"] = [0, 0]
    msg["lp"][msg["player"]] = r.read_u32()
    msg["lp"][1 - msg["player"]] = r.read_u32()
    # Deste ve ekstra deste sayıları
    msg["deck_count"] = [0, 0]
    msg["extra_count"] = [0, 0]
    msg["deck_count"][msg["player"]] = r.read_u16()
    msg["extra_count"][msg["player"]] = r.read_u16()
    msg["deck_count"][1 - msg["player"]] = r.read_u16()
    msg["extra_count"][1 - msg["player"]] = r.read_u16()


def _parse_win(r: BufferReader, msg: dict):
    """MSG_WIN: Düello kazanıldı."""
    msg["player"] = r.read_u8()
    msg["reason"] = r.read_u8()


def _parse_new_turn(r: BufferReader, msg: dict):
    """MSG_NEW_TURN: Yeni tur başladı."""
    msg["player"] = r.read_u8()


def _parse_new_phase(r: BufferReader, msg: dict):
    """MSG_NEW_PHASE: Yeni faz."""
    msg["phase"] = r.read_u16()


def _parse_draw(r: BufferReader, msg: dict):
    """MSG_DRAW: Kart çekildi."""
    msg["player"] = r.read_u8()
    count = r.read_u32()
    msg["count"] = count
    msg["cards"] = []
    for _ in range(count):
        code = r.read_u32()
        position = r.read_u32()
        msg["cards"].append({"code": code, "position": position})


def _parse_damage(r: BufferReader, msg: dict):
    """MSG_DAMAGE: LP hasarı."""
    msg["player"] = r.read_u8()
    msg["amount"] = r.read_u32()


def _parse_recover(r: BufferReader, msg: dict):
    """MSG_RECOVER: LP kazanımı."""
    msg["player"] = r.read_u8()
    msg["amount"] = r.read_u32()


def _parse_lpupdate(r: BufferReader, msg: dict):
    """MSG_LPUPDATE: LP güncelleme."""
    msg["player"] = r.read_u8()
    msg["lp"] = r.read_u32()


def _parse_pay_lpcost(r: BufferReader, msg: dict):
    """MSG_PAY_LPCOST: LP maliyeti ödendi."""
    msg["player"] = r.read_u8()
    msg["amount"] = r.read_u32()


def _parse_move(r: BufferReader, msg: dict):
    """MSG_MOVE: Kart hareket etti.

    Format: code(u32) + from(loc_info=10byte) + to(loc_info=10byte) + reason(u32)
    loc_info = {u8 con, u8 loc, u32 seq, u32 pos}
    """
    msg["code"] = r.read_u32()
    msg["from"] = {
        "controller": r.read_u8(),
        "location": r.read_u8(),
        "sequence": r.read_u32(),
        "position": r.read_u32(),
    }
    msg["to"] = {
        "controller": r.read_u8(),
        "location": r.read_u8(),
        "sequence": r.read_u32(),
        "position": r.read_u32(),
    }
    msg["reason"] = r.read_u32()


def _parse_pos_change(r: BufferReader, msg: dict):
    """MSG_POS_CHANGE: Pozisyon değişikliği."""
    msg["code"] = r.read_u32()
    msg["controller"] = r.read_u8()
    msg["location"] = r.read_u8()
    msg["sequence"] = r.read_u8()
    msg["prev_position"] = r.read_u8()
    msg["position"] = r.read_u8()


def _parse_set(r: BufferReader, msg: dict):
    """MSG_SET: code(u32) + loc_info(u8+u8+u32+u32)."""
    msg["code"] = r.read_u32()
    msg["controller"] = r.read_u8()
    msg["location"] = r.read_u8()
    msg["sequence"] = r.read_u32()
    msg["position"] = r.read_u32()


def _parse_summoning(r: BufferReader, msg: dict):
    """MSG_SUMMONING/SPSUMMONING/FLIPSUMMONING: code(u32) + loc_info(u8+u8+u32+u32)."""
    msg["code"] = r.read_u32()
    msg["controller"] = r.read_u8()
    msg["location"] = r.read_u8()
    msg["sequence"] = r.read_u32()
    msg["position"] = r.read_u32()


def _parse_summoned(r: BufferReader, msg: dict):
    """MSG_SUMMONED / MSG_SPSUMMONED / MSG_FLIPSUMMONED: Çağrı tamamlandı."""
    # Bu mesajların ek verisi yok
    pass


def _parse_chaining(r: BufferReader, msg: dict):
    """MSG_CHAINING: Zincir efekti aktifleşiyor."""
    msg["code"] = r.read_u32()
    msg["controller"] = r.read_u8()
    msg["location"] = r.read_u8()
    msg["sequence"] = r.read_u8()
    msg["position"] = r.read_u8()
    # Tetikleyen kart
    msg["triggering_controller"] = r.read_u8()
    msg["triggering_location"] = r.read_u8()
    msg["triggering_sequence"] = r.read_u8()
    msg["effect_description"] = r.read_u64()
    msg["chain_count"] = r.read_u8()


def _parse_chain_end(r: BufferReader, msg: dict):
    """MSG_CHAIN_END: Zincir sona erdi."""
    pass


def _parse_chain_count(r: BufferReader, msg: dict):
    """MSG_CHAINED / MSG_CHAIN_SOLVING / MSG_CHAIN_SOLVED / MSG_CHAIN_NEGATED / MSG_CHAIN_DISABLED."""
    msg["chain_count"] = r.read_u8()


def _parse_attack(r: BufferReader, msg: dict):
    """MSG_ATTACK: Saldırı ilan edildi.

    Format: 2x loc_info {con(u8) loc(u8) seq(u32) pos(u32)} = 20 byte
    """
    msg["attacker_controller"] = r.read_u8()
    msg["attacker_location"] = r.read_u8()
    msg["attacker_sequence"] = r.read_u32()
    msg["attacker_position"] = r.read_u32()
    msg["target_controller"] = r.read_u8()
    msg["target_location"] = r.read_u8()
    msg["target_sequence"] = r.read_u32()
    msg["target_position"] = r.read_u32()


def _parse_battle(r: BufferReader, msg: dict):
    """MSG_BATTLE: Savaş sonucu.

    Format (38 byte): con(u8) loc(u8) seq(u32) pos(u32) atk(i32) def(i32) flag(u8) x2
    """
    msg["attacker_controller"] = r.read_u8()
    msg["attacker_location"] = r.read_u8()
    msg["attacker_sequence"] = r.read_u32()
    msg["attacker_position"] = r.read_u32()
    msg["attacker_atk"] = r.read_i32()
    msg["attacker_def"] = r.read_i32()
    msg["attacker_destroyed"] = r.read_u8()
    msg["target_controller"] = r.read_u8()
    msg["target_location"] = r.read_u8()
    msg["target_sequence"] = r.read_u32()
    msg["target_position"] = r.read_u32()
    msg["target_atk"] = r.read_i32()
    msg["target_def"] = r.read_i32()
    msg["target_destroyed"] = r.read_u8()


def _parse_hint(r: BufferReader, msg: dict):
    """MSG_HINT: Motor ipucu."""
    msg["hint_type"] = r.read_u8()
    msg["player"] = r.read_u8()
    msg["data"] = r.read_u64()


def _parse_shuffle_deck(r: BufferReader, msg: dict):
    """MSG_SHUFFLE_DECK: Deste karıştırıldı."""
    msg["player"] = r.read_u8()


def _parse_shuffle_hand(r: BufferReader, msg: dict):
    """MSG_SHUFFLE_HAND: El karıştırıldı."""
    msg["player"] = r.read_u8()
    count = r.read_u32()
    msg["count"] = count
    msg["cards"] = [r.read_u32() for _ in range(count)]


def _parse_field_disabled(r: BufferReader, msg: dict):
    """MSG_FIELD_DISABLED: Bölge devre dışı."""
    msg["disabled"] = r.read_u32()


def _parse_equip(r: BufferReader, msg: dict):
    """MSG_EQUIP: Techizat edildi."""
    msg["equip_controller"] = r.read_u8()
    msg["equip_location"] = r.read_u8()
    msg["equip_sequence"] = r.read_u8()
    r.skip(1)
    msg["target_controller"] = r.read_u8()
    msg["target_location"] = r.read_u8()
    msg["target_sequence"] = r.read_u8()
    r.skip(1)


def _parse_card_hint(r: BufferReader, msg: dict):
    """MSG_CARD_HINT: Kart ipucu."""
    msg["controller"] = r.read_u8()
    msg["location"] = r.read_u8()
    msg["sequence"] = r.read_u8()
    r.skip(1)
    msg["hint_type"] = r.read_u8()
    msg["value"] = r.read_u64()


def _parse_toss_coin(r: BufferReader, msg: dict):
    """MSG_TOSS_COIN: Yazı/tura sonuçları."""
    msg["player"] = r.read_u8()
    count = r.read_u8()
    msg["results"] = [r.read_u8() for _ in range(count)]


def _parse_toss_dice(r: BufferReader, msg: dict):
    """MSG_TOSS_DICE: Zar sonuçları."""
    msg["player"] = r.read_u8()
    count = r.read_u8()
    msg["results"] = [r.read_u8() for _ in range(count)]


def _parse_become_target(r: BufferReader, msg: dict):
    """MSG_BECOME_TARGET: Hedef olundu."""
    count = r.read_u32()
    msg["targets"] = []
    for _ in range(count):
        msg["targets"].append({
            "controller": r.read_u8(),
            "location": r.read_u8(),
            "sequence": r.read_u8(),
            "position": r.read_u8(),
        })


def _parse_confirm_cards(r: BufferReader, msg: dict):
    """MSG_CONFIRM_DECKTOP / MSG_CONFIRM_CARDS."""
    msg["player"] = r.read_u8()
    count = r.read_u32()
    msg["cards"] = []
    for _ in range(count):
        msg["cards"].append({
            "code": r.read_u32(),
            "controller": r.read_u8(),
            "location": r.read_u8(),
            "sequence": r.read_u8(),
        })


def _parse_counter(r: BufferReader, msg: dict):
    """MSG_ADD_COUNTER / MSG_REMOVE_COUNTER."""
    msg["counter_type"] = r.read_u16()
    msg["controller"] = r.read_u8()
    msg["location"] = r.read_u8()
    msg["sequence"] = r.read_u8()
    msg["count"] = r.read_u16()


# ---------------------------------------------------------------------------
# Seçim (İnteraktif) Mesaj Ayrıştırıcıları
# ---------------------------------------------------------------------------

def _parse_select_idlecmd(r: BufferReader, msg: dict):
    """MSG_SELECT_IDLECMD: Ana Faz komutu seç.

    Kaynak: playerop.cpp — process(Processors::SelectIdleCmd)
    Sıra: summon, spsummon, reposition, mset, sset, activate, flags
    """
    msg["player"] = r.read_u8()

    # Çağrılabilir kartlar (Normal Summon) — seq: u32
    count = r.read_u32()
    msg["summonable"] = []
    for _ in range(count):
        msg["summonable"].append({
            "code": r.read_u32(),
            "controller": r.read_u8(),
            "location": r.read_u8(),
            "sequence": r.read_u32(),
        })

    # Özel çağrılabilir kartlar — seq: u32
    count = r.read_u32()
    msg["special_summonable"] = []
    for _ in range(count):
        msg["special_summonable"].append({
            "code": r.read_u32(),
            "controller": r.read_u8(),
            "location": r.read_u8(),
            "sequence": r.read_u32(),
        })

    # Pozisyon değiştirilebilir kartlar — seq: u8 (!)
    count = r.read_u32()
    msg["repositionable"] = []
    for _ in range(count):
        msg["repositionable"].append({
            "code": r.read_u32(),
            "controller": r.read_u8(),
            "location": r.read_u8(),
            "sequence": r.read_u8(),
        })

    # Canavar set edilebilir kartlar — seq: u32
    count = r.read_u32()
    msg["monster_setable"] = []
    for _ in range(count):
        msg["monster_setable"].append({
            "code": r.read_u32(),
            "controller": r.read_u8(),
            "location": r.read_u8(),
            "sequence": r.read_u32(),
        })

    # Büyü/Tuzak set edilebilir kartlar — seq: u32
    count = r.read_u32()
    msg["spell_setable"] = []
    for _ in range(count):
        msg["spell_setable"].append({
            "code": r.read_u32(),
            "controller": r.read_u8(),
            "location": r.read_u8(),
            "sequence": r.read_u32(),
        })

    # Aktiflenebilir efektler — seq: u32, desc: u64, client_mode: u8
    count = r.read_u32()
    msg["activatable"] = []
    for _ in range(count):
        msg["activatable"].append({
            "code": r.read_u32(),
            "controller": r.read_u8(),
            "location": r.read_u8(),
            "sequence": r.read_u32(),
            "description": r.read_u64(),
            "client_mode": r.read_u8(),
        })

    # Faz geçiş bayrakları
    msg["can_battle_phase"] = bool(r.read_u8())
    msg["can_end_phase"] = bool(r.read_u8())
    msg["can_shuffle"] = bool(r.read_u8()) if r.remaining >= 1 else False


def _parse_select_battlecmd(r: BufferReader, msg: dict):
    """MSG_SELECT_BATTLECMD: Savaş Fazı komutu seç.

    Kaynak: playerop.cpp — process(Processors::SelectBattleCmd)
    Sıra: ÖNCE activatable, SONRA attackable (idle cmd'den farklı!)
    """
    msg["player"] = r.read_u8()

    # Aktiflenebilir efektler (ÖNCE) — seq: u32, desc: u64, client_mode: u8
    count = r.read_u32()
    msg["activatable"] = []
    for _ in range(count):
        msg["activatable"].append({
            "code": r.read_u32(),
            "controller": r.read_u8(),
            "location": r.read_u8(),
            "sequence": r.read_u32(),
            "description": r.read_u64(),
            "client_mode": r.read_u8(),
        })

    # Saldırabilir kartlar (SONRA) — seq: u8
    count = r.read_u32()
    msg["attackable"] = []
    for _ in range(count):
        msg["attackable"].append({
            "code": r.read_u32(),
            "controller": r.read_u8(),
            "location": r.read_u8(),
            "sequence": r.read_u8(),
            "direct_attackable": bool(r.read_u8()),
        })

    msg["can_main2"] = bool(r.read_u8())
    msg["can_end"] = bool(r.read_u8())


def _parse_select_effectyn(r: BufferReader, msg: dict):
    """MSG_SELECT_EFFECTYN: Bir efekti aktiflemek ister misin?"""
    msg["player"] = r.read_u8()
    msg["code"] = r.read_u32()
    msg["controller"] = r.read_u8()
    msg["location"] = r.read_u8()
    msg["sequence"] = r.read_u8()
    r.skip(1)
    msg["description"] = r.read_u64()


def _parse_select_yesno(r: BufferReader, msg: dict):
    """MSG_SELECT_YESNO: Evet/Hayır sorusu."""
    msg["player"] = r.read_u8()
    msg["description"] = r.read_u64()


def _parse_select_option(r: BufferReader, msg: dict):
    """MSG_SELECT_OPTION: Seçenek seç."""
    msg["player"] = r.read_u8()
    count = r.read_u8()
    msg["options"] = [r.read_u64() for _ in range(count)]


def _parse_select_card(r: BufferReader, msg: dict):
    """MSG_SELECT_CARD: Kart sec.

    Kaynak: playerop.cpp — her kart: code(u32) + loc_info(u8+u8+u32+u32)
    """
    msg["player"] = r.read_u8()
    msg["cancelable"] = bool(r.read_u8())
    msg["min"] = r.read_u32()
    msg["max"] = r.read_u32()
    count = r.read_u32()
    msg["cards"] = []
    for _ in range(count):
        msg["cards"].append({
            "code": r.read_u32(),
            "controller": r.read_u8(),
            "location": r.read_u8(),
            "sequence": r.read_u32(),
            "position": r.read_u32(),
        })


def _parse_select_chain(r: BufferReader, msg: dict):
    """MSG_SELECT_CHAIN: Zincire yanit ver (veya pas gec).

    Kaynak: playerop.cpp — code(u32) + loc_info(u8+u8+u32+u32) + desc(u64) + client_mode(u8)
    """
    msg["player"] = r.read_u8()
    msg["spe_count"] = r.read_u8()
    msg["forced"] = bool(r.read_u8())
    msg["hint_timing"] = r.read_u32()
    msg["other_timing"] = r.read_u32()
    count = r.read_u32()
    msg["chains"] = []
    for _ in range(count):
        msg["chains"].append({
            "code": r.read_u32(),
            "controller": r.read_u8(),
            "location": r.read_u8(),
            "sequence": r.read_u32(),
            "position": r.read_u32(),
            "description": r.read_u64(),
            "client_mode": r.read_u8(),
        })


def _parse_select_place(r: BufferReader, msg: dict):
    """MSG_SELECT_PLACE / MSG_SELECT_DISFIELD: Bölge seç."""
    msg["player"] = r.read_u8()
    msg["count"] = r.read_u8()
    msg["selectable"] = r.read_u32()  # bitmask — seçilebilir bölgeler


def _parse_select_position(r: BufferReader, msg: dict):
    """MSG_SELECT_POSITION: Pozisyon seç."""
    msg["player"] = r.read_u8()
    msg["code"] = r.read_u32()
    msg["positions"] = r.read_u8()  # bitmask


def _parse_select_tribute(r: BufferReader, msg: dict):
    """MSG_SELECT_TRIBUTE: Kurban sec.

    Kaynak: playerop.cpp — code(u32) + con(u8) + loc(u8) + seq(u32) + release_param(u8)
    NOT: Burada loc_info KULLANILMIYOR, position yok!
    """
    msg["player"] = r.read_u8()
    msg["cancelable"] = bool(r.read_u8())
    msg["min"] = r.read_u32()
    msg["max"] = r.read_u32()
    count = r.read_u32()
    msg["cards"] = []
    for _ in range(count):
        msg["cards"].append({
            "code": r.read_u32(),
            "controller": r.read_u8(),
            "location": r.read_u8(),
            "sequence": r.read_u32(),
            "release_param": r.read_u8(),
        })


def _parse_select_counter(r: BufferReader, msg: dict):
    """MSG_SELECT_COUNTER: Sayaç seç."""
    msg["player"] = r.read_u8()
    msg["counter_type"] = r.read_u16()
    msg["count"] = r.read_u16()
    num = r.read_u32()
    msg["cards"] = []
    for _ in range(num):
        msg["cards"].append({
            "code": r.read_u32(),
            "controller": r.read_u8(),
            "location": r.read_u8(),
            "sequence": r.read_u8(),
            "counter_count": r.read_u16(),
        })


def _parse_select_sum(r: BufferReader, msg: dict):
    """MSG_SELECT_SUM: Toplam sec (rituel malzeme vs.).

    Kaynak: playerop.cpp — her kart: code(u32) + loc_info(u8+u8+u32+u32) + sum_param(u32)
    """
    msg["player"] = r.read_u8()
    msg["mode"] = r.read_u8()  # 0=tam esit, 1=en az
    msg["target_sum"] = r.read_u32()
    msg["min"] = r.read_u32()
    msg["max"] = r.read_u32()

    # Zorunlu kartlar
    must_count = r.read_u32()
    msg["must_cards"] = []
    for _ in range(must_count):
        msg["must_cards"].append({
            "code": r.read_u32(),
            "controller": r.read_u8(),
            "location": r.read_u8(),
            "sequence": r.read_u32(),
            "position": r.read_u32(),
            "param": r.read_u32(),
        })

    # Secilebilir kartlar
    can_count = r.read_u32()
    msg["selectable_cards"] = []
    for _ in range(can_count):
        msg["selectable_cards"].append({
            "code": r.read_u32(),
            "controller": r.read_u8(),
            "location": r.read_u8(),
            "sequence": r.read_u32(),
            "position": r.read_u32(),
            "param": r.read_u32(),
        })


def _parse_select_unselect_card(r: BufferReader, msg: dict):
    """MSG_SELECT_UNSELECT_CARD: Kart sec/secimi kaldir.

    Kaynak: playerop.cpp — her kart: code(u32) + loc_info(u8+u8+u32+u32)
    """
    msg["player"] = r.read_u8()
    msg["finishable"] = bool(r.read_u8())
    msg["cancelable"] = bool(r.read_u8())
    msg["min"] = r.read_u32()
    msg["max"] = r.read_u32()

    select_count = r.read_u32()
    msg["selectable"] = []
    for _ in range(select_count):
        msg["selectable"].append({
            "code": r.read_u32(),
            "controller": r.read_u8(),
            "location": r.read_u8(),
            "sequence": r.read_u32(),
            "position": r.read_u32(),
        })

    unselect_count = r.read_u32()
    msg["unselectable"] = []
    for _ in range(unselect_count):
        msg["unselectable"].append({
            "code": r.read_u32(),
            "controller": r.read_u8(),
            "location": r.read_u8(),
            "sequence": r.read_u32(),
            "position": r.read_u32(),
        })


def _parse_sort_card(r: BufferReader, msg: dict):
    """MSG_SORT_CARD / MSG_SORT_CHAIN: Kartlari sirala."""
    msg["player"] = r.read_u8()
    count = r.read_u32()
    msg["cards"] = []
    for _ in range(count):
        msg["cards"].append({
            "code": r.read_u32(),
            "controller": r.read_u8(),
            "location": r.read_u8(),
            "sequence": r.read_u32(),
        })


def _parse_announce_race(r: BufferReader, msg: dict):
    """MSG_ANNOUNCE_RACE: Irk ilan et."""
    msg["player"] = r.read_u8()
    msg["count"] = r.read_u8()
    # available: u64 (yeni OCGCore) veya u32 (eski) — remaining'e gore sec
    msg["available"] = r.read_u64() if r.remaining >= 8 else r.read_u32()


def _parse_announce_attrib(r: BufferReader, msg: dict):
    """MSG_ANNOUNCE_ATTRIB: Ozellik ilan et."""
    msg["player"] = r.read_u8()
    msg["count"] = r.read_u8()
    msg["available"] = r.read_u32()


def _parse_announce_card(r: BufferReader, msg: dict):
    """MSG_ANNOUNCE_CARD: Kart adi ilan et."""
    msg["player"] = r.read_u8()
    count = r.read_u8()
    msg["opcodes"] = [r.read_u64() for _ in range(count)]


def _parse_announce_number(r: BufferReader, msg: dict):
    """MSG_ANNOUNCE_NUMBER: Sayi ilan et."""
    msg["player"] = r.read_u8()
    count = r.read_u8()
    msg["numbers"] = [r.read_u64() for _ in range(count)]


def _parse_rps(r: BufferReader, msg: dict):
    """MSG_ROCK_PAPER_SCISSORS."""
    msg["player"] = r.read_u8()


def _parse_hand_res(r: BufferReader, msg: dict):
    """MSG_HAND_RES."""
    msg["result1"] = r.read_u8()
    msg["result2"] = r.read_u8()


def _parse_noop(r: BufferReader, msg: dict):
    """Veri içermeyen mesajlar."""
    pass


# ---------------------------------------------------------------------------
# Mesaj tipi → ayrıştırıcı eşleştirmesi
# ---------------------------------------------------------------------------

_PARSERS = {
    MSG_START: _parse_start,
    MSG_WIN: _parse_win,
    MSG_NEW_TURN: _parse_new_turn,
    MSG_NEW_PHASE: _parse_new_phase,
    MSG_DRAW: _parse_draw,
    MSG_DAMAGE: _parse_damage,
    MSG_RECOVER: _parse_recover,
    MSG_LPUPDATE: _parse_lpupdate,
    MSG_PAY_LPCOST: _parse_pay_lpcost,
    MSG_MOVE: _parse_move,
    MSG_POS_CHANGE: _parse_pos_change,
    MSG_SET: _parse_set,
    MSG_SUMMONING: _parse_summoning,
    MSG_SUMMONED: _parse_summoned,
    MSG_SPSUMMONING: _parse_summoning,
    MSG_SPSUMMONED: _parse_summoned,
    MSG_FLIPSUMMONING: _parse_summoning,
    MSG_FLIPSUMMONED: _parse_summoned,
    MSG_CHAINING: _parse_chaining,
    MSG_CHAINED: _parse_chain_count,
    MSG_CHAIN_SOLVING: _parse_chain_count,
    MSG_CHAIN_SOLVED: _parse_chain_count,
    MSG_CHAIN_END: _parse_chain_end,
    MSG_CHAIN_NEGATED: _parse_chain_count,
    MSG_CHAIN_DISABLED: _parse_chain_count,
    MSG_ATTACK: _parse_attack,
    MSG_BATTLE: _parse_battle,
    MSG_ATTACK_DISABLED: _parse_noop,
    MSG_DAMAGE_STEP_START: _parse_noop,
    MSG_DAMAGE_STEP_END: _parse_noop,
    MSG_HINT: _parse_hint,
    MSG_WAITING: _parse_noop,
    MSG_RETRY: _parse_noop,
    MSG_SHUFFLE_DECK: _parse_shuffle_deck,
    MSG_SHUFFLE_HAND: _parse_shuffle_hand,
    MSG_FIELD_DISABLED: _parse_field_disabled,
    MSG_EQUIP: _parse_equip,
    MSG_UNEQUIP: _parse_equip,  # aynı format
    MSG_CARD_TARGET: _parse_equip,  # aynı format
    MSG_CANCEL_TARGET: _parse_equip,
    MSG_CARD_HINT: _parse_card_hint,
    MSG_TOSS_COIN: _parse_toss_coin,
    MSG_TOSS_DICE: _parse_toss_dice,
    MSG_BECOME_TARGET: _parse_become_target,
    MSG_CONFIRM_DECKTOP: _parse_confirm_cards,
    MSG_CONFIRM_CARDS: _parse_confirm_cards,
    MSG_ADD_COUNTER: _parse_counter,
    MSG_REMOVE_COUNTER: _parse_counter,
    MSG_HAND_RES: _parse_hand_res,
    MSG_CARD_SELECTED: _parse_noop,
    MSG_SHUFFLE_SET_CARD: _parse_noop,
    MSG_SWAP: _parse_noop,
    # İnteraktif
    MSG_SELECT_IDLECMD: _parse_select_idlecmd,
    MSG_SELECT_BATTLECMD: _parse_select_battlecmd,
    MSG_SELECT_EFFECTYN: _parse_select_effectyn,
    MSG_SELECT_YESNO: _parse_select_yesno,
    MSG_SELECT_OPTION: _parse_select_option,
    MSG_SELECT_CARD: _parse_select_card,
    MSG_SELECT_CHAIN: _parse_select_chain,
    MSG_SELECT_PLACE: _parse_select_place,
    MSG_SELECT_POSITION: _parse_select_position,
    MSG_SELECT_TRIBUTE: _parse_select_tribute,
    MSG_SELECT_COUNTER: _parse_select_counter,
    MSG_SELECT_SUM: _parse_select_sum,
    MSG_SELECT_UNSELECT_CARD: _parse_select_unselect_card,
    MSG_SELECT_DISFIELD: _parse_select_place,  # ayni format
    MSG_SORT_CHAIN: _parse_sort_card,
    MSG_SORT_CARD: _parse_sort_card,
    MSG_ANNOUNCE_RACE: _parse_announce_race,
    MSG_ANNOUNCE_ATTRIB: _parse_announce_attrib,
    MSG_ANNOUNCE_CARD: _parse_announce_card,
    MSG_ANNOUNCE_NUMBER: _parse_announce_number,
    MSG_ROCK_PAPER_SCISSORS: _parse_rps,
}
