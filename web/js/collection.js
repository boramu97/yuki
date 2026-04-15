// Yuki — Koleksiyon & Deste Yonetimi

const Collection = {
    allCards: [],       // Tum kart havuzu [{c,n,t,a,d,l}]
    myCards: new Set(), // Kullanicinin koleksiyonu (kod seti)
    presetDecks: {},    // {isim: [kodlar]}
    deckSlots: [
        { name: "Deste 1", cards: [] },
        { name: "Deste 2", cards: [] },
        { name: "Deste 3", cards: [] },
    ],
    activeSlot: 0,
    activeDeckSlot: 0,  // Sunucudaki aktif deste slotu
    filter: "all",
    search: "",
    deckFilter: "",

    dust: 0,

    // Limited kartlar: max 1 kopya
    LIMITED_1: new Set([83764718, 55144522]), // Monster Reborn, Pot of Greed

    // Tier sistemi
    DUST_TABLE: {S:{dis:25,craft:100},A:{dis:15,craft:60},B:{dis:8,craft:30},C:{dis:3,craft:10}},

    cardTier(card) {
        if (!card) return "B";
        if (card.t === "spell" || card.t === "trap") return "B";
        if (card.a >= 2500) return "S";
        if (card.a >= 1800) return "A";
        if (card.a < 1000) return "C";
        return "B";
    },

    craftCost(card) { return this.DUST_TABLE[this.cardTier(card)].craft; },
    disCost(card) { return this.DUST_TABLE[this.cardTier(card)].dis; },

    IMG: (code) => `https://images.ygoprodeck.com/images/cards_small/${code}.jpg`,
    IMG_BIG: (code) => `https://images.ygoprodeck.com/images/cards/${code}.jpg`,

    deck() { return this.deckSlots[this.activeSlot].cards; },
    countInDeck(code) { return this.deck().filter(c => c === code).length; },
    maxCopies(code) { return this.LIMITED_1.has(code) ? 1 : 3; },
    isMonster(t) { return t === "monster" || t === "fusion"; },

    open() {
        UI.showScreen("collection-screen");
        WS.getCollection();
        WS.getDecks();
    },

    init(data) {
        this.allCards = data.card_pool || [];
        this.myCards = new Set(data.cards || []);
        this.presetDecks = data.preset_decks || {};
        this.dust = data.dust || 0;

        // Deste filtresi dropdown doldur
        const sel = document.getElementById("coll-deck-filter");
        sel.innerHTML = '<option value="">Tum Kartlar</option>';
        for (const name of Object.keys(this.presetDecks)) {
            const opt = document.createElement("option");
            opt.value = name;
            opt.textContent = name + " (" + this.presetDecks[name].length + ")";
            sel.appendChild(opt);
        }

        document.getElementById("coll-count").textContent =
            this.myCards.size + " / " + this.allCards.length + " kart";
        this.updateDust();

        this.render();
        this.renderSlotTabs();
    },

    loadDecks(decks) {
        for (const d of decks) {
            if (d.slot >= 0 && d.slot <= 2) {
                this.deckSlots[d.slot].name = d.name;
                this.deckSlots[d.slot].cards = d.cards || [];
            }
        }
        document.getElementById("coll-deck-name").value = this.deckSlots[this.activeSlot].name;
        this.renderSlotTabs();
        this.renderDeck();
        this.render(); // Grid'deki in-deck badge'leri guncelle
    },

    getFiltered() {
        let cards = this.allCards;

        if (this.deckFilter && this.presetDecks[this.deckFilter]) {
            const codes = new Set(this.presetDecks[this.deckFilter]);
            cards = cards.filter(c => codes.has(c.c));
        }
        if (this.filter === "monster") {
            cards = cards.filter(c => this.isMonster(c.t));
        } else if (this.filter !== "all") {
            cards = cards.filter(c => c.t === this.filter);
        }
        if (this.search) {
            const q = this.search.toLowerCase();
            cards = cards.filter(c => c.n.toLowerCase().includes(q));
        }
        cards.sort((a, b) => {
            const ao = this.myCards.has(a.c) ? 0 : 1;
            const bo = this.myCards.has(b.c) ? 0 : 1;
            if (ao !== bo) return ao - bo;
            return a.n.localeCompare(b.n);
        });
        return cards;
    },

    render() {
        const filtered = this.getFiltered();
        const grid = document.getElementById("coll-grid");
        const info = document.getElementById("coll-results");

        const dkCodes = this.deckFilter && this.presetDecks[this.deckFilter]
            ? new Set(this.presetDecks[this.deckFilter]) : null;
        const ownedInDk = dkCodes ? [...dkCodes].filter(c => this.myCards.has(c)).length : 0;

        if (this.deckFilter) {
            info.innerHTML = `<span class="hl">${this.deckFilter}</span> — ${filtered.length} kart (elinde: <span class="hl">${ownedInDk}</span>/${dkCodes.size})`;
        } else if (this.search) {
            info.innerHTML = `"${this.search}" icin <span class="hl">${filtered.length}</span> sonuc`;
        } else {
            info.textContent = filtered.length + " kart";
        }

        // Tip sayaclari
        const src = dkCodes ? this.allCards.filter(c => dkCodes.has(c.c)) : this.allCards;
        document.getElementById("cnt-all").textContent = src.length;
        document.getElementById("cnt-monster").textContent = src.filter(c => this.isMonster(c.t)).length;
        document.getElementById("cnt-spell").textContent = src.filter(c => c.t === "spell").length;
        document.getElementById("cnt-trap").textContent = src.filter(c => c.t === "trap").length;

        if (!filtered.length) {
            grid.innerHTML = '<div style="text-align:center;padding:40px;color:var(--text-muted);font-style:italic">Kart bulunamadi</div>';
            return;
        }

        grid.innerHTML = filtered.map(card => {
            const owned = this.myCards.has(card.c);
            const copies = this.countInDeck(card.c);
            const cls = [
                "coll-card",
                owned ? "" : "locked",
                copies > 0 ? "in-deck" : "",
            ].join(" ");

            let badge = "";
            if (dkCodes) {
                badge = owned
                    ? '<span class="coll-deck-badge owned">Var</span>'
                    : '<span class="coll-deck-badge missing">Eksik</span>';
            }
            const copyBadge = copies > 0 ? `<span class="coll-copy-badge">x${copies}</span>` : "";

            return `<div class="${cls}" onclick="Collection.preview(${card.c})">
                <span class="coll-lock">&#x1F512;</span>
                ${badge}${copyBadge}
                <img class="coll-card-img" src="${this.IMG(card.c)}" alt="${card.n}" loading="lazy">
                <div class="coll-card-info">
                    <div class="coll-card-name"><span class="coll-type-dot ${card.t}"></span>${card.n}</div>
                    ${this.isMonster(card.t) && card.a >= 0 ? `<div class="coll-card-stats"><span class="atk">ATK ${card.a}</span> / <span class="def">DEF ${card.d}</span></div>` : ""}
                </div>
            </div>`;
        }).join("");

        this.renderDeck();
    },

    renderDeck() {
        const dk = this.deck();
        const codeSet = new Set(dk);
        const deckCards = this.allCards.filter(c => codeSet.has(c.c));
        const monsters = deckCards.filter(c => this.isMonster(c.t));
        const spells = deckCards.filter(c => c.t === "spell");
        const traps = deckCards.filter(c => c.t === "trap");
        const list = document.getElementById("coll-deck-list");

        let html = "";
        const section = (title, cls, cards) => {
            if (!cards.length) return "";
            let s = `<div class="coll-dk-section"><div class="coll-dk-title ${cls}">${title} (${cards.reduce((n,c) => n + this.countInDeck(c.c), 0)})</div></div>`;
            s += cards.map(c => this.deckCardHTML(c)).join("");
            return s;
        };
        html += section("Canavarlar", "monster", monsters);
        html += section("Buyuler", "spell", spells);
        html += section("Tuzaklar", "trap", traps);

        list.innerHTML = html;
        document.getElementById("coll-deck-num").textContent = dk.length;
        const mobNum = document.getElementById("coll-mob-deck-num");
        if (mobNum) mobNum.textContent = dk.length;
        document.getElementById("btn-duel-with-deck").disabled = dk.length !== 40;
        this.renderSlotTabs();
    },

    deckCardHTML(c) {
        const count = this.countInDeck(c.c);
        const max = this.maxCopies(c.c);
        const lbl = max === 1 ? '<span style="color:var(--danger);font-size:0.6rem;margin-right:4px" title="Limit 1">L</span>' : "";
        const qty = count > 1 ? `<span style="font-size:0.65rem;color:var(--gold);margin-right:4px">x${count}</span>` : "";
        return `<div class="coll-dk-card" onclick="Collection.toggleDeck(${c.c})">
            <img src="${this.IMG(c.c)}" alt="${c.n}">
            ${lbl}${qty}<span class="coll-dk-card-name">${c.n}</span>
            <span class="coll-dk-card-rm" onclick="event.stopPropagation();Collection.removeOne(${c.c})">&#x2715;</span>
        </div>`;
    },

    renderSlotTabs() {
        const el = document.getElementById("coll-slots");
        el.innerHTML = this.deckSlots.map((slot, i) => {
            const cnt = slot.cards.length;
            const active = i === this.activeSlot ? "active" : "";
            const ready = cnt === 40 ? "ready" : "";
            const isActive = i === this.activeDeckSlot;
            const badge = isActive ? '<span class="slot-active-badge">AKTIF</span>' : "";
            return `<button class="coll-slot-tab ${active} ${ready} ${isActive?"is-active":""}" onclick="Collection.switchSlot(${i})">
                ${slot.name}<span class="slot-cnt">${cnt}/40</span>${badge}
            </button>`;
        }).join("");
    },

    setAsActiveDeck() {
        const slot = this.activeSlot;
        if (this.deckSlots[slot].cards.length !== 40) return;
        this.activeDeckSlot = slot;
        WS.setActiveDeck(slot);
        this.renderSlotTabs();
    },

    switchSlot(i) {
        this.saveCurrent();
        this.activeSlot = i;
        document.getElementById("coll-deck-name").value = this.deckSlots[i].name;
        this.render();
    },

    toggleDeck(code) {
        if (!this.myCards.has(code)) return;
        const count = this.countInDeck(code);
        const max = this.maxCopies(code);
        if (count > 0 && count >= max) {
            const idx = this.deck().indexOf(code);
            if (idx !== -1) this.deck().splice(idx, 1);
        } else if (count > 0) {
            if (this.deck().length < 40) this.deck().push(code);
            else { const idx = this.deck().indexOf(code); if (idx !== -1) this.deck().splice(idx, 1); }
        } else {
            if (this.deck().length < 40) this.deck().push(code);
        }
        this.render();
        this.autoSave();
    },

    removeOne(code) {
        const idx = this.deck().indexOf(code);
        if (idx !== -1) this.deck().splice(idx, 1);
        this.render();
        this.autoSave();
    },

    updateDust() {
        const el = document.getElementById("coll-dust");
        if (el) el.textContent = this.dust;
    },

    preview(code) {
        const card = this.allCards.find(c => c.c === code);
        const owned = this.myCards.has(code);
        const overlay = document.getElementById("coll-preview-overlay");
        const img = document.getElementById("coll-preview-img");
        const actions = document.getElementById("coll-preview-actions");
        img.src = this.IMG_BIG(code);
        img.className = owned ? "" : "locked";

        let html = "";

        if (card && owned) {
            // Desteye ekle/cikar butonu
            const copies = this.countInDeck(code);
            const max = this.maxCopies(code);
            if (copies < max) {
                html += `<button class="coll-prev-btn deck-add" onclick="Collection.toggleDeck(${code});Collection.preview(${code})">Desteye Ekle (${copies}/${max})</button>`;
            } else {
                html += `<button class="coll-prev-btn deck-add" disabled>Destede (${copies}/${max})</button>`;
            }
            if (copies > 0) {
                html += `<button class="coll-prev-btn deck-rm" onclick="Collection.removeOne(${code});Collection.preview(${code})">Desteden Cikar</button>`;
            }
            // Bozdur butonu
            const gain = this.disCost(card);
            const inDeck = this.isCardInAnyDeck(code);
            if (inDeck) {
                html += `<button class="coll-prev-btn dis" disabled>Destede — bozdurulamaz</button>`;
            } else {
                html += `<button class="coll-prev-btn dis" onclick="Collection.confirmDisenchant(${code}, '${card.n.replace(/'/g,"\\'")}', ${gain})">Bozdur — +${gain} toz</button>`;
            }
        } else if (card && !owned) {
            // Kilitli kart — Aç butonu
            const cost = this.craftCost(card);
            const canAfford = this.dust >= cost;
            html += `<button class="coll-prev-btn craft" ${canAfford ? "" : "disabled"} onclick="Collection.doCraft(${code})">Ac — ${cost} toz</button>`;
        }

        actions.innerHTML = html;
        overlay.classList.add("active");
    },

    isCardInAnyDeck(code) {
        return this.deckSlots.some(slot => slot.cards.includes(code));
    },

    doCraft(code) {
        WS.craftCard(code);
        document.getElementById("coll-preview-overlay").classList.remove("active");
    },

    confirmDisenchant(code, name, gain) {
        const overlay = document.getElementById("coll-confirm-overlay");
        document.getElementById("coll-confirm-text").innerHTML =
            `<strong>${name}</strong> kartini bozdurmak istedigine emin misin?<br>` +
            `<span style="color:var(--gold)">+${gain} toz</span> kazanacaksin. Bu islem geri alinamaz.`;
        document.getElementById("coll-confirm-yes").onclick = () => {
            WS.disenchantCard(code);
            overlay.classList.remove("active");
            document.getElementById("coll-preview-overlay").classList.remove("active");
        };
        overlay.classList.add("active");
    },

    // Deste otomatik kaydet (debounced)
    _saveTimer: null,
    autoSave() {
        clearTimeout(this._saveTimer);
        this._saveTimer = setTimeout(() => this.saveCurrent(), 800);
    },
    saveCurrent() {
        const slot = this.deckSlots[this.activeSlot];
        slot.name = document.getElementById("coll-deck-name").value || `Deste ${this.activeSlot + 1}`;
        WS.saveDeck(this.activeSlot, slot.name, slot.cards);
    },
};

// Event listeners
document.getElementById("coll-preview-overlay").addEventListener("click", (e) => {
    if (e.target === e.currentTarget) e.currentTarget.classList.remove("active");
});
document.getElementById("coll-preview-img").addEventListener("click", (e) => {
    e.stopPropagation();
});
document.getElementById("coll-preview-actions").addEventListener("click", (e) => {
    e.stopPropagation();
});
// Confirm dialog
document.getElementById("coll-confirm-no").addEventListener("click", () => {
    document.getElementById("coll-confirm-overlay").classList.remove("active");
});

document.querySelectorAll(".coll-filter").forEach(tab => {
    tab.addEventListener("click", () => {
        document.querySelectorAll(".coll-filter").forEach(t => t.classList.remove("active"));
        tab.classList.add("active");
        Collection.filter = tab.dataset.filter;
        Collection.render();
    });
});

let _collSearchTimer;
document.getElementById("coll-search").addEventListener("input", (e) => {
    clearTimeout(_collSearchTimer);
    _collSearchTimer = setTimeout(() => {
        Collection.search = e.target.value.trim();
        Collection.render();
    }, 200);
});

document.getElementById("coll-deck-filter").addEventListener("change", (e) => {
    Collection.deckFilter = e.target.value;
    Collection.render();
});

document.getElementById("coll-deck-name").addEventListener("input", () => {
    Collection.deckSlots[Collection.activeSlot].name =
        document.getElementById("coll-deck-name").value;
    Collection.renderSlotTabs();
    Collection.autoSave();
});

// Aktif deste yap butonu
document.getElementById("btn-duel-with-deck").addEventListener("click", () => {
    Collection.setAsActiveDeck();
});

// WS handlers
WS.on("collection", (d) => Collection.init(d));
WS.on("decks", (d) => Collection.loadDecks(d.decks));
WS.on("deck_saved", (d) => { /* sessiz */ });
WS.on("active_deck_set", (d) => { if(d.success) { Collection.activeDeckSlot = d.slot; Collection.renderSlotTabs(); } });
WS.on("craft_result", (d) => {
    Collection.dust = d.dust;
    Collection.updateDust();
    if (d.success && d.cards) {
        Collection.myCards = new Set(d.cards);
        document.getElementById("coll-count").textContent =
            Collection.myCards.size + " / " + Collection.allCards.length + " kart";
        Collection.render();
    }
});
WS.on("disenchant_result", (d) => {
    Collection.dust = d.dust;
    Collection.updateDust();
    if (d.success && d.cards) {
        Collection.myCards = new Set(d.cards);
        document.getElementById("coll-count").textContent =
            Collection.myCards.size + " / " + Collection.allCards.length + " kart";
        Collection.render();
    }
});

// Mobil koleksiyon tab degistirme
document.querySelectorAll(".coll-mob-tab").forEach(tab => {
    tab.addEventListener("click", () => {
        document.querySelectorAll(".coll-mob-tab").forEach(t => t.classList.remove("active"));
        tab.classList.add("active");
        const main = document.querySelector(".coll-main");
        if (main) main.dataset.activeTab = tab.dataset.collTab;
    });
});
