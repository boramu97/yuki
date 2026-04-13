import asyncio, json, sys, io
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8")
sys.path.insert(0, ".")
import websockets
from server.ocg_binding import *

async def test():
    ws1 = await websockets.connect("ws://localhost:8765")
    await ws1.send(json.dumps({"action":"create_room","name":"P0"}))
    r1 = json.loads(await ws1.recv())
    rid = r1["room_id"]

    ws2 = await websockets.connect("ws://localhost:8765")
    await ws2.send(json.dumps({"action":"join_room","name":"P1","room_id":rid}))
    json.loads(await ws2.recv())
    await asyncio.wait_for(ws1.recv(), timeout=5)
    for ws in [ws1, ws2]:
        json.loads(await asyncio.wait_for(ws.recv(), timeout=5))
    print("Duello basladi\n")

    # P2 auto-play
    async def p2():
        while True:
            try:
                raw = await asyncio.wait_for(ws2.recv(), timeout=30)
                d = json.loads(raw)
                if d.get("action") == "select":
                    mt = d["msg"]["type"]
                    if mt == MSG_SELECT_CHAIN:
                        await ws2.send(json.dumps({"action":"response","msg_type":16,"data":{"index":-1}}))
                    elif mt == MSG_SELECT_IDLECMD:
                        await ws2.send(json.dumps({"action":"response","msg_type":11,"data":{"action":"end"}}))
                    else:
                        await ws2.send(json.dumps({"action":"response","msg_type":mt,"data":{}}))
            except: break
    t2 = asyncio.create_task(p2())

    # P0: Tum mesajlari logla, her SELECT'e yanit ver
    print("=== P0 tum mesajlar ===")
    for i in range(80):
        try:
            raw = await asyncio.wait_for(ws1.recv(), timeout=10)
        except asyncio.TimeoutError:
            print(f"\n[STUCK] Timeout step {i}")
            break

        d = json.loads(raw)
        act = d.get("action")
        msg = d.get("msg", {})
        mt = msg.get("type", 0)
        mn = msg.get("name", "")

        if act == "info":
            if mn in ("MSG_DRAW","MSG_NEW_TURN","MSG_NEW_PHASE","MSG_SET",
                       "MSG_SUMMONING","MSG_SPSUMMONING","MSG_MOVE","MSG_CHAINING"):
                cname = msg.get("card_name", "")
                print(f"  INFO: {mn} {cname}")
        elif act == "select":
            # HER SELECT mesajini detayli logla
            print(f"\n  >>> SELECT type={mt} ({mn})")
            print(f"      player={msg.get('player')} min={msg.get('min')} max={msg.get('max')}")
            if msg.get("cards"):
                for j, c in enumerate(msg["cards"][:5]):
                    print(f"      card[{j}]: {c.get('card_name','?')} code={c.get('code')} loc={c.get('location')}")
            if msg.get("must_cards"):
                for j, c in enumerate(msg["must_cards"][:5]):
                    print(f"      must[{j}]: {c.get('card_name','?')} code={c.get('code')} param={c.get('param')}")
            if msg.get("selectable_cards"):
                for j, c in enumerate(msg["selectable_cards"][:5]):
                    print(f"      sel[{j}]: {c.get('card_name','?')} code={c.get('code')} param={c.get('param')}")
            if msg.get("selectable"):
                if isinstance(msg["selectable"], list):
                    for j, c in enumerate(msg["selectable"][:5]):
                        print(f"      selectable[{j}]: {c.get('card_name','?')} code={c.get('code')}")
                else:
                    print(f"      selectable(flag)={msg['selectable']:#x}")
            if msg.get("chains"):
                for j, c in enumerate(msg["chains"][:3]):
                    print(f"      chain[{j}]: {c.get('card_name','?')}")
            if msg.get("summonable"):
                print(f"      summonable: {len(msg['summonable'])} kart")
            if msg.get("spell_setable"):
                print(f"      spell_setable: {[c.get('card_name','?') for c in msg['spell_setable']]}")
            if msg.get("activatable"):
                print(f"      activatable: {[c.get('card_name','?') for c in msg['activatable']]}")

            # Yanit ver
            if mt == MSG_SELECT_CHAIN:
                # Zincir varsa aktifle, yoksa pas
                chains = msg.get("chains", [])
                # Black Luster Ritual'i aktifle
                ritual_idx = next((j for j, c in enumerate(chains) if "Ritual" in (c.get("card_name",""))), -1)
                if ritual_idx >= 0:
                    print(f"      -> Zincir: {chains[ritual_idx].get('card_name')} idx={ritual_idx}")
                    await ws1.send(json.dumps({"action":"response","msg_type":16,"data":{"index":ritual_idx}}))
                else:
                    await ws1.send(json.dumps({"action":"response","msg_type":16,"data":{"index":-1}}))

            elif mt == MSG_SELECT_IDLECMD:
                # Ritual spell set et veya aktifle
                activatable = msg.get("activatable", [])
                ssets = msg.get("spell_setable", [])
                ritual_act = next((j for j, c in enumerate(activatable) if "Ritual" in (c.get("card_name",""))), -1)
                ritual_set = next((j for j, c in enumerate(ssets) if "Ritual" in (c.get("card_name",""))), -1)

                if ritual_act >= 0:
                    print(f"      -> Aktifle Ritual idx={ritual_act}")
                    await ws1.send(json.dumps({"action":"response","msg_type":11,"data":{"action":"activate","index":ritual_act}}))
                elif ritual_set >= 0:
                    print(f"      -> Set Ritual idx={ritual_set}")
                    await ws1.send(json.dumps({"action":"response","msg_type":11,"data":{"action":"sset","index":ritual_set}}))
                else:
                    await ws1.send(json.dumps({"action":"response","msg_type":11,"data":{"action":"end"}}))

            elif mt == MSG_SELECT_CARD:
                # Black Luster Soldier'i sec
                cards = msg.get("cards", [])
                bls_idx = next((j for j, c in enumerate(cards) if "Black Luster" in (c.get("card_name",""))), 0)
                n = msg.get("min", 1)
                print(f"      -> Card sec idx={bls_idx}")
                await ws1.send(json.dumps({"action":"response","msg_type":15,"data":{"indices":[bls_idx]}}))

            elif mt == MSG_SELECT_TRIBUTE:
                n = msg.get("min", 1)
                cards = msg.get("cards", [])
                indices = list(range(min(n, len(cards))))
                print(f"      -> Tribute idx={indices}")
                await ws1.send(json.dumps({"action":"response","msg_type":20,"data":{"indices":indices}}))

            elif mt == MSG_SELECT_SUM:  # type 23
                must = msg.get("must_cards", [])
                selectable = msg.get("selectable_cards", [])
                # Tum secilebilir kartlari sec
                indices = list(range(len(must)))
                for j in range(len(selectable)):
                    indices.append(len(must) + j)
                print(f"      -> Sum idx={indices}")
                await ws1.send(json.dumps({"action":"response","msg_type":23,"data":{"indices":indices}}))

            elif mt == MSG_SELECT_PLACE:
                flag = msg.get("selectable", 0)
                for seq in range(7):
                    if not (flag & (1 << seq)):
                        print(f"      -> Place mzone seq={seq}")
                        await ws1.send(json.dumps({"action":"response","msg_type":18,"data":{"player":0,"location":4,"sequence":seq}}))
                        break

            elif mt == MSG_SELECT_POSITION:
                print(f"      -> Position ATK")
                await ws1.send(json.dumps({"action":"response","msg_type":19,"data":{"position":1}}))

            elif mt == 26:  # UNSELECT
                sel = msg.get("selectable", [])
                print(f"      -> Unselect idx=0")
                await ws1.send(json.dumps({"action":"response","msg_type":26,"data":{"index":0 if sel else -1}}))

            else:
                print(f"      -> Default response for type {mt}")
                await ws1.send(json.dumps({"action":"response","msg_type":mt,"data":{}}))

        elif act == "retry":
            print(f"  !!! RETRY !!!")

    t2.cancel()
    await ws1.close()
    await ws2.close()
    print("\nDone")

asyncio.run(test())
