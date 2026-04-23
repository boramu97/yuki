// Yuki — D3 Field Renderer

function cardImageUrl(code) {
    return code ? `https://images.ygoprodeck.com/images/cards_small/${code}.jpg` : "";
}
function cardImageUrlFull(code) {
    return code ? `https://images.ygoprodeck.com/images/cards/${code}.jpg` : "";
}
function cardBackHTML() {
    return '<div class="card-back-inner"><div class="card-back-oval"></div></div>';
}

const Field = {
    myTeam: -1, lp: [8000,8000], startLp: 8000, turn: 0,
    cards: {},

    init(team) {
        this.myTeam = team; this.lp = [8000,8000]; this.startLp = 8000; this.turn = 0;
        this.cards = {
            0:{mzone:{},szone:{},hand:[],grave:[],exile:[]},
            1:{mzone:{},szone:{},hand:[],grave:[],exile:[]},
        };
        this.render();
    },
    selfTeam() { return this.myTeam; },
    oppTeam() { return 1 - this.myTeam; },

    updateLP(player, newLp) {
        this.lp[player] = Math.max(0, newLp);
        const isSelf = player === this.myTeam;
        const el = document.getElementById(isSelf ? "self-lp" : "opp-lp");
        const bar = document.getElementById(isSelf ? "self-lp-bar" : "opp-lp-bar");
        el.textContent = this.lp[player]; el.classList.add("lp-hit");
        setTimeout(() => el.classList.remove("lp-hit"), 600);
        bar.style.width = Math.max(0, (this.lp[player] / this.startLp) * 100) + "%";
    },
    damageLP(p, a) { this.updateLP(p, this.lp[p] - a); },
    recoverLP(p, a) { this.updateLP(p, this.lp[p] + a); },

    setTurn(n) {
        this.turn = n;
        const r=["","I","II","III","IV","V","VI","VII","VIII","IX","X","XI","XII","XIII","XIV","XV","XVI","XVII","XVIII","XIX","XX"];
        document.getElementById("turn-counter").textContent = n <= 20 ? r[n] : n.toString();
    },
    setPhase(code) {
        const n={0x01:"Draw",0x02:"Standby",0x04:"Main Phase",0x08:"Battle",0x10:"Battle Step",0x20:"Damage",0x40:"Damage Cal",0x80:"Battle",0x100:"Main Phase 2",0x200:"End Phase"};
        document.getElementById("phase-name").textContent = n[code] || "—";
        const hud = document.querySelector(".phase-hud");
        if (hud) {
            hud.classList.remove("phase-battle","phase-end","phase-draw");
            if (code === 0x01) hud.classList.add("phase-draw");
            else if (code & 0xF8) hud.classList.add("phase-battle");
            else if (code === 0x200) hud.classList.add("phase-end");
        }
    },
    setStatus(text) {
        document.getElementById("status-text").textContent = text;
    },

    getCardAt(con, loc, seq) {
        const z = loc===0x04?"mzone":loc===0x08?"szone":null;
        return z ? this.cards[con]?.[z]?.[seq] || null : null;
    },

    // Server snapshot'tan gelen kart kaydini normalize et (render'in bekledigi
    // alan isimleri: card_atk / card_def / card_type).
    _normalizeSnapshotCard(c) {
        if (!c) return null;
        return {
            code: c.code || 0,
            position: c.position || 0,
            card_name: c.card_name || "",
            card_atk: c.atk !== undefined ? c.atk : c.card_atk,
            card_def: c.def !== undefined ? c.def : c.card_def,
            card_type: c.type !== undefined ? c.type : (c.card_type || 0),
            card_level: c.level || 0,
            overlays: c.overlays || [],
            counters: c.counters || null,
            equip: c.equip || null,
        };
    },

    // Motor otoriteli saha snapshot'ini uygula. mzone/szone/grave/exile
    // tamamen replace edilir — event-driven drift imkansiz.
    applyFieldSnapshot(field) {
        if (!field) return;
        if (window.YUKI_DEBUG_SYNC) {
            console.log("[field_sync] mzone self:", field.mzone && field.mzone[String(this.myTeam)]);
            console.log("[field_sync] szone self:", field.szone && field.szone[String(this.myTeam)]);
        }
        for (const team of [0, 1]) {
            const key = String(team);
            const bucket = this.cards[team];
            if (!bucket) continue;
            const mz = (field.mzone && field.mzone[key]) || [];
            const sz = (field.szone && field.szone[key]) || [];
            bucket.mzone = {};
            bucket.szone = {};
            mz.forEach((c, i) => { const n = this._normalizeSnapshotCard(c); if (n) bucket.mzone[i] = n; });
            sz.forEach((c, i) => { const n = this._normalizeSnapshotCard(c); if (n) bucket.szone[i] = n; });
            const gr = (field.grave && field.grave[key]) || [];
            const ex = (field.exile && field.exile[key]) || [];
            bucket.grave = gr.map(c => this._normalizeSnapshotCard(c)).filter(Boolean);
            bucket.exile = ex.map(c => this._normalizeSnapshotCard(c)).filter(Boolean);
        }
        this.render();
    },

    render() {
        this._renderZone("self-mzone",this.selfTeam(),"mzone");
        this._renderZone("opp-mzone",this.oppTeam(),"mzone");
        this._renderZone("self-szone",this.selfTeam(),"szone");
        this._renderZone("opp-szone",this.oppTeam(),"szone");
        this._renderHand();
        this._renderOppHand();
        this._renderGraveCount();
    },

    _renderGraveCount() {
        const selfG=this.cards[this.selfTeam()]?.grave||[];
        const oppG=this.cards[this.oppTeam()]?.grave||[];
        const se=document.getElementById("self-grave-count");
        const oe=document.getElementById("opp-grave-count");
        if(se) se.textContent=selfG.length;
        if(oe) oe.textContent=oppG.length;
    },

    openGraveViewer(team) {
        const grave=this.cards[team]?.grave||[];
        const overlay=document.getElementById("grave-viewer-overlay");
        const container=document.getElementById("grave-viewer-cards");
        const title=document.getElementById("grave-viewer-title");
        if(!overlay||!container) return;
        title.textContent=team===this.myTeam?"Mezarlığın":"Rakip Mezarlık";
        container.innerHTML="";
        if(grave.length===0){
            container.innerHTML='<div class="grave-empty">Mezarlık boş</div>';
        } else {
            // En son eklenen uste gelsin
            [...grave].reverse().forEach(card=>{
                const tile=document.createElement("div");
                tile.className="grave-card-tile";
                if(card.code){
                    const img=document.createElement("img");
                    img.src=cardImageUrl(card.code); img.loading="lazy";
                    img.onclick=(e)=>{
                        e.stopPropagation();
                        document.getElementById("preview-img").src=cardImageUrlFull(card.code);
                        document.getElementById("card-preview-overlay").classList.add("active");
                    };
                    tile.appendChild(img);
                }
                const name=document.createElement("div");
                name.className="grave-card-name";
                name.textContent=card.card_name||`#${card.code}`;
                tile.appendChild(name);
                container.appendChild(tile);
            });
        }
        overlay.classList.add("active");
    },

    _renderOppHand() {
        const el=document.getElementById("opp-hand"); if(!el) return;
        const hand=this.cards[this.oppTeam()]?.hand||[];
        // Sadece kart elementlerini sil — console-info panel'leri koru
        el.querySelectorAll(".opp-hand-card").forEach(c=>c.remove());
        hand.forEach(()=>{
            const div=document.createElement("div");
            div.className="opp-hand-card";
            div.innerHTML=cardBackHTML();
            el.appendChild(div);
        });
    },

    _renderZone(elId, team, zone) {
        const el=document.getElementById(elId); if(!el) return;
        const slots=el.querySelectorAll(".card-slot");
        const data=this.cards[team][zone];
        slots.forEach((slot,i) => {
            slot.innerHTML="";
            const card=data[i]; if(!card) return;
            const pos=card.position||0;
            const isFD=(pos&0x0A)!==0, isDef=(pos&0x0C)!==0, isMon=!!(card.card_type&0x1);
            const face=document.createElement("div");
            face.className="card-face";
            face.dataset.code=card.code||0;
            face.dataset.controller=team;
            face.dataset.location=zone==="mzone"?4:8;
            face.dataset.sequence=i;

            if(isFD){
                face.classList.add("facedown");
                if(isDef&&zone==="mzone") face.classList.add("defense-monster");
                face.innerHTML=cardBackHTML();
            } else {
                if(isDef&&isMon) face.classList.add("defense-monster");
                const img=document.createElement("img");
                img.src=cardImageUrl(card.code); img.loading="lazy";
                img.onerror=function(){this.style.display="none";face.style.background="#1c1a10";face.style.display="flex";face.style.alignItems="center";face.style.justifyContent="center";face.style.fontSize="0.6vw";face.style.color="#a09070";face.textContent=card.card_name||"#"+card.code;};
                face.appendChild(img);
                if(isMon&&card.card_atk!==undefined){
                    const st=document.createElement("div");st.className="card-stats-bar";
                    st.innerHTML=`<span class="atk">${card.card_atk}</span><span class="def">${card.card_def}</span>`;
                    face.appendChild(st);
                }
                if(card.counters){
                    const entries=Object.entries(card.counters).filter(([,v])=>v>0);
                    if(entries.length>0){
                        const wrap=document.createElement("div");
                        wrap.className="counter-stack";
                        entries.forEach(([type,count])=>{
                            const b=document.createElement("div");
                            b.className="counter-badge";
                            b.dataset.counterType=type;
                            b.textContent=count;
                            b.title=`Sayaç #${type}`;
                            wrap.appendChild(b);
                        });
                        face.appendChild(wrap);
                    }
                }
                if(card.equip){face.classList.add("card-equipped");}
            }
            // Menu container (ui.js dolduracak)
            const menu=document.createElement("div");
            menu.className="card-menu";
            menu.dataset.slotId=`${team}-${zone}-${i}`;
            face.appendChild(menu);
            slot.appendChild(face);
        });
    },

    _renderHand() {
        const el=document.getElementById("hand"); if(!el) return;
        // Sadece kart elementlerini sil — console-info panel'leri koru
        el.querySelectorAll(".hand-card").forEach(c=>c.remove());
        this.cards[this.myTeam].hand.forEach((card,i) => {
            const div=document.createElement("div");
            div.className="hand-card"; div.dataset.index=i; div.dataset.code=card.code;
            if(card.code){
                const img=document.createElement("img");
                img.src=cardImageUrl(card.code); img.loading="lazy";
                img.onerror=function(){this.style.display="none";const f=document.createElement("div");f.style.cssText="flex:1;display:flex;align-items:center;justify-content:center;font-size:0.5vw;color:#a09070;text-align:center;padding:4px";f.textContent=card.card_name||"#"+card.code;div.insertBefore(f,div.firstChild);};
                div.appendChild(img);
                if((card.card_type&0x1)&&card.card_atk!==undefined){
                    const st=document.createElement("div");st.className="card-stats-bar";
                    st.innerHTML=`<span class="atk">${card.card_atk}</span><span class="def">${card.card_def}</span>`;
                    div.appendChild(st);
                }
            } else {
                div.style.background="#6b4c2a"; div.style.border="2px solid #b8960a";
                div.innerHTML=cardBackHTML();
            }
            // Menu container
            const menu=document.createElement("div");
            menu.className="card-menu"; menu.dataset.handIndex=i;
            div.appendChild(menu);
            el.appendChild(div);
        });
    },
};

// Sag tik onizleme — saha, el ve log gorselleri
document.addEventListener("contextmenu",(e)=>{
    // 1. Saha/el kartlari
    const card=e.target.closest(".hand-card,.card-face");
    if(card){
        e.preventDefault();
        if(card.classList.contains("facedown")){
            const slot=card.closest(".card-slot");
            const zone=slot?.parentElement;
            if(zone&&(zone.id==="opp-mzone"||zone.id==="opp-szone")) return;
        }
        const code=card.dataset?.code||card.closest("[data-code]")?.dataset?.code;
        if(code&&code!=="0"){
            document.getElementById("preview-img").src=cardImageUrlFull(code);
            document.getElementById("preview-name").textContent="";
            document.getElementById("card-preview-overlay").classList.add("active");
        }
        return;
    }
    // 2. Log banner gorselleri
    const logImg=e.target.closest(".log-banner img, .mp-card-img");
    if(logImg && logImg.src){
        e.preventDefault();
        const src=logImg.src;
        const match=src.match(/\/(\d+)\.jpg/);
        if(match){
            document.getElementById("preview-img").src=cardImageUrlFull(match[1]);
            document.getElementById("preview-name").textContent="";
            document.getElementById("card-preview-overlay").classList.add("active");
        }
    }
});
document.getElementById("card-preview-overlay")?.addEventListener("click",function(){this.classList.remove("active")});

// Kart tikla → highlight varsa popup, yoksa preview
// NOT: el kartlari icin sol tik preview ACMAZ — o onizleme sag tik /
// long-press ile acilir. El kartinin sol tiki drag&drop icin reservelidir.
document.addEventListener("click",(e)=>{
    // Popup butonuna tiklandi
    if(e.target.closest(".popup-btn")) return;

    // Mevcut popup'lari kapat
    document.querySelectorAll(".card-popup.open").forEach(p=>p.remove());

    // El kartlari: sol tik drag icin, preview sag tik/long-press'le acilir
    if(e.target.closest(".hand-card")) return;

    const card=e.target.closest(".card-face");
    if(!card) return;

    // Highlight yoksa → preview ac
    if(!card.classList.contains("mp-highlight")){
        if(card.classList.contains("facedown")){
            const slot=card.closest(".card-slot");
            const zone=slot?.parentElement;
            if(zone&&(zone.id==="opp-mzone"||zone.id==="opp-szone")) return;
        }
        const code=card.dataset?.code||card.closest("[data-code]")?.dataset?.code;
        if(code&&code!=="0"){
            document.getElementById("preview-img").src=cardImageUrlFull(code);
            document.getElementById("preview-name").textContent="";
            document.getElementById("card-preview-overlay").classList.add("active");
        }
        return;
    }

    // Highlight var → popup menu
    const actionsJson=card.dataset.popupActions;
    if(!actionsJson) return;

    let actions;
    try { actions=JSON.parse(actionsJson); } catch { return; }
    if(!actions.length) return;

    // Popup olustur
    const popup=document.createElement("div");
    popup.className="card-popup open";
    actions.forEach(a=>{
        const btn=document.createElement("button");
        btn.className="popup-btn "+(a.cls||"");
        btn.textContent=a.label;
        btn.onclick=(ev)=>{
            ev.stopPropagation();
            popup.remove();
            // Callback index'i kullanarak WS.sendResponse cagir
            if(a.callback){
                // callback serialized degilse dogrudan cagir
                // Gercek oyunda _idleCmd zaten callback'leri bind ediyor
            }
            // Panel uzerinden ayni aksiyonu tetikle — paneldeki butonu bul ve tikla
            const panel=document.getElementById("mp-actions");
            if(panel){
                const tiles=panel.querySelectorAll(".mp-action-card");
                tiles.forEach(tile=>{
                    const img=tile.querySelector(".mp-card-img");
                    if(img && img.src.includes(card.dataset.code)){
                        const btns=tile.querySelectorAll(".mp-btn");
                        btns.forEach(b=>{
                            if(b.textContent.trim().toUpperCase()===a.label.toUpperCase()) b.click();
                        });
                    }
                });
            }
        };
        popup.appendChild(btn);
    });

    card.style.position=card.style.position||"relative";
    card.appendChild(popup);
    e.stopPropagation();
});

// Motor panel toggle — handle ve minimize butonu
document.getElementById("mp-swipe-handle")?.addEventListener("click",(e)=>{e.stopPropagation();UI.toggleMotorPanel();});
document.getElementById("mp-minimize-btn")?.addEventListener("click",(e)=>{e.stopPropagation();UI.toggleMotorPanel();});

// Mezarlik zone tiklama
document.getElementById("self-grave")?.addEventListener("click",()=>Field.openGraveViewer(Field.selfTeam()));
document.getElementById("opp-grave")?.addEventListener("click",()=>Field.openGraveViewer(Field.oppTeam()));
document.getElementById("grave-viewer-overlay")?.addEventListener("click",(e)=>{if(e.target.id==="grave-viewer-overlay")e.target.classList.remove("active")});
document.getElementById("grave-viewer-close")?.addEventListener("click",()=>document.getElementById("grave-viewer-overlay")?.classList.remove("active"));

// Mobil drawer tab degistirme
document.querySelectorAll(".drawer-tab").forEach(tab=>{
    tab.addEventListener("click",()=>{
        document.querySelectorAll(".drawer-tab").forEach(t=>t.classList.remove("active"));
        document.querySelectorAll(".drawer-pane").forEach(p=>p.classList.remove("active"));
        tab.classList.add("active");
        const pane=document.getElementById("drawer-"+tab.dataset.drawer);
        if(pane) pane.classList.add("active");
    });
});

