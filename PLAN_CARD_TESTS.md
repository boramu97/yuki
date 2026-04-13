# Kapsamlı Kart Efekt & Mekanik Test Planı

> Bu plan `executing-plans` skill'i ile uygulanacak.
> Her worktree'de bir kart grubu test edilecek, `systematic-debugging` ile hatalar çözülecek,
> `webapp-testing` ile tarayıcıda doğrulanacak.

---

## FAZA 0: Test Altyapısı İyileştirmesi

### Adım 0.1 — Test helper modülü oluştur
- `tests/helpers.py` — Ortak duel setup, kart ekleme, mesaj okuma fonksiyonları
- Motor init, callback, script yükleme tek yerden
- Kartları belirli bölgelere (hand, field, GY, deck) yerleştirme yardımcıları
- Query fonksiyonu: sahada kartın ATK/DEF/counter bilgisini sorgula

### Adım 0.2 — Mevcut test_all_effects.py'yi refactor et
- helpers.py kullansın
- Her test bağımsız duel oluştursun
- Doğrulama fonksiyonları daha spesifik olsun (sadece activated değil, gerçek sonuç kontrolü)

---

## FAZ 1: Normal Monster Kartları (Temel Mekanikler)

**Worktree branch:** `test/normal-monsters`

Deste'deki normal canavar kartları:
- 46986414 — Dark Magician (Lv7, ATK 2500, DEF 2100)
- 78193831 — Buster Blader (Lv7, ATK 2600, DEF 2300)
- 70781052 — Summoned Skull (Lv6, ATK 2500, DEF 1200)
- 67724379 — Koumori Dragon (Lv4, ATK 1500, DEF 1200)
- 15025844 — Mystical Elf (Lv4, ATK 800, DEF 2000)
- 87796900 — Winged Dragon Guardian (Lv4, ATK 1400, DEF 1200)
- 52077741 — Obnoxious Celtic Guard (Lv4, ATK 1400, DEF 1200, efektli)

### Test 1.1 — Normal Summon (Lv4 ve altı)
- Koumori Dragon, Mystical Elf, Winged Dragon: Normal Summon → sahada olmalı
- Doğrulama: MSG_SUMMONING + MSG_SUMMONED mesajları, doğru pozisyon

### Test 1.2 — Tribute Summon (Lv5-6: 1 kurban)
- Summoned Skull: 1 monster tribute → sahada olmalı
- Doğrulama: MSG_SELECT_TRIBUTE → MSG_SUMMONING → MSG_SUMMONED

### Test 1.3 — Tribute Summon (Lv7+: 2 kurban)
- Dark Magician: 2 monster tribute → sahada olmalı
- Buster Blader: 2 monster tribute → sahada olmalı
- Doğrulama: 2 kurban seçimi, MSG_SUMMONING → MSG_SUMMONED

### Test 1.4 — Set (yüzü kapalı savunma)
- Herhangi bir Lv4: Set → POS_FACEDOWN_DEFENSE
- Doğrulama: MSG_SET mesajı, pozisyon doğrulaması

### Test 1.5 — Flip Summon
- Set edilmiş kartı flip → POS_FACEUP_ATTACK
- Doğrulama: MSG_FLIPSUMMONING → MSG_FLIPSUMMONED

### Test 1.6 — Battle (savaş hesabı)
- ATK 1900 vs ATK 1500 → ATK farkı kadar hasar (400)
- ATK 1900 vs DEF 2000 → saldırana 100 hasar
- ATK 1900 vs ATK 1900 → her ikisi de yok olur, 0 hasar
- Doğrulama: MSG_DAMAGE değerleri, MSG_BATTLE sonuçları

### Test 1.7 — Obnoxious Celtic Guard (savaş yıkımı koruması)
- ATK 3000'e karşı savaşta yok edilmemeli (efekti: ATK 1900+ ile savaşta yok olmaz)
- Doğrulama: Savaştan sonra hala sahada

---

## FAZ 2: Efekt Monster Kartları

**Worktree branch:** `test/effect-monsters`

### Test 2.1 — Dark Magician Girl (38033121)
- **Efekt:** GY'deki her DM/DMG için +300 ATK
- **Kurulum:** GY'ye 1x Dark Magician koy, DMG'yi summon et
- **Doğrulama:** ATK = 2000 + 300 = 2300 (query ile kontrol)
- **Mevcut durum:** BAŞARISIZ — çağrılamadı (Lv6, tribute gerekli)

### Test 2.2 — Breaker the Magical Warrior (71413901)
- **Efekt:** Summon olduğunda 1 Spell Counter eklenir. Counter çıkararak 1 Spell/Trap yok et.
- **Kurulum:** Normal summon
- **Doğrulama:** MSG_ADD_COUNTER mesajı, ATK = 1600+300 = 1900
- **İleri test:** Counter'ı kullanarak rakip Spell/Trap yok etme
- **Mevcut durum:** GEÇTİ (sadece counter eklenmesi)

### Test 2.3 — The Tricky (14778250)
- **Efekt:** 1 kart discard → Special Summon (elden)
- **Kurulum:** Elde en az 2 kart (1 discard + kendisi)
- **Doğrulama:** MSG_SPSUMMONING, discard edilen kart GY'de
- **Mevcut durum:** GEÇTİ

### Test 2.4 — Old Vindictive Magician (45141844)
- **Efekt:** FLIP: Rakibin 1 monster'ını yok et
- **Kurulum:** Set et, rakip saldırsın veya flip summon
- **Doğrulama:** Flip sonrası rakip monster yok olmalı
- **Mevcut durum:** Sadece summon test edilmiş, flip efekti test edilmemiş

### Test 2.5 — Skilled Dark Magician (73752131)
- **Efekt:** Her Spell aktivasyonunda 1 Spell Counter. 3 counter olunca → tribute ederek Dark Magician özel çağır
- **Kurulum:** SDM summon, 3 Spell oyna (örn. Pot of Greed x3)
- **Doğrulama:** 3x MSG_ADD_COUNTER, sonra efekt aktifleştirme ile DM çağırma
- **Mevcut durum:** BAŞARISIZ — counter yok (spell oynanmıyor)

### Test 2.6 — Big Shield Gardna (65240384)
- **Efekt:** Set iken saldırıya uğrarsa yüzü açık savunmaya geçer. Spell'leri negate edebilir.
- **Kurulum:** Set et, rakip saldırsın
- **Doğrulama:** POS_CHANGE mesajı

### Test 2.7 — Electromagnetic Turtle (34710660)
- **Efekt:** GY'den banish → Battle Phase sonlandır (duel başına 1 kez)
- **Kurulum:** GY'ye koy, rakip Battle Phase'de aktifle
- **Doğrulama:** Battle Phase sona ermeli

### Test 2.8 — King's Knight (64788463) + Queen's Knight (25652259) + Jack's Knight (90876561)
- **Efekt:** Queen's Knight sahadayken King's Knight summon → Jack's Knight desteden özel çağır
- **Kurulum:** Queen sahada, King summon
- **Doğrulama:** MSG_SPSUMMONING Jack's Knight (90876561)
- **Mevcut durum:** GEÇTİ

### Test 2.9 — Kuriboh (40640057)
- **Efekt:** Elden discard → o turda savaş hasarı 0
- **Kurulum:** Kuriboh elde, rakip saldırsın
- **Doğrulama:** Savaş hasarı 0 olmalı

### Test 2.10 — Valkyrion the Magna Warrior (75347539)
- **Efekt:** Alpha + Beta + Gamma'yı tribute ederek özel çağır. Kendini tribute ederek üçünü geri çağır.
- **Kurulum:** Alpha, Beta, Gamma sahada
- **Doğrulama:** 3 tribute → MSG_SPSUMMONING Valkyrion

### Test 2.11 — Magnet Warriors (Alpha/Beta/Gamma)
- 99785935 Alpha (ATK 1400), 39256679 Beta (ATK 1700), 11549357 Gamma (ATK 1500)
- Normal summon testi + Valkyrion fusion mekanizması

---

## FAZ 3: Spell Kartları

**Worktree branch:** `test/spell-cards`

### Test 3.1 — Pot of Greed (55144522)
- **Efekt:** 2 kart çek
- **Doğrulama:** MSG_DRAW count=2
- **Mevcut durum:** GEÇTİ

### Test 3.2 — Graceful Charity (79571449)
- **Efekt:** 3 kart çek, sonra 2 kart discard
- **Doğrulama:** MSG_DRAW count=3, ardından 2 kart seçimi
- **Mevcut durum:** GEÇTİ

### Test 3.3 — Change of Heart (4031928)
- **Efekt:** Rakibin 1 monster'ının kontrolünü al (bu tur)
- **Kurulum:** Rakipte en az 1 monster
- **Doğrulama:** MSG_CHAINING + kontrol değişimi
- **Mevcut durum:** GEÇTİ

### Test 3.4 — Monster Reborn (83764718)
- **Efekt:** Herhangi bir GY'den 1 monster özel çağır
- **Kurulum:** GY'de en az 1 monster (birkaç tur beklemek gerekebilir)
- **Doğrulama:** MSG_SPSUMMONING
- **Mevcut durum:** GEÇTİ

### Test 3.5 — Dark Magic Curtain (99789342)
- **Efekt:** LP'nin yarısını öde → desteden Dark Magician özel çağır
- **Kurulum:** Destede Dark Magician olmalı, sahada başka summon yapılmamış olmalı
- **Doğrulama:** MSG_PAY_LPCOST (4000) + MSG_SPSUMMONING (DM)
- **Mevcut durum:** BAŞARISIZ — Efekt çalışmadı
- **Debug:** O turda başka summon yapılmış olabilir (kısıtlama var)

### Test 3.6 — Mystical Space Typhoon (5318639)
- **Efekt:** Sahada 1 Spell/Trap yok et
- **Kurulum:** Rakipte set Spell/Trap olmalı
- **Doğrulama:** Hedef kart yok edildi (MSG_MOVE → GY)
- **Mevcut durum:** BAŞARISIZ — rakipte hedef yok
- **Debug:** P1 deck'ine Spell/Trap koyup P1'in set etmesini sağlamak gerek

### Test 3.7 — Swords of Revealing Light (72302403)
- **Efekt:** 3 tur boyunca rakip saldıramaz. Rakip yüzü kapalı monster'lar açılır.
- **Doğrulama:** 3 tur boyunca rakip saldırı yapamamalı
- **Mevcut durum:** GEÇTİ (sadece aktivasyon testi)
- **İleri test:** Gerçekten 3 tur saldırı engeli

### Test 3.8 — Thousand Knives (63391643)
- **Efekt:** Sahada Dark Magician varsa: rakibin 1 monster'ını yok et
- **Kurulum:** DM sahada olmalı + rakipte monster
- **Doğrulama:** Rakip monster yok edildi
- **Mevcut durum:** BAŞARISIZ — DM sahada olmadığı için aktifleşmiyor
- **Debug:** Önce DM summon et, sonra aynı turda Thousand Knives aktifle

### Test 3.9 — Monster Reincarnation (74848038)
- **Efekt:** 1 kart discard → GY'den 1 monster ele al
- **Doğrulama:** Kart elde geri döndü
- **Mevcut durum:** GEÇTİ

### Test 3.10 — Magical Dimension (28553439)
- **Efekt:** Quick-Play. Sahada Spellcaster varsa: 1 monster tribute + desteden/elden Spellcaster özel çağır + rakibin 1 monster'ını yok et (opsiyonel)
- **Doğrulama:** Tribute + SpSummon + Destroy
- **Mevcut durum:** GEÇTİ (sadece aktivasyon)

### Test 3.11 — Black Luster Ritual (55761792)
- **Efekt:** Toplam seviye 8+ olan monster'ları tribute et → Black Luster Soldier ritual çağır
- **Kurulum:** BLS elde + tributable monster'lar elde
- **Doğrulama:** MSG_SPSUMMONING BLS
- **Mevcut durum:** GEÇTİ (sadece aktivasyon)

### Test 3.12 — Card of Sanctity (42664989)
- **Efekt:** Her oyuncu elinde 6 kart olana kadar çeker
- **Doğrulama:** MSG_DRAW, elde 6 kart

### Test 3.13 — Polymerization (24094653)
- **Efekt:** Elden Fusion malzemelerini GY'ye gönder → Fusion monster çağır
- **Not:** Destede Fusion monster yok (BLS hariç), bu test Limited olabilir
- **Doğrulama:** Aktivasyon kontrolü (malzeme/hedef yoksa aktifleşmemeli)

---

## FAZ 4: Trap Kartları

**Worktree branch:** `test/trap-cards`

### Test 4.1 — Mirror Force (44095762)
- **Efekt:** Rakip saldırı ilan ettiğinde: rakibin tüm saldırı pozisyonundaki monster'larını yok et
- **Kurulum:** Set et, rakip saldırsın
- **Doğrulama:** Tüm ATK pozisyon monster'lar yok edildi

### Test 4.2 — Magic Cylinder (62279055)
- **Efekt:** Rakip saldırı ilan ettiğinde: saldırıyı negate et + saldıran monster'ın ATK'sı kadar hasar ver
- **Kurulum:** Set et, rakip ATK 2000 ile saldırsın
- **Doğrulama:** MSG_ATTACK_DISABLED + MSG_DAMAGE (2000 to P1)

### Test 4.3 — Spellbinding Circle (18807108)
- **Efekt:** Rakibin 1 monster'ını hedef al: saldıramaz, pozisyon değiştiremez
- **Kurulum:** Set et, rakip monster varken aktifle
- **Doğrulama:** Hedef monster saldırı/pozisyon kilitlendi

---

## FAZ 5: Özel Mekanikler & Edge Case'ler

**Worktree branch:** `test/special-mechanics`

### Test 5.1 — Chain (Zincir) Mekaniği
- Spell aktifle → Trap zincirle → doğru sırada çözülmeli (LIFO)
- Doğrulama: MSG_CHAIN_SOLVING sırası

### Test 5.2 — Black Luster Soldier (Ritual tam akış)
- Ritual Spell aktifle → tributable seç → BLS sahaya gelsin → ATK 3000 doğrula

### Test 5.3 — Phase geçişleri
- DP → SP → MP1 → BP → MP2 → EP tam döngü
- Her fazda doğru MSG_NEW_PHASE değeri

### Test 5.4 — Deck-out kontrolü
- 0 kartlık deste → çekememe → kaybetme
- Doğrulama: MSG_WIN

### Test 5.5 — LP 0 kontrolü
- LP 0'a düşen oyuncu kaybeder
- Doğrulama: MSG_WIN

---

## FAZ 6: WebSocket & UI Entegrasyon Testleri

**Worktree branch:** `test/webapp-integration`

> `webapp-testing` skill'i ile Playwright kullanarak

### Test 6.1 — Sunucu başlatma
- `python -m server` çalışıyor mu?
- WebSocket bağlantısı kabul ediliyor mu?

### Test 6.2 — 2 oyunculu bağlantı
- 2 tarayıcı tab aç → her ikisi de bağlansın
- Duel başlasın

### Test 6.3 — Kart çekme görselliği
- Draw Phase'de elde kart görünmeli
- Kart görselleri (ygoprodeck) yüklenmeli

### Test 6.4 — Kart oynama
- Elden karta tıkla → menü açılsın
- Summon/Set/Activate seçenekleri doğru olsun

### Test 6.5 — Savaş fazı
- Battle Phase'e geç → saldırı hedefi seç → hasar gösterilsin

### Test 6.6 — Zincir UI
- Chain oluştuğunda kullanıcıya seçenek sunulsun
- Pas geç veya zincire ekle

---

## UYGULAMA SIRASI

1. **FAZ 0** — Test altyapısı (helpers.py) → doğrudan main branch
2. **FAZ 1** — Normal monsters → worktree `test/normal-monsters`
3. **FAZ 2** — Effect monsters → worktree `test/effect-monsters`
4. **FAZ 3** — Spell cards → worktree `test/spell-cards`
5. **FAZ 4** — Trap cards → worktree `test/trap-cards`
6. **FAZ 5** — Special mechanics → worktree `test/special-mechanics`
7. **FAZ 6** — Webapp integration → worktree `test/webapp-integration`

Her fazda:
1. Worktree oluştur (izole branch)
2. Testleri yaz ve çalıştır
3. Başarısız testleri `systematic-debugging` ile analiz et
4. Düzelt, tekrar çalıştır
5. Tümü geçince merge et

---

## BAŞARI KRİTERİ

- Tüm 40 kart için en az 1 efekt/mekanik testi
- 5 başarısız testin tümü düzeltilmiş
- Trap kartları (Mirror Force, Magic Cylinder, Spellbinding Circle) tam test
- WebSocket üzerinden en az 1 tam duel tamamlanmış
- Tarayıcıda kart oynama + savaş görsel olarak doğrulanmış
