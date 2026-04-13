# Yuki — Browser-Based Duel Game
# Copyright (C) 2026 Yuki Contributors
# SPDX-License-Identifier: AGPL-3.0-or-later
#
# config.py — Proje ayarları ve dosya yolları

from pathlib import Path

# Proje kök dizini (bu dosyanın iki üst klasörü)
PROJECT_ROOT = Path(__file__).resolve().parent.parent

# OCGCore kütüphanesi
CORE_LIB_PATH = PROJECT_ROOT / "bin" / "ocgcore.dll"

# Kart veritabanı
CARD_DB_PATH = PROJECT_ROOT / "data" / "cards.cdb"

# Lua script dizini
SCRIPT_DIR = PROJECT_ROOT / "data" / "script"

# Varsayılan düello ayarları
DEFAULT_LP = 8000
DEFAULT_STARTING_DRAW = 5
DEFAULT_DRAW_PER_TURN = 1
