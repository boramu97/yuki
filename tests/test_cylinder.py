import sys,io,asyncio,json
sys.stdout=io.TextIOWrapper(sys.stdout.buffer,encoding="utf-8"); sys.path.insert(0,".")
from server.websocket_server import handle_connection
import websockets
from server.ocg_binding import *

async def run():
    async with websockets.serve(handle_connection,"0.0.0.0",8765):
        ws1=await websockets.connect("ws://localhost:8765")
        deck0=[62279055]*4+[43096270]*36
        deck1=[43096270]*40
        await ws1.send(json.dumps({"action":"create_room","name":"P0","deck":deck0}))
        r=json.loads(await ws1.recv()); rid=r["room_id"]
        ws2=await websockets.connect("ws://localhost:8765")
        await ws2.send(json.dumps({"action":"join_room","name":"P1","room_id":rid,"deck":deck1}))
        json.loads(await ws2.recv())
        await asyncio.wait_for(ws1.recv(),timeout=5)
        for ws in[ws1,ws2]:json.loads(await asyncio.wait_for(ws.recv(),timeout=5))
        print("Duello basladi")

        async def p2():
            while True:
                try:
                    d=json.loads(await asyncio.wait_for(ws2.recv(),timeout=30))
                    if d.get("action")!="select": continue
                    mt=d["msg"]["type"]; msg=d["msg"]
                    if mt==16: await ws2.send(json.dumps({"action":"response","msg_type":16,"data":{"index":-1}}))
                    elif mt==11:
                        summ=msg.get("summonable",[])
                        if summ: await ws2.send(json.dumps({"action":"response","msg_type":11,"data":{"action":"summon","index":0}}))
                        elif msg.get("can_battle_phase"): await ws2.send(json.dumps({"action":"response","msg_type":11,"data":{"action":"battle"}}))
                        else: await ws2.send(json.dumps({"action":"response","msg_type":11,"data":{"action":"end"}}))
                    elif mt==10:
                        if msg.get("attackable"): await ws2.send(json.dumps({"action":"response","msg_type":10,"data":{"action":"attack","index":0}}))
                        elif msg.get("can_main2"): await ws2.send(json.dumps({"action":"response","msg_type":10,"data":{"action":"main2"}}))
                        else: await ws2.send(json.dumps({"action":"response","msg_type":10,"data":{"action":"end"}}))
                    elif mt==18:
                        f=msg.get("selectable",0)
                        for s in range(7):
                            if not(f&(1<<s)):await ws2.send(json.dumps({"action":"response","msg_type":18,"data":{"player":1,"location":4,"sequence":s}}));break
                    elif mt==19: await ws2.send(json.dumps({"action":"response","msg_type":19,"data":{"position":1}}))
                    elif mt==15:
                        n=msg.get("min",1);cards=msg.get("cards",[])
                        await ws2.send(json.dumps({"action":"response","msg_type":15,"data":{"indices":list(range(min(n,len(cards))))}}))
                    else: await ws2.send(json.dumps({"action":"response","msg_type":mt,"data":{}}))
                except: break
        asyncio.create_task(p2())

        cylinder_set=False; activated=False
        for i in range(100):
            try: raw=await asyncio.wait_for(ws1.recv(),timeout=10)
            except: print(f"TIMEOUT {i}"); break
            d=json.loads(raw); act=d.get("action"); msg=d.get("msg",{}); mt=msg.get("type",0); mn=msg.get("name","")

            if act=="info":
                if mn in("MSG_ATTACK","MSG_DAMAGE","MSG_CHAINING","MSG_CHAIN_END","MSG_ATTACK_DISABLED","MSG_SET","MSG_MOVE"):
                    print(f"  INFO: {mn} {msg.get('card_name','')} amt={msg.get('amount','')}")
            elif act=="select":
                print(f"  SELECT {mt}({mn})",end="")
                if mt==16:
                    chains=msg.get("chains",[])
                    cyl=next((j for j,c in enumerate(chains) if c.get("code")==62279055),-1)
                    if cyl>=0 and cylinder_set:
                        print(f" -> ACTIVATE CYLINDER idx={cyl}")
                        await ws1.send(json.dumps({"action":"response","msg_type":16,"data":{"index":cyl}}))
                        activated=True
                    else:
                        print(f" -> pass (chains={len(chains)})")
                        await ws1.send(json.dumps({"action":"response","msg_type":16,"data":{"index":-1}}))
                elif mt==11:
                    ssets=msg.get("spell_setable",[])
                    cyl_idx=next((j for j,c in enumerate(ssets) if c.get("code")==62279055),-1)
                    if not cylinder_set and cyl_idx>=0:
                        print(f" -> SET CYLINDER idx={cyl_idx}")
                        await ws1.send(json.dumps({"action":"response","msg_type":11,"data":{"action":"sset","index":cyl_idx}}))
                        cylinder_set=True
                    else:
                        print(f" -> end")
                        await ws1.send(json.dumps({"action":"response","msg_type":11,"data":{"action":"end"}}))
                elif mt==18:
                    f=msg.get("selectable",0)
                    for s in range(8):
                        if not(f&(1<<(s+8))):
                            print(f" -> szone {s}")
                            await ws1.send(json.dumps({"action":"response","msg_type":18,"data":{"player":0,"location":8,"sequence":s}})); break
                elif mt==15:
                    cards=msg.get("cards",[]); n=msg.get("min",1)
                    print(f" -> card[0]")
                    await ws1.send(json.dumps({"action":"response","msg_type":15,"data":{"indices":list(range(min(n,len(cards))))}}))
                else:
                    print(f" -> default {mt}")
                    await ws1.send(json.dumps({"action":"response","msg_type":mt,"data":{}}))
            elif act=="retry": print(f"  RETRY!")

            if activated:
                for _ in range(15):
                    try:
                        r2=await asyncio.wait_for(ws1.recv(),timeout=3)
                        d2=json.loads(r2); a2=d2.get("action"); m2=d2.get("msg",{})
                        mn2=m2.get("name","")
                        if mn2 in("MSG_DAMAGE","MSG_ATTACK_DISABLED","MSG_CHAIN_END","MSG_MOVE"):
                            print(f"  AFTER: {mn2} {m2.get('card_name','')} amt={m2.get('amount','')}")
                        if a2=="select":
                            t2=m2.get("type",0)
                            print(f"  AFTER SELECT {t2}")
                            if t2==16: await ws1.send(json.dumps({"action":"response","msg_type":16,"data":{"index":-1}}))
                            else: await ws1.send(json.dumps({"action":"response","msg_type":t2,"data":{}}))
                    except: break
                break

        await ws1.close(); await ws2.close()
        print("Done")

asyncio.run(run())
