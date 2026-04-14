# Yuki — Browser-Based Duel Game
# Copyright (C) 2026 Yuki Contributors
# SPDX-License-Identifier: AGPL-3.0-or-later
#
# duel_manager.py — Düello durumu yönetimi
#
# OCGCore motoru ile WebSocket oyuncuları arasında köprü. Sorumluluğu:
#   1. Düello oluştur, kartları ekle, başlat
#   2. Motor mesajlarını ayrıştırıp doğru oyuncuya ilet
#   3. Oyuncudan gelen yanıtları motora aktar
#   4. Düello döngüsünü async olarak yürüt

import asyncio
import ctypes
import random
from pathlib import Path

import struct as _struct
from server.ocg_binding import (
    OCGCore,
    LOCATION_DECK, LOCATION_EXTRA, LOCATION_MZONE, LOCATION_SZONE,
    LOCATION_HAND,
    POS_FACEDOWN_DEFENSE, POS_FACEDOWN,
    DUEL_MODE_MR2,
    DUEL_STATUS_END, DUEL_STATUS_AWAITING, DUEL_STATUS_CONTINUE,
    MSG_WIN, MSG_RETRY, MSG_ADD_COUNTER, MSG_REMOVE_COUNTER,
    MSG_SUMMONING, MSG_SUMMONED, MSG_SPSUMMONING, MSG_SPSUMMONED,
    MSG_FLIPSUMMONING, MSG_FLIPSUMMONED, MSG_SELECT_BATTLECMD,
    QUERY_CODE, QUERY_ATTACK, QUERY_DEFENSE, QUERY_POSITION,
)
from server.card_database import CardDatabase
from server.message_parser import split_messages, parse_message, INTERACTIVE_MESSAGES
from server.config import SCRIPT_DIR, CARD_DB_PATH
from server.room import Room, RoomState, Player
from server.ai_player import ai_respond


# Sistem scriptleri — düello oluşturulduktan sonra yüklenmeli
SYSTEM_SCRIPTS = ["constant.lua", "utility.lua"]

# Global kaynaklar (sunucu başına bir tane)
_core: OCGCore | None = None
_db: CardDatabase | None = None

# ctypes callback'ler için GC koruması
_setcode_buffers: list = []


def get_core() -> OCGCore:
    """Tekil OCGCore örneği döndürür."""
    global _core
    if _core is None:
        _core = OCGCore()
    return _core


def get_db() -> CardDatabase:
    """Tekil CardDatabase örneği döndürür."""
    global _db
    if _db is None:
        _db = CardDatabase(CARD_DB_PATH)
    return _db


def _card_reader(payload, code, data_ptr):
    """OCGCore callback: Kart verisini veritabanından oku."""
    db = get_db()
    card = db.get_card(code)
    if card is None:
        data_ptr.contents.code = code
        empty = (ctypes.c_uint16 * 1)(0)
        _setcode_buffers.append(empty)
        data_ptr.contents.setcodes = ctypes.cast(
            empty, ctypes.POINTER(ctypes.c_uint16)
        )
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

    sc_list = card.setcodes + [0]
    sc_arr = (ctypes.c_uint16 * len(sc_list))(*sc_list)
    _setcode_buffers.append(sc_arr)
    data_ptr.contents.setcodes = ctypes.cast(
        sc_arr, ctypes.POINTER(ctypes.c_uint16)
    )


class DuelManager:
    """Tek bir düelloyu yöneten sınıf.

    Her Room'a bir DuelManager atanır. Motor döngüsünü async olarak yürütür,
    mesajları oyunculara iletir, yanıtları motora aktarır.
    """

    def __init__(self, room: Room, bot_team: int = -1):
        self.room = room
        self.bot_team = bot_team  # -1 = bot yok, 0 veya 1 = o taraf bot
        self._core = get_core()
        self._db = get_db()
        self._duel = None
        self._running = False
        self._response_event = asyncio.Event()
        self._pending_response: bytes | None = None
        self._pending_player: int = -1  # Yanıt bekleyen oyuncu
        self._last_select_msg: dict | None = None  # RETRY icin son SELECT
        self._last_select_type: int = 0  # Son SELECT mesaj tipi (bot için)
        self._pending_summon: dict | None = None  # Çağrı tamamlanınca stat sorgusu için

    def _script_reader(self, payload, duel, name):
        """OCGCore callback: Lua scriptini dosyadan yükle."""
        name_str = name.decode("utf-8") if isinstance(name, bytes) else name
        for path in [SCRIPT_DIR / name_str, SCRIPT_DIR / "official" / name_str]:
            if path.exists():
                try:
                    content = path.read_text(encoding="utf-8")
                    content_bytes = content.encode("utf-8")
                    self._core._lib.OCG_LoadScript(
                        duel, content_bytes, len(content_bytes),
                        name_str.encode("utf-8")
                    )
                    return 1
                except Exception:
                    return 0
        return 0

    def _log_handler(self, payload, string, log_type):
        """OCGCore callback: Log mesajlarını yazdır."""
        if string and log_type == 0:
            msg = string.decode("utf-8", errors="replace")
            print(f"[OCG ERROR] {msg}")

    def _create_duel(self):
        """Düello oluşturur, kartları ekler, başlatır."""
        p0 = self.room.get_player(0)
        p1 = self.room.get_player(1)

        self._duel = self._core.create_duel(
            card_reader=_card_reader,
            script_reader=self._script_reader,
            log_handler=self._log_handler,
            starting_lp=8000,
            flags=DUEL_MODE_MR2,
        )

        # Sistem scriptlerini yükle (KRITIK — efektler için gerekli)
        for script_name in SYSTEM_SCRIPTS:
            path = SCRIPT_DIR / script_name
            if path.exists():
                content = path.read_text(encoding="utf-8")
                self._core.load_script(self._duel, content, script_name)

        # Desteleri karistir ve ekle
        deck0 = list(p0.deck)
        deck1 = list(p1.deck)
        random.shuffle(deck0)
        random.shuffle(deck1)
        for code in deck0:
            self._core.add_card(self._duel, team=0, code=code, loc=LOCATION_DECK)
        for code in deck1:
            self._core.add_card(self._duel, team=1, code=code, loc=LOCATION_DECK)

        self._core.start_duel(self._duel)

    async def start(self):
        """Düelloyu başlatır ve ana döngüyü çalıştırır."""
        self.room.state = RoomState.DUELING
        self._running = True

        # Düelloyu oluştur (senkron — hızlı)
        self._create_duel()

        # Oyunculara düello başladı bildir
        await self.room.broadcast({"action": "duel_start"})

        # Ana düello döngüsü
        try:
            await self._duel_loop()
        except Exception as e:
            print(f"[DUEL ERROR] {e}")
            await self.room.broadcast({
                "action": "duel_error",
                "message": str(e),
            })
        finally:
            self._cleanup()

    async def _duel_loop(self):
        """Ana düello döngüsü — motor mesajları işle, yanıtları bekle."""
        while self._running:
            # Motor bir adım ilerlet
            status = self._core.process(self._duel)

            # Mesajları oku ve ilet
            raw = self._core.get_message(self._duel)
            if raw:
                await self._handle_messages(raw)

            if status == DUEL_STATUS_END:
                self._running = False
                break

            # Yanit bekleyen interaktif mesaj varsa — bekle
            # (status AWAITING veya CONTINUE olabilir, onemli olan
            # _pending_player set edilmis olmasi)
            if self._pending_player >= 0:
                response = await self._wait_for_response()
                if response is not None:
                    self._core.set_response(self._duel, response)

            # asyncio'ya kontrol ver
            await asyncio.sleep(0)

    async def _handle_messages(self, raw: bytes):
        """Motor mesajlarını ayrıştır ve oyunculara ilet."""
        messages = split_messages(raw)

        for msg_type, msg_data in messages:
            try:
                await self._process_single_message(msg_type, msg_data)
            except Exception as e:
                from server.ocg_binding import MSG_NAMES
                mname = MSG_NAMES.get(msg_type, f"UNKNOWN_{msg_type}")
                print(f"[PARSE ERROR] {mname}: {e}")
                import traceback; traceback.print_exc()

    async def _process_single_message(self, msg_type, msg_data):
            if msg_type == MSG_RETRY:
                if self._last_select_msg:
                    target = self._last_select_msg.get("player", 0)
                    self._pending_player = target

                    if target == self.bot_team:
                        # Bot'un yanıtı geçersizdi — AI'ı yeniden tetikle
                        print(f"[BOT RETRY] msg={self._last_select_type:#x}")
                        response = ai_respond(self._last_select_type, self._last_select_msg)
                        self._pending_response = response
                        self._response_event.set()
                    else:
                        player = self.room.get_player(target)
                        if player:
                            await player.send({"action": "retry"})
                            await player.send({
                                "action": "select",
                                "msg": self._last_select_msg,
                            })
                return

            msg = parse_message(msg_type, msg_data)
            self._enrich_message(msg)

            if msg_type == MSG_WIN:
                winner = msg.get("player", -1)
                reward = await self._check_adventure_reward(winner)
                await self.room.broadcast({
                    "action": "duel_end",
                    "winner": winner,
                    "reason": msg.get("reason", 0),
                    "reward": reward,
                })
                self.room.state = RoomState.FINISHED
                self._running = False
                return

            if msg.get("interactive"):
                # Secim mesaji — sadece ilgili oyuncuya gonder
                target_player = msg.get("player", 0)
                self._pending_player = target_player
                self._last_select_type = msg_type

                # Rakibin kapali kartlarinin bilgisini gizle
                self._hide_opponent_facedowns(msg, target_player)
                self._last_select_msg = msg

                # Bot takımıysa AI yanıt üretir
                if target_player == self.bot_team:
                    # Savaş fazında rakibin sahası hakkında bilgi ekle
                    if msg_type == MSG_SELECT_BATTLECMD:
                        opp_team = 1 - self.bot_team
                        msg["opponent_monsters"] = self._query_field_monsters(opp_team)

                    from server.ocg_binding import MSG_NAMES
                    mname = MSG_NAMES.get(msg_type, f"{msg_type:#x}")
                    print(f"[BOT] {mname} → ai_respond")
                    response = ai_respond(msg_type, msg)
                    print(f"[BOT] response={response.hex()}")
                    self._pending_response = response
                    self._response_event.set()
                    # İnsan oyuncuya "bekle" bildir
                    human_player = self.room.get_player(1 - self.bot_team)
                    if human_player:
                        await human_player.send({
                            "action": "info",
                            "msg": {"name": "MSG_WAITING", "type": 3},
                        })
                else:
                    player = self.room.get_player(target_player)
                    if player:
                        await player.send({
                            "action": "select",
                            "msg": msg,
                        })
                        # Diger oyuncuya "bekle" bildir
                        opponent = self.room.get_opponent(player)
                        if opponent:
                            await opponent.send({
                                "action": "info",
                                "msg": {"name": "MSG_WAITING", "type": 3},
                            })
            else:
                # Bilgi mesaji — her iki oyuncuya gonder (bot hariç)
                for p in self.room.players:
                    if p.team == self.bot_team:
                        continue  # Bot'a mesaj gönderme
                    filtered = self._filter_message(msg, p.team)
                    await p.send({
                        "action": "info",
                        "msg": filtered,
                    })

                # Çağrı başladığında konum kaydet
                if msg_type in (MSG_SUMMONING, MSG_SPSUMMONING, MSG_FLIPSUMMONING):
                    self._pending_summon = {
                        "controller": msg.get("controller", 0),
                        "location": msg.get("location", 0),
                        "sequence": msg.get("sequence", 0),
                    }

                # Çağrı tamamlandığında motordan gerçek ATK/DEF sorgula
                # (Clone Token gibi "?" stat'lı kartlar için)
                if msg_type in (MSG_SUMMONED, MSG_SPSUMMONED, MSG_FLIPSUMMONED):
                    if self._pending_summon:
                        await self._send_card_stat_update(
                            self._pending_summon["controller"],
                            self._pending_summon["location"],
                            self._pending_summon["sequence"],
                        )
                        self._pending_summon = None

                # Counter degistiginde kartın guncel ATK/DEF'ini sorgula ve gonder
                if msg_type in (MSG_ADD_COUNTER, MSG_REMOVE_COUNTER):
                    await self._send_card_stat_update(
                        msg.get("controller", 0),
                        msg.get("location", 0),
                        msg.get("sequence", 0),
                    )

    async def _send_card_stat_update(self, controller, location, sequence):
        """Kartin guncel ATK/DEF degerini motordan sorgulayip istemcilere gonderir."""
        if not self._duel or location not in (LOCATION_MZONE, LOCATION_SZONE):
            return
        try:
            flags = QUERY_CODE | QUERY_ATTACK | QUERY_DEFENSE
            raw = self._core.query(self._duel, controller, location, sequence, flags)
            if not raw or len(raw) < 10:
                return

            # Query formati (card.cpp CHECK_AND_INSERT):
            # Her alan: [u16 payload_size][u32 flag][data...]
            # payload_size = sizeof(flag) + sizeof(data) = 4 + 4 = 8
            # Ornek: QUERY_ATTACK → [u16=8][u32=0x100][i32=1900] = 10 byte
            # Son: [u16=4][u32=QUERY_END=0x80000000] = 6 byte
            code = 0; atk = 0; defense = 0
            off = 0
            while off + 2 <= len(raw):
                sz = _struct.unpack_from("<H", raw, off)[0]; off += 2
                if sz < 4: break
                flag = _struct.unpack_from("<I", raw, off)[0]; off += 4
                data_size = sz - 4  # payload minus flag

                if flag == QUERY_CODE and data_size >= 4:
                    code = _struct.unpack_from("<I", raw, off)[0]
                elif flag == QUERY_ATTACK and data_size >= 4:
                    atk = _struct.unpack_from("<i", raw, off)[0]
                elif flag == QUERY_DEFENSE and data_size >= 4:
                    defense = _struct.unpack_from("<i", raw, off)[0]
                elif flag == 0x80000000:
                    break

                off += data_size

            await self.room.broadcast({
                "action": "info",
                "msg": {
                    "name": "MSG_STAT_UPDATE",
                    "controller": controller,
                    "location": location,
                    "sequence": sequence,
                    "code": code,
                    "card_atk": atk,
                    "card_def": defense,
                },
            })
        except Exception as e:
            print(f"[STAT QUERY ERROR] {e}")

    def _enrich_card(self, code: int) -> dict:
        """Kart kodundan isim/ATK/DEF/type bilgisi dondurur."""
        if not code:
            return {}
        card = self._db.get_card(code)
        if not card:
            return {}
        return {
            "card_name": card.name,
            "card_atk": card.attack,
            "card_def": card.defense,
            "card_type": card.type,
            "card_level": card.level,
            "card_attribute": card.attribute,
            "card_race": card.race,
            "card_desc": card.desc,
        }

    def _enrich_message(self, msg: dict):
        """Mesajdaki kart kodlarini isim/ATK/DEF ile zenginlestirir."""
        # Dogrudan "code" alani olan mesajlar (SUMMONING, SET, MOVE vs.)
        if "code" in msg and msg["code"]:
            msg.update(self._enrich_card(msg["code"]))

        # "cards" listesi olan mesajlar (DRAW, SELECT_CARD vs.)
        for card_entry in msg.get("cards", []):
            if isinstance(card_entry, dict) and card_entry.get("code"):
                card_entry.update(self._enrich_card(card_entry["code"]))

        # summonable, attackable gibi listeler (SELECT_IDLECMD, SELECT_BATTLECMD)
        for list_key in ("summonable", "special_summonable", "repositionable",
                         "monster_setable", "spell_setable", "activatable",
                         "attackable", "chains", "must_cards", "selectable_cards",
                         "unselectable"):
            items = msg.get(list_key, [])
            if not isinstance(items, list):
                return
            for entry in items:
                if isinstance(entry, dict) and entry.get("code"):
                    entry.update(self._enrich_card(entry["code"]))

    def _filter_message(self, msg: dict, viewer_team: int) -> dict:
        """Mesaji oyuncu perspektifine gore filtrele.

        Rakibin elindeki kartlarin kodlarini gizle (0 yap).
        """
        name = msg.get("name", "")

        # MSG_DRAW: Rakibin cektigi kartlarin kodlarini gizle
        if name == "MSG_DRAW" and msg.get("player") != viewer_team:
            filtered = dict(msg)
            filtered["cards"] = [
                {"code": 0, "position": c.get("position", 0)}
                for c in msg.get("cards", [])
            ]
            return filtered

        # MSG_SHUFFLE_HAND: Rakibin el kartlarini gizle
        if name == "MSG_SHUFFLE_HAND" and msg.get("player") != viewer_team:
            filtered = dict(msg)
            filtered["cards"] = [0] * msg.get("count", 0)
            return filtered

        return msg

    def _hide_opponent_facedowns(self, msg: dict, viewer_team: int):
        """Interaktif mesajlardaki rakibin kapali kartlarinin bilgisini gizle.

        Oyuncu, rakibin yuz asagi (facedown) kartlarinin ne oldugunu
        gormemeli. code, card_name, card_atk, card_def, card_type sifirlanir.
        """
        hidden_info = {
            "code": 0, "card_name": "", "card_atk": None, "card_def": None,
            "card_type": 0, "card_level": 0, "card_attribute": 0,
            "card_race": 0, "card_desc": "",
        }

        def is_opponent_facedown(entry):
            """Kart rakibin kontrolunde ve kapali mi?"""
            con = entry.get("controller")
            pos = entry.get("position", 0)
            loc = entry.get("location", 0)
            if con is None or con == viewer_team:
                return False
            # El kartlari (LOCATION_HAND=0x02) zaten gizli olmali
            if loc == 0x02:
                return True
            # Facedown kontrolu: position bit 1 (0x2) veya bit 3 (0x8)
            if pos & 0x0A:
                return True
            return False

        def hide_entry(entry):
            """Tek bir kart girdisini gizle."""
            if is_opponent_facedown(entry):
                seq = entry.get("sequence", 0)
                loc = entry.get("location", 0)
                loc_name = {0x02: "El", 0x04: "Canavar", 0x08: "Buyu/Tuzak"}.get(loc, "?")
                entry.update(hidden_info)
                entry["card_name"] = f"Kapali Kart (Slot {seq + 1})"

        # cards listesi (SELECT_CARD, SELECT_TRIBUTE, vs.)
        for card_entry in msg.get("cards", []):
            if isinstance(card_entry, dict):
                hide_entry(card_entry)

        # Diger listeler
        for list_key in ("attackable", "selectable", "unselectable",
                         "selectable_cards", "must_cards", "chains"):
            items = msg.get(list_key, [])
            if isinstance(items, list):
                for entry in items:
                    if isinstance(entry, dict):
                        hide_entry(entry)

    async def _wait_for_response(self) -> bytes | None:
        """Oyuncudan yanıt gelene kadar bekle (timeout ile).

        Not: Yanıt, beklemeye başlamadan ÖNCE gelebilir (örn. SELECT_PLACE
        gibi otomatik yanıtlanan mesajlarda). Bu durumda event zaten set
        edilmiştir — temizlemeden doğrudan kullanırız.
        """
        if not self._response_event.is_set():
            # Yanıt henüz gelmedi — sınırsız bekle (surrender ile bitirilir)
            await self._response_event.wait()

        # Yanıtı al ve sıfırla
        self._response_event.clear()
        response = self._pending_response
        self._pending_response = None
        self._pending_player = -1
        return response

    async def surrender(self, player_team: int):
        """Oyuncu teslim oldu — rakip kazanır."""
        if not self._running:
            return
        self._running = False
        winner = 1 - player_team
        await self.room.broadcast({
            "action": "duel_end",
            "winner": winner,
            "reason": "surrender",
        })
        self.room.state = RoomState.FINISHED
        # Yanıt bekliyorsa kilidi aç (döngü dursun)
        self._response_event.set()

    def _query_field_monsters(self, team: int) -> list[dict]:
        """Bir oyuncunun MZONE'undaki canavarların ATK/DEF/position bilgisini motordan sorgular."""
        monsters = []
        if not self._duel:
            return monsters
        for seq in range(7):
            try:
                flags = QUERY_CODE | QUERY_ATTACK | QUERY_DEFENSE | QUERY_POSITION
                raw = self._core.query(self._duel, team, LOCATION_MZONE, seq, flags)
                if not raw or len(raw) < 10:
                    continue
                code = 0; atk = 0; defense = 0; pos = 0
                off = 0
                while off + 2 <= len(raw):
                    sz = _struct.unpack_from("<H", raw, off)[0]; off += 2
                    if sz < 4: break
                    flag = _struct.unpack_from("<I", raw, off)[0]; off += 4
                    data_size = sz - 4
                    if flag == QUERY_CODE and data_size >= 4:
                        code = _struct.unpack_from("<I", raw, off)[0]
                    elif flag == QUERY_ATTACK and data_size >= 4:
                        atk = _struct.unpack_from("<i", raw, off)[0]
                    elif flag == QUERY_DEFENSE and data_size >= 4:
                        defense = _struct.unpack_from("<i", raw, off)[0]
                    elif flag == QUERY_POSITION and data_size >= 4:
                        pos = _struct.unpack_from("<I", raw, off)[0]
                    elif flag == 0x80000000:
                        break
                    off += data_size
                if code:
                    monsters.append({"code": code, "atk": atk, "def": defense, "position": pos})
            except Exception:
                continue
        return monsters

    async def _check_adventure_reward(self, winner: int) -> dict | None:
        """Macera düellosuysa ve insan kazandıysa ödül ver."""
        info = getattr(self, "adventure_info", None)
        if not info:
            return None
        # İnsan oyuncu team 0, bot team 1 — insan kazanmalı
        if winner != 0:
            return None

        from server.websocket_server import ADVENTURES, BOT_DECKS, user_db

        adv_id = info["adventure"]
        stage_num = info["stage"]
        user_id = info["user_id"]
        adv = ADVENTURES.get(adv_id)
        if not adv:
            return None

        stage = adv["stages"][stage_num]
        dust_reward = stage["dust"]
        card_count = stage["cards"]

        # Rakibin destesinden koleksiyonda olmayan kartları bul
        bot_deck = BOT_DECKS.get(stage["bot"], [])
        owned = set(user_db.get_collection(user_id))
        available = [c for c in set(bot_deck) if c not in owned]
        random.shuffle(available)
        card_reward = available[:card_count]

        result = user_db.complete_adventure_stage(
            user_id, adv_id, stage_num, dust_reward, card_reward,
        )
        if result["already_done"]:
            return None

        return {
            "dust": result["dust"],
            "cards": result["cards"],
        }

    def receive_response(self, player_team: int, response: bytes):
        """Oyuncudan gelen yanıtı motora aktarmak için kaydet."""
        if player_team != self._pending_player:
            return

        self._pending_response = response
        self._response_event.set()

    def _cleanup(self):
        """Düello kaynaklarını temizle."""
        if self._duel is not None:
            self._core.destroy_duel(self._duel)
            self._duel = None
        self._running = False
        if self.room.state != RoomState.FINISHED:
            self.room.state = RoomState.FINISHED
