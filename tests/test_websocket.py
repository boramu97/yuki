# Yuki — WebSocket düello testi
# İki AI oyuncu WebSocket üzerinden bağlanıp düello oynar.
# Sunucu önceden çalışıyor olmalı: python -m server

import asyncio
import json
import sys
import io

sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8")
sys.path.insert(0, ".")

import websockets

from server.ocg_binding import (
    MSG_SELECT_IDLECMD, MSG_SELECT_BATTLECMD, MSG_SELECT_CHAIN,
    MSG_SELECT_EFFECTYN, MSG_SELECT_YESNO, MSG_SELECT_OPTION,
    MSG_SELECT_CARD, MSG_SELECT_PLACE, MSG_SELECT_POSITION,
    MSG_SELECT_TRIBUTE,
)

WS_URL = "ws://localhost:8765"


def make_response(team, msg):
    """Mesaja gore AI yaniti olustur."""
    mt = msg.get("type", 0)
    data = {}

    if mt == MSG_SELECT_IDLECMD:
        if msg.get("summonable"):
            data = {"action": "summon", "index": 0}
        elif msg.get("can_battle_phase"):
            data = {"action": "battle"}
        else:
            data = {"action": "end"}
    elif mt == MSG_SELECT_BATTLECMD:
        if msg.get("attackable"):
            data = {"action": "attack", "index": 0}
        elif msg.get("can_main2"):
            data = {"action": "main2"}
        else:
            data = {"action": "end"}
    elif mt == MSG_SELECT_CHAIN:
        data = {"index": -1}
    elif mt == MSG_SELECT_EFFECTYN:
        data = {"yes": False}
    elif mt == MSG_SELECT_YESNO:
        data = {"yes": False}
    elif mt == MSG_SELECT_OPTION:
        data = {"index": 0}
    elif mt == MSG_SELECT_CARD:
        n = msg.get("min", 1)
        cards = msg.get("cards", [])
        data = {"indices": list(range(min(n, len(cards))))}
    elif mt == MSG_SELECT_POSITION:
        data = {"position": 0x1}
    elif mt == MSG_SELECT_PLACE:
        flag = msg.get("selectable", 0)
        placed = False
        for seq in range(7):
            if not (flag & (1 << seq)):
                data = {"player": team, "location": 0x04, "sequence": seq}
                placed = True
                break
        if not placed:
            for seq in range(8):
                if not (flag & (1 << (seq + 8))):
                    data = {"player": team, "location": 0x08, "sequence": seq}
                    placed = True
                    break
        if not placed:
            data = {"player": team, "location": 0x04, "sequence": 0}
    elif mt == MSG_SELECT_TRIBUTE:
        n = msg.get("min", 1)
        data = {"indices": list(range(n))}
    elif mt == 26:  # SELECT_UNSELECT_CARD
        selectable = msg.get("selectable", [])
        data = {"index": 0 if selectable else -1}

    return {"action": "response", "msg_type": mt, "data": data}


async def main():
    print("=" * 50)
    print("  WebSocket Duello Testi")
    print("=" * 50)

    # P1 oda olustur
    ws1 = await websockets.connect(WS_URL)
    await ws1.send(json.dumps({"action": "create_room", "name": "Yugi"}))
    resp1 = json.loads(await ws1.recv())
    room_id = resp1["room_id"]
    print(f"[Yugi]  Oda: {room_id} (team 0)")

    # P2 odaya katil
    ws2 = await websockets.connect(WS_URL)
    await ws2.send(json.dumps({"action": "join_room", "name": "Kaiba", "room_id": room_id}))
    resp2 = json.loads(await ws2.recv())
    print(f"[Kaiba] Katildi (team {resp2.get('team')})")

    # P1: player_joined mesaji
    _ = await asyncio.wait_for(ws1.recv(), timeout=5)

    # Her ikisi: duel_start
    for ws in [ws1, ws2]:
        m = json.loads(await asyncio.wait_for(ws.recv(), timeout=5))
        if m.get("action") == "duel_start":
            print(f"  Duello basladi!")

    # Dinleme dongusu
    duel_ended = False
    turn = 0
    msg_count = 0

    async def listen(team, name, ws):
        nonlocal duel_ended, turn, msg_count
        while not duel_ended:
            try:
                raw = await asyncio.wait_for(ws.recv(), timeout=60)
            except Exception:
                break
            data = json.loads(raw)
            act = data.get("action")
            msg_count += 1

            if act == "info":
                msg = data.get("msg", {})
                mn = msg.get("name", "")
                if mn == "MSG_NEW_TURN":
                    turn += 1
                    if turn <= 5 or turn % 5 == 0:
                        print(f"  Tur {turn}")
                elif mn == "MSG_DAMAGE":
                    print(f"  P{msg.get('player')} -{msg.get('amount')} LP")

            elif act == "select":
                msg = data.get("msg", {})
                resp = make_response(team, msg)
                await ws.send(json.dumps(resp))

            elif act == "duel_end":
                winner = data.get("winner", -1)
                names = {0: "Yugi", 1: "Kaiba"}
                print(f"\n  KAZANAN: {names.get(winner, '?')} (P{winner})")
                duel_ended = True

    await asyncio.gather(listen(0, "Yugi", ws1), listen(1, "Kaiba", ws2))

    print(f"  Toplam tur: {turn}")
    print(f"  Toplam mesaj: {msg_count}")
    print("=" * 50)
    print("  WebSocket Duello Testi BASARILI!")
    print("=" * 50)

    await ws1.close()
    await ws2.close()


if __name__ == "__main__":
    asyncio.run(main())
