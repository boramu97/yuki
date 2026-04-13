"""Change of Heart: Kontrol al + tur sonu geri ver testi"""
import sys,io,ctypes
sys.stdout=io.TextIOWrapper(sys.stdout.buffer,encoding="utf-8")
sys.path.insert(0,".")
from server.ocg_binding import *
from server.card_database import CardDatabase
from server.message_parser import split_messages, parse_message, MSG_NAMES
from server.response_builder import *
from server.config import SCRIPT_DIR, CARD_DB_PATH

db=CardDatabase(CARD_DB_PATH);core=OCGCore()
_bufs=[]
def cr(p,code,dp):
    c=db.get_card(code)
    if not c:dp.contents.code=code;e=(ctypes.c_uint16*1)(0);_bufs.append(e);dp.contents.setcodes=ctypes.cast(e,ctypes.POINTER(ctypes.c_uint16));return
    dp.contents.code=c.code;dp.contents.alias=c.alias;dp.contents.type=c.type;dp.contents.level=c.level;dp.contents.attribute=c.attribute;dp.contents.race=c.race;dp.contents.attack=c.attack;dp.contents.defense=c.defense;dp.contents.lscale=c.lscale;dp.contents.rscale=c.rscale;dp.contents.link_marker=c.link_marker
    sc=c.setcodes+[0];a=(ctypes.c_uint16*len(sc))(*sc);_bufs.append(a);dp.contents.setcodes=ctypes.cast(a,ctypes.POINTER(ctypes.c_uint16))
def sr(p,d,name):
    n=name.decode("utf-8") if isinstance(name,bytes) else name
    for pa in[SCRIPT_DIR/n,SCRIPT_DIR/"official"/n]:
        if pa.exists():c=pa.read_text(encoding="utf-8");cb=c.encode("utf-8");core._lib.OCG_LoadScript(d,cb,len(cb),n.encode("utf-8"));return 1
    return 0

# P0: CoH son sirada (ilk cekilen) + Alexandrite dolgu
# P1: Gene-Warped Warwolf (P1 sahaya koyacak)
deck0=[43096270]*39+[4031928]  # CoH en uste
deck1=[69247929]*40

duel=core.create_duel(card_reader=cr,script_reader=sr,starting_lp=8000,flags=DUEL_MODE_MR2)
for n in["constant.lua","utility.lua"]:
    p=SCRIPT_DIR/n;core.load_script(duel,p.read_text(encoding="utf-8"),n)
for c in deck0:core.add_card(duel,team=0,code=c,loc=LOCATION_DECK)
for c in deck1:core.add_card(duel,team=1,code=c,loc=LOCATION_DECK)
core.start_duel(duel)

print("=== CHANGE OF HEART — KONTROL AL + GERİ VER ===\n")

turn=0;coh_done=False;p1_summoned=False

for step in range(500):
    status=core.process(duel)
    raw=core.get_message(duel)
    if not raw:
        if status==DUEL_STATUS_END:break
        continue
    for mt,md in split_messages(raw):
        mn=MSG_NAMES.get(mt,"?");msg=parse_message(mt,md)
        code=msg.get("code",0);card=db.get_card(code) if code else None

        if mt==MSG_NEW_TURN:
            turn+=1;print(f"\n--- TUR {turn} (P{msg['player']}) ---")
        elif mt==MSG_NEW_PHASE:
            ph={0x01:"Draw",0x02:"Standby",0x04:"Main1",0x100:"Main2",0x200:"End"}
            pn=ph.get(msg.get("phase",0),"")
            if pn:print(f"  {pn}")
        elif mt==MSG_MOVE:
            cn=card.name if card else f"#{code}"
            frm=msg.get("from",{});to=msg.get("to",{})
            fc=frm.get("controller",0);tc=to.get("controller",0)
            fl=frm.get("location",0);tl=to.get("location",0)
            if fc!=tc:
                print(f"  >>> MOVE: {cn} P{fc}→P{tc} (loc {fl:#x}→{tl:#x})")
                print(f"      *** KONTROL DEGİŞTİ ***")
            elif tl==0x10:
                print(f"  >>> MOVE: {cn} → Mezarlik")
            elif fl!=tl:
                print(f"  >>> MOVE: {cn} loc {fl:#x}→{tl:#x}")
        elif mt==MSG_CHAINING:
            cn=card.name if card else "?"
            print(f"  >>> CHAINING: {cn}")
        elif mt in(MSG_SUMMONING,MSG_SPSUMMONING):
            cn=card.name if card else "?"
            print(f"  >>> {mn}: {cn} P{msg.get('controller')} seq={msg.get('sequence')}")
            if msg.get("controller")==1:p1_summoned=True

        # YANITLAR
        if msg.get("interactive"):
            player=msg.get("player",0)
            if mt==MSG_SELECT_CHAIN:
                core.set_response(duel,build_chain_response(-1))
            elif mt==MSG_SELECT_IDLECMD:
                acts=msg.get("activatable",[])
                summ=msg.get("summonable",[])
                coh_idx=next((j for j,c in enumerate(acts) if c["code"]==4031928),-1)

                if player==1:
                    # P1: her turda canavar cagir
                    if summ:
                        core.set_response(duel,build_idle_cmd_response("summon",0))
                    else:
                        core.set_response(duel,build_idle_cmd_response("end"))
                elif player==0:
                    # P0 Tur 1: canavar cagir
                    if turn<=1 and summ:
                        core.set_response(duel,build_idle_cmd_response("summon",0))
                    # P0 Tur 3+: CoH aktifle (rakipte canavar varsa)
                    elif not coh_done and coh_idx>=0 and p1_summoned:
                        print(f"  <<< ACTIVATE CHANGE OF HEART")
                        core.set_response(duel,build_idle_cmd_response("activate",coh_idx))
                        coh_done=True
                    elif coh_done and msg.get("can_battle_phase"):
                        core.set_response(duel,build_idle_cmd_response("battle"))
                    else:
                        core.set_response(duel,build_idle_cmd_response("end"))
            elif mt==MSG_SELECT_BATTLECMD:
                atks=msg.get("attackable",[])
                if atks:
                    core.set_response(duel,build_battle_cmd_response("attack",0))
                else:
                    core.set_response(duel,build_battle_cmd_response("end"))
            elif mt==MSG_SELECT_CARD:
                cards=msg.get("cards",[]);n=msg.get("min",1)
                names=[db.get_card(c["code"]).name if db.get_card(c["code"]) else str(c["code"]) for c in cards[:3]]
                print(f"  <<< Select: {names}")
                core.set_response(duel,build_card_response(list(range(min(n,len(cards))))))
            elif mt==MSG_SELECT_PLACE:
                flag=msg.get("selectable",0)
                for s in range(7):
                    if not(flag&(1<<s)):core.set_response(duel,build_place_response(msg["player"],0x04,s));break
                else:
                    for s in range(8):
                        if not(flag&(1<<(s+8))):core.set_response(duel,build_place_response(msg["player"],0x08,s));break
            elif mt==MSG_SELECT_POSITION:
                core.set_response(duel,build_position_response(0x1))
            elif mt==MSG_SELECT_TRIBUTE:
                n=msg.get("min",1);cards=msg.get("cards",[])
                core.set_response(duel,build_tribute_response(list(range(min(n,len(cards))))))
            else:
                core.set_response(duel,b"\x00\x00\x00\x00")

    if coh_done and turn>6:break
    if status==DUEL_STATUS_END:break

core.destroy_duel(duel);db.close()
print("\nDone")
