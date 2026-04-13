# Yuki — Browser-Based Duel Game
# Copyright (C) 2026 Yuki Contributors
# SPDX-License-Identifier: AGPL-3.0-or-later
#
# room.py — Oda ve oyuncu yönetimi
#
# Her oda iki oyuncu barındırır. Oyuncu bir oda oluşturur veya mevcut bir
# odaya katılır. İki oyuncu hazır olunca düello başlar.

import asyncio
import secrets
from dataclasses import dataclass, field
from enum import Enum


class RoomState(Enum):
    WAITING = "waiting"      # Bir oyuncu bekliyor
    READY = "ready"          # İki oyuncu hazır, düello başlayabilir
    DUELING = "dueling"      # Düello devam ediyor
    FINISHED = "finished"    # Düello bitti


@dataclass
class Player:
    """Bağlı bir oyuncuyu temsil eder."""
    ws: object              # WebSocket bağlantısı
    name: str               # Oyuncu adı
    team: int = -1          # Takım (0 veya 1), oda atayacak
    deck: list[int] = field(default_factory=list)  # Deste (kart kodları)
    ready: bool = False     # Düelloya hazır mı

    async def send(self, data: dict):
        """Oyuncuya JSON mesaj gönderir."""
        import json
        try:
            await self.ws.send(json.dumps(data))
        except Exception:
            pass  # Bağlantı kopmuş olabilir

    @property
    def connected(self) -> bool:
        try:
            return self.ws.open
        except AttributeError:
            return False


@dataclass
class Room:
    """İki oyuncunun düello yaptığı oda."""
    room_id: str
    state: RoomState = RoomState.WAITING
    players: list[Player] = field(default_factory=list)
    duel_manager: object = None  # DuelManager atanacak

    @property
    def is_full(self) -> bool:
        return len(self.players) >= 2

    @property
    def player_count(self) -> int:
        return len(self.players)

    def add_player(self, player: Player) -> bool:
        """Odaya oyuncu ekler. Başarılıysa True döner."""
        if self.is_full:
            return False
        player.team = len(self.players)  # İlk oyuncu 0, ikinci 1
        self.players.append(player)
        if self.is_full:
            self.state = RoomState.READY
        return True

    def remove_player(self, player: Player):
        """Oyuncuyu odadan çıkarır."""
        if player in self.players:
            self.players.remove(player)
        if not self.players:
            self.state = RoomState.FINISHED
        elif self.state == RoomState.READY:
            self.state = RoomState.WAITING

    def get_player(self, team: int) -> Player | None:
        """Takım numarasına göre oyuncu döndürür."""
        for p in self.players:
            if p.team == team:
                return p
        return None

    def get_opponent(self, player: Player) -> Player | None:
        """Rakip oyuncuyu döndürür."""
        for p in self.players:
            if p is not player:
                return p
        return None

    async def broadcast(self, data: dict, exclude: Player | None = None):
        """Odadaki tüm oyunculara mesaj gönderir."""
        for p in self.players:
            if p is not exclude:
                await p.send(data)


class RoomManager:
    """Tüm odaları yöneten merkezi sınıf."""

    def __init__(self):
        self._rooms: dict[str, Room] = {}

    def create_room(self) -> Room:
        """Yeni bir oda oluşturur, benzersiz ID ile."""
        room_id = secrets.token_hex(4)  # 8 karakter hex
        while room_id in self._rooms:
            room_id = secrets.token_hex(4)
        room = Room(room_id=room_id)
        self._rooms[room_id] = room
        return room

    def get_room(self, room_id: str) -> Room | None:
        return self._rooms.get(room_id)

    def remove_room(self, room_id: str):
        self._rooms.pop(room_id, None)

    def find_waiting_room(self) -> Room | None:
        """Bekleyen (bir oyunculu) oda bulur — hızlı eşleştirme için."""
        for room in self._rooms.values():
            if room.state == RoomState.WAITING:
                return room
        return None

    def list_rooms(self) -> list[dict]:
        """Oda listesini döndürür (lobi için)."""
        return [
            {
                "room_id": r.room_id,
                "state": r.state.value,
                "players": [p.name for p in r.players],
            }
            for r in self._rooms.values()
            if r.state in (RoomState.WAITING, RoomState.READY, RoomState.DUELING)
        ]

    def cleanup_finished(self):
        """Bitmiş odaları temizler."""
        to_remove = [
            rid for rid, r in self._rooms.items()
            if r.state == RoomState.FINISHED
        ]
        for rid in to_remove:
            del self._rooms[rid]
