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
from server.decks import YUGI_DECK
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

# Varsayilan test destesi — Yugi Muto
DEFAULT_DECK = YUGI_DECK

# Global yöneticiler
room_manager = RoomManager()
user_db = UserDatabase()

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
                player.deck = data.get("deck", DEFAULT_DECK)

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
                player.deck = data.get("deck", DEFAULT_DECK)
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
                deck = data.get("deck", DEFAULT_DECK)

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
