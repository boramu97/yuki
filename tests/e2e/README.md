# E2E Smoke Tests

Playwright ile browser uzerinden uctan uca regression testi.

## Calistir

```bash
python tests/e2e/smoke_hand_sync.py
```

Test kendisi:
1. Izole `YUKI_USER_DB=$TEMP/yuki_smoke_test.db` ile server'i spawn eder (production DB'ye dokunmaz).
2. HTTP 8080 + WS 8765 hazir olana kadar bekler.
3. Chromium headless → register → login → adventures → training → Yugi bot.
4. `#hand .hand-card >= 5` koşulunu bekler (hand_sync regression).
5. Screenshot: `tests/e2e/last_smoke.png` (pass) veya `last_failure.png` (fail).

## Ön gereksinimler

```bash
pip install playwright
python -m playwright install chromium
```

## Gelecek senaryolar

- Oversoul + Clayman (Polymerization → grave → Oversoul target filter) regression — arketip setcode yukleme fix'inin koruyucusu
- MIP SELECT chain context: Monster Reborn aktiflestir → "[Monster Reborn] — ..." header assert
- Mobil viewport (iPad 768x1024, 820x1180) responsive smoke
