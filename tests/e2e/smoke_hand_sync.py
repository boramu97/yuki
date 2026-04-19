"""Smoke test: register -> login -> bot duello -> el 5 kart assert.

Regression koruma:
- hand_sync motor otoriteli gorsellestirme (2026-04-19 fix)
- Oversoul / arketip setcode yuklemesi (SELECT_EFFECTYN sorunu senaryosu icin genisletilebilir)

Izole test DB: YUKI_USER_DB ile tmp path; production users.db'ye dokunmaz.
"""
import os
import socket
import subprocess
import sys
import time
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent
TEST_DB = Path(os.environ.get("TEMP", "/tmp")) / "yuki_smoke_test.db"
HTTP_PORT = 8080
WS_PORT = 8765


def wait_port(port: int, host: str = "localhost", timeout: float = 20.0) -> bool:
    deadline = time.time() + timeout
    while time.time() < deadline:
        try:
            socket.create_connection((host, port), timeout=0.5).close()
            return True
        except OSError:
            time.sleep(0.3)
    return False


def start_server() -> subprocess.Popen:
    if TEST_DB.exists():
        TEST_DB.unlink()
    env = os.environ.copy()
    env["YUKI_USER_DB"] = str(TEST_DB)
    env["PYTHONUNBUFFERED"] = "1"
    print(f"[smoke] Test DB: {TEST_DB}")
    proc = subprocess.Popen(
        [sys.executable, "-m", "server"],
        cwd=str(PROJECT_ROOT),
        env=env,
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
    )
    if not wait_port(HTTP_PORT) or not wait_port(WS_PORT):
        proc.terminate()
        raise RuntimeError(f"Server {HTTP_PORT}/{WS_PORT} ayaga kalkmadi")
    print(f"[smoke] Server hazir (PID {proc.pid}, HTTP :{HTTP_PORT}, WS :{WS_PORT})")
    return proc


def run_test() -> int:
    from playwright.sync_api import sync_playwright, TimeoutError as PwTimeout

    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        ctx = browser.new_context(viewport={"width": 1280, "height": 800})
        page = ctx.new_page()

        errors: list[str] = []
        page.on("pageerror", lambda exc: errors.append(f"JS error: {exc}"))
        page.on("console", lambda msg:
            errors.append(f"[console.{msg.type}] {msg.text}") if msg.type == "error" else None)

        try:
            page.goto(f"http://localhost:{HTTP_PORT}", wait_until="networkidle")

            # --- AUTH ---
            page.wait_for_selector("#auth-screen.active", timeout=5000)
            print("[test] auth screen OK")

            page.fill("#auth-username", "smoketest")
            page.fill("#auth-password", "testpass123")
            page.click("#btn-register")
            page.wait_for_timeout(800)  # register_result
            # Login (ayni form alanlari dolu)
            page.click("#btn-login")
            page.wait_for_selector("#home-screen.active", timeout=5000)
            print("[test] home screen OK")

            # --- ADVENTURES -> TRAINING -> BOT ---
            page.click("#nav-adventures")
            page.wait_for_selector("#adventures-screen.active", timeout=3000)
            page.click("#banner-training")
            page.wait_for_selector("#training-screen.active", timeout=3000)
            print("[test] training screen OK")

            page.click('.adv-card[data-bot="Yugi"]')
            page.wait_for_selector("#duel.active", timeout=10000)
            print("[test] duel screen OK")

            # --- HAND SYNC ASSERTION ---
            # motor 5 kart ceksin, hand_sync tetiklensin
            page.wait_for_function(
                "document.querySelectorAll('#hand .hand-card').length >= 5",
                timeout=15000,
            )
            hand_count = page.locator("#hand .hand-card").count()
            opp_count = page.locator("#opp-hand .opp-hand-card").count()
            img_count = page.locator("#hand .hand-card img").count()
            print(f"[test] hand={hand_count}  opp_hand={opp_count}  imgs={img_count}")

            assert hand_count >= 5, f"Self el < 5: {hand_count}"
            assert opp_count >= 5, f"Opp el < 5: {opp_count}"
            assert img_count >= hand_count, f"Kart img eksik (code=0 kart var): img={img_count} hand={hand_count}"

            screenshot = PROJECT_ROOT / "tests" / "e2e" / "last_smoke.png"
            page.screenshot(path=str(screenshot), full_page=True)
            print(f"[test] screenshot -> {screenshot}")

            print("[test] === SMOKE PASS ===")
            return 0
        except (PwTimeout, AssertionError) as e:
            screenshot = PROJECT_ROOT / "tests" / "e2e" / "last_failure.png"
            try:
                page.screenshot(path=str(screenshot), full_page=True)
            except Exception:
                pass
            print(f"[test] FAIL: {e}")
            print(f"[test] screenshot -> {screenshot}")
            for err in errors:
                print(f"  {err}")
            return 1
        finally:
            browser.close()


def main() -> int:
    proc = start_server()
    try:
        return run_test()
    finally:
        proc.terminate()
        try:
            proc.wait(timeout=5)
        except subprocess.TimeoutExpired:
            proc.kill()


if __name__ == "__main__":
    sys.exit(main())
