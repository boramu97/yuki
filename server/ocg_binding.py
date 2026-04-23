# Yuki — Browser-Based Duel Game
# Copyright (C) 2026 Yuki Contributors
# SPDX-License-Identifier: AGPL-3.0-or-later
#
# ocg_binding.py — OCGCore C++ motorunu Python'dan çağırmak için ctypes sarmalama
#
# Bu dosya, ocgcore.dll (Windows) veya libocgcore.so (Linux) içindeki
# tüm fonksiyonları Python fonksiyonlarına çevirir. Motor binary konuşur,
# biz bu katmanda sadece C fonksiyonlarını çağırıp ham veriyi alıyoruz.
# Mesaj ayrıştırma ayrı bir dosyada (message_parser.py) yapılacak.

import ctypes
import ctypes.util
import os
import platform
import struct
from ctypes import (
    CFUNCTYPE, POINTER,
    Structure,
    c_char_p, c_int, c_int32, c_uint8, c_uint16, c_uint32, c_uint64,
    c_void_p,
    byref, cast,
)
from pathlib import Path


# ---------------------------------------------------------------------------
# Sabitler (ocgapi_constants.h'den)
# ---------------------------------------------------------------------------

# Düello durumları — OCG_DuelProcess() dönüş değerleri
DUEL_STATUS_END       = 0   # Düello bitti
DUEL_STATUS_AWAITING  = 1   # Oyuncudan yanıt bekleniyor
DUEL_STATUS_CONTINUE  = 2   # Motor çalışmaya devam edebilir

# Düello oluşturma durumları — OCG_CreateDuel() dönüş değerleri
DUEL_CREATION_SUCCESS             = 0
DUEL_CREATION_NO_OUTPUT           = 1
DUEL_CREATION_NOT_CREATED         = 2
DUEL_CREATION_NULL_DATA_READER    = 3
DUEL_CREATION_NULL_SCRIPT_READER  = 4
DUEL_CREATION_INCOMPATIBLE_LUA    = 5
DUEL_CREATION_NULL_RNG_SEED       = 6

# Kart konumları (bölgeler)
LOCATION_DECK    = 0x01
LOCATION_HAND    = 0x02
LOCATION_MZONE   = 0x04    # Canavar Bölgesi
LOCATION_SZONE   = 0x08    # Büyü/Tuzak Bölgesi
LOCATION_GRAVE   = 0x10    # Mezarlık
LOCATION_REMOVED = 0x20    # Sürgün Bölgesi
LOCATION_EXTRA   = 0x40    # Ekstra Deste (Fusion)
LOCATION_OVERLAY = 0x80
LOCATION_ONFIELD = LOCATION_MZONE | LOCATION_SZONE

# Kart pozisyonları
POS_FACEUP_ATTACK    = 0x1   # Yüzü açık saldırı
POS_FACEDOWN_ATTACK  = 0x2   # Yüzü kapalı saldırı
POS_FACEUP_DEFENSE   = 0x4   # Yüzü açık savunma
POS_FACEDOWN_DEFENSE = 0x8   # Yüzü kapalı savunma (set)
POS_FACEUP   = POS_FACEUP_ATTACK | POS_FACEUP_DEFENSE
POS_FACEDOWN = POS_FACEDOWN_ATTACK | POS_FACEDOWN_DEFENSE
POS_ATTACK   = POS_FACEUP_ATTACK | POS_FACEDOWN_ATTACK
POS_DEFENSE  = POS_FACEUP_DEFENSE | POS_FACEDOWN_DEFENSE

# Kart tipleri
TYPE_MONSTER     = 0x1
TYPE_SPELL       = 0x2
TYPE_TRAP        = 0x4
TYPE_NORMAL      = 0x10
TYPE_EFFECT      = 0x20
TYPE_FUSION      = 0x40
TYPE_RITUAL      = 0x80
TYPE_TRAPMONSTER = 0x100
TYPE_SPIRIT      = 0x200
TYPE_UNION       = 0x400
TYPE_GEMINI      = 0x800
TYPE_TUNER       = 0x1000
TYPE_SYNCHRO     = 0x2000
TYPE_TOKEN       = 0x4000
TYPE_QUICKPLAY   = 0x10000
TYPE_CONTINUOUS  = 0x20000
TYPE_EQUIP       = 0x40000
TYPE_FIELD       = 0x80000
TYPE_COUNTER     = 0x100000
TYPE_FLIP        = 0x200000
TYPE_TOON        = 0x400000
TYPE_XYZ         = 0x800000
TYPE_PENDULUM    = 0x1000000
TYPE_LINK        = 0x4000000

# Özellikler (Attribute)
ATTRIBUTE_EARTH  = 0x01
ATTRIBUTE_WATER  = 0x02
ATTRIBUTE_FIRE   = 0x04
ATTRIBUTE_WIND   = 0x08
ATTRIBUTE_LIGHT  = 0x10
ATTRIBUTE_DARK   = 0x20
ATTRIBUTE_DIVINE = 0x40

# Irklar (Race) — Klasik/GX dönemindekiler
RACE_WARRIOR      = 0x1
RACE_SPELLCASTER  = 0x2
RACE_FAIRY        = 0x4
RACE_FIEND        = 0x8
RACE_ZOMBIE       = 0x10
RACE_MACHINE      = 0x20
RACE_AQUA         = 0x40
RACE_PYRO         = 0x80
RACE_ROCK         = 0x100
RACE_WINGEDBEAST  = 0x200
RACE_PLANT        = 0x400
RACE_INSECT       = 0x800
RACE_THUNDER      = 0x1000
RACE_DRAGON       = 0x2000
RACE_BEAST        = 0x4000
RACE_BEASTWARRIOR = 0x8000
RACE_DINOSAUR     = 0x10000
RACE_FISH         = 0x20000
RACE_SEASERPENT   = 0x40000
RACE_REPTILE      = 0x80000
RACE_DIVINE       = 0x200000

# Düello fazları
PHASE_DRAW         = 0x01
PHASE_STANDBY      = 0x02
PHASE_MAIN1        = 0x04
PHASE_BATTLE_START = 0x08
PHASE_BATTLE_STEP  = 0x10
PHASE_DAMAGE       = 0x20
PHASE_DAMAGE_CAL   = 0x40
PHASE_BATTLE       = 0x80
PHASE_MAIN2        = 0x100
PHASE_END          = 0x200

# Düello modu bayrakları — Klasik/GX dönemi için MR1 veya MR2
DUEL_1ST_TURN_DRAW          = 0x200
DUEL_1_FACEUP_FIELD         = 0x400
DUEL_SPSUMMON_ONCE_OLD_NEGATE = 0x40000
DUEL_RETURN_TO_DECK_TRIGGERS  = 0x10000
DUEL_CANNOT_SUMMON_OATH_OLD   = 0x80000
DUEL_OCG_OBSOLETE_IGNITION    = 0x100
DUEL_MODE_MR1 = (
    DUEL_OCG_OBSOLETE_IGNITION | DUEL_1ST_TURN_DRAW |
    DUEL_1_FACEUP_FIELD | DUEL_SPSUMMON_ONCE_OLD_NEGATE |
    DUEL_RETURN_TO_DECK_TRIGGERS | DUEL_CANNOT_SUMMON_OATH_OLD
)
DUEL_MODE_MR2 = (
    DUEL_1ST_TURN_DRAW | DUEL_1_FACEUP_FIELD |
    DUEL_SPSUMMON_ONCE_OLD_NEGATE | DUEL_RETURN_TO_DECK_TRIGGERS |
    DUEL_CANNOT_SUMMON_OATH_OLD
)

# Sorgu bayrakları — kart bilgisi sorgularken hangi alanları istiyoruz
QUERY_CODE         = 0x1
QUERY_POSITION     = 0x2
QUERY_ALIAS        = 0x4
QUERY_TYPE         = 0x8
QUERY_LEVEL        = 0x10
QUERY_RANK         = 0x20
QUERY_ATTRIBUTE    = 0x40
QUERY_RACE         = 0x80
QUERY_ATTACK       = 0x100
QUERY_DEFENSE      = 0x200
QUERY_BASE_ATTACK  = 0x400
QUERY_BASE_DEFENSE = 0x800
QUERY_REASON       = 0x1000
QUERY_REASON_CARD  = 0x2000
QUERY_EQUIP_CARD   = 0x4000
QUERY_TARGET_CARD  = 0x8000
QUERY_OVERLAY_CARD = 0x10000
QUERY_COUNTERS     = 0x20000
QUERY_OWNER        = 0x40000
QUERY_STATUS       = 0x80000
QUERY_IS_PUBLIC    = 0x100000
QUERY_LSCALE       = 0x200000
QUERY_RSCALE       = 0x400000
QUERY_LINK         = 0x800000
QUERY_END          = 0x80000000

# Mesaj tipleri — motordan gelen binary mesajların ilk byte'ı
MSG_RETRY              = 1
MSG_HINT               = 2
MSG_WAITING            = 3
MSG_START              = 4
MSG_WIN                = 5
MSG_UPDATE_DATA        = 6
MSG_UPDATE_CARD        = 7
MSG_SELECT_BATTLECMD   = 10
MSG_SELECT_IDLECMD     = 11
MSG_SELECT_EFFECTYN    = 12
MSG_SELECT_YESNO       = 13
MSG_SELECT_OPTION      = 14
MSG_SELECT_CARD        = 15
MSG_SELECT_CHAIN       = 16
MSG_SELECT_PLACE       = 18
MSG_SELECT_POSITION    = 19
MSG_SELECT_TRIBUTE     = 20
MSG_SORT_CHAIN         = 21
MSG_SELECT_COUNTER     = 22
MSG_SELECT_SUM         = 23
MSG_SELECT_DISFIELD    = 24
MSG_SORT_CARD          = 25
MSG_SELECT_UNSELECT_CARD = 26
MSG_CONFIRM_DECKTOP    = 30
MSG_CONFIRM_CARDS      = 31
MSG_SHUFFLE_DECK       = 32
MSG_SHUFFLE_HAND       = 33
MSG_SHUFFLE_SET_CARD   = 36
MSG_NEW_TURN           = 40
MSG_NEW_PHASE          = 41
MSG_MOVE               = 50
MSG_POS_CHANGE         = 53
MSG_SET                = 54
MSG_SWAP               = 55
MSG_FIELD_DISABLED     = 56
MSG_SUMMONING          = 60
MSG_SUMMONED           = 61
MSG_SPSUMMONING        = 62
MSG_SPSUMMONED         = 63
MSG_FLIPSUMMONING      = 64
MSG_FLIPSUMMONED       = 65
MSG_CHAINING           = 70
MSG_CHAINED            = 71
MSG_CHAIN_SOLVING      = 72
MSG_CHAIN_SOLVED       = 73
MSG_CHAIN_END          = 74
MSG_CHAIN_NEGATED      = 75
MSG_CHAIN_DISABLED     = 76
MSG_CARD_SELECTED      = 80
MSG_RANDOM_SELECTED    = 81
MSG_BECOME_TARGET      = 83
MSG_DRAW               = 90
MSG_DAMAGE             = 91
MSG_RECOVER            = 92
MSG_EQUIP              = 93
MSG_LPUPDATE           = 94
MSG_UNEQUIP            = 95
MSG_CARD_TARGET        = 96
MSG_CANCEL_TARGET      = 97
MSG_PAY_LPCOST         = 100
MSG_ADD_COUNTER        = 101
MSG_REMOVE_COUNTER     = 102
MSG_ATTACK             = 110
MSG_BATTLE             = 111
MSG_ATTACK_DISABLED    = 112
MSG_DAMAGE_STEP_START  = 113
MSG_DAMAGE_STEP_END    = 114
MSG_TOSS_COIN          = 130
MSG_TOSS_DICE          = 131
MSG_ROCK_PAPER_SCISSORS = 132
MSG_HAND_RES           = 133
MSG_ANNOUNCE_RACE      = 140
MSG_ANNOUNCE_ATTRIB    = 141
MSG_ANNOUNCE_CARD      = 142
MSG_ANNOUNCE_NUMBER    = 143
MSG_CARD_HINT          = 160
MSG_MATCH_KILL         = 170
MSG_REMOVE_CARDS       = 190

# Mesaj tipi isimleri — hata ayıklama için
MSG_NAMES = {v: k for k, v in globals().items() if k.startswith("MSG_")}

# Log tipleri
LOG_TYPE_ERROR       = 0
LOG_TYPE_FROM_SCRIPT = 1
LOG_TYPE_FOR_DEBUG   = 2
LOG_TYPE_UNDEFINED   = 3

# Oyuncu sabitleri
PLAYER_NONE = 2
PLAYER_ALL  = 3


# ---------------------------------------------------------------------------
# ctypes Yapıları (Struct) — C header'lardaki struct'ların Python karşılığı
# ---------------------------------------------------------------------------

class OCG_CardData(Structure):
    """Bir kartın statik verisi — veritabanından okunur, callback ile motora verilir."""
    _fields_ = [
        ("code", c_uint32),          # Kart kodu (ör. 89631139 = Blue-Eyes)
        ("alias", c_uint32),         # Alternatif kart kodu (0 = yok)
        ("setcodes", POINTER(c_uint16)),  # Arketip kodları (null-terminated dizi)
        ("type", c_uint32),          # Kart tipi (TYPE_MONSTER | TYPE_NORMAL vs.)
        ("level", c_uint32),         # Seviye (veya Rank/Link rating)
        ("attribute", c_uint32),     # Özellik (ATTRIBUTE_DARK vs.)
        ("race", c_uint64),          # Irk (RACE_DRAGON vs.)
        ("attack", c_int32),         # ATK değeri (-1 = ?)
        ("defense", c_int32),        # DEF değeri (-1 = ?)
        ("lscale", c_uint32),        # Pendulum sol ölçek (0 = yok)
        ("rscale", c_uint32),        # Pendulum sağ ölçek (0 = yok)
        ("link_marker", c_uint32),   # Link ok yönleri (0 = yok)
    ]


class OCG_Player(Structure):
    """Bir oyuncunun başlangıç ayarları."""
    _fields_ = [
        ("startingLP", c_uint32),         # Başlangıç yaşam puanı (genelde 8000)
        ("startingDrawCount", c_uint32),  # İlk çekiş sayısı (genelde 5)
        ("drawCountPerTurn", c_uint32),   # Tur başı çekiş (genelde 1)
    ]


# Callback fonksiyon tipleri — motor bu fonksiyonları çağırarak bizden veri ister
#   OCG_DataReader(payload, code, data_ptr)  → kartın verisini data_ptr'ye yaz
#   OCG_DataReaderDone(payload, data_ptr)    → kart okuma bitti, temizlik yap
#   OCG_ScriptReader(payload, duel, name)    → script yükle, başarılıysa 1 döndür
#   OCG_LogHandler(payload, string, type)    → log mesajını işle
OCG_DataReader     = CFUNCTYPE(None, c_void_p, c_uint32, POINTER(OCG_CardData))
OCG_DataReaderDone = CFUNCTYPE(None, c_void_p, POINTER(OCG_CardData))
OCG_ScriptReader   = CFUNCTYPE(c_int, c_void_p, c_void_p, c_char_p)
OCG_LogHandler     = CFUNCTYPE(None, c_void_p, c_char_p, c_int)


class OCG_DuelOptions(Structure):
    """Düello oluşturma seçenekleri — callback fonksiyonları dahil."""
    _fields_ = [
        ("seed", c_uint64 * 4),           # 4x64-bit rastgele tohum
        ("flags", c_uint64),              # Düello modu bayrakları
        ("team1", OCG_Player),            # Oyuncu 1 ayarları
        ("team2", OCG_Player),            # Oyuncu 2 ayarları
        ("cardReader", OCG_DataReader),   # Kart verisi callback
        ("payload1", c_void_p),           # cardReader'a geçirilen veri
        ("scriptReader", OCG_ScriptReader),  # Script yükleme callback
        ("payload2", c_void_p),           # scriptReader'a geçirilen veri
        ("logHandler", OCG_LogHandler),   # Log callback
        ("payload3", c_void_p),           # logHandler'a geçirilen veri
        ("cardReaderDone", OCG_DataReaderDone),  # Okuma bitti callback
        ("payload4", c_void_p),           # cardReaderDone'a geçirilen veri
        ("enableUnsafeLibraries", c_uint8),  # Güvensiz Lua kütüphaneleri (0)
    ]


class OCG_NewCardInfo(Structure):
    """Düelloya yeni kart eklerken kullanılır."""
    _fields_ = [
        ("team", c_uint8),     # Hangi takım (0 veya 1)
        ("duelist", c_uint8),  # Orijinal sahip indeksi
        ("code", c_uint32),    # Kart kodu
        ("con", c_uint8),      # Kontrol eden oyuncu (genelde team ile aynı)
        ("loc", c_uint32),     # Konum (LOCATION_DECK vs.)
        ("seq", c_uint32),     # Sıra numarası (0'dan başlar)
        ("pos", c_uint32),     # Pozisyon (POS_FACEDOWN_DEFENSE vs.)
    ]


class OCG_QueryInfo(Structure):
    """Kart sorgulama parametreleri."""
    _fields_ = [
        ("flags", c_uint32),        # Hangi alanlar isteniyor (QUERY_CODE | QUERY_ATTACK...)
        ("con", c_uint8),           # Kontrol eden oyuncu
        ("loc", c_uint32),          # Konum
        ("seq", c_uint32),          # Sıra numarası
        ("overlay_seq", c_uint32),  # Overlay sıra numarası
    ]


# ---------------------------------------------------------------------------
# OCGCore Kütüphane Yükleyici
# ---------------------------------------------------------------------------

def _find_library() -> str:
    """OCGCore kütüphanesinin yolunu bulur.

    Arama sırası:
      1. bin/ocgcore.dll (veya .so) — proje dizini
      2. Çalışma dizinindeki ocgcore.dll
      3. Sistem PATH'i
    """
    # Proje kök dizini: bu dosyanın bir üst klasörü
    project_root = Path(__file__).resolve().parent.parent

    if platform.system() == "Windows":
        lib_name = "ocgcore.dll"
    elif platform.system() == "Darwin":
        lib_name = "libocgcore.dylib"
    else:
        lib_name = "libocgcore.so"

    # 1. Proje bin/ klasörü
    candidate = project_root / "bin" / lib_name
    if candidate.exists():
        return str(candidate)

    # 2. Çalışma dizini
    candidate = Path.cwd() / lib_name
    if candidate.exists():
        return str(candidate)

    # 3. Sistem
    found = ctypes.util.find_library("ocgcore")
    if found:
        return found

    raise FileNotFoundError(
        f"{lib_name} bulunamadı. Önce OCGCore'u derleyin: bash tools/build_core.sh"
    )


def load_library(path: str | None = None) -> ctypes.CDLL:
    """OCGCore kütüphanesini yükler ve fonksiyon imzalarını tanımlar.

    Args:
        path: Kütüphane dosyasının tam yolu. None ise otomatik arar.

    Returns:
        Fonksiyon imzaları tanımlanmış ctypes.CDLL nesnesi.
    """
    if path is None:
        path = _find_library()

    lib = ctypes.CDLL(path)

    # --- OCG_GetVersion ---
    lib.OCG_GetVersion.argtypes = [POINTER(c_int), POINTER(c_int)]
    lib.OCG_GetVersion.restype = None

    # --- OCG_CreateDuel ---
    lib.OCG_CreateDuel.argtypes = [POINTER(c_void_p), POINTER(OCG_DuelOptions)]
    lib.OCG_CreateDuel.restype = c_int

    # --- OCG_DestroyDuel ---
    lib.OCG_DestroyDuel.argtypes = [c_void_p]
    lib.OCG_DestroyDuel.restype = None

    # --- OCG_DuelNewCard ---
    lib.OCG_DuelNewCard.argtypes = [c_void_p, POINTER(OCG_NewCardInfo)]
    lib.OCG_DuelNewCard.restype = None

    # --- OCG_StartDuel ---
    lib.OCG_StartDuel.argtypes = [c_void_p]
    lib.OCG_StartDuel.restype = None

    # --- OCG_DuelProcess ---
    lib.OCG_DuelProcess.argtypes = [c_void_p]
    lib.OCG_DuelProcess.restype = c_int

    # --- OCG_DuelGetMessage ---
    lib.OCG_DuelGetMessage.argtypes = [c_void_p, POINTER(c_uint32)]
    lib.OCG_DuelGetMessage.restype = c_void_p

    # --- OCG_DuelSetResponse ---
    lib.OCG_DuelSetResponse.argtypes = [c_void_p, c_void_p, c_uint32]
    lib.OCG_DuelSetResponse.restype = None

    # --- OCG_LoadScript ---
    lib.OCG_LoadScript.argtypes = [c_void_p, c_char_p, c_uint32, c_char_p]
    lib.OCG_LoadScript.restype = c_int

    # --- OCG_DuelQueryCount ---
    lib.OCG_DuelQueryCount.argtypes = [c_void_p, c_uint8, c_uint32]
    lib.OCG_DuelQueryCount.restype = c_uint32

    # --- OCG_DuelQuery ---
    lib.OCG_DuelQuery.argtypes = [c_void_p, POINTER(c_uint32), POINTER(OCG_QueryInfo)]
    lib.OCG_DuelQuery.restype = c_void_p

    # --- OCG_DuelQueryLocation ---
    lib.OCG_DuelQueryLocation.argtypes = [c_void_p, POINTER(c_uint32), POINTER(OCG_QueryInfo)]
    lib.OCG_DuelQueryLocation.restype = c_void_p

    # --- OCG_DuelQueryField ---
    lib.OCG_DuelQueryField.argtypes = [c_void_p, POINTER(c_uint32)]
    lib.OCG_DuelQueryField.restype = c_void_p

    return lib


# ---------------------------------------------------------------------------
# OCGCore Python Sarmalama Sınıfı
# ---------------------------------------------------------------------------

class OCGCore:
    """OCGCore motorunun Python arayüzü.

    Kullanım:
        core = OCGCore()
        print(f"Motor versiyonu: {core.get_version()}")
        duel = core.create_duel(card_reader_fn, script_reader_fn)
        core.add_card(duel, team=0, code=89631139, loc=LOCATION_DECK)
        core.start_duel(duel)
        status = core.process(duel)
        ...
        core.destroy_duel(duel)
    """

    def __init__(self, lib_path: str | None = None):
        self._lib = load_library(lib_path)
        # Callback referanslarını sakla — garbage collector'ın silmesini engelle
        self._callbacks: dict = {}

    def get_version(self) -> tuple[int, int]:
        """Motor versiyonunu döndürür: (major, minor)."""
        major = c_int(0)
        minor = c_int(0)
        self._lib.OCG_GetVersion(byref(major), byref(minor))
        return (major.value, minor.value)

    def create_duel(
        self,
        card_reader,
        script_reader,
        card_reader_done=None,
        log_handler=None,
        starting_lp: int = 8000,
        starting_draw: int = 5,
        draw_per_turn: int = 1,
        flags: int = DUEL_MODE_MR2,
        seed: tuple[int, int, int, int] | None = None,
    ) -> c_void_p:
        """Yeni bir düello oluşturur.

        Args:
            card_reader:  Kart verisi callback — card_reader(payload, code, data_ptr)
            script_reader: Script yükleme callback — script_reader(payload, duel, name) -> int
            card_reader_done: (opsiyonel) Okuma bitti callback
            log_handler:  (opsiyonel) Log callback
            starting_lp:  Başlangıç LP (varsayılan 8000)
            starting_draw: İlk çekiş sayısı (varsayılan 5)
            draw_per_turn: Tur başı çekiş (varsayılan 1)
            flags:  Düello modu bayrakları (varsayılan MR2 — GX dönemi)
            seed:   4 adet 64-bit rastgele tohum

        Returns:
            Düello nesnesi (opaque pointer)
        """
        if seed is None:
            # Rastgele tohum üret
            seed = tuple(
                int.from_bytes(os.urandom(8), "little") for _ in range(4)
            )

        # Callback'leri ctypes fonksiyonlarına çevir ve sakla
        cb_card_reader = OCG_DataReader(card_reader)
        cb_script_reader = OCG_ScriptReader(script_reader)

        if card_reader_done is not None:
            cb_card_reader_done = OCG_DataReaderDone(card_reader_done)
        else:
            cb_card_reader_done = OCG_DataReaderDone(lambda p, d: None)

        if log_handler is not None:
            cb_log_handler = OCG_LogHandler(log_handler)
        else:
            cb_log_handler = OCG_LogHandler(lambda p, s, t: None)

        # Seçenekleri doldur
        options = OCG_DuelOptions()
        for i in range(4):
            options.seed[i] = seed[i]
        options.flags = flags

        options.team1.startingLP = starting_lp
        options.team1.startingDrawCount = starting_draw
        options.team1.drawCountPerTurn = draw_per_turn

        options.team2.startingLP = starting_lp
        options.team2.startingDrawCount = starting_draw
        options.team2.drawCountPerTurn = draw_per_turn

        options.cardReader = cb_card_reader
        options.payload1 = None
        options.scriptReader = cb_script_reader
        options.payload2 = None
        options.logHandler = cb_log_handler
        options.payload3 = None
        options.cardReaderDone = cb_card_reader_done
        options.payload4 = None
        options.enableUnsafeLibraries = 0

        # Düello oluştur
        duel = c_void_p()
        status = self._lib.OCG_CreateDuel(byref(duel), byref(options))

        if status != DUEL_CREATION_SUCCESS:
            error_names = {
                1: "NO_OUTPUT", 2: "NOT_CREATED",
                3: "NULL_DATA_READER", 4: "NULL_SCRIPT_READER",
                5: "INCOMPATIBLE_LUA", 6: "NULL_RNG_SEED",
            }
            name = error_names.get(status, f"UNKNOWN({status})")
            raise RuntimeError(f"Düello oluşturulamadı: {name}")

        # Callback referanslarını sakla (GC'nin silmemesi için)
        duel_id = duel.value
        self._callbacks[duel_id] = {
            "card_reader": cb_card_reader,
            "script_reader": cb_script_reader,
            "card_reader_done": cb_card_reader_done,
            "log_handler": cb_log_handler,
            "options": options,  # struct da referans tutsun
        }

        return duel

    def destroy_duel(self, duel: c_void_p) -> None:
        """Düelloyu yok eder ve kaynakları serbest bırakır."""
        duel_id = duel.value
        self._lib.OCG_DestroyDuel(duel)
        self._callbacks.pop(duel_id, None)

    def add_card(
        self,
        duel: c_void_p,
        team: int,
        code: int,
        loc: int,
        seq: int = 0,
        pos: int = POS_FACEDOWN_DEFENSE,
        con: int | None = None,
        duelist: int = 0,
    ) -> None:
        """Düelloya bir kart ekler.

        Args:
            duel:  Düello nesnesi
            team:  Takım (0 veya 1)
            code:  Kart kodu
            loc:   Konum (LOCATION_DECK, LOCATION_EXTRA vs.)
            seq:   Sıra numarası (varsayılan 0)
            pos:   Pozisyon (varsayılan yüzü kapalı savunma)
            con:   Kontrol eden (None ise team ile aynı)
            duelist: Orijinal sahip indeksi
        """
        if con is None:
            con = team

        info = OCG_NewCardInfo()
        info.team = team
        info.duelist = duelist
        info.code = code
        info.con = con
        info.loc = loc
        info.seq = seq
        info.pos = pos
        self._lib.OCG_DuelNewCard(duel, byref(info))

    def start_duel(self, duel: c_void_p) -> None:
        """Düelloyu başlatır. Kartlar eklendikten sonra çağrılır."""
        self._lib.OCG_StartDuel(duel)

    def process(self, duel: c_void_p) -> int:
        """Motoru bir adım ilerletir.

        Returns:
            DUEL_STATUS_END (0)       — düello bitti
            DUEL_STATUS_AWAITING (1)  — oyuncudan yanıt bekliyor
            DUEL_STATUS_CONTINUE (2)  — tekrar process() çağır
        """
        return self._lib.OCG_DuelProcess(duel)

    def get_message(self, duel: c_void_p) -> bytes:
        """Motorun ürettiği binary mesaj buffer'ını döndürür.

        Boş buffer → boş bytes.
        Mesajlar art arda sıralanmıştır, her biri:
          [uzunluk: uint32][mesaj_tipi: uint8][mesaj_verisi: değişken]
        """
        length = c_uint32(0)
        ptr = self._lib.OCG_DuelGetMessage(duel, byref(length))
        if length.value == 0 or ptr is None:
            return b""
        return ctypes.string_at(ptr, length.value)

    def set_response(self, duel: c_void_p, response: bytes) -> None:
        """Oyuncunun yanıtını motora gönderir.

        Args:
            duel:     Düello nesnesi
            response: Binary yanıt verisi
        """
        buf = ctypes.create_string_buffer(response)
        self._lib.OCG_DuelSetResponse(duel, buf, len(response))

    def load_script(self, duel: c_void_p, script: str, name: str) -> bool:
        """Bir Lua scriptini düelloya yükler.

        Args:
            duel:   Düello nesnesi
            script: Script içeriği (string)
            name:   Script dosya adı (ör. "c89631139.lua")

        Returns:
            True başarılı, False başarısız
        """
        script_bytes = script.encode("utf-8")
        name_bytes = name.encode("utf-8")
        result = self._lib.OCG_LoadScript(
            duel, script_bytes, len(script_bytes), name_bytes
        )
        return result != 0

    def query_count(self, duel: c_void_p, team: int, loc: int) -> int:
        """Belirli bir bölgedeki kart sayısını döndürür.

        Args:
            duel: Düello nesnesi
            team: Takım (0 veya 1)
            loc:  Konum (LOCATION_DECK, LOCATION_HAND vs.)
        """
        return self._lib.OCG_DuelQueryCount(duel, team, loc)

    def query(
        self,
        duel: c_void_p,
        con: int,
        loc: int,
        seq: int,
        flags: int = QUERY_CODE | QUERY_POSITION | QUERY_ATTACK | QUERY_DEFENSE,
        overlay_seq: int = 0,
    ) -> bytes:
        """Tek bir kartın bilgisini sorgular.

        Args:
            duel:        Düello nesnesi
            con:         Kontrol eden oyuncu
            loc:         Konum
            seq:         Sıra numarası
            flags:       İstenen alanlar
            overlay_seq: Overlay sırası

        Returns:
            Binary sorgu sonucu
        """
        info = OCG_QueryInfo()
        info.flags = flags
        info.con = con
        info.loc = loc
        info.seq = seq
        info.overlay_seq = overlay_seq

        length = c_uint32(0)
        ptr = self._lib.OCG_DuelQuery(duel, byref(length), byref(info))
        if length.value == 0 or ptr is None:
            return b""
        return ctypes.string_at(ptr, length.value)

    def query_location(
        self,
        duel: c_void_p,
        con: int,
        loc: int,
        flags: int = QUERY_CODE | QUERY_POSITION,
    ) -> bytes:
        """Bir bölgedeki tüm kartları sorgular.

        Args:
            duel:  Düello nesnesi
            con:   Kontrol eden oyuncu
            loc:   Konum (LOCATION_MZONE, LOCATION_HAND vs.)
            flags: İstenen alanlar
        """
        info = OCG_QueryInfo()
        info.flags = flags
        info.con = con
        info.loc = loc
        info.seq = 0
        info.overlay_seq = 0

        length = c_uint32(0)
        ptr = self._lib.OCG_DuelQueryLocation(duel, byref(length), byref(info))
        if length.value == 0 or ptr is None:
            return b""
        return ctypes.string_at(ptr, length.value)

    def query_field(self, duel: c_void_p) -> bytes:
        """Tüm oyun alanının durumunu sorgular."""
        length = c_uint32(0)
        ptr = self._lib.OCG_DuelQueryField(duel, byref(length))
        if length.value == 0 or ptr is None:
            return b""
        return ctypes.string_at(ptr, length.value)
