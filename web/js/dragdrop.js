// Yuki — Drag & Drop
//
// Kullanici el kartini mzone/szone slot'una surukleyip birakir. Motor o karta
// aksiyon sunuyorsa slot'a "pending" kart oturur, uzerinde summon/set/aktifle/
// ozel cagri/iptal popup'i acilir. Hic aksiyon yoksa veya yanlis zone ise
// spring-back animasyonu ile ele geri doner — motora mesaj gitmez.
//
// Alternatif giris: Mevcut action panel (mp-actions) aynen calisir, ikisi de
// ayni SELECT_IDLECMD listesine basar. Kullanici tercih ettigi yolu kullanir.
//
// Touch uyumlu: pointer events, 8px drag threshold. touch.js long-press (400ms)
// ile coexistence — 8px hareket once long-press'i iptal eder (kendi 5px
// threshold'uyla), drag kendi threshold'unda aktif olur.

const DRAG_THRESHOLD = 4;     // px — bu kadar hareket sonrasi drag aktif
const FIELD_SPELL_SLOT = 5;   // szone 5 = field spell zone

const DragDrop = {
    armed: null,      // pointerdown sonrasi threshold bekliyor: {card, rect, code, handIndex, pointerId, startX, startY, actions, validSlots}
    dragging: null,   // threshold asildi: {ghost, offsetX, offsetY, origRect, ...}
    pendingSlot: null, // drop sonrasi popup acik: {slotEl, vs, originalCard}

    _suppressClick: false,

    init() {
        document.addEventListener("pointerdown", this._onDown.bind(this), true);
        document.addEventListener("pointermove", this._onMove.bind(this), true);
        document.addEventListener("pointerup", this._onUp.bind(this), true);
        document.addEventListener("pointercancel", this._cancel.bind(this), true);
        // Browser native HTML5 drag'i yut — img elementi varsayilan olarak
        // draggable:true, tutunca "no-drop" cursor gosterir ve pointer event'leri
        // calismaz. Hand-card ile ilgili herhangi bir native drag'i iptal et.
        document.addEventListener("dragstart", (e) => {
            if (e.target && e.target.closest && e.target.closest(".hand-card,.card-face,.drag-ghost")) {
                e.preventDefault();
            }
        }, true);
        // Drag sonrasi patlayan synthetic click'i yut — hand-card preview /
        // highlight menu yanlislikla tetiklenmesin.
        document.addEventListener("click", (e) => {
            if (this._suppressClick) {
                e.stopPropagation();
                e.preventDefault();
                this._suppressClick = false;
            }
        }, true);
    },

    _onDown(e) {
        if (e.pointerType === "mouse" && e.button !== 0) return;
        if (this.pendingSlot) return;  // Popup aktifse drag yok

        const card = e.target.closest(".hand-card");
        if (!card) return;

        const dbg = (...a) => { if (window.YUKI_DEBUG_DRAG) console.log("[dd]", ...a); };
        dbg("pointerdown on hand-card", card);

        // Sadece kendi elimizdeki kartlar
        const handEl = document.getElementById("hand");
        if (!handEl || !handEl.contains(card)) { dbg("skip: not in #hand"); return; }

        // Bir SELECT aktif mi? (IDLECMD=11 veya BATTLECMD=10 — her ikisinde de
        // el aksiyonu olabilir). Aksiyon listesi bos ise zaten return edilir.
        const select = (typeof UI !== "undefined") ? UI.currentSelect : null;
        if (!select) { dbg("skip: no UI.currentSelect"); return; }

        const code = +(card.dataset.code || 0);
        const handIndex = +(card.dataset.index || 0);
        if (!code) { dbg("skip: code=0"); return; }

        // Bu kart icin aksiyon var mi?
        const actions = this._actionsForHandCard(code, select);
        dbg("actions for code", code, actions);
        if (actions.length === 0) { dbg("skip: no actions for this card"); return; }

        const validSlots = this._validSlotsForActions(actions);
        dbg("validSlots", validSlots);
        if (validSlots.length === 0) { dbg("skip: no valid slots"); return; }
        dbg("ARMED — move >= " + DRAG_THRESHOLD + "px baslat");

        // Arm: threshold'a kadar bekle
        this.armed = {
            card, code, handIndex, actions, validSlots,
            pointerId: e.pointerId,
            startX: e.clientX, startY: e.clientY,
            rect: card.getBoundingClientRect(),
        };
    },

    _onMove(e) {
        // Drag aktif — ghost hareket ettir + hover feedback
        if (this.dragging) {
            if (e.pointerId !== this.dragging.pointerId) return;
            const d = this.dragging;
            d.ghost.style.left = (e.clientX - d.offsetX) + "px";
            d.ghost.style.top = (e.clientY - d.offsetY) + "px";
            this._updateHoverSlot(e.clientX, e.clientY);
            e.preventDefault();
            return;
        }

        // Armed — threshold aşıldı mı?
        if (!this.armed) return;
        if (e.pointerId !== this.armed.pointerId) return;

        const dx = e.clientX - this.armed.startX;
        const dy = e.clientY - this.armed.startY;
        if (dx * dx + dy * dy < DRAG_THRESHOLD * DRAG_THRESHOLD) return;

        this._startDrag(e);
        e.preventDefault();
    },

    _onUp(e) {
        if (this.dragging) {
            if (e.pointerId !== this.dragging.pointerId) return;
            this._suppressClick = true;
            this._commitOrRollback(e.clientX, e.clientY);
            return;
        }
        // Armed ama hic hareket etmedi — normal click'e birak
        this.armed = null;
    },

    _cancel() {
        this.armed = null;
        if (this.dragging) this._rollback();
    },

    _startDrag(e) {
        const a = this.armed;
        this.armed = null;

        const ghost = a.card.cloneNode(true);
        // Menu/popup icerigi kopyalanmasin
        ghost.querySelectorAll(".card-menu, .card-popup").forEach(n => n.remove());
        ghost.classList.add("drag-ghost");
        ghost.style.position = "fixed";
        ghost.style.left = a.rect.left + "px";
        ghost.style.top = a.rect.top + "px";
        ghost.style.width = a.rect.width + "px";
        ghost.style.height = a.rect.height + "px";
        ghost.style.pointerEvents = "none";
        ghost.style.zIndex = "9999";
        ghost.style.transition = "none";
        document.body.appendChild(ghost);

        a.card.classList.add("dragging-source");

        // Valid slot'lari highlight et
        a.validSlots.forEach(vs => {
            const zoneEl = document.getElementById(vs.zoneId);
            if (!zoneEl) return;
            const slotEls = zoneEl.querySelectorAll(".card-slot");
            if (slotEls[vs.slot]) slotEls[vs.slot].classList.add("valid-drop");
        });

        this.dragging = {
            ghost,
            pointerId: a.pointerId,
            card: a.card,
            code: a.code,
            handIndex: a.handIndex,
            actions: a.actions,
            validSlots: a.validSlots,
            offsetX: a.startX - a.rect.left,
            offsetY: a.startY - a.rect.top,
            origRect: a.rect,
        };

        // Ilk pozisyonu güncelle (e'nin mevcut konumunda)
        ghost.style.left = (e.clientX - this.dragging.offsetX) + "px";
        ghost.style.top = (e.clientY - this.dragging.offsetY) + "px";
        this._updateHoverSlot(e.clientX, e.clientY);
    },

    _updateHoverSlot(x, y) {
        document.querySelectorAll(".card-slot.hover-drop").forEach(s => s.classList.remove("hover-drop"));
        const el = document.elementFromPoint(x, y);
        const slot = el && el.closest && el.closest(".card-slot.valid-drop");
        if (slot) slot.classList.add("hover-drop");
    },

    _commitOrRollback(x, y) {
        const el = document.elementFromPoint(x, y);
        const slot = el && el.closest && el.closest(".card-slot.valid-drop");
        if (slot) {
            const zoneEl = slot.parentElement;
            const slotIndex = Array.from(zoneEl.children).indexOf(slot);
            const vs = this.dragging.validSlots.find(v => v.zoneId === zoneEl.id && v.slot === slotIndex);
            if (vs) {
                this._commitDrop(vs);
                return;
            }
        }
        this._rollback();
    },

    _cleanupHighlights() {
        document.querySelectorAll(".card-slot.valid-drop, .card-slot.hover-drop").forEach(s => {
            s.classList.remove("valid-drop", "hover-drop");
        });
    },

    _commitDrop(vs) {
        const d = this.dragging;
        this.dragging = null;
        this._cleanupHighlights();
        d.card.classList.remove("dragging-source");
        d.ghost.remove();

        const zoneEl = document.getElementById(vs.zoneId);
        const slotEl = zoneEl && zoneEl.querySelectorAll(".card-slot")[vs.slot];
        if (!slotEl) { this._softRender(); return; }

        // Pending kart goster
        slotEl.innerHTML = "";
        const face = document.createElement("div");
        face.className = "card-face pending";
        const img = document.createElement("img");
        img.src = cardImageUrl(d.code);
        face.appendChild(img);

        // Popup menu
        const popup = document.createElement("div");
        popup.className = "drop-popup";
        d.actions.forEach(a => {
            // Slot icin uygun aksiyon mu? (monster aksiyonlari mzone'a, spell aksiyonlari szone'a)
            if (!this._actionMatchesSlot(a, vs)) return;
            const btn = document.createElement("button");
            btn.className = "popup-btn " + (a.cls || "gold");
            btn.textContent = a.label;
            btn.onclick = (ev) => { ev.stopPropagation(); this._chooseAction(a, vs); };
            popup.appendChild(btn);
        });
        const cancelBtn = document.createElement("button");
        cancelBtn.className = "popup-btn cancel";
        cancelBtn.textContent = "Iptal";
        cancelBtn.onclick = (ev) => { ev.stopPropagation(); this._cancelDrop(); };
        popup.appendChild(cancelBtn);
        face.appendChild(popup);

        slotEl.appendChild(face);
        this.pendingSlot = { slotEl, vs, code: d.code };
    },

    _chooseAction(action, vs) {
        if (window.YUKI_DEBUG_DRAG) console.log("[dd] chooseAction", action, "slot", vs);
        // Deferred SELECT_PLACE — motor slot sorarsa kullanicinin sectigi slot'u yanitla
        if (typeof UI !== "undefined") {
            UI._deferredPlace = {
                controller: vs.controller,
                location: vs.location,
                sequence: vs.slot,
            };
        }
        // Pending state'i temizle (motor cevabi snapshot ile gelecek)
        this.pendingSlot = null;
        // Aksiyonu tetikle — callback WS.sendResponse cagirir
        try { action.callback(); } catch (e) { console.error("[dragdrop] action error", e); }
        // Slot pending class'ini kaldirmak icin render
        this._softRender();
    },

    _cancelDrop() {
        this.pendingSlot = null;
        this._softRender();
    },

    _softRender() {
        if (typeof Field !== "undefined" && Field.render) Field.render();
    },

    _rollback() {
        const d = this.dragging;
        this.dragging = null;
        this._cleanupHighlights();
        if (!d) return;
        d.card.classList.remove("dragging-source");

        // Spring-back animasyonu
        d.ghost.style.transition = "left 0.32s cubic-bezier(.2,1.2,.3,1), top 0.32s cubic-bezier(.2,1.2,.3,1), opacity 0.28s ease-out";
        d.ghost.style.left = d.origRect.left + "px";
        d.ghost.style.top = d.origRect.top + "px";
        d.ghost.style.opacity = "0";
        setTimeout(() => { try { d.ghost.remove(); } catch(_) {} }, 360);
    },

    // ========================================================================
    //  ACTION DISCOVERY
    // ========================================================================

    // SELECT_IDLECMD / SELECT_BATTLECMD listelerinde kod ile eslesen el
    // aksiyonlarini bul. Sadece location=0x02 (hand) olanlar — sahadaki ayni
    // kodlu kart icin aksiyon drag kapsaminda degil.
    _actionsForHandCard(code, select) {
        const actions = [];
        const respType = select.type;  // 11=IDLECMD, 10=BATTLECMD
        const map = [
            ["summonable",         "Cagir",        "summon",   "gold"],
            ["special_summonable", "Ozel Cagir",   "spsummon", "gold"],
            ["monster_setable",    "Set",          "mset",     "dim"],
            ["spell_setable",      "Set",          "sset",     "dim"],
            ["activatable",        "Aktifle",      "activate", "purple"],
        ];
        map.forEach(([key, label, actionType, cls]) => {
            const list = select[key] || [];
            list.forEach((c, i) => {
                if (c.code !== code) return;
                const loc = c.location || 0;
                if (loc !== 0x02) return;  // sadece hand'den
                actions.push({
                    label, cls, actionType, index: i,
                    zoneHint: (actionType === "sset" || actionType === "activate") ? "szone" :
                              "mzone",  // summon / spsummon / mset
                    callback: () => WS.sendResponse(respType, { action: actionType, index: i }),
                });
            });
        });
        return actions;
    },

    _validSlotsForActions(actions) {
        const selfTeam = Field.myTeam;
        const slots = [];
        const hasMzone = actions.some(a => a.zoneHint === "mzone");
        const hasSzone = actions.some(a => a.zoneHint === "szone");

        if (hasMzone) {
            for (let i = 0; i < 5; i++) {
                if (!Field.cards[selfTeam].mzone[i]) {
                    slots.push({ zoneId: "self-mzone", slot: i, controller: selfTeam, location: 0x04 });
                }
            }
        }
        if (hasSzone) {
            for (let i = 0; i < 5; i++) {
                if (!Field.cards[selfTeam].szone[i]) {
                    slots.push({ zoneId: "self-szone", slot: i, controller: selfTeam, location: 0x08 });
                }
            }
            // Field spell slot (szone 5) — aktivatable field spell icin
            if (!Field.cards[selfTeam].szone[FIELD_SPELL_SLOT]) {
                slots.push({ zoneId: "self-szone", slot: FIELD_SPELL_SLOT, controller: selfTeam, location: 0x08 });
            }
        }
        return slots;
    },

    _actionMatchesSlot(action, vs) {
        if (vs.location === 0x04) return action.zoneHint === "mzone";
        if (vs.location === 0x08) return action.zoneHint === "szone";
        return false;
    },
};

// DOM hazir olunca bagla
if (document.readyState === "loading") {
    document.addEventListener("DOMContentLoaded", () => DragDrop.init());
} else {
    DragDrop.init();
}
