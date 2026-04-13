# Yuki — Browser-Based Duel Game

An open-source, browser-based card duel game for playing with friends.
No installation required — just open a browser and play.

## Architecture

```
Browser (HTML/JS) ←→ WebSocket ←→ Python Server ←→ OCGCore Engine (C++)
```

## Tech Stack

- **Engine:** [OCGCore](https://github.com/edo9300/ygopro-core) (C++17, AGPLv3)
- **Server:** Python 3.10+ (asyncio, websockets, ctypes)
- **Frontend:** Vanilla HTML/CSS/JavaScript
- **Card Data:** SQLite database + Lua scripts (community-maintained)

## Building

### Prerequisites

- C++17 compiler (MSVC / GCC / Clang)
- Python 3.10+
- premake5 (for OCGCore build)

### Build OCGCore

```bash
cd ocgcore
git submodule update --init --recursive
premake5 vs2022    # Windows
# or: premake5 gmake2  # Linux/macOS
```

### Run Server

```bash
pip install websockets
python -m server
```

## License

This project is licensed under the **GNU Affero General Public License v3.0** (AGPLv3).
See [LICENSE](LICENSE) for the full text.

This is required because OCGCore is licensed under AGPLv3.

## Disclaimer

This project is **not affiliated with, endorsed by, or sponsored by** Konami Digital Entertainment, Kazuki Takahashi, or any related entities. All card game mechanics and concepts referenced belong to their respective copyright holders.

This is a **non-commercial, open-source, fan-made** project created for educational and personal entertainment purposes only. No copyrighted card artwork or imagery is distributed with this project.

All trademarks and copyrights are the property of their respective owners.
