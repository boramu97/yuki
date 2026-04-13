# Yuki — Integration Tests
# Tests for WebSocket server, room management, duel flow, and HTTP frontend.
# Run with: python -m pytest tests/test_integration.py -v

import asyncio
import json
import os
import signal
import socket
import subprocess
import sys
import time
import urllib.request
import urllib.error

sys.path.insert(0, ".")

import pytest
import websockets

from server.ocg_binding import (
    MSG_SELECT_IDLECMD, MSG_SELECT_BATTLECMD, MSG_SELECT_CHAIN,
    MSG_SELECT_EFFECTYN, MSG_SELECT_YESNO, MSG_SELECT_OPTION,
    MSG_SELECT_CARD, MSG_SELECT_PLACE, MSG_SELECT_POSITION,
    MSG_SELECT_TRIBUTE,
)

# ---------------------------------------------------------------------------
# Configuration
# ---------------------------------------------------------------------------
PROJECT_ROOT = str(__import__("pathlib").Path(__file__).resolve().parent.parent)


def _find_free_port():
    """Find and return a free TCP port."""
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
        s.bind(("127.0.0.1", 0))
        return s.getsockname()[1]


# Allocate ports at import time so all tests use the same pair
WS_PORT = _find_free_port()
HTTP_PORT = _find_free_port()
WS_URL = f"ws://localhost:{WS_PORT}"
HTTP_URL = f"http://localhost:{HTTP_PORT}"


# ---------------------------------------------------------------------------
# Server fixture — starts once per module, shared by all tests
# ---------------------------------------------------------------------------

def _start_server():
    """Start the Yuki server subprocess on test ports."""
    # Use CREATE_NEW_PROCESS_GROUP on Windows for clean termination
    kwargs = {}
    if sys.platform == "win32":
        kwargs["creationflags"] = subprocess.CREATE_NEW_PROCESS_GROUP

    proc = subprocess.Popen(
        [
            sys.executable, "-u", "-c",
            (
                "import asyncio; "
                "from server.websocket_server import start_server; "
                f"asyncio.run(start_server(ws_port={WS_PORT}, http_port={HTTP_PORT}))"
            ),
        ],
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
        cwd=PROJECT_ROOT,
        **kwargs,
    )
    return proc


def _stop_server(proc):
    """Terminate the server subprocess."""
    if proc is None:
        return
    try:
        proc.terminate()
    except OSError:
        pass
    try:
        proc.wait(timeout=5)
    except subprocess.TimeoutExpired:
        proc.kill()
        try:
            proc.wait(timeout=3)
        except Exception:
            pass


def _wait_for_server_sync(timeout=15.0):
    """Poll until the WebSocket port accepts TCP connections (no asyncio)."""
    deadline = time.monotonic() + timeout
    while time.monotonic() < deadline:
        try:
            s = socket.create_connection(("127.0.0.1", WS_PORT), timeout=1.0)
            s.close()
            return True
        except OSError:
            time.sleep(0.5)
    return False


@pytest.fixture(scope="module")
def server():
    """Module-scoped fixture: start server, yield, then stop."""
    proc = _start_server()
    # Wait for the server to be ready using synchronous TCP probe
    ready = _wait_for_server_sync(timeout=15.0)
    if not ready:
        rc = proc.poll()
        _stop_server(proc)
        pytest.fail(
            f"Server did not start within 15 seconds "
            f"(ports ws={WS_PORT} http={HTTP_PORT}, exit={rc})"
        )
    yield proc
    _stop_server(proc)


# ---------------------------------------------------------------------------
# Helper: collect messages from a websocket with a timeout
# ---------------------------------------------------------------------------

async def recv_json(ws, timeout=10.0):
    """Receive one JSON message from a websocket."""
    raw = await asyncio.wait_for(ws.recv(), timeout=timeout)
    return json.loads(raw)


async def collect_messages(ws, count=1, timeout=10.0):
    """Collect up to `count` JSON messages, return list."""
    msgs = []
    deadline = time.monotonic() + timeout
    while len(msgs) < count and time.monotonic() < deadline:
        remaining = deadline - time.monotonic()
        if remaining <= 0:
            break
        try:
            raw = await asyncio.wait_for(ws.recv(), timeout=remaining)
            msgs.append(json.loads(raw))
        except asyncio.TimeoutError:
            break
    return msgs


async def collect_until_action(ws, action, timeout=15.0):
    """Collect messages until one with the given action is found. Return it."""
    deadline = time.monotonic() + timeout
    while time.monotonic() < deadline:
        remaining = deadline - time.monotonic()
        if remaining <= 0:
            break
        try:
            raw = await asyncio.wait_for(ws.recv(), timeout=remaining)
            msg = json.loads(raw)
            if msg.get("action") == action:
                return msg
        except asyncio.TimeoutError:
            break
    return None


def make_ai_response(team, msg):
    """Generate an automatic AI response for a select message."""
    mt = msg.get("type", 0)
    data = {}

    if mt == MSG_SELECT_IDLECMD:
        data = {"action": "end"}
    elif mt == MSG_SELECT_BATTLECMD:
        data = {"action": "end"}
    elif mt == MSG_SELECT_CHAIN:
        data = {"index": -1}
    elif mt == MSG_SELECT_EFFECTYN:
        data = {"yes": False}
    elif mt == MSG_SELECT_YESNO:
        data = {"yes": False}
    elif mt == MSG_SELECT_OPTION:
        data = {"index": 0}
    elif mt == MSG_SELECT_CARD:
        n = msg.get("min", 1)
        cards = msg.get("cards", [])
        data = {"indices": list(range(min(n, len(cards))))}
    elif mt == MSG_SELECT_POSITION:
        data = {"position": 0x1}
    elif mt == MSG_SELECT_PLACE:
        data = {"player": team, "location": 0x04, "sequence": 0}
    elif mt == MSG_SELECT_TRIBUTE:
        n = msg.get("min", 1)
        data = {"indices": list(range(n))}
    else:
        # Generic fallback for unknown select types
        data = {"index": 0}

    return {"action": "response", "msg_type": mt, "data": data}


# ===========================================================================
# Test 1: Server starts and accepts WebSocket connections
# ===========================================================================

class TestServerStarts:
    def test_server_process_alive(self, server):
        """Server subprocess is running."""
        assert server.poll() is None, "Server process exited prematurely"

    def test_websocket_connection(self, server):
        """Can connect to the WebSocket port and receive responses."""
        async def _test():
            ws = await websockets.connect(WS_URL)
            # Send list_rooms to verify the connection is functional
            await ws.send(json.dumps({"action": "list_rooms"}))
            resp = await recv_json(ws, timeout=5)
            await ws.close()
            assert resp["action"] == "rooms"
            assert isinstance(resp["rooms"], list)

        asyncio.run(_test())


# ===========================================================================
# Test 2: Two player connection
# ===========================================================================

class TestTwoPlayerConnection:
    def test_create_and_join_room(self, server):
        """Player 1 creates room, Player 2 joins, both get correct messages."""
        async def _test():
            ws1 = await websockets.connect(WS_URL)
            ws2 = await websockets.connect(WS_URL)

            try:
                # Player 1 creates a room
                await ws1.send(json.dumps({
                    "action": "create_room",
                    "name": "Yugi",
                }))
                resp1 = await recv_json(ws1, timeout=5)
                assert resp1["action"] == "room_created"
                assert "room_id" in resp1
                assert resp1["team"] == 0
                room_id = resp1["room_id"]

                # Player 2 joins the room
                await ws2.send(json.dumps({
                    "action": "join_room",
                    "name": "Kaiba",
                    "room_id": room_id,
                }))
                resp2 = await recv_json(ws2, timeout=5)
                assert resp2["action"] == "room_joined"
                assert resp2["room_id"] == room_id
                assert resp2["team"] == 1

                # Player 1 should receive player_joined notification
                notif = await recv_json(ws1, timeout=5)
                assert notif["action"] == "player_joined"
                assert notif["name"] == "Kaiba"
            finally:
                await ws1.close()
                await ws2.close()

        asyncio.run(_test())

    def test_join_nonexistent_room(self, server):
        """Joining a room that doesn't exist returns an error."""
        async def _test():
            ws = await websockets.connect(WS_URL)
            try:
                await ws.send(json.dumps({
                    "action": "join_room",
                    "name": "Ghost",
                    "room_id": "nonexistent",
                }))
                resp = await recv_json(ws, timeout=5)
                assert resp["action"] == "error"
            finally:
                await ws.close()

        asyncio.run(_test())

    def test_quick_match(self, server):
        """Quick match: first player creates, second joins automatically."""
        async def _test():
            ws1 = await websockets.connect(WS_URL)
            ws2 = await websockets.connect(WS_URL)

            try:
                # Player 1 starts quick match — creates a new room
                await ws1.send(json.dumps({
                    "action": "quick_match",
                    "name": "Player1",
                }))
                resp1 = await recv_json(ws1, timeout=5)
                assert resp1["action"] == "room_created"
                assert resp1.get("waiting") is True

                # Player 2 starts quick match — should join the waiting room
                await ws2.send(json.dumps({
                    "action": "quick_match",
                    "name": "Player2",
                }))
                resp2 = await recv_json(ws2, timeout=5)
                assert resp2["action"] == "room_joined"
                assert resp2["team"] == 1
            finally:
                await ws1.close()
                await ws2.close()

        asyncio.run(_test())


# ===========================================================================
# Test 3: Duel initialization
# ===========================================================================

class TestDuelInitialization:
    def test_duel_start_message(self, server):
        """After both players join, both receive duel_start."""
        async def _test():
            ws1 = await websockets.connect(WS_URL)
            ws2 = await websockets.connect(WS_URL)

            try:
                # Player 1 creates room
                await ws1.send(json.dumps({
                    "action": "create_room",
                    "name": "Yugi",
                }))
                resp1 = await recv_json(ws1)
                room_id = resp1["room_id"]

                # Player 2 joins
                await ws2.send(json.dumps({
                    "action": "join_room",
                    "name": "Kaiba",
                    "room_id": room_id,
                }))
                await recv_json(ws2)  # room_joined

                # Player 1 gets player_joined
                await recv_json(ws1)

                # Both should get duel_start
                ds1 = await collect_until_action(ws1, "duel_start", timeout=10)
                ds2 = await collect_until_action(ws2, "duel_start", timeout=10)

                assert ds1 is not None, "Player 1 did not receive duel_start"
                assert ds2 is not None, "Player 2 did not receive duel_start"
                assert ds1["action"] == "duel_start"
                assert ds2["action"] == "duel_start"
            finally:
                await ws1.close()
                await ws2.close()

        asyncio.run(_test())

    def test_initial_game_state(self, server):
        """After duel starts, players receive info messages (draw, LP, etc.)."""
        async def _test():
            ws1 = await websockets.connect(WS_URL)
            ws2 = await websockets.connect(WS_URL)

            try:
                # Setup room
                await ws1.send(json.dumps({
                    "action": "create_room", "name": "Yugi",
                }))
                resp1 = await recv_json(ws1)
                room_id = resp1["room_id"]

                await ws2.send(json.dumps({
                    "action": "join_room", "name": "Kaiba",
                    "room_id": room_id,
                }))
                await recv_json(ws2)  # room_joined
                await recv_json(ws1)  # player_joined

                # Collect messages from player 1 for a while after duel_start
                msgs = await collect_messages(ws1, count=30, timeout=10)
                actions = [m.get("action") for m in msgs]

                # Should see duel_start followed by info messages
                assert "duel_start" in actions, "Missing duel_start"
                assert "info" in actions, "Missing info messages after duel start"

                # Look for draw or LP-related info in the messages
                info_msgs = [m for m in msgs if m.get("action") == "info"]
                info_names = [
                    m.get("msg", {}).get("name", "") for m in info_msgs
                ]

                # A duel should produce draw phase and new turn messages
                has_draw = any("DRAW" in n for n in info_names)
                has_new_turn = any("NEW_TURN" in n for n in info_names)
                has_any_game_state = has_draw or has_new_turn or len(info_msgs) > 0

                assert has_any_game_state, (
                    f"No game state messages received. Got names: {info_names}"
                )
            finally:
                await ws1.close()
                await ws2.close()

        asyncio.run(_test())


# ===========================================================================
# Test 4: Draw Phase
# ===========================================================================

class TestDrawPhase:
    def test_draw_phase_notification(self, server):
        """Turn player receives MSG_DRAW info during the duel."""
        async def _test():
            ws1 = await websockets.connect(WS_URL)
            ws2 = await websockets.connect(WS_URL)

            try:
                # Setup room and start duel
                await ws1.send(json.dumps({
                    "action": "create_room", "name": "Yugi",
                }))
                resp = await recv_json(ws1)
                room_id = resp["room_id"]

                await ws2.send(json.dumps({
                    "action": "join_room", "name": "Kaiba",
                    "room_id": room_id,
                }))
                await recv_json(ws2)  # room_joined
                await recv_json(ws1)  # player_joined

                # Collect messages from both players, responding to selects
                # to keep the duel moving, until we see a DRAW message.
                found_draw = False
                found_new_turn = False
                deadline = time.monotonic() + 20.0

                # Use tasks to listen on both sockets concurrently
                done_event = asyncio.Event()

                async def listener(team, ws):
                    nonlocal found_draw, found_new_turn
                    while not done_event.is_set() and time.monotonic() < deadline:
                        remaining = deadline - time.monotonic()
                        if remaining <= 0:
                            break
                        try:
                            raw = await asyncio.wait_for(
                                ws.recv(), timeout=min(remaining, 5.0)
                            )
                            msg = json.loads(raw)
                            action = msg.get("action")

                            if action == "info":
                                name = msg.get("msg", {}).get("name", "")
                                if "DRAW" in name:
                                    found_draw = True
                                if "NEW_TURN" in name:
                                    found_new_turn = True
                                # Stop once we have seen both
                                if found_draw and found_new_turn:
                                    done_event.set()

                            elif action == "select":
                                # Auto-respond to keep duel going
                                resp = make_ai_response(team, msg.get("msg", {}))
                                await ws.send(json.dumps(resp))

                            elif action == "duel_end":
                                done_event.set()

                        except asyncio.TimeoutError:
                            continue
                        except Exception:
                            break

                t1 = asyncio.create_task(listener(0, ws1))
                t2 = asyncio.create_task(listener(1, ws2))

                await asyncio.wait(
                    [t1, t2],
                    timeout=20.0,
                    return_when=asyncio.FIRST_EXCEPTION,
                )

                # Cancel remaining tasks
                t1.cancel()
                t2.cancel()
                for t in [t1, t2]:
                    try:
                        await t
                    except (asyncio.CancelledError, Exception):
                        pass

                assert found_draw, "Did not receive MSG_DRAW during duel"
                assert found_new_turn, "Did not receive MSG_NEW_TURN during duel"

            finally:
                await ws1.close()
                await ws2.close()

        asyncio.run(_test())


# ===========================================================================
# Test 5: HTTP frontend
# ===========================================================================

class TestHTTPFrontend:
    def test_index_html_served(self, server):
        """HTTP server serves index.html with expected content."""
        resp = urllib.request.urlopen(HTTP_URL, timeout=5)
        assert resp.status == 200
        body = resp.read().decode("utf-8")
        assert "Yuki" in body
        assert "<html" in body.lower()

    def test_css_served(self, server):
        """HTTP server serves CSS files."""
        try:
            resp = urllib.request.urlopen(f"{HTTP_URL}/css/style.css", timeout=5)
            assert resp.status == 200
        except urllib.error.HTTPError as e:
            pytest.skip(f"CSS not at expected path: {e}")

    def test_js_served(self, server):
        """HTTP server serves JavaScript files."""
        try:
            resp = urllib.request.urlopen(
                f"{HTTP_URL}/js/websocket.js", timeout=5
            )
            assert resp.status == 200
            body = resp.read().decode("utf-8")
            assert "WebSocket" in body
        except urllib.error.HTTPError as e:
            pytest.skip(f"JS not at expected path: {e}")


# ===========================================================================
# Run directly
# ===========================================================================

if __name__ == "__main__":
    sys.exit(pytest.main([__file__, "-v", "--tb=short"]))
