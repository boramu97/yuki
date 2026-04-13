# Yuki — Browser-Based Duel Game
# Copyright (C) 2026 Yuki Contributors
# SPDX-License-Identifier: AGPL-3.0-or-later
#
# card_database.py — SQLite kart veritabanını okuyucu
#
# EDOPro topluluğunun cards.cdb dosyasını okur. Bu dosya iki tablo içerir:
#   - datas: Kartların sayısal verileri (ATK, DEF, seviye, tür, ırk, özellik...)
#   - texts: Kartların metin verileri (isim, açıklama, efekt açıklamaları)
#
# Bu modül, OCGCore'un card_reader callback'i için veri sağlar.

import sqlite3
from pathlib import Path
from dataclasses import dataclass


@dataclass
class CardInfo:
    """Bir kartın tüm bilgilerini tutan yapı."""
    code: int          # Kart kodu (benzersiz ID, ör. 89631139 = Blue-Eyes)
    alias: int         # Alternatif kart kodu (0 = yok, farklıysa başka kartın resmi)
    setcodes: list[int]  # Arketip kodları listesi (boş olabilir)
    type: int          # Kart tipi bit maskesi (TYPE_MONSTER | TYPE_NORMAL vs.)
    level: int         # Seviye (1-12), üst byte'larda Pendulum scale olabilir
    attribute: int     # Özellik (ATTRIBUTE_DARK vs.)
    race: int          # Irk (RACE_DRAGON vs.)
    attack: int        # ATK değeri (-1 = ?)
    defense: int       # DEF değeri (-1 = ?)
    lscale: int        # Pendulum sol ölçek (Klasik/GX'te 0)
    rscale: int        # Pendulum sağ ölçek (Klasik/GX'te 0)
    link_marker: int   # Link ok yönleri (Klasik/GX'te 0)
    name: str          # Kartın adı
    desc: str          # Kartın açıklaması


class CardDatabase:
    """SQLite kart veritabanı okuyucu.

    Kullanım:
        db = CardDatabase("data/cards.cdb")
        card = db.get_card(89631139)  # Blue-Eyes White Dragon
        if card:
            print(f"{card.name}: ATK {card.attack} / DEF {card.defense}")
        db.close()
    """

    def __init__(self, db_path: str | Path):
        """Veritabanını açar.

        Args:
            db_path: cards.cdb dosyasının yolu
        """
        self._path = Path(db_path)
        if not self._path.exists():
            raise FileNotFoundError(f"Kart veritabanı bulunamadı: {self._path}")

        self._conn = sqlite3.connect(str(self._path))
        self._conn.row_factory = sqlite3.Row  # Sütun adıyla erişim
        self._cache: dict[int, CardInfo] = {}  # Kart önbelleği

    def close(self) -> None:
        """Veritabanı bağlantısını kapatır."""
        self._conn.close()

    def __enter__(self):
        return self

    def __exit__(self, *args):
        self.close()

    def _parse_setcodes(self, setcode_raw: int) -> list[int]:
        """setcode alanını arketip kodları listesine çevirir.

        EDOPro formatı: 64-bit integer, her 16-bit bir arketip kodu.
        Ör. 0x009500A6 → [0x0095, 0x00A6]
        """
        codes = []
        val = setcode_raw & 0xFFFFFFFFFFFFFFFF
        for _ in range(4):
            sc = val & 0xFFFF
            if sc != 0:
                codes.append(sc)
            val >>= 16
        return codes

    def get_card(self, code: int) -> CardInfo | None:
        """Kart koduna göre kart bilgisi döndürür.

        Sonuçlar önbelleğe alınır — aynı kart tekrar sorgulandığında
        veritabanına gitmez.

        Args:
            code: Kart kodu

        Returns:
            CardInfo nesnesi veya None (kart bulunamadıysa)
        """
        # Önbellekte var mı?
        if code in self._cache:
            return self._cache[code]

        cursor = self._conn.cursor()

        # datas tablosundan sayısal verileri çek
        cursor.execute("SELECT * FROM datas WHERE id = ?", (code,))
        data_row = cursor.fetchone()
        if data_row is None:
            return None

        # texts tablosundan metin verilerini çek
        cursor.execute("SELECT * FROM texts WHERE id = ?", (code,))
        text_row = cursor.fetchone()

        name = text_row["name"] if text_row else f"Card #{code}"
        desc = text_row["desc"] if text_row else ""

        # setcode alanını parse et
        setcodes = self._parse_setcodes(data_row["setcode"])

        # level alanından gerçek seviye ve Pendulum scale'leri çıkar
        level_raw = data_row["level"]
        level = level_raw & 0xFF          # Alt 8 bit: seviye/rank
        lscale = (level_raw >> 24) & 0xFF  # Üst byte: sol ölçek
        rscale = (level_raw >> 16) & 0xFF  # İkinci üst byte: sağ ölçek

        card = CardInfo(
            code=data_row["id"],
            alias=data_row["alias"],
            setcodes=setcodes,
            type=data_row["type"],
            level=level,
            attribute=data_row["attribute"],
            race=data_row["race"],
            attack=data_row["atk"],
            defense=data_row["def"],
            lscale=lscale,
            rscale=rscale,
            link_marker=0,  # Klasik/GX döneminde Link yok
            name=name,
            desc=desc,
        )

        self._cache[code] = card
        return card

    def search_by_name(self, name: str, limit: int = 20) -> list[CardInfo]:
        """Kart adına göre arama yapar (LIKE).

        Args:
            name:  Aranacak isim (kısmi eşleşme)
            limit: Maksimum sonuç sayısı

        Returns:
            Eşleşen kartların listesi
        """
        cursor = self._conn.cursor()
        cursor.execute(
            "SELECT id FROM texts WHERE name LIKE ? LIMIT ?",
            (f"%{name}%", limit),
        )
        results = []
        for row in cursor.fetchall():
            card = self.get_card(row["id"])
            if card:
                results.append(card)
        return results

    def get_all_codes(self) -> list[int]:
        """Veritabanındaki tüm kart kodlarını döndürür."""
        cursor = self._conn.cursor()
        cursor.execute("SELECT id FROM datas")
        return [row["id"] for row in cursor.fetchall()]

    def count(self) -> int:
        """Veritabanındaki toplam kart sayısını döndürür."""
        cursor = self._conn.cursor()
        cursor.execute("SELECT COUNT(*) as cnt FROM datas")
        return cursor.fetchone()["cnt"]
