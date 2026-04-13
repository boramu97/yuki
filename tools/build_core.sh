#!/bin/bash
# OCGCore Derleme Scripti (Windows - MinGW)
# Kullanım: bash tools/build_core.sh
#
# Gereksinimler:
#   - MinGW-w64 (g++ derleyici)
#   - premake5
#
# Bu script OCGCore'u shared library (DLL) olarak derler
# ve bin/ klasörüne kopyalar.

set -e

# Proje kök dizini
PROJECT_ROOT="$(cd "$(dirname "$0")/.." && pwd)"
OCGCORE_DIR="$PROJECT_ROOT/ocgcore"
BIN_DIR="$PROJECT_ROOT/bin"

# MinGW yolu (winget ile kurulmuş)
MINGW_BIN="/c/Users/boram/AppData/Local/Microsoft/WinGet/Packages/BrechtSanders.WinLibs.POSIX.UCRT_Microsoft.Winget.Source_8wekyb3d8bbwe/mingw64/bin"

# premake5 yolu — yoksa indir
PREMAKE5="/tmp/premake5/premake5.exe"
if [ ! -f "$PREMAKE5" ]; then
    echo "premake5 bulunamadi, indiriliyor..."
    mkdir -p /tmp/premake5
    curl -sL "https://github.com/premake/premake-core/releases/download/v5.0.0-beta6/premake-5.0.0-beta6-windows.zip" -o /tmp/premake5.zip
    unzip -o /tmp/premake5.zip -d /tmp/premake5
fi

# PATH'e MinGW ekle
export PATH="$MINGW_BIN:$PATH"

echo "=== OCGCore Derleme ==="
echo "g++ versiyonu: $(g++ --version | head -1)"

# Lua submodule kontrolu
if [ ! -f "$OCGCORE_DIR/lua/src/lapi.c" ]; then
    echo "Lua submodule eksik, cekiliyor..."
    cd "$OCGCORE_DIR"
    git submodule update --init --recursive
fi

# Makefile olustur
echo "Makefile olusturuluyor..."
cd "$OCGCORE_DIR"
"$PREMAKE5" gmake2

# Derle
echo "Derleniyor (Release x64)..."
cd "$OCGCORE_DIR/build"
mingw32-make config=release_x64 ocgcoreshared -j$(nproc)

# Kopyala
echo "DLL kopyalaniyor..."
mkdir -p "$BIN_DIR"
cp "$OCGCORE_DIR/bin/x64/release/ocgcore.dll" "$BIN_DIR/ocgcore.dll"

echo "=== Tamamlandi ==="
echo "DLL: $BIN_DIR/ocgcore.dll"
ls -lh "$BIN_DIR/ocgcore.dll"
