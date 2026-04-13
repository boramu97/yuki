import asyncio, json, sys, io
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8")
sys.path.insert(0, ".")
import websockets
from server.ocg_binding import MSG_SELECT_IDLECMD, MSG_SELECT_CHAIN, MSG_SELECT_PLACE, MSG_SELECT_CARD

async def test():
    ws1 = await websockets.connect("ws://localhost:8765")
    await ws1.send(json.dumps({"action":"create_room","name":"Yugi"}))
    r1 = json.loads(await ws1.recv())
    rid = r1["room_id"]

    ws2 = await websockets.connect("ws://localhost:8765")
    await ws2.send(json.dumps({"action":"join_room","name":"Kaiba","room_id":rid}))
    r2 = json.loads(await ws2.recv())
    _ = await asyncio.wait_for(ws1.recv(), timeout=5)

    # duel_start
    for ws in [ws1, ws2]:
        json.loads(await asyncio.wait_for(ws.recv(), timeout=5))
    print("Duello basladi\n")

    # P2'yi de dinle (arka planda)
    async def p2_listen():
        while True:
            try:
                raw = await asyncio.wait_for(ws2.recv(), timeout=30)
                data = json.loads(raw)
                act = data.get("action")
                msg = data.get("msg", {})
                mt = msg.get("type", 0)
                mn = msg.get("name", "")
                if act == "select":
                    print(f"  P1-SELECT: type={mt} {mn}")
                    if mt == MSG_SELECT_CHAIN:
                        await ws2.send(json.dumps({"action":"response","msg_type":16,"data":{"index":-1}}))
                        print(f"  P1 -> chain pass")
                    elif mt == MSG_SELECT_IDLECMD:
                        await ws2.send(json.dumps({"action":"response","msg_type":11,"data":{"action":"end"}}))
                        print(f"  P1 -> end turn")
                    elif mt == MSG_SELECT_PLACE:
                        flag = msg.get("selectable", 0)
                        for seq in range(8):
                            if not (flag & (1 << (seq + 8))):
                                await ws2.send(json.dumps({"action":"response","msg_type":18,"data":{"player":1,"location":0x08,"sequence":seq}}))
                                print(f"  P1 -> place szone {seq}")
                                break
                    elif mt == MSG_SELECT_CARD:
                        n = msg.get("min", 1)
                        await ws2.send(json.dumps({"action":"response","msg_type":15,"data":{"indices":list(range(n))}}))
                    else:
                        await ws2.send(json.dumps({"action":"response","msg_type":mt,"data":{}}))
                        print(f"  P1 -> default resp for {mt}")
            except asyncio.TimeoutError:
                print("  P1 TIMEOUT")
                break
            except Exception as e:
                print(f"  P1 ERROR: {e}")
                break

    p2_task = asyncio.create_task(p2_listen())

    # P0: mesajlari isle
    sset_done = False
    for i in range(50):
        try:
            raw = await asyncio.wait_for(ws1.recv(), timeout=8)
        except asyncio.TimeoutError:
            print(f"\n[STUCK] P0 TIMEOUT at step {i} — sset_done={sset_done}")
            break

        data = json.loads(raw)
        act = data.get("action")
        msg = data.get("msg", {})
        mt = msg.get("type", 0)
        mn = msg.get("name", "")

        if act == "info":
            if mn in ("MSG_DRAW","MSG_NEW_TURN","MSG_NEW_PHASE","MSG_SET","MSG_SUMMONING","MSG_SUMMONED"):
                print(f"P0-INFO: {mn}")
        elif act == "select":
            print(f"P0-SELECT: type={mt} {mn}")
            if mt == MSG_SELECT_CHAIN:
                await ws1.send(json.dumps({"action":"response","msg_type":16,"data":{"index":-1}}))
                print(f"P0 -> chain pass")
            elif mt == MSG_SELECT_IDLECMD:
                ssets = msg.get("spell_setable", [])
                if not sset_done and ssets:
                    print(f"P0 -> SSET {ssets[0].get('card_name','?')}")
                    await ws1.send(json.dumps({"action":"response","msg_type":11,"data":{"action":"sset","index":0}}))
                    sset_done = True
                else:
                    print(f"P0 -> end turn")
                    await ws1.send(json.dumps({"action":"response","msg_type":11,"data":{"action":"end"}}))
            elif mt == MSG_SELECT_PLACE:
                flag = msg.get("selectable", 0)
                print(f"P0 SELECT_PLACE flag={flag:#010x}")
                placed = False
                for seq in range(8):
                    if not (flag & (1 << (seq + 8))):
                        print(f"P0 -> place szone {seq}")
                        await ws1.send(json.dumps({"action":"response","msg_type":18,"data":{"player":0,"location":0x08,"sequence":seq}}))
                        placed = True
                        break
                if not placed:
                    for seq in range(7):
                        if not (flag & (1 << seq)):
                            print(f"P0 -> place mzone {seq}")
                            await ws1.send(json.dumps({"action":"response","msg_type":18,"data":{"player":0,"location":0x04,"sequence":seq}}))
                            placed = True
                            break
                if not placed:
                    print(f"P0 -> CANT FIND SLOT!")
            elif mt == MSG_SELECT_CARD:
                n = msg.get("min", 1)
                await ws1.send(json.dumps({"action":"response","msg_type":15,"data":{"indices":list(range(n))}}))
            else:
                print(f"P0 -> default resp for {mt}")
                await ws1.send(json.dumps({"action":"response","msg_type":mt,"data":{}}))
        elif act == "retry":
            print(f"P0-RETRY!")

    p2_task.cancel()
    await ws1.close()
    await ws2.close()
    print("\nDone")

asyncio.run(test())
