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
        this.cards = {0:{mzone:{},szone:{},hand:[]},1:{mzone:{},szone:{},hand:[]}};
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
        document.getElementById("phase-name").textContent = n[code] || "";
    },
    setStatus(text) {
        document.getElementById("status-text").textContent = text;
    },

    getCardAt(con, loc, seq) {
        const z = loc===0x04?"mzone":loc===0x08?"szone":null;
        return z ? this.cards[con]?.[z]?.[seq] || null : null;
    },
    addCounter(con, loc, seq, type, count) {
        const c = this.getCardAt(con, loc, seq); if (!c) return;
        if (!c.counters) c.counters = {}; c.counters[type] = (c.counters[type]||0) + count; this.render();
    },
    removeCounter(con, loc, seq, type, count) {
        const c = this.getCardAt(con, loc, seq); if (!c) return;
        if (!c.counters) c.counters = {}; c.counters[type] = Math.max(0,(c.counters[type]||0)-count);
        if (!c.counters[type]) delete c.counters[type]; this.render();
    },

    moveCard(code, from, to, info) {
        this._removeFrom(from.controller, from.location, from.sequence, code);
        this._addTo(to.controller, to.location, to.sequence, {code, position:to.position||0, ...(info||{})});
        this.render();
    },
    _removeFrom(con, loc, seq, code) {
        if (loc===0x04) delete this.cards[con]?.mzone[seq];
        else if (loc===0x08) delete this.cards[con]?.szone[seq];
        else if (loc===0x02) { const h=this.cards[con]?.hand; if(h){const i=h.findIndex(c=>c.code===code);if(i>=0)h.splice(i,1);} }
    },
    _addTo(con, loc, seq, data) {
        if (loc===0x04) this.cards[con].mzone[seq]=data;
        else if (loc===0x08) this.cards[con].szone[seq]=data;
        else if (loc===0x02) this.cards[con].hand.push(data);
    },
    addToHand(player, cards) {
        for (const c of cards) this.cards[player].hand.push({code:c.code||0,position:c.position||0,card_name:c.card_name||"",card_atk:c.card_atk,card_def:c.card_def,card_type:c.card_type||0});
        this.render();
    },
    summonCard(msg) {
        const z=(msg.location||0x04)===0x04?"mzone":"szone";
        this.cards[msg.controller][z][msg.sequence]={code:msg.code,position:msg.position||1,card_name:msg.card_name||"",card_atk:msg.card_atk,card_def:msg.card_def,card_type:msg.card_type||0};
        const h=this.cards[msg.controller].hand; const i=h.findIndex(c=>c.code===msg.code); if(i>=0)h.splice(i,1);
        this.render();
    },

    render() {
        this._renderZone("self-mzone",this.selfTeam(),"mzone");
        this._renderZone("opp-mzone",this.oppTeam(),"mzone");
        this._renderZone("self-szone",this.selfTeam(),"szone");
        this._renderZone("opp-szone",this.oppTeam(),"szone");
        this._renderHand();
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
                    const total=Object.values(card.counters).reduce((a,b)=>a+b,0);
                    if(total>0){const b=document.createElement("div");b.className="counter-badge";b.textContent=total;face.appendChild(b);}
                }
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
        const el=document.getElementById("hand"); if(!el) return; el.innerHTML="";
        this.cards[this.myTeam].hand.forEach((card,i) => {
            const div=document.createElement("div");
            div.className="hand-card"; div.dataset.index=i; div.dataset.code=card.code;
            if(card.code&&card.card_name){
                const img=document.createElement("img");
                img.src=cardImageUrl(card.code); img.loading="lazy";
                img.onerror=function(){this.style.display="none";const f=document.createElement("div");f.style.cssText="flex:1;display:flex;align-items:center;justify-content:center;font-size:0.5vw;color:#a09070;text-align:center;padding:4px";f.textContent=card.card_name;div.insertBefore(f,div.firstChild);};
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
document.addEventListener("click",(e)=>{
    // Popup butonuna tiklandi
    if(e.target.closest(".popup-btn")) return;

    // Mevcut popup'lari kapat
    document.querySelectorAll(".card-popup.open").forEach(p=>p.remove());

    const card=e.target.closest(".hand-card,.card-face");
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

