"""Gercek duelloda canavar cagrisi ve spell aktivasyonunun
tam veri akisini yakalayip gosteren test.

Motor ←→ Sunucu arasindaki her binary mesaji ve response'u loglar.
"""
import sys, io, asyncio, json, struct
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8")
sys.path.insert(0, ".")

from server.ocg_binding import *
from server.card_database import CardDatabase
from server.message_parser import split_messages, parse_message, MSG_NAMES
from server.response_builder import *
from server.config import SCRIPT_DIR, CARD_DB_PATH

db = CardDatabase(CARD_DB_PATH)
core = OCGCore()

import ctypes
_bufs = []
def card_reader(payload, code, data_ptr):
    card = db.get_card(code)
    if not card:
        data_ptr.contents.code = code
        e = (ctypes.c_uint16 * 1)(0); _bufs.append(e)
        data_ptr.contents.setcodes = ctypes.cast(e, ctypes.POINTER(ctypes.c_uint16))
        return
    data_ptr.contents.code = card.code
    data_ptr.contents.alias = card.alias
    data_ptr.contents.type = card.type
    data_ptr.contents.level = card.level
    data_ptr.contents.attribute = card.attribute
    data_ptr.contents.race = card.race
    data_ptr.contents.attack = card.attack
    data_ptr.contents.defense = card.defense
    data_ptr.contents.lscale = card.lscale
    data_ptr.contents.rscale = card.rscale
    data_ptr.contents.link_marker = card.link_marker
    sc = card.setcodes + [0]
    a = (ctypes.c_uint16 * len(sc))(*sc); _bufs.append(a)
    data_ptr.contents.setcodes = ctypes.cast(a, ctypes.POINTER(ctypes.c_uint16))

def script_reader(payload, duel, name):
    n = name.decode("utf-8") if isinstance(name, bytes) else name
    for p in [SCRIPT_DIR / n, SCRIPT_DIR / "official" / n]:
        if p.exists():
            c = p.read_text(encoding="utf-8"); cb = c.encode("utf-8")
            core._lib.OCG_LoadScript(duel, cb, len(cb), n.encode("utf-8"))
            return 1
    return 0

# Deste: Alexandrite Dragon + Pot of Greed EN SONDA (en son eklenen = destenin ustu = ilk cekilen)
deck = [
    43096270,   # padding (destenin alti)
    43096270, 43096270, 43096270, 43096270,  # Alexandrite Dragon x4
    43096270, 43096270, 43096270, 43096270,
    43096270, 43096270, 43096270, 43096270,
    43096270, 43096270, 43096270, 43096270,
    43096270, 43096270, 43096270, 43096270,
    43096270, 43096270, 43096270, 43096270,
    43096270, 43096270, 43096270, 43096270,
    43096270, 43096270, 43096270, 43096270,
    43096270, 43096270, 43096270, 43096270,
    43096270, 43096270,
    55144522,   # Pot of Greed — destenin ustu, ilk elde olur
]

duel = core.create_duel(
    card_reader=card_reader, script_reader=script_reader,
    starting_lp=8000, flags=DUEL_MODE_MR2,
)
for name in ["constant.lua", "utility.lua"]:
    p = SCRIPT_DIR / name
    core.load_script(duel, p.read_text(encoding="utf-8"), name)

for c in deck:
    core.add_card(duel, team=0, code=c, loc=LOCATION_DECK)
for c in [43096270]*40:
    core.add_card(duel, team=1, code=c, loc=LOCATION_DECK)
core.start_duel(duel)

print("=" * 70)
print("  CANAVAR CAGRISI + SPELL AKTIVASYONU — TAM VERİ AKISI")
print("=" * 70)

phase = 0  # 0=baslangic, 1=canavar cagrildi, 2=spell oynandi

for step in range(200):
    status = core.process(duel)
    raw = core.get_message(duel)
    if not raw:
        if status == DUEL_STATUS_END: break
        continue

    msgs = split_messages(raw)
    for msg_type, msg_data in msgs:
        mname = MSG_NAMES.get(msg_type, f"UNKNOWN_{msg_type}")
        msg = parse_message(msg_type, msg_data)

        # Ilginc mesajlari detayli goster
        if msg_type in (MSG_SELECT_IDLECMD, MSG_SELECT_CHAIN, MSG_SELECT_PLACE,
                         MSG_SELECT_POSITION, MSG_SUMMONING, MSG_SUMMONED,
                         MSG_DRAW, MSG_MOVE, MSG_CHAINING, MSG_CHAIN_END,
                         MSG_NEW_TURN, MSG_NEW_PHASE, MSG_SET):

            if msg_type == MSG_SELECT_IDLECMD and phase == 0:
                # CANAVAR CAGRISI
                summ = msg.get("summonable", [])
                if summ:
                    print("\n" + "=" * 70)
                    print("  SENARYO 1: CANAVAR CAGRISI (Normal Summon)")
                    print("=" * 70)
                    print(f"\n>>> MOTORDAN GELEN: {mname}")
                    print(f"    Ham binary: {msg_data[:40].hex()}{'...' if len(msg_data)>40 else ''}")
                    print(f"    Parse sonucu:")
                    print(f"      player: {msg.get('player')}")
                    print(f"      summonable ({len(summ)} kart):")
                    for j, c in enumerate(summ[:3]):
                        card = db.get_card(c["code"])
                        print(f"        [{j}] code={c['code']} ({card.name if card else '?'}) con={c['controller']} loc={c['location']} seq={c['sequence']}")

                    # Yanit olustur: ilk karti cagir
                    resp = build_idle_cmd_response("summon", 0)
                    print(f"\n<<< MOTORA GONDERILEN YANIT:")
                    print(f"    Fonksiyon: build_idle_cmd_response('summon', 0)")
                    print(f"    Binary: {resp.hex()}")
                    val = struct.unpack("<i", resp)[0]
                    print(f"    Decode: (index={val>>16}, action_type={val&0xFFFF}) → i32={val}")
                    core.set_response(duel, resp)
                    phase = 1
                    continue

            elif msg_type == MSG_SELECT_PLACE:
                print(f"\n>>> MOTORDAN GELEN: {mname}")
                print(f"    Ham binary: {msg_data.hex()}")
                print(f"    Parse: player={msg.get('player')} count={msg.get('count')} flag={msg.get('selectable'):#010x}")
                print(f"    Flag aciklama: 1=dolu, 0=bos")
                flag = msg.get("selectable", 0)
                for seq in range(5):
                    status_m = "DOLU" if (flag & (1 << seq)) else "BOS"
                    print(f"      MZONE seq={seq}: {status_m}")

                # Bos slot bul — MZONE sonra SZONE
                placed = False
                for seq in range(7):
                    if not (flag & (1 << seq)):
                        resp = build_place_response(msg["player"], 0x04, seq)
                        print(f"\n<<< MOTORA GONDERILEN: place_response(player={msg['player']}, loc=MZONE, seq={seq})")
                        print(f"    Binary: {resp.hex()}")
                        core.set_response(duel, resp); placed = True; break
                if not placed:
                    for seq in range(8):
                        if not (flag & (1 << (seq + 8))):
                            resp = build_place_response(msg["player"], 0x08, seq)
                            print(f"\n<<< MOTORA GONDERILEN: place_response(player={msg['player']}, loc=SZONE, seq={seq})")
                            print(f"    Binary: {resp.hex()}")
                            core.set_response(duel, resp); placed = True; break
                continue

            elif msg_type == MSG_SELECT_POSITION:
                print(f"\n>>> MOTORDAN GELEN: {mname}")
                print(f"    Ham binary: {msg_data.hex()}")
                print(f"    Parse: player={msg.get('player')} code={msg.get('code')} positions={msg.get('positions'):#x}")
                positions = msg.get("positions", 0)
                pos_names = []
                if positions & 0x1: pos_names.append("FACEUP_ATK")
                if positions & 0x4: pos_names.append("FACEUP_DEF")
                if positions & 0x8: pos_names.append("FACEDOWN_DEF")
                print(f"    Secenekler: {pos_names}")

                resp = build_position_response(0x1)
                print(f"\n<<< MOTORA GONDERILEN: position_response(FACEUP_ATTACK)")
                print(f"    Binary: {resp.hex()}")
                core.set_response(duel, resp)
                continue

            elif msg_type == MSG_SUMMONING:
                card = db.get_card(msg.get("code", 0))
                print(f"\n>>> MOTORDAN GELEN: {mname}")
                print(f"    Ham binary: {msg_data.hex()}")
                print(f"    Parse: code={msg.get('code')} ({card.name if card else '?'}) con={msg.get('controller')} loc={msg.get('location')} seq={msg.get('sequence')} pos={msg.get('position')}")
                print(f"    → Bu mesaj oyunculara 'cagri yapiliyor' bildirimi olarak gonderilir")

            elif msg_type == MSG_SUMMONED:
                print(f"\n>>> MOTORDAN GELEN: {mname}")
                print(f"    Ham binary: {msg_data.hex()}")
                print(f"    → Cagri tamamlandi, tarayicida kart sahaya yerlesir")

            elif msg_type == MSG_SELECT_IDLECMD and phase == 1:
                # SPELL AKTIVASYONU
                acts = msg.get("activatable", [])
                pot = next((j for j, c in enumerate(acts) if c["code"] == 55144522), -1)
                if pot >= 0:
                    print("\n" + "=" * 70)
                    print("  SENARYO 2: SPELL AKTIVASYONU (Pot of Greed)")
                    print("=" * 70)
                    print(f"\n>>> MOTORDAN GELEN: {mname}")
                    print(f"    activatable ({len(acts)} efekt):")
                    for j, c in enumerate(acts):
                        card = db.get_card(c["code"])
                        print(f"      [{j}] code={c['code']} ({card.name if card else '?'}) loc={c['location']} desc={c.get('description','?')}")

                    resp = build_idle_cmd_response("activate", pot)
                    print(f"\n<<< MOTORA GONDERILEN: idle_cmd('activate', {pot})")
                    print(f"    Binary: {resp.hex()}")
                    val = struct.unpack("<i", resp)[0]
                    print(f"    Decode: (index={val>>16}, action=activate=5) → i32={val}")
                    core.set_response(duel, resp)
                    phase = 2
                    break  # dis donguye don, process tekrar cagirilsin
                else:
                    resp = build_idle_cmd_response("end")
                    core.set_response(duel, resp)
                    continue

            elif msg_type == MSG_CHAINING:
                card = db.get_card(msg.get("code", 0))
                print(f"\n>>> MOTORDAN GELEN: {mname}")
                print(f"    Ham binary: {msg_data.hex()}")
                print(f"    Parse: code={msg.get('code')} ({card.name if card else '?'}) con={msg.get('controller')} loc={msg.get('location')} seq={msg.get('sequence')} chain_count={msg.get('chain_count')}")
                print(f"    → Spell/Trap aktiflestirildi bildirimi")

            elif msg_type == MSG_DRAW and phase >= 2:
                print(f"\n>>> MOTORDAN GELEN: {mname}")
                print(f"    Ham binary: {msg_data[:40].hex()}...")
                cards = msg.get("cards", [])
                print(f"    Parse: player={msg.get('player')} count={msg.get('count')}")
                for c in cards:
                    card = db.get_card(c["code"])
                    print(f"      code={c['code']} ({card.name if card else '?'}) position={c.get('position'):#x}")
                print(f"    → Pot of Greed efekti: 2 kart cekildi!")

            elif msg_type == MSG_MOVE:
                card = db.get_card(msg.get("code", 0))
                frm = msg.get("from", {})
                to = msg.get("to", {})
                print(f"\n>>> MOTORDAN GELEN: {mname}")
                print(f"    code={msg.get('code')} ({card.name if card else '?'})")
                print(f"    from: con={frm.get('controller')} loc={frm.get('location'):#x} seq={frm.get('sequence')}")
                print(f"    to:   con={to.get('controller')} loc={to.get('location'):#x} seq={to.get('sequence')}")

            elif msg_type == MSG_CHAIN_END:
                print(f"\n>>> MOTORDAN GELEN: {mname}")
                print(f"    → Zincir cozumlendi, normal akisa don")
                if phase == 2: phase = 3

            elif msg_type == MSG_NEW_TURN:
                print(f"\n--- TUR (P{msg.get('player')}) ---")
            elif msg_type == MSG_NEW_PHASE:
                phases = {0x01:"Draw",0x02:"Standby",0x04:"Main1",0x100:"Main2",0x200:"End"}
                print(f"    Faz: {phases.get(msg.get('phase'), hex(msg.get('phase',0)))}")

        # Phase 2 sonrasi: tum mesajlari logla
        if phase >= 2 and msg_type not in (MSG_SELECT_IDLECMD,):
            if msg_type not in (MSG_NEW_TURN, MSG_NEW_PHASE):
                card_obj = db.get_card(msg.get("code", 0)) if msg.get("code") else None
                print(f"\n>>> MOTORDAN GELEN: {mname}")
                if card_obj: print(f"    Kart: {card_obj.name}")
                if msg_type == MSG_DRAW:
                    for c in msg.get("cards", []):
                        cd = db.get_card(c["code"])
                        print(f"    Cekilen: {c['code']} ({cd.name if cd else '?'})")
                elif msg_type == MSG_MOVE:
                    print(f"    {msg.get('from',{}).get('location',0):#x} → {msg.get('to',{}).get('location',0):#x}")
                elif msg_type == MSG_CHAINING:
                    print(f"    Zincir aktif: con={msg.get('controller')} loc={msg.get('location'):#x}")

        # Diger SELECT mesajlarina basit yanit
        if msg.get("interactive") and msg_type not in (MSG_SELECT_IDLECMD, MSG_SELECT_PLACE, MSG_SELECT_POSITION):
            if msg_type == MSG_SELECT_CHAIN:
                if phase >= 2: print(f"    → Auto-pas chain")
                core.set_response(duel, build_chain_response(-1))
            elif msg_type == MSG_SELECT_CARD:
                n = msg.get("min", 1); cards = msg.get("cards", [])
                core.set_response(duel, build_card_response(list(range(min(n, len(cards))))))

    if phase >= 3:
        break
    if status == DUEL_STATUS_END:
        break

core.destroy_duel(duel)
db.close()
print("\n" + "=" * 70)
print("  BITTI")
print("=" * 70)
