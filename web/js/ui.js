// Yuki — Motor Iletisim Paneli (MIP)
// Motorun tum sorularini tek panelde gosterir, cevaplari motora iletir.

const UI = {
    currentSelect: null,
    selectedIndices: [],
    autoPassChain: true,

    // --- Ekran yonetimi ---
    showScreen(id) {
        document.querySelectorAll(".screen").forEach(s => s.classList.remove("active"));
        document.getElementById(id)?.classList.add("active");
    },
    setStatus(t) { const el = document.getElementById("lobby-status"); if (el) el.textContent = t; },
    setGameStatus(t) { document.getElementById("status-text").textContent = t; },

    // --- LOG ---
    log(text, cls, cardCode) {
        const log = document.getElementById("duel-log"); if (!log) return;
        const entry = document.createElement("div");
        entry.className = "log-banner" + (cls ? ` ${cls}` : "");
        if (cardCode) {
            const img = document.createElement("img");
            img.src = `https://images.ygoprodeck.com/images/cards_small/${cardCode}.jpg`;
            img.onerror = function () { this.style.display = "none"; };
            entry.appendChild(img);
        }
        const span = document.createElement("div"); span.className = "lb-text";
        span.textContent = text; entry.appendChild(span);
        log.insertBefore(entry, log.firstChild);
        while (log.children.length > 100) log.removeChild(log.lastChild);
    },

    // =====================================================================
    //  MOTOR PANELI — Altyapi
    // =====================================================================

    showMotorPanel(question, phase) {
        const panel = document.getElementById("motor-panel");
        document.getElementById("mp-phase").textContent = phase || "";
        document.getElementById("mp-question").textContent = question || "";
        document.getElementById("mp-actions").innerHTML = "";
        document.getElementById("mp-footer-actions").innerHTML = "";
        document.getElementById("mp-footer").style.display = "none";
        panel.classList.add("open");
        // Mobilde minimized basla — kullanici yukari cekerek acar
        if (window.innerWidth <= 768) panel.classList.add("minimized");
    },

    hideMotorPanel() {
        const panel = document.getElementById("motor-panel");
        panel.classList.remove("open");
        panel.classList.remove("minimized");
        document.getElementById("mp-actions").innerHTML = "";
        this._clearHighlights();
    },

    toggleMotorPanel() {
        document.getElementById("motor-panel").classList.toggle("minimized");
    },

    _addGroupHeader(label) {
        const el = document.getElementById("mp-actions");
        const h = document.createElement("div");
        h.className = "mp-group-header";
        h.textContent = label;
        el.appendChild(h);
    },

    _addCardAction(card, buttons, locationLabel) {
        const el = document.getElementById("mp-actions");
        const tile = document.createElement("div");
        tile.className = "mp-action-card";

        // Sol: Buyuk gorsel (code=0 → kapali kart)
        if (card.code) {
            const img = document.createElement("img");
            img.className = "mp-card-img";
            img.src = `https://images.ygoprodeck.com/images/cards_small/${card.code}.jpg`;
            img.onerror = function () { this.style.display = "none"; };
            img.onclick = (e) => {
                e.stopPropagation();
                document.getElementById("preview-img").src = `https://images.ygoprodeck.com/images/cards/${card.code}.jpg`;
                document.getElementById("card-preview-overlay").classList.add("active");
            };
            tile.appendChild(img);
        } else {
            // Kapali kart — arka yuz gorseli (oyundaki ile ayni)
            const back = document.createElement("div");
            back.className = "mp-card-img mp-card-back";
            back.innerHTML = '<div class="mp-back-inner"><div class="mp-back-oval"></div></div>';
            tile.appendChild(back);
        }

        // Sag: bilgi + butonlar
        const body = document.createElement("div");
        body.className = "mp-card-info";

        // Bilgi alani
        const infoText = document.createElement("div");
        infoText.className = "mp-card-info-text";
        const name = document.createElement("div");
        name.className = "mp-card-name";
        name.textContent = card.card_name || `#${card.code}`;
        infoText.appendChild(name);

        const isMonster = card.card_type & 0x1;
        const isSpell = card.card_type & 0x2;
        const isTrap = card.card_type & 0x4;

        if (isMonster && card.card_atk !== undefined) {
            const stats = document.createElement("div");
            stats.className = "mp-card-stats";
            stats.innerHTML = `<span class="atk-val">ATK ${card.card_atk}</span><span class="def-val">DEF ${card.card_def}</span>`;
            infoText.appendChild(stats);
        } else if (isSpell) {
            const stats = document.createElement("div");
            stats.className = "mp-card-stats";
            stats.innerHTML = `<span class="spell-type">Buyu Karti</span>`;
            infoText.appendChild(stats);
        } else if (isTrap) {
            const stats = document.createElement("div");
            stats.className = "mp-card-stats";
            stats.innerHTML = `<span class="trap-type">Tuzak Karti</span>`;
            infoText.appendChild(stats);
        }

        if (locationLabel) {
            const loc = document.createElement("div");
            loc.className = "mp-card-location";
            loc.textContent = locationLabel;
            infoText.appendChild(loc);
        }
        body.appendChild(infoText);

        // Butonlar — altta tam genislik
        const btnArea = document.createElement("div");
        btnArea.className = "mp-card-buttons";
        for (const b of buttons) {
            const btn = document.createElement("button");
            const cls = b.primary === "purple" ? "mp-btn mp-btn-purple" :
                        b.primary ? "mp-btn mp-btn-primary" : "mp-btn mp-btn-dim";
            btn.className = cls;
            btn.textContent = b.label;
            btn.onclick = () => { this.hideMotorPanel(); b.callback(); };
            btnArea.appendChild(btn);
        }
        body.appendChild(btnArea);
        tile.appendChild(body);

        el.appendChild(tile);
    },

    _addButtonRow(buttons) {
        const el = document.getElementById("mp-actions");
        const row = document.createElement("div");
        row.className = "mp-btn-row";
        for (const b of buttons) {
            const btn = document.createElement("button");
            btn.className = "mp-btn" + (b.primary ? " mp-btn-primary" : "") + (b.selected ? " selected" : "");
            btn.textContent = b.label;
            btn.onclick = () => {
                if (!b.toggle) this.hideMotorPanel();
                b.callback();
            };
            row.appendChild(btn);
        }
        el.appendChild(row);
    },

    _showFooter(actions) {
        const footer = document.getElementById("mp-footer");
        const area = document.getElementById("mp-footer-actions");
        area.innerHTML = "";
        for (const a of actions) {
            const btn = document.createElement("button");
            btn.className = "mp-btn" + (a.primary ? " mp-btn-battle" : " mp-btn-end");
            btn.textContent = a.label;
            btn.onclick = () => { this.hideMotorPanel(); a.callback(); };
            area.appendChild(btn);
        }
        footer.style.display = "flex";
    },

    _highlightCard(con, loc, seq, actions) {
        const isSelf = con === Field.myTeam;
        const zoneId = loc === 0x04
            ? (isSelf ? "self-mzone" : "opp-mzone")
            : loc === 0x08
                ? (isSelf ? "self-szone" : "opp-szone")
                : null;
        if (!zoneId) return;
        const slots = document.getElementById(zoneId)?.querySelectorAll(".card-face");
        if (slots && slots[seq]) {
            slots[seq].classList.add("mp-highlight");
            if (actions && actions.length) {
                slots[seq].dataset.popupActions = JSON.stringify(actions);
            }
        }
    },

    _highlightHandCard(code, actions) {
        const hand = document.getElementById("hand")?.querySelectorAll(".hand-card");
        if (!hand) return;
        hand.forEach(h => {
            if (parseInt(h.dataset.code) === code && !h.classList.contains("mp-highlight")) {
                h.classList.add("mp-highlight");
                if (actions && actions.length) {
                    h.dataset.popupActions = JSON.stringify(actions);
                }
            }
        });
    },

    _clearHighlights() {
        document.querySelectorAll(".mp-highlight").forEach(el => {
            el.classList.remove("mp-highlight");
            delete el.dataset.popupActions;
        });
        document.querySelectorAll(".card-popup").forEach(p => p.remove());
    },

    _locationLabel(loc) {
        const map = { 0x02: "El", 0x04: "Canavar Bolgesi", 0x08: "Buyu/Tuzak Bolgesi", 0x10: "Mezarlik", 0x20: "Surgun", 0x40: "Ekstra Deste" };
        return map[loc] || "";
    },

    _shortName(c) { return c.card_name || `#${c.code}`; },

    // =====================================================================
    //  ANA DISPATCH
    // =====================================================================

    handleSelect(msg) {
        this.currentSelect = msg;
        const t = msg.type;
        console.log("[MIP] handleSelect type="+t, msg.name);
        const h = {
            11: "_idleCmd", 10: "_battleCmd", 16: "_chain",
            12: "_effectYN", 13: "_yesNo", 14: "_option",
            15: "_selectCard", 19: "_position", 18: "_place",
            20: "_tribute", 26: "_unselectCard", 23: "_selectSum",
            21: "_sortChain", 22: "_counter", 24: "_place", 25: "_sortCard",
            140: "_announceRace", 141: "_announceAttrib",
            142: "_announceCard", 143: "_announceNumber", 132: "_rps"
        };
        const fn = h[t];
        if (fn && this[fn]) return this[fn](msg);
        WS.sendResponse(t, {});
    },

    // =====================================================================
    //  HANDLER'LAR
    // =====================================================================

    // --- ANA FAZ ---
    _idleCmd(msg) {
        this._clearHighlights();
        this.showMotorPanel("Bir hamle yap veya turu bitir", "Ana Faz");

        // Tum aksiyonlanabilir kartlari topla: key → {card, actions[]}
        const cardMap = new Map();
        const add = (list, label, actionType, primary) => {
            (list || []).forEach((c, i) => {
                const key = `${c.code}-${c.location || 0}-${c.sequence || 0}`;
                if (!cardMap.has(key)) cardMap.set(key, { card: c, actions: [] });
                cardMap.get(key).actions.push({
                    label, primary,
                    callback: () => WS.sendResponse(11, { action: actionType, index: i })
                });
            });
        };

        add(msg.summonable, "Cagir", "summon", true);
        add(msg.special_summonable, "Ozel Cagir", "spsummon", true);
        add(msg.monster_setable, "Set", "mset", false);
        add(msg.spell_setable, "Set", "sset", false);
        add(msg.activatable, "Aktifle", "activate", "purple");
        add(msg.repositionable, "Pozisyon", "reposition", false);

        // Lokasyona gore grupla
        const locOrder = { 0x02: 0, 0x04: 1, 0x08: 2, 0x10: 3 };
        const locNames = { 0x02: "El Kartlari", 0x04: "Canavar Bolgesi", 0x08: "Buyu/Tuzak Bolgesi", 0x10: "Mezarlik" };
        const sorted = [...cardMap.values()].sort((a, b) =>
            (locOrder[a.card.location] ?? 9) - (locOrder[b.card.location] ?? 9)
        );

        let lastLoc = -1;
        for (const { card, actions } of sorted) {
            const loc = card.location || 0;
            if (loc !== lastLoc) {
                if (locNames[loc]) this._addGroupHeader(locNames[loc]);
                lastLoc = loc;
            }
            this._addCardAction(card, actions, this._locationLabel(loc));
            // Popup actions for field/hand cards
            const popupActions = actions.map(a => ({
                label: a.label,
                cls: a.primary === "purple" ? "purple" : a.primary ? "gold" : "dim",
                callback: a.callback
            }));
            if (loc === 0x04 || loc === 0x08) {
                this._highlightCard(card.controller ?? Field.myTeam, loc, card.sequence ?? 0, popupActions);
            } else if (loc === 0x02) {
                this._highlightHandCard(card.code, popupActions);
            }
        }

        // Footer: savas + tur bitir
        const footer = [];
        if (msg.can_battle_phase) footer.push({
            label: "Savas Fazina Gec", primary: true,
            callback: () => WS.sendResponse(11, { action: "battle" })
        });
        footer.push({
            label: "Turu Bitir",
            callback: () => WS.sendResponse(11, { action: "end" })
        });
        this._showFooter(footer);
    },

    // --- SAVAS FAZI ---
    _battleCmd(msg) {
        this._clearHighlights();
        this.showMotorPanel("Saldirmak icin canavar sec", "Savas Fazi");

        // Saldirabilir canavarlar
        (msg.attackable || []).forEach((c, i) => {
            const label = c.direct_attackable ? "Direkt Saldir" : "Saldir";
            const btns = [{ label, primary: true, callback: () => WS.sendResponse(10, { action: "attack", index: i }) }];
            this._addCardAction(c, btns, "Canavar Bolgesi");
            this._highlightCard(c.controller ?? Field.myTeam, 0x04, c.sequence ?? 0);
        });

        // Aktiflestirebilir efektler
        (msg.activatable || []).forEach((c, i) => {
            this._addCardAction(c, [{ label: "Aktifle", primary: true, callback: () => WS.sendResponse(10, { action: "activate", index: i }) }], this._locationLabel(c.location));
        });

        const footer = [];
        if (msg.can_main2) footer.push({
            label: "Main Phase 2",
            callback: () => WS.sendResponse(10, { action: "main2" })
        });
        footer.push({
            label: "Turu Bitir",
            callback: () => WS.sendResponse(10, { action: "end" })
        });
        this._showFooter(footer);
    },

    // --- ZINCIR ---
    _chain(msg) {
        const chains = msg.chains || [];
        if (chains.length === 0) { WS.sendResponse(16, { index: -1 }); return; }
        if (!msg.forced && this.autoPassChain) {
            const hasActivatable = chains.some(ch =>
                ch.location === 0x02 || ch.location === 0x04 ||
                ch.location === 0x08 || ch.location === 0x10 || ch.location === 0x20
            );
            if (!hasActivatable) { WS.sendResponse(16, { index: -1 }); return; }
        }

        this.showMotorPanel("Zincire efekt eklemek ister misin?", "Zincir");
        chains.forEach((c, i) => {
            this._addCardAction(c, [{
                label: "Aktifle", primary: true,
                callback: () => WS.sendResponse(16, { index: i })
            }], this._locationLabel(c.location));
        });
        if (!msg.forced) {
            this._addButtonRow([{
                label: "Pas Gec",
                callback: () => WS.sendResponse(16, { index: -1 })
            }]);
        }
    },

    // --- EFEKT EVET/HAYIR ---
    _effectYN(msg) {
        const name = msg.card_name || `#${msg.code}`;
        this.showMotorPanel(`${name} efektini aktiflestir?`, "Efekt");
        if (msg.code) {
            this._addCardAction(msg, [
                { label: "Evet", primary: true, callback: () => WS.sendResponse(12, { yes: true }) },
                { label: "Hayir", callback: () => WS.sendResponse(12, { yes: false }) },
            ], "");
        } else {
            this._addButtonRow([
                { label: "Evet", primary: true, callback: () => WS.sendResponse(12, { yes: true }) },
                { label: "Hayir", callback: () => WS.sendResponse(12, { yes: false }) },
            ]);
        }
    },

    // --- EVET/HAYIR ---
    _yesNo(msg) {
        this.showMotorPanel("Karar ver", "Karar");
        this._addButtonRow([
            { label: "Evet", primary: true, callback: () => WS.sendResponse(13, { yes: true }) },
            { label: "Hayir", callback: () => WS.sendResponse(13, { yes: false }) },
        ]);
    },

    // --- SECENEK ---
    _option(msg) {
        this.showMotorPanel("Bir secenek sec", "Secenek");
        this._addButtonRow((msg.options || []).map((o, i) => ({
            label: `Secenek ${i + 1}`,
            callback: () => WS.sendResponse(14, { index: i })
        })));
    },

    // --- KART SECIMI ---
    _selectCard(msg) {
        const min = msg.min || 1, max = msg.max || 1, cards = msg.cards || [];

        if (min === 1 && max === 1) {
            this.showMotorPanel("Bir kart sec", "Kart Secimi");
            cards.forEach((c, i) => {
                this._addCardAction(c, [{
                    label: "Sec", primary: true,
                    callback: () => WS.sendResponse(15, { indices: [i] })
                }], this._locationLabel(c.location));
            });
            if (msg.cancelable) {
                this._addButtonRow([{ label: "Iptal", callback: () => WS.sendResponse(15, { cancel: true }) }]);
            }
        } else {
            // Coklu secim
            this.selectedIndices = [];
            const self = this;

            function update() {
                self.showMotorPanel(`${min} kart sec (${self.selectedIndices.length}/${min})`, "Kart Secimi");
                cards.forEach((c, i) => {
                    const sel = self.selectedIndices.includes(i);
                    self._addCardAction(c, [{
                        label: sel ? "Secildi" : "Sec",
                        primary: sel,
                        callback: () => {
                            if (sel) self.selectedIndices = self.selectedIndices.filter(x => x !== i);
                            else if (self.selectedIndices.length < max) self.selectedIndices.push(i);
                            update();
                        }
                    }], self._locationLabel(c.location));
                });
                if (self.selectedIndices.length >= min) {
                    self._addButtonRow([{
                        label: `Onayla (${self.selectedIndices.length})`, primary: true,
                        callback: () => WS.sendResponse(15, { indices: self.selectedIndices })
                    }]);
                }
                if (msg.cancelable) {
                    self._addButtonRow([{ label: "Iptal", callback: () => WS.sendResponse(15, { cancel: true }) }]);
                }
            }
            update();
        }
    },

    // --- POZISYON ---
    _position(msg) {
        const name = msg.card_name || `#${msg.code}`;
        this.showMotorPanel(`${name} icin pozisyon sec`, "Pozisyon");
        const p = msg.positions || 0;
        const btns = [];
        if (p & 0x1) btns.push({ label: "Saldiri Pozisyonu", primary: true, callback: () => WS.sendResponse(19, { position: 0x1 }) });
        if (p & 0x4) btns.push({ label: "Savunma Pozisyonu", callback: () => WS.sendResponse(19, { position: 0x4 }) });
        if (p & 0x8) btns.push({ label: "Kapali Savunma (Set)", callback: () => WS.sendResponse(19, { position: 0x8 }) });
        this._addButtonRow(btns);
    },

    // --- BOLGE SECIMI (otomatik) ---
    _place(msg) {
        const flag = msg.selectable || 0, player = msg.player;
        for (let s = 0; s < 7; s++) { if (!(flag & (1 << s))) { WS.sendResponse(18, { player, location: 0x04, sequence: s }); return; } }
        for (let s = 0; s < 8; s++) { if (!(flag & (1 << (s + 8)))) { WS.sendResponse(18, { player, location: 0x08, sequence: s }); return; } }
        for (let s = 0; s < 7; s++) { if (!(flag & (1 << (s + 16)))) { WS.sendResponse(18, { player: 1 - player, location: 0x04, sequence: s }); return; } }
        for (let s = 0; s < 8; s++) { if (!(flag & (1 << (s + 24)))) { WS.sendResponse(18, { player: 1 - player, location: 0x08, sequence: s }); return; } }
        WS.sendResponse(18, { player, location: 0x04, sequence: 0 });
    },

    // --- KURBAN ---
    _tribute(msg) {
        const min = msg.min || 1, cards = msg.cards || [];
        if (cards.length <= min) { WS.sendResponse(20, { indices: cards.map((_, i) => i) }); return; }

        this.selectedIndices = [];
        const self = this;

        function update() {
            self.showMotorPanel(`${min} canavar kurban et (${self.selectedIndices.length}/${min})`, "Kurban");
            cards.forEach((c, i) => {
                const sel = self.selectedIndices.includes(i);
                self._addCardAction(c, [{
                    label: sel ? "Secildi" : "Kurban Et",
                    primary: sel,
                    callback: () => {
                        if (sel) self.selectedIndices = self.selectedIndices.filter(x => x !== i);
                        else if (self.selectedIndices.length < min) self.selectedIndices.push(i);
                        update();
                    }
                }], self._locationLabel(c.location));
            });
            if (self.selectedIndices.length >= min) {
                self._addButtonRow([{
                    label: "Onayla", primary: true,
                    callback: () => WS.sendResponse(20, { indices: self.selectedIndices })
                }]);
            }
        }
        update();
    },

    // --- SEC/KALDIR ---
    _unselectCard(msg) {
        const sel = msg.selectable || [];
        this.showMotorPanel("Kart sec", "Kart Secimi");
        sel.forEach((c, i) => {
            this._addCardAction(c, [{
                label: "Sec", primary: true,
                callback: () => { this.hideMotorPanel(); WS.sendResponse(26, { index: i }); }
            }], this._locationLabel(c.location));
        });
        const btns = [];
        if (msg.finishable) btns.push({ label: "Tamam", primary: true, callback: () => WS.sendResponse(26, { index: -1 }) });
        if (msg.cancelable) btns.push({ label: "Iptal", callback: () => WS.sendResponse(26, { index: -1 }) });
        if (btns.length) this._addButtonRow(btns);
    },

    // --- TOPLAM SECIMI ---
    _selectSum(msg) {
        const must = msg.must_cards || [], sel = msg.selectable_cards || [], target = msg.target_sum || 0;
        this.selectedIndices = [];
        const self = this;

        function update() {
            let sum = 0;
            must.forEach(c => { sum += (c.param & 0xFFFF); });
            self.selectedIndices.forEach(i => { if (sel[i]) sum += (sel[i].param & 0xFFFF); });

            self.showMotorPanel(`Toplam ${target} olacak sekilde sec (simdi: ${sum})`, "Toplam");

            if (must.length > 0) {
                self._addGroupHeader("Zorunlu");
                must.forEach(c => {
                    self._addCardAction(c, [{ label: `Lv ${c.param & 0xFFFF}`, primary: false, callback: () => { } }], "");
                });
            }

            self._addGroupHeader("Secilebilir");
            sel.forEach((c, i) => {
                const s = self.selectedIndices.includes(i);
                self._addCardAction(c, [{
                    label: s ? `Secildi (${c.param & 0xFFFF})` : `Sec (${c.param & 0xFFFF})`,
                    primary: s,
                    callback: () => {
                        if (s) self.selectedIndices = self.selectedIndices.filter(x => x !== i);
                        else self.selectedIndices.push(i);
                        update();
                    }
                }], self._locationLabel(c.location));
            });

            const ok = msg.mode === 1 ? sum >= target : sum === target;
            if (ok && self.selectedIndices.length > 0) {
                self._addButtonRow([{
                    label: "Onayla", primary: true,
                    callback: () => {
                        const all = must.map((_, i) => i).concat(self.selectedIndices.map(i => must.length + i));
                        WS.sendResponse(23, { indices: all });
                    }
                }]);
            }
        }
        update();
    },

    // --- SIRALAMA (otomatik) ---
    _sortChain() { WS.sendResponse(21, { indices: [] }); },
    _sortCard() { WS.sendResponse(25, { indices: [] }); },

    // --- SAYAC (otomatik) ---
    _counter(msg) {
        const cards = msg.cards || [], n = msg.count || 0;
        const counts = cards.map((c, i) => i === 0 ? Math.min(n, c.counter_count || 0) : 0);
        WS.sendResponse(22, { counts });
    },

    // --- IRK ILAN ---
    _announceRace(msg) {
        const races = {
            0x1: "Savasci", 0x2: "Buyucu", 0x4: "Peri", 0x8: "Seytan",
            0x10: "Zombie", 0x20: "Makine", 0x40: "Su", 0x80: "Ates",
            0x100: "Kaya", 0x200: "Kanatli", 0x400: "Bitki", 0x800: "Bocek",
            0x1000: "Yildirim", 0x2000: "Ejderha", 0x4000: "Canavar", 0x8000: "Canavar-Savasci",
            0x10000: "Dinozor", 0x20000: "Balik", 0x40000: "Deniz Yilani", 0x80000: "Surungan"
        };
        this.showMotorPanel("Bir irk ilan et", "Ilan");
        const btns = [];
        for (const [v, n] of Object.entries(races)) {
            if ((msg.available || 0) & parseInt(v)) btns.push({ label: n, callback: () => WS.sendResponse(140, { race: parseInt(v) }) });
        }
        this._addButtonRow(btns);
    },

    // --- OZELLIK ILAN ---
    _announceAttrib(msg) {
        const a = { 0x01: "TOPRAK", 0x02: "SU", 0x04: "ATES", 0x08: "RUZGAR", 0x10: "ISIK", 0x20: "KARANLIK" };
        this.showMotorPanel("Bir ozellik ilan et", "Ilan");
        const btns = [];
        for (const [v, n] of Object.entries(a)) {
            if ((msg.available || 0) & parseInt(v)) btns.push({ label: n, callback: () => WS.sendResponse(141, { attribute: parseInt(v) }) });
        }
        this._addButtonRow(btns);
    },

    // --- KART ILAN ---
    _announceCard(msg) {
        this.showMotorPanel("Bir kart adi ilan et", "Ilan");
        this._addButtonRow([
            { label: "Dark Magician", callback: () => WS.sendResponse(142, { code: 46986414 }) },
            { label: "Blue-Eyes White Dragon", callback: () => WS.sendResponse(142, { code: 89631139 }) },
        ]);
    },

    // --- SAYI SEC ---
    _announceNumber(msg) {
        this.showMotorPanel("Bir sayi sec", "Sayi");
        this._addButtonRow((msg.numbers || []).map((n, i) => ({
            label: `${n}`, callback: () => WS.sendResponse(143, { index: i })
        })));
    },

    // --- TAS KAGIT MAKAS ---
    _rps() {
        this.showMotorPanel("Tas Kagit Makas sec", "Basla");
        this._addButtonRow([
            { label: "Tas", callback: () => WS.sendResponse(132, { choice: 1 }) },
            { label: "Kagit", callback: () => WS.sendResponse(132, { choice: 2 }) },
            { label: "Makas", callback: () => WS.sendResponse(132, { choice: 3 }) },
        ]);
    },
};
