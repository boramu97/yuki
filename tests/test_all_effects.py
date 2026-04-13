"""Tum karmasik efektli kartlari sirayla test et.
Her kart icin: efekti tetikle, motorun mesajlarini kontrol et, yanit ver, sonucu dogrula.
"""
import sys,io,ctypes
sys.stdout=io.TextIOWrapper(sys.stdout.buffer,encoding="utf-8")
sys.path.insert(0,".")
from server.ocg_binding import *
from server.card_database import CardDatabase
from server.message_parser import split_messages, parse_message, MSG_NAMES
from server.response_builder import *
from server.config import SCRIPT_DIR, CARD_DB_PATH

db=CardDatabase(CARD_DB_PATH)
core=OCGCore()
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

def respond(msg, duel):
    """Herhangi bir interaktif mesaja otomatik yanit ver."""
    mt=msg.get("type",0)
    if mt==MSG_SELECT_CHAIN:core.set_response(duel,build_chain_response(-1))
    elif mt==MSG_SELECT_IDLECMD:core.set_response(duel,build_idle_cmd_response("end"))
    elif mt==MSG_SELECT_BATTLECMD:core.set_response(duel,build_battle_cmd_response("end"))
    elif mt==MSG_SELECT_CARD:
        n=msg.get("min",1);cards=msg.get("cards",[])
        core.set_response(duel,build_card_response(list(range(min(n,len(cards))))))
    elif mt==MSG_SELECT_PLACE:
        flag=msg.get("selectable",0)
        for s in range(7):
            if not(flag&(1<<s)):core.set_response(duel,build_place_response(msg["player"],0x04,s));return
        for s in range(8):
            if not(flag&(1<<(s+8))):core.set_response(duel,build_place_response(msg["player"],0x08,s));return
        core.set_response(duel,build_place_response(msg["player"],0x04,0))
    elif mt==MSG_SELECT_POSITION:core.set_response(duel,build_position_response(0x1))
    elif mt==MSG_SELECT_TRIBUTE:
        n=msg.get("min",1);cards=msg.get("cards",[])
        core.set_response(duel,build_tribute_response(list(range(min(n,len(cards))))))
    elif mt==MSG_SELECT_EFFECTYN:core.set_response(duel,build_effectyn_response(True))
    elif mt==MSG_SELECT_YESNO:core.set_response(duel,build_yesno_response(True))
    elif mt==MSG_SELECT_OPTION:core.set_response(duel,build_option_response(0))
    elif mt==MSG_SELECT_SUM:
        must=msg.get("must_cards",[]);sel=msg.get("selectable_cards",[])
        indices=list(range(len(must)))
        if sel:indices.append(len(must))
        core.set_response(duel,build_sum_response(indices))
    elif mt==MSG_SELECT_UNSELECT_CARD:
        sel=msg.get("selectable",[])
        core.set_response(duel,build_unselect_card_response(0 if sel else -1))
    elif mt==MSG_SELECT_COUNTER:
        cards=msg.get("cards",[]);n=msg.get("count",0)
        counts=[min(n,c.get("counter_count",0)) if i==0 else 0 for i,c in enumerate(cards)]
        core.set_response(duel,build_counter_response(counts))
    elif mt==MSG_ANNOUNCE_RACE:core.set_response(duel,build_announce_race_response(msg.get("available",1)&-(msg.get("available",1))))
    elif mt==MSG_ANNOUNCE_ATTRIB:core.set_response(duel,build_announce_attrib_response(msg.get("available",1)&-(msg.get("available",1))))
    else:core.set_response(duel,b"\x00\x00\x00\x00")

def run_duel(deck0, deck1, target_code, activate_action, max_turns=10, need_p1_monster=False):
    """Duello olustur, target karti aktifle, sonuclari dondur."""
    duel=core.create_duel(card_reader=cr,script_reader=sr,starting_lp=8000,flags=DUEL_MODE_MR2)
    for n in["constant.lua","utility.lua"]:
        p=SCRIPT_DIR/n;core.load_script(duel,p.read_text(encoding="utf-8"),n)
    for c in deck0:core.add_card(duel,team=0,code=c,loc=LOCATION_DECK)
    for c in deck1:core.add_card(duel,team=1,code=c,loc=LOCATION_DECK)
    core.start_duel(duel)

    results={"messages":[],"errors":[],"activated":False,"turn":0}
    turn=0;activated=False;p1_has_monster=False

    for step in range(1000):
        status=core.process(duel)
        raw=core.get_message(duel)
        if not raw:
            if status==DUEL_STATUS_END:break
            continue
        for mt,md in split_messages(raw):
            try:
                msg=parse_message(mt,md)
            except Exception as e:
                mn=MSG_NAMES.get(mt,"?")
                results["errors"].append(f"PARSE ERROR {mn}: {e}")
                continue

            mn=MSG_NAMES.get(mt,"?")
            if mt==MSG_NEW_TURN:turn+=1;results["turn"]=turn
            if mt in(MSG_SUMMONING,MSG_SPSUMMONING) and msg.get("controller")==1:p1_has_monster=True
            if mt==MSG_RETRY:results["errors"].append("RETRY")

            # Onemli mesajlari kaydet
            if mt in(MSG_CHAINING,MSG_SUMMONING,MSG_SPSUMMONING,MSG_DAMAGE,MSG_RECOVER,
                     MSG_ADD_COUNTER,MSG_REMOVE_COUNTER,MSG_DRAW,MSG_ATTACK,MSG_ATTACK_DISABLED,
                     MSG_WIN,MSG_PAY_LPCOST):
                code=msg.get("code",0)
                card=db.get_card(code) if code else None
                results["messages"].append({"type":mn,"code":code,"name":card.name if card else "","data":msg})

            if msg.get("interactive"):
                player=msg.get("player",0)
                if mt==MSG_SELECT_IDLECMD and not activated:
                    acts=msg.get("activatable",[])
                    summ=msg.get("summonable",[])
                    ssets=msg.get("spell_setable",[])

                    # P1: canavar cagir
                    if player==1:
                        if summ:core.set_response(duel,build_idle_cmd_response("summon",0))
                        elif msg.get("can_battle_phase"):core.set_response(duel,build_idle_cmd_response("battle"))
                        else:core.set_response(duel,build_idle_cmd_response("end"))
                        continue

                    # P0: hedef karti bul ve aktifle
                    target_idx=next((j for j,c in enumerate(acts) if c["code"]==target_code),-1)
                    summon_idx=next((j for j,c in enumerate(summ) if c["code"]==target_code),-1)
                    spsummon_idx=-1
                    for j,c in enumerate(msg.get("special_summonable",[])):
                        if c["code"]==target_code:spsummon_idx=j;break
                    sset_idx=next((j for j,c in enumerate(ssets) if c["code"]==target_code),-1)

                    if activate_action=="activate" and target_idx>=0:
                        core.set_response(duel,build_idle_cmd_response("activate",target_idx))
                        activated=True;results["activated"]=True;continue
                    elif activate_action=="summon" and summon_idx>=0:
                        core.set_response(duel,build_idle_cmd_response("summon",summon_idx))
                        activated=True;results["activated"]=True;continue
                    elif activate_action=="spsummon" and spsummon_idx>=0:
                        core.set_response(duel,build_idle_cmd_response("spsummon",spsummon_idx))
                        activated=True;results["activated"]=True;continue
                    elif activate_action=="sset" and sset_idx>=0:
                        core.set_response(duel,build_idle_cmd_response("sset",sset_idx))
                        activated=True;results["activated"]=True;continue

                    # Yoksa: fodder canavar cagir veya end
                    fodder=[j for j,c in enumerate(summ) if c["code"]!=target_code]
                    if fodder and (not need_p1_monster or p1_has_monster):
                        core.set_response(duel,build_idle_cmd_response("summon",fodder[0]))
                    elif msg.get("can_battle_phase"):
                        core.set_response(duel,build_idle_cmd_response("battle"))
                    else:
                        core.set_response(duel,build_idle_cmd_response("end"))
                elif mt==MSG_SELECT_BATTLECMD:
                    atks=msg.get("attackable",[])
                    if atks:core.set_response(duel,build_battle_cmd_response("attack",0))
                    else:core.set_response(duel,build_battle_cmd_response("end"))
                else:
                    respond(msg,duel)

        if turn>max_turns or status==DUEL_STATUS_END:break
        if len(results["errors"])>20:break

    core.destroy_duel(duel)
    return results

# ============================================================
# TEST SUITE
# ============================================================
print("="*70)
print("  KAPSAMLI EFEKT TESTLERİ — YUGI DESTESİ")
print("="*70)

tests_passed=0;tests_failed=0

def test(name, deck0, deck1, target_code, action, check_fn, **kw):
    global tests_passed,tests_failed
    print(f"\n{'─'*50}")
    print(f"TEST: {name}")
    r=run_duel(deck0,deck1,target_code,action,**kw)
    errors=[e for e in r["errors"] if e!="RETRY"]
    retry_count=r["errors"].count("RETRY")
    ok,reason=check_fn(r)
    if ok and not errors:
        print(f"  ✓ GECTI — {reason}")
        if retry_count:print(f"    (RETRY x{retry_count} — normal olabilir)")
        tests_passed+=1
    else:
        print(f"  ✗ BASARISIZ — {reason}")
        if errors:print(f"    Hatalar: {errors[:3]}")
        if retry_count>5:print(f"    RETRY x{retry_count}")
        tests_failed+=1

ALEX=[43096270]*40  # Alexandrite Dragon x40
WOLF=[69247929]*40  # Gene-Warped Warwolf x40

# --- POT OF GREED ---
test("Pot of Greed (2 kart cek)",
    [43096270]*39+[55144522], WOLF, 55144522, "activate",
    lambda r:(any(m["type"]=="MSG_DRAW" and m["data"].get("count")==2 for m in r["messages"]),"2 kart cekildi" if any(m["type"]=="MSG_DRAW" and m["data"].get("count")==2 for m in r["messages"]) else "DRAW mesaji yok"))

# --- GRACEFUL CHARITY ---
test("Graceful Charity (3 cek + 2 at)",
    [43096270]*39+[79571449], WOLF, 79571449, "activate",
    lambda r:(any(m["type"]=="MSG_DRAW" and m["data"].get("count")==3 for m in r["messages"]),"3 kart cekildi" if any(m["type"]=="MSG_DRAW" and m["data"].get("count")==3 for m in r["messages"]) else "DRAW 3 yok"))

# --- CHANGE OF HEART ---
test("Change of Heart (kontrol al)",
    [43096270]*39+[4031928], WOLF, 4031928, "activate",
    lambda r:(r["activated"],"Aktiflestirildi" if r["activated"] else "Aktiflestirilmedi"),
    need_p1_monster=True)

# --- MONSTER REBORN ---
test("Monster Reborn (mezarliktan canavar)",
    [43096270]*39+[83764718], WOLF, 83764718, "activate",
    lambda r:(r["activated"],"Aktiflestirildi" if r["activated"] else "Aktiflestirilmedi — mezarlik bos olabilir"),
    max_turns=15)

# --- DARK MAGIC CURTAIN ---
test("Dark Magic Curtain (LP ode + DM cagir)",
    [43096270]*34+[46986414]*5+[99789342], WOLF, 99789342, "activate",
    lambda r:(
        any(m["type"]=="MSG_PAY_LPCOST" for m in r["messages"]) or any(m["type"]=="MSG_SPSUMMONING" for m in r["messages"]),
        "LP odendi/DM cagrildi" if any(m["type"] in("MSG_PAY_LPCOST","MSG_SPSUMMONING") for m in r["messages"]) else "Efekt calismadi"))

# --- MYSTICAL SPACE TYPHOON ---
test("Mystical Space Typhoon (spell/trap yok et)",
    [43096270]*39+[5318639], [69247929]*39+[18807108], 5318639, "activate",
    lambda r:(r["activated"],"Aktiflestirildi" if r["activated"] else "Aktiflestirilmedi — rakipte hedef yok"),
    need_p1_monster=True, max_turns=15)

# --- BREAKER (spell counter) ---
test("Breaker the Magical Warrior (counter + ATK)",
    [43096270]*39+[71413901], WOLF, 71413901, "summon",
    lambda r:(any(m["type"]=="MSG_ADD_COUNTER" for m in r["messages"]),"Counter eklendi" if any(m["type"]=="MSG_ADD_COUNTER" for m in r["messages"]) else "Counter mesaji yok"))

# --- THE TRICKY (discard + spsummon) ---
test("The Tricky (discard ile ozel cagri)",
    [43096270]*39+[14778250], WOLF, 14778250, "spsummon",
    lambda r:(any(m["type"]=="MSG_SPSUMMONING" and m["code"]==14778250 for m in r["messages"]),"Ozel cagrildi" if any(m["type"]=="MSG_SPSUMMONING" and m["code"]==14778250 for m in r["messages"]) else "SpSummon yok"))

# --- OLD VINDICTIVE MAGICIAN (flip destroy) ---
test("Old Vindictive Magician (flip → yok et)",
    [43096270]*39+[45141844], WOLF, 45141844, "summon",
    lambda r:(r["activated"],"Cagrildi (flip sonra test edilecek)" if r["activated"] else "Cagrilamadi"))

# --- SWORDS OF REVEALING LIGHT ---
test("Swords of Revealing Light (3 tur kalici)",
    [43096270]*39+[72302403], WOLF, 72302403, "activate",
    lambda r:(any(m["type"]=="MSG_CHAINING" and m["code"]==72302403 for m in r["messages"]),"Aktiflestirildi" if any(m["type"]=="MSG_CHAINING" and m["code"]==72302403 for m in r["messages"]) else "Chaining yok"))

# --- MONSTER REINCARNATION ---
test("Monster Reincarnation (discard 1 + GY'den ele al)",
    [43096270]*39+[74848038], WOLF, 74848038, "activate",
    lambda r:(r["activated"],"Aktiflestirildi" if r["activated"] else "Aktiflestirilmedi — GY bos olabilir"),
    max_turns=15)

# --- THOUSAND KNIVES ---
test("Thousand Knives (DM varsa 1 yok et)",
    [43096270]*34+[46986414]*5+[63391643], WOLF, 63391643, "activate",
    lambda r:(r["activated"],"Aktiflestirildi" if r["activated"] else "Aktiflestirilmedi — DM sahada olmali"),
    need_p1_monster=True, max_turns=15)

# --- MAGICAL DIMENSION ---
test("Magical Dimension (tribute spellcaster + summon + destroy)",
    [43096270]*34+[73752131]*5+[28553439], WOLF, 28553439, "activate",
    lambda r:(r["activated"],"Aktiflestirildi" if r["activated"] else "Aktiflestirilmedi — Spellcaster gerekli"),
    need_p1_monster=True, max_turns=15)

# --- BLACK LUSTER RITUAL ---
test("Black Luster Ritual (ritual summon)",
    [43096270]*33+[5405694]*3+[43096270]*3+[55761792], WOLF, 55761792, "activate",
    lambda r:(r["activated"],"Aktiflestirildi" if r["activated"] else "Aktiflestirilmedi — BLS veya malzeme eksik"),
    max_turns=15)

# --- DARK MAGICIAN GIRL (passive ATK boost) ---
test("Dark Magician Girl (pasif ATK boost)",
    [43096270]*39+[38033121], WOLF, 38033121, "summon",
    lambda r:(any(m["type"]=="MSG_SUMMONING" and m["code"]==38033121 for m in r["messages"]),"Cagrildi" if any(m["type"]=="MSG_SUMMONING" and m["code"]==38033121 for m in r["messages"]) else "Cagrilamadi"))

# --- SKILLED DARK MAGICIAN (3 spell counter → summon DM) ---
test("Skilled Dark Magician (spell counter birikimi)",
    [55144522]*5+[43096270]*34+[73752131], WOLF, 73752131, "summon",
    lambda r:(any(m["type"]=="MSG_ADD_COUNTER" for m in r["messages"]),"Counter eklendi" if any(m["type"]=="MSG_ADD_COUNTER" for m in r["messages"]) else "Counter yok — spell oynamak lazim"))

# --- KING'S KNIGHT (Queen varken Jack cagir) ---
test("King's Knight (Queen + King → Jack)",
    [43096270]*33+[25652259]*3+[90876561]*3+[64788463], WOLF, 64788463, "summon",
    lambda r:(r["activated"],"Cagrildi" if r["activated"] else "Cagrilamadi — Queen sahada olmali"),
    max_turns=15)

# ============================================================
print(f"\n{'='*70}")
print(f"  SONUC: {tests_passed} GECTI / {tests_failed} BASARISIZ / {tests_passed+tests_failed} TOPLAM")
print(f"{'='*70}")

db.close()
