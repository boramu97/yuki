# Bot vs Bot 12x12 matrix runner.
# Her eslesme icin tek match; aggregate metrikler + deadlock listesi.
#
# Kullanim:
#   python tests/ai_sim/run_matrix.py [--subset name1,name2,...] [--quiet]
#
# Exit code 1 eger herhangi bir deadlock olursa (CI'da bozulma sinyali).

from __future__ import annotations

import argparse
import os
import sys
import time

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

from tests.ai_sim.simulator import simulate_match
from server.decks import (
    YUGI_DECK, KAIBA_DECK, JOEY_DECK, MAI_DECK, BASTION_DECK,
    DINO_DECK, INSECT_DECK, REX_RAPTOR_DECK, PEGASUS_DECK,
    JADEN_DECK, SYRUS_DECK, ANCIENT_GEAR_DECK,
)


DECKS: dict[str, list[int]] = {
    "Yugi":         YUGI_DECK,
    "Kaiba":        KAIBA_DECK,
    "Joey":         JOEY_DECK,
    "Mai":          MAI_DECK,
    "Bastion":      BASTION_DECK,
    "Dino":         DINO_DECK,
    "Weevil":       INSECT_DECK,
    "Rex":          REX_RAPTOR_DECK,
    "Pegasus":      PEGASUS_DECK,
    "Jaden":        JADEN_DECK,
    "Syrus":        SYRUS_DECK,
    "Ancient Gear": ANCIENT_GEAR_DECK,
}


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--subset", help="Comma-separated bot names; default = all 12")
    ap.add_argument("--quiet", action="store_true", help="only show summary")
    ap.add_argument("--max-steps", type=int, default=5000)
    args = ap.parse_args()

    names = list(DECKS.keys())
    if args.subset:
        names = [n.strip() for n in args.subset.split(",") if n.strip() in DECKS]
        if not names:
            print("No valid bot names in subset"); return 2

    total = len(names) ** 2
    results: list[dict] = []
    deadlocks: list[dict] = []
    wins = {n: 0 for n in names}
    losses = {n: 0 for n in names}

    start = time.time()
    idx = 0
    for a in names:
        for b in names:
            idx += 1
            t0 = time.time()
            r = simulate_match(
                DECKS[a], a, DECKS[b], b,
                max_steps=args.max_steps, verbose=False,
            )
            dt = time.time() - t0
            r["dt"] = dt
            results.append(r)
            if r["deadlock"]:
                deadlocks.append(r)
            if r["winner"] == 0:
                wins[a] += 1; losses[b] += 1
            elif r["winner"] == 1:
                wins[b] += 1; losses[a] += 1

            if not args.quiet:
                status = (
                    "DEADLOCK" if r["deadlock"] else
                    ("TIMEOUT" if r["timeout"] else
                     (f"WIN:{a}" if r["winner"] == 0 else
                      (f"WIN:{b}" if r["winner"] == 1 else "DRAW")))
                )
                print(f"[{idx:3d}/{total}] {a:<14} vs {b:<14} | "
                      f"{status:<20} | t={r['turn_count']:>3} rt={r['retry_total']:>2} "
                      f"streak={r['max_retry_streak']:>2} dt={dt:>5.1f}s")

    elapsed = time.time() - start

    # ------------- Ozet ---------------
    print("\n" + "=" * 72)
    print("BOT MATRIX OZETI")
    print("=" * 72)
    print(f"Toplam maç:          {total}")
    print(f"Süre:                {elapsed:.1f} s  (ort {elapsed/total:.2f} s/mac)")
    total_deadlock = sum(1 for r in results if r["deadlock"])
    total_timeout = sum(1 for r in results if r["timeout"])
    avg_turns = sum(r["turn_count"] for r in results) / total if total else 0
    avg_retry = sum(r["retry_total"] for r in results) / total if total else 0
    print(f"Deadlock:            {total_deadlock}")
    print(f"Timeout:             {total_timeout}")
    print(f"Ortalama tur sayisi: {avg_turns:.1f}")
    print(f"Ortalama retry:      {avg_retry:.1f}")

    print("\nWin/Loss (bot acisindan toplam):")
    print(f"{'Bot':<16} {'Win':>5} {'Loss':>5} {'Total':>7}")
    for n in names:
        tot = wins[n] + losses[n]
        print(f"  {n:<14} {wins[n]:>5} {losses[n]:>5} {tot:>7}")

    if deadlocks:
        print("\n!!! DEADLOCK MACLARI !!!")
        for r in deadlocks:
            print(f"  {r['bot_a']:<14} vs {r['bot_b']:<14} | "
                  f"msg={r['deadlock_msg']} player={r['deadlock_player']} "
                  f"turn={r['turn_count']}")

    print("=" * 72)
    return 1 if total_deadlock else 0


if __name__ == "__main__":
    sys.exit(main())
