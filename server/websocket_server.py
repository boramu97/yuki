# Yuki — Browser-Based Duel Game
# Copyright (C) 2026 Yuki Contributors
# SPDX-License-Identifier: AGPL-3.0-or-later
#
# websocket_server.py — Ana WebSocket sunucusu
#
# Tarayıcıdan gelen bağlantıları yönetir. Mesaj protokolü:
#
# İstemci → Sunucu (JSON):
#   {"action": "create_room", "name": "Oyuncu1"}
#   {"action": "join_room", "name": "Oyuncu2", "room_id": "abc123"}
#   {"action": "quick_match", "name": "Oyuncu"}
#   {"action": "set_deck", "deck": [89631139, 46986414, ...]}
#   {"action": "ready"}
#   {"action": "response", "data": {...}}  ← düello yanıtı
#   {"action": "list_rooms"}
#
# Sunucu → İstemci (JSON):
#   {"action": "room_created", "room_id": "abc123"}
#   {"action": "room_joined", "room_id": "abc123", "team": 0}
#   {"action": "player_joined", "name": "Oyuncu2"}
#   {"action": "player_left", "name": "Oyuncu1"}
#   {"action": "duel_start"}
#   {"action": "info", "msg": {...}}       ← bilgi mesajı
#   {"action": "select", "msg": {...}}     ← seçim mesajı
#   {"action": "retry"}                    ← geçersiz yanıt
#   {"action": "duel_end", "winner": 0}
#   {"action": "error", "message": "..."}
#   {"action": "rooms", "rooms": [...]}

import asyncio
import json
import struct

import websockets

from server.room import RoomManager, Player, RoomState
from server.duel_manager import DuelManager
from server.user_database import UserDatabase
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
from server.decks import (
    YUGI_DECK, BASTION_DECK, KAIBA_DECK, ANCIENT_GEAR_DECK,
    JOEY_DECK, MAI_DECK, SYRUS_DECK, DINO_DECK,
    INSECT_DECK, REX_RAPTOR_DECK, PEGASUS_DECK, JADEN_DECK,
    # Battle City bot desteleri
    SEEKER_DECK, STRINGS_DECK, ARKANA_DECK, UMBRA_LUMIS_DECK,
    YAMI_BAKURA_DECK, KAIBA_BATTLECITY_DECK, YAMI_MARIK_DECK,
)
import random as _random
from server.ocg_binding import (
    MSG_SELECT_IDLECMD, MSG_SELECT_BATTLECMD, MSG_SELECT_CHAIN,
    MSG_SELECT_EFFECTYN, MSG_SELECT_YESNO, MSG_SELECT_OPTION,
    MSG_SELECT_CARD, MSG_SELECT_PLACE, MSG_SELECT_POSITION,
    MSG_SELECT_TRIBUTE, MSG_SELECT_COUNTER, MSG_SELECT_SUM,
    MSG_SELECT_UNSELECT_CARD, MSG_SELECT_DISFIELD,
    MSG_SORT_CHAIN, MSG_SORT_CARD,
    MSG_ANNOUNCE_RACE, MSG_ANNOUNCE_ATTRIB, MSG_ANNOUNCE_CARD, MSG_ANNOUNCE_NUMBER,
    MSG_ROCK_PAPER_SCISSORS,
)

# Varsayilan test destesi
DEFAULT_DECK = BASTION_DECK

# Bot desteleri (main + extra deck — motor ayirir)
BOT_DECKS = {
    "Yugi": YUGI_DECK,
    "Kaiba": KAIBA_DECK,
    "Joey": JOEY_DECK,
    "Mai": MAI_DECK,
    "Bastion": BASTION_DECK,
    "Dino": DINO_DECK,
    "Weevil": INSECT_DECK,
    "Rex": REX_RAPTOR_DECK,
    "Pegasus": PEGASUS_DECK,
    "Jaden": JADEN_DECK,
    # Battle City
    "Seeker": SEEKER_DECK,
    "Strings": STRINGS_DECK,
    "Arkana": ARKANA_DECK,
    "UmbraLumis": UMBRA_LUMIS_DECK,
    "YamiBakura": YAMI_BAKURA_DECK,
    "KaibaBC": KAIBA_BATTLECITY_DECK,
    "YamiMarik": YAMI_MARIK_DECK,
}

# --- Macera Tanımları ---
# Node tipleri:
#   duel   — rakiple duello. Galibiyet → dust + rastgele kartlar
#   mystery — 3 rastgele kart sunulur, birini koleksiyona ekler
#   shop   — 5 rastgele kart, %50 indirimli toz maliyetiyle alınabilir
#   boss   — final duello, özel tema
# Her macera lineer yol: node_index 0'dan başlar, sırayla ilerler.
# Tamamlanan node'lar bir daha oynanamaz (adventure_progress tablosunda işaretlenir).
ADVENTURES = {
    "duel_island": {
        "name": "Duello Adasi",
        "nodes": [
            {"type": "duel",    "bot": "Rex",     "bot_name": "Rex Raptor",       "dust": 50,  "cards": 2},
            {"type": "mystery"},
            {"type": "duel",    "bot": "Weevil",  "bot_name": "Weevil Underwood", "dust": 75,  "cards": 2},
            {"type": "shop"},
            {"type": "duel",    "bot": "Mai",     "bot_name": "Mai Valentine",    "dust": 100, "cards": 3},
            {"type": "mystery"},
            {"type": "duel",    "bot": "Joey",    "bot_name": "Joey Wheeler",     "dust": 125, "cards": 3},
            {"type": "shop"},
            {"type": "boss",    "bot": "Pegasus", "bot_name": "Maximillion Pegasus", "dust": 200, "cards": 5},
        ],
    },
    "battle_city": {
        "name": "Battle City",
        "nodes": [
            # 4 ön eleme — serbest sırada oynanır (gate=[])
            {"type": "duel",  "bot": "Seeker",     "bot_name": "Rare Hunter (Seeker)",
             "subtitle": "Sahte Exodia ile hile yapan Nadir Avcı",
             "dust": 75, "cards": 1, "locator": 1, "gate": []},
            {"type": "duel",  "bot": "Strings",    "bot_name": "Strings",
             "subtitle": "Marik'in zihin kontrolündeki kukla",
             "dust": 75, "cards": 1, "locator": 1, "gate": []},
            {"type": "duel",  "bot": "Arkana",     "bot_name": "Arkana (Pandora)",
             "subtitle": "Karanlık Büyücü ustası",
             "dust": 75, "cards": 1, "locator": 1, "gate": []},
            {"type": "duel",  "bot": "UmbraLumis", "bot_name": "Umbra & Lumis",
             "subtitle": "Maskeli İkili",
             "dust": 75, "cards": 1, "locator": 1, "gate": []},
            # Final etabı — 4 locator ile Battle Ship açılır, sonra linear
            {"type": "duel",  "bot": "YamiBakura", "bot_name": "Yami Bakura",
             "subtitle": "Binyıl Yüzüğü'nün kara ruhu",
             "dust": 150, "cards": 2, "gate": [0, 1, 2, 3]},
            {"type": "duel",  "bot": "KaibaBC",    "bot_name": "Seto Kaiba",
             "subtitle": "Yarı Final — KaibaCorp hava gemisinde",
             "dust": 200, "cards": 3, "gate": [4]},
            {"type": "boss",  "bot": "YamiMarik",  "bot_name": "Yami Marik",
             "subtitle": "Final — İşigitsuzlu Kral",
             "dust": 500, "cards": 5, "gate": [5]},
        ],
    },
}

# Global yöneticiler
room_manager = RoomManager()
user_db = UserDatabase()


# --- Macera Node Yardımcıları ---

def _adv_node(adv_id: str, node_idx: int):
    """ADVENTURES'tan node dondurur, gecersizse (None, hata_mesaji)."""
    adv = ADVENTURES.get(adv_id)
    if not adv:
        return None, None, "Gecersiz macera"
    nodes = adv.get("nodes", [])
    if node_idx < 0 or node_idx >= len(nodes):
        return None, None, "Gecersiz node"
    return adv, nodes[node_idx], None


def _check_node_available(user_id: int, adv_id: str, node_idx: int) -> str | None:
    """Node oynanabilir mi? Hata varsa mesaj, yoksa None dondurur.

    `gate` field'i varsa: belirtilen tum node index'leri tamamlanmis olmali.
    Yoksa fallback: klasik linear (onceki node tamamlanmis).
    """
    progress = user_db.get_adventure_progress(user_id, adv_id)
    if node_idx in progress:
        return "Bu asama zaten tamamlandi"
    adv, node, err = _adv_node(adv_id, node_idx)
    if err:
        return err
    gate = node.get("gate")
    if gate is not None:
        # Serbest sira — gate icindeki tum node'lar tamamlanmis olmali
        missing = [g for g in gate if g not in progress]
        if missing:
            return "Bu asama henuz kilitli (gerekli rakipler yenilmedi)"
    else:
        # Default linear
        if node_idx > 0 and (node_idx - 1) not in progress:
            return "Onceki asamayi tamamla"
    return None


def _roll_random_cards(user_id: int, count: int, exclude_owned: bool = True) -> list[int]:
    """Kart havuzundan rastgele kodlar dondurur (fusion haric — onlar zaten bedava)."""
    monsters, spells, traps, _fusions = user_db._load_card_pool()
    pool = monsters + spells + traps
    if exclude_owned:
        owned = set(user_db.get_collection(user_id))
        pool = [c for c in pool if c not in owned]
    if not pool:
        # Her seyi sahipse fusion disindan tekrar havuz olustur
        pool = monsters + spells + traps
    _random.shuffle(pool)
    return pool[:count]


def _card_meta(code: int) -> dict:
    """Kart kodundan isim/ATK/DEF/tier meta bilgisi."""
    from server.config import CARD_DB_PATH
    import sqlite3 as _sq
    meta = {"code": code, "card_name": "", "card_atk": 0, "card_def": 0, "card_type": 0, "tier": "B"}
    try:
        conn = _sq.connect(str(CARD_DB_PATH))
        row = conn.execute(
            "SELECT d.name, t.atk, t.def, t.type FROM datas t LEFT JOIN texts d ON d.id = t.id WHERE t.id=?",
            (code,),
        ).fetchone()
        conn.close()
        if row:
            meta["card_name"] = row[0] or ""
            meta["card_atk"] = row[1] or 0
            meta["card_def"] = row[2] or 0
            meta["card_type"] = row[3] or 0
            meta["tier"] = user_db.card_tier(code)
    except Exception:
        pass
    return meta


def _shop_price(code: int) -> tuple[int, int]:
    """(orijinal_fiyat, indirimli_fiyat) — %50 indirim."""
    tier = user_db.card_tier(code)
    original = user_db.DUST_TABLE[tier]["craft"]
    return original, max(1, original // 2)


def _handle_mystery_offer(user_id: int, adv_id: str, node_idx: int) -> dict:
    adv, node, err = _adv_node(adv_id, node_idx)
    if err:
        return {"action": "error", "message": err}
    if node.get("type") != "mystery":
        return {"action": "error", "message": "Bu node gizem degil"}
    err = _check_node_available(user_id, adv_id, node_idx)
    if err:
        return {"action": "error", "message": err}

    pending = user_db.get_pending_offer(user_id, adv_id, node_idx)
    if not pending:
        codes = _roll_random_cards(user_id, 3)
        pending = {"type": "mystery", "cards": [_card_meta(c) for c in codes]}
        user_db.save_pending_offer(user_id, adv_id, node_idx, pending)
    return {
        "action": "mystery_offer",
        "adventure": adv_id,
        "node": node_idx,
        "cards": pending["cards"],
    }


def _handle_mystery_claim(user_id: int, adv_id: str, node_idx: int, code: int) -> dict:
    adv, node, err = _adv_node(adv_id, node_idx)
    if err:
        return {"action": "error", "message": err}
    if node.get("type") != "mystery":
        return {"action": "error", "message": "Bu node gizem degil"}
    err = _check_node_available(user_id, adv_id, node_idx)
    if err:
        return {"action": "error", "message": err}

    pending = user_db.get_pending_offer(user_id, adv_id, node_idx)
    if not pending or code not in [c.get("code") for c in pending.get("cards", [])]:
        return {"action": "error", "message": "Gecersiz kart secimi"}

    user_db.add_card(user_id, code)
    user_db.complete_adventure_stage(user_id, adv_id, node_idx, 0, [])
    user_db.clear_pending_offer(user_id, adv_id, node_idx)
    return {
        "action": "mystery_claimed",
        "adventure": adv_id,
        "node": node_idx,
        "code": code,
    }


def _handle_shop_offer(user_id: int, adv_id: str, node_idx: int) -> dict:
    adv, node, err = _adv_node(adv_id, node_idx)
    if err:
        return {"action": "error", "message": err}
    if node.get("type") != "shop":
        return {"action": "error", "message": "Bu node dukkan degil"}
    err = _check_node_available(user_id, adv_id, node_idx)
    if err:
        return {"action": "error", "message": err}

    pending = user_db.get_pending_offer(user_id, adv_id, node_idx)
    if not pending:
        codes = _roll_random_cards(user_id, 5)
        cards = []
        for c in codes:
            meta = _card_meta(c)
            original, discounted = _shop_price(c)
            meta["price_original"] = original
            meta["price"] = discounted
            cards.append(meta)
        pending = {"type": "shop", "cards": cards, "purchased": []}
        user_db.save_pending_offer(user_id, adv_id, node_idx, pending)
    return {
        "action": "shop_offer",
        "adventure": adv_id,
        "node": node_idx,
        "cards": pending["cards"],
        "purchased": pending.get("purchased", []),
        "dust": user_db.get_dust(user_id),
    }


def _handle_shop_buy(user_id: int, adv_id: str, node_idx: int, code: int) -> dict:
    adv, node, err = _adv_node(adv_id, node_idx)
    if err:
        return {"action": "error", "message": err}
    if node.get("type") != "shop":
        return {"action": "error", "message": "Bu node dukkan degil"}
    err = _check_node_available(user_id, adv_id, node_idx)
    if err:
        return {"action": "error", "message": err}

    pending = user_db.get_pending_offer(user_id, adv_id, node_idx)
    if not pending:
        return {"action": "error", "message": "Dukkan henuz acilmadi"}

    # Kart tekliflerde mi?
    card_entry = next((c for c in pending["cards"] if c.get("code") == code), None)
    if not card_entry:
        return {"action": "error", "message": "Gecersiz kart"}

    purchased = set(pending.get("purchased", []))
    if code in purchased:
        return {"action": "error", "message": "Zaten alindi"}

    price = int(card_entry.get("price", 0))
    if not user_db.spend_dust(user_id, price):
        return {"action": "error", "message": "Yetersiz toz"}

    user_db.add_card(user_id, code)
    purchased.add(code)
    pending["purchased"] = list(purchased)
    user_db.save_pending_offer(user_id, adv_id, node_idx, pending)
    return {
        "action": "shop_bought",
        "adventure": adv_id,
        "node": node_idx,
        "code": code,
        "dust": user_db.get_dust(user_id),
        "purchased": pending["purchased"],
    }


def _handle_shop_leave(user_id: int, adv_id: str, node_idx: int) -> dict:
    adv, node, err = _adv_node(adv_id, node_idx)
    if err:
        return {"action": "error", "message": err}
    if node.get("type") != "shop":
        return {"action": "error", "message": "Bu node dukkan degil"}
    err = _check_node_available(user_id, adv_id, node_idx)
    if err:
        return {"action": "error", "message": err}

    user_db.complete_adventure_stage(user_id, adv_id, node_idx, 0, [])
    user_db.clear_pending_offer(user_id, adv_id, node_idx)
    return {
        "action": "shop_left",
        "adventure": adv_id,
        "node": node_idx,
    }

# Oyuncu → Player eşleştirmesi (bağlantı bazlı)
_connections: dict[object, Player] = {}
_player_rooms: dict[object, str] = {}  # ws → room_id
_auth_tokens: dict[object, str] = {}  # ws → token


def _build_response(msg_type: int, data: dict) -> bytes:
    """İstemciden gelen yanıt verisini motor binary formatına çevirir.

    İstemci JSON gönderir, biz binary'ye çeviririz.
    """
    if msg_type == MSG_SELECT_IDLECMD:
        action = data.get("action", "end")
        index = data.get("index", 0)
        return build_idle_cmd_response(action, index)

    if msg_type == MSG_SELECT_BATTLECMD:
        action = data.get("action", "end")
        index = data.get("index", 0)
        return build_battle_cmd_response(action, index)

    if msg_type == MSG_SELECT_CHAIN:
        index = data.get("index", -1)
        return build_chain_response(index)

    if msg_type == MSG_SELECT_EFFECTYN:
        return build_effectyn_response(data.get("yes", False))

    if msg_type == MSG_SELECT_YESNO:
        return build_yesno_response(data.get("yes", False))

    if msg_type == MSG_SELECT_OPTION:
        return build_option_response(data.get("index", 0))

    if msg_type == MSG_SELECT_CARD:
        indices = data.get("indices", [0])
        cancel = data.get("cancel", False)
        return build_card_response(indices, cancel)

    if msg_type in (MSG_SELECT_PLACE, MSG_SELECT_DISFIELD):
        return build_place_response(
            data.get("player", 0),
            data.get("location", 0x04),
            data.get("sequence", 0),
        )

    if msg_type == MSG_SELECT_POSITION:
        return build_position_response(data.get("position", 0x1))

    if msg_type == MSG_SELECT_TRIBUTE:
        return build_tribute_response(data.get("indices", [0]))

    if msg_type == MSG_SELECT_COUNTER:
        return build_counter_response(data.get("counts", []))

    if msg_type == MSG_SELECT_SUM:
        return build_sum_response(data.get("indices", []))

    if msg_type == MSG_SELECT_UNSELECT_CARD:
        return build_unselect_card_response(data.get("index", -1))

    if msg_type == MSG_ANNOUNCE_RACE:
        return build_announce_race_response(data.get("race", 1))

    if msg_type == MSG_ANNOUNCE_ATTRIB:
        return build_announce_attrib_response(data.get("attribute", 1))

    if msg_type == MSG_ANNOUNCE_CARD:
        return build_announce_card_response(data.get("code", 0))

    if msg_type == MSG_ANNOUNCE_NUMBER:
        return build_announce_number_response(data.get("index", 0))

    if msg_type == MSG_ROCK_PAPER_SCISSORS:
        return build_rps_response(data.get("choice", 1))

    if msg_type in (MSG_SORT_CHAIN, MSG_SORT_CARD):
        return build_sort_response(data.get("indices", []))

    # Bilinmeyen tip — ham veri geç
    return b"\x00\x00\x00\x00"


def _resolve_deck(data: dict, user_id: int) -> list[int]:
    """Client'tan deste geliyorsa onu kullan, yoksa sunucudaki aktif desteyi yükle."""
    deck = data.get("deck")
    if deck and len(deck) >= 40:
        return deck
    cards = user_db.get_active_deck_cards(user_id)
    return cards if cards else DEFAULT_DECK


async def _send_error(ws, message: str):
    await ws.send(json.dumps({"action": "error", "message": message}))


async def handle_connection(ws):
    """Tek bir WebSocket bağlantısını yönetir."""
    player = None
    room_id = None

    try:
        async for raw_msg in ws:
            try:
                data = json.loads(raw_msg)
            except json.JSONDecodeError:
                await _send_error(ws, "Geçersiz JSON")
                continue

            action = data.get("action")

            # --- Kayıt ---
            if action == "register":
                username = data.get("username", "")
                password = data.get("password", "")
                ok, msg = user_db.register(username, password)
                await ws.send(json.dumps({
                    "action": "register_result",
                    "success": ok,
                    "message": msg,
                }))
                continue

            # --- Giriş ---
            if action == "login":
                username = data.get("username", "")
                password = data.get("password", "")
                token, msg = user_db.login(username, password)
                if token:
                    _auth_tokens[ws] = token
                    user = user_db.get_user(token)
                    await ws.send(json.dumps({
                        "action": "login_result",
                        "success": True,
                        "message": msg,
                        "token": token,
                        "username": user.username,
                        "active_deck_slot": user_db.get_active_deck_slot(user.user_id),
                    }))
                else:
                    await ws.send(json.dumps({
                        "action": "login_result",
                        "success": False,
                        "message": msg,
                    }))
                continue

            # --- Token ile oturum doğrula ---
            if action == "auth":
                token = data.get("token", "")
                user = user_db.get_user(token)
                if user:
                    _auth_tokens[ws] = token
                    await ws.send(json.dumps({
                        "action": "auth_result",
                        "success": True,
                        "username": user.username,
                        "active_deck_slot": user_db.get_active_deck_slot(user.user_id),
                    }))
                else:
                    await ws.send(json.dumps({
                        "action": "auth_result",
                        "success": False,
                    }))
                continue

            # Auth gerektiren actionlar — giriş yapmadan oda oluşturulamaz
            if ws not in _auth_tokens:
                await _send_error(ws, "Once giris yap")
                continue

            # Auth'lu kullanıcı adını al
            _user = user_db.get_user(_auth_tokens[ws])
            _username = _user.username if _user else "Player"

            # --- Koleksiyon ---
            if action == "get_collection":
                cards = user_db.get_collection(_user.user_id)
                card_pool = user_db.get_card_pool()
                preset_decks = user_db.get_preset_decks()
                dust = user_db.get_dust(_user.user_id)
                await ws.send(json.dumps({
                    "action": "collection",
                    "cards": cards,
                    "card_pool": card_pool,
                    "preset_decks": preset_decks,
                    "dust": dust,
                }))
                continue

            # --- Dust (Toz) ---
            if action == "craft_card":
                code = data.get("code", 0)
                ok, msg, dust = user_db.craft_card(_user.user_id, code)
                cards = user_db.get_collection(_user.user_id) if ok else None
                resp = {"action": "craft_result", "success": ok, "message": msg, "dust": dust}
                if cards is not None:
                    resp["cards"] = cards
                await ws.send(json.dumps(resp))
                continue

            if action == "disenchant_card":
                code = data.get("code", 0)
                ok, msg, dust = user_db.disenchant_card(_user.user_id, code)
                cards = user_db.get_collection(_user.user_id) if ok else None
                resp = {"action": "disenchant_result", "success": ok, "message": msg, "dust": dust}
                if cards is not None:
                    resp["cards"] = cards
                await ws.send(json.dumps(resp))
                continue

            # --- Desteler ---
            if action == "get_decks":
                decks = user_db.get_decks(_user.user_id)
                await ws.send(json.dumps({
                    "action": "decks",
                    "decks": decks,
                }))
                continue

            if action == "save_deck":
                slot = data.get("slot", 0)
                name = data.get("name", f"Deste {slot + 1}")
                cards = data.get("cards", [])
                ok = user_db.save_deck(_user.user_id, slot, name, cards)
                await ws.send(json.dumps({
                    "action": "deck_saved",
                    "success": ok,
                    "slot": slot,
                }))
                continue

            # --- Aktif Deste ---
            if action == "set_active_deck":
                slot = data.get("slot", 0)
                ok = user_db.set_active_deck_slot(_user.user_id, slot)
                await ws.send(json.dumps({
                    "action": "active_deck_set",
                    "success": ok,
                    "slot": slot,
                }))
                continue

            # --- Macera İlerlemesi ---
            if action == "get_adventures":
                result = {}
                for adv_id, adv in ADVENTURES.items():
                    progress = user_db.get_adventure_progress(_user.user_id, adv_id)
                    result[adv_id] = {
                        "name": adv["name"],
                        "nodes": adv["nodes"],
                        "completed": progress,
                    }
                await ws.send(json.dumps({
                    "action": "adventures",
                    "adventures": result,
                }))
                continue

            # --- Macera Düellosu (duel / boss node) ---
            if action == "play_adventure":
                adv_id = data.get("adventure", "")
                node_idx = data.get("stage", data.get("node", 0))
                deck = _resolve_deck(data, _user.user_id)

                adv = ADVENTURES.get(adv_id)
                if not adv or node_idx < 0 or node_idx >= len(adv["nodes"]):
                    await _send_error(ws, "Gecersiz macera")
                    continue

                node = adv["nodes"][node_idx]
                if node.get("type") not in ("duel", "boss"):
                    await _send_error(ws, "Bu node duello degil")
                    continue

                progress = user_db.get_adventure_progress(_user.user_id, adv_id)
                # Bu node zaten tamamlanmış mı?
                if node_idx in progress:
                    await _send_error(ws, "Bu asama zaten tamamlandi")
                    continue
                # Önceki node tamamlandı mı? (0. node her zaman açık)
                if node_idx > 0 and (node_idx - 1) not in progress:
                    await _send_error(ws, "Onceki asamayi tamamla")
                    continue

                bot_key = node["bot"]
                bot_deck = BOT_DECKS.get(bot_key, DEFAULT_DECK)
                bot_display = node["bot_name"]
                stage_num = node_idx  # duel_manager adventure_info için

                room = room_manager.create_room()
                player = Player(ws=ws, name=_username, deck=deck)
                room.add_player(player)
                _connections[ws] = player
                _player_rooms[ws] = room.room_id
                room_id = room.room_id

                bot_player = Player(ws=None, name=bot_display, deck=bot_deck)
                room.add_player(bot_player)

                await ws.send(json.dumps({
                    "action": "room_joined",
                    "room_id": room.room_id,
                    "team": 0,
                }))
                await ws.send(json.dumps({
                    "action": "player_joined",
                    "name": bot_display,
                }))

                dm = DuelManager(room, bot_team=1)
                # Macera bilgisini kaydet — galibiyet sonrası ödül için
                dm.adventure_info = {
                    "adventure": adv_id,
                    "stage": stage_num,
                    "user_id": _user.user_id,
                }
                # Pegasus: Toon World garantili ilk kart + ozel arkaplan
                if bot_key == "Pegasus":
                    dm.guaranteed_draws = {1: [15259703]}  # Toon World
                    dm.duel_theme = "toon"
                room.duel_manager = dm
                asyncio.create_task(dm.start())
                continue

            # --- Macera: Gizem (3 kart sunulur, 1 seçilir) ---
            if action == "mystery_offer":
                adv_id = data.get("adventure", "")
                node_idx = data.get("node", 0)
                resp = _handle_mystery_offer(_user.user_id, adv_id, node_idx)
                await ws.send(json.dumps(resp))
                continue

            if action == "mystery_claim":
                adv_id = data.get("adventure", "")
                node_idx = data.get("node", 0)
                code = int(data.get("code", 0))
                resp = _handle_mystery_claim(_user.user_id, adv_id, node_idx, code)
                await ws.send(json.dumps(resp))
                continue

            # --- Macera: Dükkân (5 kart, %50 indirimli) ---
            if action == "shop_offer":
                adv_id = data.get("adventure", "")
                node_idx = data.get("node", 0)
                resp = _handle_shop_offer(_user.user_id, adv_id, node_idx)
                await ws.send(json.dumps(resp))
                continue

            if action == "shop_buy":
                adv_id = data.get("adventure", "")
                node_idx = data.get("node", 0)
                code = int(data.get("code", 0))
                resp = _handle_shop_buy(_user.user_id, adv_id, node_idx, code)
                await ws.send(json.dumps(resp))
                continue

            if action == "shop_leave":
                adv_id = data.get("adventure", "")
                node_idx = data.get("node", 0)
                resp = _handle_shop_leave(_user.user_id, adv_id, node_idx)
                await ws.send(json.dumps(resp))
                continue

            # --- Bot ile Oyna (PvE) ---
            if action == "play_vs_bot":
                name = _username
                deck = _resolve_deck(data, _user.user_id)
                bot_name_key = data.get("bot", None)

                # Bot destesi seç
                if bot_name_key and bot_name_key in BOT_DECKS:
                    bot_deck = BOT_DECKS[bot_name_key]
                    bot_display = bot_name_key
                else:
                    bot_display = _random.choice(list(BOT_DECKS.keys()))
                    bot_deck = BOT_DECKS[bot_display]

                room = room_manager.create_room()

                # İnsan oyuncu (team 0)
                player = Player(ws=ws, name=name, deck=deck)
                room.add_player(player)
                _connections[ws] = player
                _player_rooms[ws] = room.room_id
                room_id = room.room_id

                # Bot oyuncu (team 1) — ws=None
                bot_player = Player(ws=None, name=bot_display, deck=bot_deck)
                room.add_player(bot_player)

                await ws.send(json.dumps({
                    "action": "room_joined",
                    "room_id": room.room_id,
                    "team": 0,
                }))
                await ws.send(json.dumps({
                    "action": "player_joined",
                    "name": bot_display,
                }))

                # Düelloyu başlat (bot_team=1)
                dm = DuelManager(room, bot_team=1)
                room.duel_manager = dm
                asyncio.create_task(dm.start())
                continue

            # --- Oda Oluştur ---
            if action == "create_room":
                name = _username
                room = room_manager.create_room()
                player = Player(ws=ws, name=name)
                room.add_player(player)
                _connections[ws] = player
                _player_rooms[ws] = room.room_id
                room_id = room.room_id

                # Deste yoksa varsayılanı kullan
                player.deck = _resolve_deck(data, _user.user_id)

                await ws.send(json.dumps({
                    "action": "room_created",
                    "room_id": room.room_id,
                    "team": player.team,
                }))

            # --- Odaya Katıl ---
            elif action == "join_room":
                target_id = data.get("room_id", "")
                name = _username
                room = room_manager.get_room(target_id)

                if not room:
                    await _send_error(ws, "Oda bulunamadı")
                    continue
                if room.is_full:
                    await _send_error(ws, "Oda dolu")
                    continue

                player = Player(ws=ws, name=name)
                player.deck = _resolve_deck(data, _user.user_id)
                room.add_player(player)
                _connections[ws] = player
                _player_rooms[ws] = room.room_id
                room_id = room.room_id

                await ws.send(json.dumps({
                    "action": "room_joined",
                    "room_id": room.room_id,
                    "team": player.team,
                }))

                # Diğer oyuncuya bildir
                opponent = room.get_opponent(player)
                if opponent:
                    await opponent.send({
                        "action": "player_joined",
                        "name": player.name,
                    })

                # Oda doluysa düelloyu başlat
                if room.is_full and room.state == RoomState.READY:
                    dm = DuelManager(room)
                    room.duel_manager = dm
                    asyncio.create_task(dm.start())

            # --- Hızlı Eşleştirme ---
            elif action == "quick_match":
                name = _username
                deck = _resolve_deck(data, _user.user_id)

                room = room_manager.find_waiting_room()
                if room:
                    # Mevcut odaya katıl
                    player = Player(ws=ws, name=name, deck=deck)
                    room.add_player(player)
                    _connections[ws] = player
                    _player_rooms[ws] = room.room_id
                    room_id = room.room_id

                    await ws.send(json.dumps({
                        "action": "room_joined",
                        "room_id": room.room_id,
                        "team": player.team,
                    }))

                    opponent = room.get_opponent(player)
                    if opponent:
                        await opponent.send({
                            "action": "player_joined",
                            "name": player.name,
                        })

                    if room.is_full and room.state == RoomState.READY:
                        dm = DuelManager(room)
                        room.duel_manager = dm
                        asyncio.create_task(dm.start())
                else:
                    # Yeni oda oluştur ve bekle
                    room = room_manager.create_room()
                    player = Player(ws=ws, name=name, deck=deck)
                    room.add_player(player)
                    _connections[ws] = player
                    _player_rooms[ws] = room.room_id
                    room_id = room.room_id

                    await ws.send(json.dumps({
                        "action": "room_created",
                        "room_id": room.room_id,
                        "team": player.team,
                        "waiting": True,
                    }))

            # --- Deste Ayarla ---
            elif action == "set_deck":
                if player:
                    deck = data.get("deck", [])
                    if len(deck) >= 40:
                        player.deck = deck
                        await ws.send(json.dumps({"action": "deck_set", "count": len(deck)}))
                    else:
                        await _send_error(ws, "Deste en az 40 kart olmalı")

            # --- Düello Yanıtı ---
            elif action == "response":
                if not room_id:
                    continue
                room = room_manager.get_room(room_id)
                if not room or not room.duel_manager:
                    continue
                if not player:
                    continue

                msg_type = data.get("msg_type", 0)
                response_data = data.get("data", {})
                response_bytes = _build_response(msg_type, response_data)
                room.duel_manager.receive_response(player.team, response_bytes)

            # --- Teslim Ol (Surrender) ---
            elif action == "surrender":
                if room_id and player:
                    room = room_manager.get_room(room_id)
                    if room and room.duel_manager:
                        await room.duel_manager.surrender(player.team)

            # --- Oda Listesi ---
            elif action == "list_rooms":
                rooms = room_manager.list_rooms()
                await ws.send(json.dumps({"action": "rooms", "rooms": rooms}))

            else:
                await _send_error(ws, f"Bilinmeyen action: {action}")

    except websockets.exceptions.ConnectionClosed:
        pass
    finally:
        # Bağlantı koptu — temizle
        if ws in _player_rooms:
            rid = _player_rooms.pop(ws)
            room = room_manager.get_room(rid)
            if room and player:
                opponent = room.get_opponent(player)
                room.remove_player(player)
                if opponent:
                    await opponent.send({
                        "action": "player_left",
                        "name": player.name,
                    })
                if not room.players:
                    room_manager.remove_room(rid)
        _connections.pop(ws, None)
        _auth_tokens.pop(ws, None)


async def start_server(host: str = "0.0.0.0", ws_port: int = 8765, http_port: int = 8080):
    """WebSocket ve HTTP sunucularını başlatır."""
    from http.server import HTTPServer, SimpleHTTPRequestHandler
    from pathlib import Path
    import threading

    # HTTP sunucu — web/ klasöründen statik dosya servis et
    web_dir = Path(__file__).resolve().parent.parent / "web"

    class Handler(SimpleHTTPRequestHandler):
        def __init__(self, *args, **kwargs):
            super().__init__(*args, directory=str(web_dir), **kwargs)
        def log_message(self, format, *args):
            pass  # Sessiz

    http_server = HTTPServer(("0.0.0.0", http_port), Handler)
    http_thread = threading.Thread(target=http_server.serve_forever, daemon=True)
    http_thread.start()

    print(f"Yuki sunucu baslatildi!")
    print(f"  Web:       http://localhost:{http_port}")
    print(f"  WebSocket: ws://localhost:{ws_port}")
    print(f"  Tarayicinizi acin ve oynamaya baslayin!")

    async with websockets.serve(handle_connection, host, ws_port):
        await asyncio.Future()


def main():
    asyncio.run(start_server())


if __name__ == "__main__":
    main()
