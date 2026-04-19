# Bot vs Bot Simulation Harness

AI regression koruması — her AI değişikliği 12×12 bot matrisinde test edilir,
deadlock sayısı baseline'dan artarsa CI fails.

## Çalıştır

**Tek maç (debug):**
```bash
python tests/ai_sim/simulator.py           # Yugi vs Kaiba, verbose
```

**Subset matrix (hızlı geri bildirim):**
```bash
python tests/ai_sim/run_matrix.py --subset Yugi,Kaiba,Jaden
```

**Tam 12x12 matrix:**
```bash
python tests/ai_sim/run_matrix.py           # detaylı (144 satır)
python tests/ai_sim/run_matrix.py --quiet   # sadece özet
```

Exit code 1 → en az 1 deadlock var (regression). Exit 0 → temiz.

## Baseline (2026-04-19)

```
Deadlock: 3/144  (Bastion içeren MSG_SELECT_BATTLECMD)
Timeout:  0
Ort tur:  38.9
Ort retry: 0.3
```

Her AI değişikliğinden sonra bu baseline korunmalı. Deadlock sayısı
artarsa yeni bir bug açıldı demektir.

## Simülatör iç yapı

`simulate_match(deck_a, bot_name_a, deck_b, bot_name_b)` → dict:
- `winner`: 0 / 1 / -1 (belirsiz)
- `turn_count`: oyunda kaç tur oynandı
- `retry_total`: toplam MSG_RETRY sayısı
- `max_retry_streak`: en uzun consecutive retry (15 = deadlock)
- `deadlock`: True ise consecutive retry > 15 → hard-stuck
- `deadlock_msg`: takıldığı mesaj tipi (debug için)
- `timeout`: True ise max_steps aşıldı, kimse kazanmadı

Simulator her iki team için `ai_respond(bot_name=X)` çağırır. Test DB yok,
HTTP/WS yok — sadece OCGCore + AI. Hızlı (ortalama maç ~0.3s).

## Bug kaynakları (geliştirme notu)

Matrix altyapısı açarken yakalanan bug'lar:
1. **`MSG_ANNOUNCE_CARD`** — opcode DSL yorumlanmıyor, sadece `0` döndürülüyordu.
   Fix: retry rotation ile common kart kodları (Dark Magician, BEWD vb.)
2. **`MSG_SELECT_SUM`** — Valkyrion gibi sum-based summon için target_sum
   karşılamıyordu. Fix: brute-force subset-sum + retry rotation.

Kalan deadlock'lar (Bastion BATTLECMD) production'da 15-retry escape ile
bot teslim olur; oyuncu mağdur olmaz ama AI kalitesi optimum değil.
İleri iterasyonda araştır.

## Baseline güncelleme

Matrix temizse (0 deadlock) sonuçları baseline olarak kaydet. Yeni
deadlock yakalandıysa:
1. Verbose mode ile debug: `python tests/ai_sim/simulator.py` (top of file single match configure)
2. `deadlock_msg` → hangi SELECT tipinde patladı
3. ai_player.py'da ilgili handler'ı retry-aware fix
