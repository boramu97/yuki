// Yuki — D3 UI — Kart ici menüler + floating tur paneli

const UI = {
    currentSelect: null,
    selectedIndices: [],
    autoPassChain: true,

    showScreen(id) {
        document.querySelectorAll(".screen").forEach(s => s.classList.remove("active"));
        document.getElementById(id)?.classList.add("active");
    },
    setStatus(t) { const el=document.getElementById("lobby-status"); if(el) el.textContent=t; },

    // --- LOG (floating sag panel, banner stili) ---
    log(text, cls, cardCode) {
        const log = document.getElementById("duel-log"); if(!log) return;
        const entry = document.createElement("div");
        entry.className = "log-banner" + (cls ? ` ${cls}` : "");
        if (cardCode) {
            const img = document.createElement("img");
            img.src = `https://images.ygoprodeck.com/images/cards_small/${cardCode}.jpg`;
            img.onerror = function(){ this.style.display="none"; };
            entry.appendChild(img);
        }
        const span = document.createElement("div"); span.className = "lb-text";
        span.textContent = text; entry.appendChild(span);
        log.insertBefore(entry, log.firstChild);
        while (log.children.length > 100) log.removeChild(log.lastChild);
    },

    // --- Tum menuleri kapat ---
    closeAllMenus() {
        document.querySelectorAll(".card-menu").forEach(m => { m.innerHTML=""; m.classList.remove("open"); });
    },

    // --- Dinamik secim paneli (kart sec, tribute, chain vs.) ---
    showSelectPanel(title, buttons) {
        const panel = document.getElementById("select-panel");
        panel.innerHTML = "";
        if (title) { const t=document.createElement("div"); t.className="sp-title"; t.textContent=title; panel.appendChild(t); }
        buttons.forEach(b => {
            const btn = document.createElement("button");
            btn.className = b.primary ? "go" : "";
            btn.textContent = b.label;
            btn.onclick = () => {
                if (!b.toggle) this.hideSelectPanel();
                b.callback();
            };
            panel.appendChild(btn);
        });
        panel.classList.add("open"); panel.style.display = "flex";
    },
    hideSelectPanel() {
        const panel = document.getElementById("select-panel");
        panel.classList.remove("open"); panel.style.display = "none"; panel.innerHTML = "";
    },

    // --- Kart ici menu olustur ---
    _buildCardMenu(menuEl, title, buttons) {
        menuEl.innerHTML = "";
        if (title) {
            const t = document.createElement("div"); t.className="menu-title"; t.textContent=title;
            menuEl.appendChild(t);
        }
        buttons.forEach(b => {
            const btn = document.createElement("button");
            btn.className = b.primary ? "primary" : "";
            btn.textContent = b.label;
            btn.onclick = (e) => { e.stopPropagation(); this.closeAllMenus(); b.callback(); };
            menuEl.appendChild(btn);
        });
    },

    // --- Tur aksyon panelini goster ---
    showTurnActions(canBattle, canEnd) {
        const panel = document.getElementById("turn-panel");
        const btnB = document.getElementById("btn-battle");
        const btnE = document.getElementById("btn-end-turn");
        panel.style.display = "flex";
        btnB.style.display = canBattle ? "block" : "none";
        btnE.style.display = canEnd !== false ? "block" : "none";
    },
    hideTurnActions() {
        document.getElementById("turn-panel").style.display = "none";
    },

    // --- Durum cubugu ---
    setGameStatus(text) {
        document.getElementById("status-text").textContent = text;
    },

    // --- ANA SELECT HANDLER ---
    handleSelect(msg) {
        this.currentSelect = msg;
        const t = msg.type;
        const h = {11:"_idleCmd",10:"_battleCmd",16:"_chain",12:"_effectYN",13:"_yesNo",14:"_option",
            15:"_selectCard",19:"_position",18:"_place",20:"_tribute",26:"_unselectCard",23:"_selectSum",
            21:"_sortChain",22:"_counter",24:"_place",25:"_sortCard",140:"_announceRace",141:"_announceAttrib",
            142:"_announceCard",143:"_announceNumber",132:"_rps"};
        const fn = h[t]; if(fn && this[fn]) return this[fn](msg);
        WS.sendResponse(t, {});
    },

    _shortName(c) { return c.card_name || `#${c.code}`; },

    // --- IDLE CMD: kart ici menüler + tur paneli ---
    _idleCmd(msg) {
        this.closeAllMenus();
        this.hideSelectPanel();
        this.setGameStatus("Ana Faz — kart sec veya tur aksyonu sec");

        // Her kart icin menu olustur
        const handEl = document.getElementById("hand");
        const handCards = handEl?.querySelectorAll(".hand-card") || [];

        // El kartlarına menü ekle
        handCards.forEach((hc, idx) => {
            const code = parseInt(hc.dataset.code);
            if (!code) return;
            const menu = hc.querySelector(".card-menu"); if(!menu) return;
            const btns = [];
            (msg.summonable||[]).forEach((c,i) => { if(c.code===code) btns.push({label:"Cagir",primary:true,callback:()=>WS.sendResponse(11,{action:"summon",index:i})}); });
            (msg.special_summonable||[]).forEach((c,i) => { if(c.code===code) btns.push({label:"Ozel Cagir",primary:true,callback:()=>WS.sendResponse(11,{action:"spsummon",index:i})}); });
            (msg.monster_setable||[]).forEach((c,i) => { if(c.code===code) btns.push({label:"Set (Canavar)",callback:()=>WS.sendResponse(11,{action:"mset",index:i})}); });
            (msg.spell_setable||[]).forEach((c,i) => { if(c.code===code) btns.push({label:"Set (Buyu/Tuzak)",callback:()=>WS.sendResponse(11,{action:"sset",index:i})}); });
            (msg.activatable||[]).forEach((c,i) => { if(c.code===code) btns.push({label:"Aktifle",primary:true,callback:()=>WS.sendResponse(11,{action:"activate",index:i})}); });
            if(btns.length>0) this._buildCardMenu(menu, this._shortName({code,card_name:Field.cards[Field.myTeam].hand[idx]?.card_name}), btns);
        });

        // Sahadaki kartlara menü ekle (repositionable, activatable)
        document.querySelectorAll("#self-mzone .card-face, #self-szone .card-face").forEach(face => {
            const code = parseInt(face.dataset.code);
            const seq = parseInt(face.dataset.sequence);
            const loc = parseInt(face.dataset.location);
            if (!code) return;
            const menu = face.querySelector(".card-menu"); if(!menu) return;
            const btns = [];
            // Repositionable — sequence ile eslesir (ayni code'lu birden fazla kart olabilir)
            (msg.repositionable||[]).forEach((c,i) => {
                if(c.code===code && c.sequence===seq) btns.push({label:"Pozisyon Degistir",callback:()=>WS.sendResponse(11,{action:"reposition",index:i})});
            });
            // Activatable — MZONE(0x04) veya SZONE(0x08) kartlari, code+location eslesmesi
            (msg.activatable||[]).forEach((c,i) => {
                if(c.code===code && (c.location===loc || !c.location))
                    btns.push({label:"Aktifle",primary:true,callback:()=>WS.sendResponse(11,{action:"activate",index:i})});
            });
            if(btns.length>0) this._buildCardMenu(menu, this._shortName({code,card_name:Field.getCardAt(Field.myTeam,loc,seq)?.card_name}), btns);
        });

        // Tur aksyonlari
        this.showTurnActions(msg.can_battle_phase, true);
        document.getElementById("btn-battle").onclick = () => { this.hideTurnActions(); this.closeAllMenus(); WS.sendResponse(11, {action:"battle"}); };
        document.getElementById("btn-end-turn").onclick = () => { this.hideTurnActions(); this.closeAllMenus(); WS.sendResponse(11, {action:"end"}); };
    },

    _battleCmd(msg) {
        this.closeAllMenus();
        this.hideSelectPanel();
        this.setGameStatus("Savas Fazi — saldirmak icin canavar sec");

        // Saldirabilir canavar menuleri
        document.querySelectorAll("#self-mzone .card-face").forEach(face => {
            const code = parseInt(face.dataset.code); if(!code) return;
            const menu = face.querySelector(".card-menu"); if(!menu) return;
            const btns = [];
            (msg.attackable||[]).forEach((c,i) => {
                if(c.code===code) {
                    btns.push({label:c.direct_attackable?"Direkt Saldir":"Saldir",primary:true,callback:()=>WS.sendResponse(10,{action:"attack",index:i})});
                }
            });
            (msg.activatable||[]).forEach((c,i) => { if(c.code===code) btns.push({label:"Aktifle",callback:()=>WS.sendResponse(10,{action:"activate",index:i})}); });
            if(btns.length>0) this._buildCardMenu(menu, this._shortName({code,card_name:Field.getCardAt(Field.myTeam,4,parseInt(face.dataset.sequence))?.card_name}), btns);
        });

        this.showTurnActions(false, true);
        document.getElementById("btn-battle").style.display = msg.can_main2 ? "block" : "none";
        if(msg.can_main2) {
            document.getElementById("btn-battle").textContent = "Main Phase 2";
            document.getElementById("btn-battle").onclick = () => { this.hideTurnActions(); this.closeAllMenus(); WS.sendResponse(10,{action:"main2"}); };
        }
        document.getElementById("btn-end-turn").onclick = () => { this.hideTurnActions(); this.closeAllMenus(); WS.sendResponse(10,{action:"end"}); };
    },

    _chain(msg) {
        const chains = msg.chains || [];
        if (chains.length === 0) { WS.sendResponse(16,{index:-1}); return; }
        if (!msg.forced && this.autoPassChain) {
            // Herhangi bir konumda aktiflestirebilecek kart varsa sor
            // MZONE(0x04)=sahada canavar efekti, SZONE(0x08)=set trap, EL(0x02)=Kuriboh, GY(0x10)=Turtle
            const hasActivatable = chains.some(ch =>
                ch.location === 0x02 || ch.location === 0x04 ||
                ch.location === 0x08 || ch.location === 0x10 || ch.location === 0x20
            );
            if (!hasActivatable) { WS.sendResponse(16,{index:-1}); return; }
        }
        this.setGameStatus("Efekt aktifle veya pas gec");
        const btns = chains.map((ch,i) => ({label:`Aktifle: ${this._shortName(ch)}`,primary:true,callback:()=>WS.sendResponse(16,{index:i})}));
        if (!msg.forced) btns.push({label:"Pas Gec",callback:()=>WS.sendResponse(16,{index:-1})});
        this.showSelectPanel("Zincir", btns);
    },

    _effectYN(msg) {
        this.setGameStatus(`${msg.card_name||"#"+msg.code} efektini aktifle?`);
        this.showSelectPanel(msg.card_name||"Efekt", [
            {label:"Evet",primary:true,callback:()=>WS.sendResponse(12,{yes:true})},
            {label:"Hayir",callback:()=>WS.sendResponse(12,{yes:false})},
        ]);
    },

    _yesNo(msg) {
        this.setGameStatus("Evet mi Hayir mi?");
        this.showSelectPanel("Karar", [
            {label:"Evet",primary:true,callback:()=>WS.sendResponse(13,{yes:true})},
            {label:"Hayir",callback:()=>WS.sendResponse(13,{yes:false})},
        ]);
    },

    _option(msg) {
        this.setGameStatus("Bir secenek sec");
        this.showSelectPanel("Secenek", (msg.options||[]).map((o,i)=>({label:`Secenek ${i+1}`,callback:()=>WS.sendResponse(14,{index:i})})));
    },

    _selectCard(msg) {
        const min=msg.min||1,max=msg.max||1,cards=msg.cards||[];
        if(min===1&&max===1){
            this.setGameStatus("Bir kart sec");
            const btns = cards.map((c,i)=>({label:this._shortName(c),callback:()=>WS.sendResponse(15,{indices:[i]})}));
            if(msg.cancelable) btns.push({label:"Iptal",callback:()=>WS.sendResponse(15,{cancel:true})});
            this.showSelectPanel("Kart Sec", btns);
        } else {
            this.selectedIndices=[]; const self=this;
            this.setGameStatus(`${min} kart sec (0/${min})`);
            function update(){
                const btns = cards.map((c,i)=>{
                    const sel=self.selectedIndices.includes(i);
                    return {label:(sel?"\u2713 ":"")+self._shortName(c),primary:sel,toggle:true,
                        callback:()=>{if(sel)self.selectedIndices=self.selectedIndices.filter(x=>x!==i);else if(self.selectedIndices.length<max)self.selectedIndices.push(i);self.setGameStatus(`${min} kart sec (${self.selectedIndices.length}/${min})`);update()}};
                });
                if(self.selectedIndices.length>=min) btns.push({label:`Onayla (${self.selectedIndices.length})`,primary:true,callback:()=>WS.sendResponse(15,{indices:self.selectedIndices})});
                if(msg.cancelable) btns.push({label:"Iptal",callback:()=>WS.sendResponse(15,{cancel:true})});
                self.showSelectPanel(`${min} Kart Sec`, btns);
            }
            update();
        }
    },

    _position(msg) {
        const name=msg.card_name||`#${msg.code}`;
        this.setGameStatus(`${name} — Pozisyon sec`);
        const p=msg.positions||0; const btns=[];
        if(p&0x1) btns.push({label:"Saldiri",primary:true,callback:()=>WS.sendResponse(19,{position:0x1})});
        if(p&0x4) btns.push({label:"Savunma",callback:()=>WS.sendResponse(19,{position:0x4})});
        if(p&0x8) btns.push({label:"Set",callback:()=>WS.sendResponse(19,{position:0x8})});
        this.showSelectPanel(name,btns);
    },

    _place(msg) {
        const flag=msg.selectable||0,player=msg.player;
        for(let s=0;s<7;s++){if(!(flag&(1<<s))){WS.sendResponse(18,{player,location:0x04,sequence:s});return;}}
        for(let s=0;s<8;s++){if(!(flag&(1<<(s+8)))){WS.sendResponse(18,{player,location:0x08,sequence:s});return;}}
        for(let s=0;s<7;s++){if(!(flag&(1<<(s+16)))){WS.sendResponse(18,{player:1-player,location:0x04,sequence:s});return;}}
        for(let s=0;s<8;s++){if(!(flag&(1<<(s+24)))){WS.sendResponse(18,{player:1-player,location:0x08,sequence:s});return;}}
        WS.sendResponse(18,{player,location:0x04,sequence:0});
    },

    _tribute(msg) {
        const min=msg.min||1,cards=msg.cards||[];
        if(cards.length<=min){WS.sendResponse(20,{indices:cards.map((_,i)=>i)});return;}
        this.selectedIndices=[]; const self=this;
        this.setGameStatus(`${min} kurban sec`);
        function update(){
            const btns=cards.map((c,i)=>{const sel=self.selectedIndices.includes(i);
                return{label:(sel?"\u2713 ":"")+"Kurban: "+self._shortName(c),primary:sel,toggle:true,
                    callback:()=>{if(sel)self.selectedIndices=self.selectedIndices.filter(x=>x!==i);else if(self.selectedIndices.length<min)self.selectedIndices.push(i);update()}};});
            if(self.selectedIndices.length>=min) btns.push({label:"Onayla",primary:true,callback:()=>WS.sendResponse(20,{indices:self.selectedIndices})});
            self.showSelectPanel(`${min} Kurban Sec`,btns);
        }
        update();
    },

    _unselectCard(msg) {
        const sel=msg.selectable||[];
        this.setGameStatus("Kart sec (at/cikar)");
        const btns=sel.map((c,i)=>({label:this._shortName(c),callback:()=>WS.sendResponse(26,{index:i})}));
        if(msg.finishable) btns.push({label:"Tamam",primary:true,callback:()=>WS.sendResponse(26,{index:-1})});
        if(msg.cancelable) btns.push({label:"Iptal",callback:()=>WS.sendResponse(26,{index:-1})});
        this.showSelectPanel("Kart Sec",btns);
    },

    _selectSum(msg) {
        const must=msg.must_cards||[],sel=msg.selectable_cards||[],target=msg.target_sum||0;
        this.selectedIndices=[]; const self=this;
        function update(){
            let sum=0;must.forEach(c=>{sum+=(c.param&0xFFFF)});self.selectedIndices.forEach(i=>{if(sel[i])sum+=(sel[i].param&0xFFFF)});
            self.setGameStatus(`Toplam ${target} (simdi: ${sum})`);
            const btns=sel.map((c,i)=>{const s=self.selectedIndices.includes(i);
                return{label:(s?"\u2713 ":"")+self._shortName(c)+` (${c.param&0xFFFF})`,primary:s,toggle:true,
                    callback:()=>{if(s)self.selectedIndices=self.selectedIndices.filter(x=>x!==i);else self.selectedIndices.push(i);update()}};});
            const ok=msg.mode===1?sum>=target:sum===target;
            if(ok&&self.selectedIndices.length>0) btns.push({label:"Onayla",primary:true,callback:()=>{const all=must.map((_,i)=>i).concat(self.selectedIndices.map(i=>must.length+i));WS.sendResponse(23,{indices:all})}});
            self.showSelectPanel(`Toplam: ${sum}/${target}`,btns);
        }
        update();
    },

    _sortChain(){WS.sendResponse(21,{indices:[]})},
    _sortCard(){WS.sendResponse(25,{indices:[]})},
    _counter(msg){const cards=msg.cards||[];const n=msg.count||0;const counts=cards.map((c,i)=>i===0?Math.min(n,c.counter_count||0):0);WS.sendResponse(22,{counts})},

    _announceRace(msg){
        const races={0x1:"Warrior",0x2:"Spellcaster",0x4:"Fairy",0x8:"Fiend",0x10:"Zombie",0x20:"Machine",0x40:"Aqua",0x80:"Pyro",0x100:"Rock",0x200:"Winged Beast",0x400:"Plant",0x800:"Insect",0x1000:"Thunder",0x2000:"Dragon",0x4000:"Beast",0x8000:"Beast-Warrior",0x10000:"Dinosaur",0x20000:"Fish",0x40000:"Sea Serpent",0x80000:"Reptile"};
        this.setGameStatus("Irk sec");
        const btns=[];for(const[v,n]of Object.entries(races)){if((msg.available||0)&parseInt(v))btns.push({label:n,callback:()=>WS.sendResponse(140,{race:parseInt(v)})});}
        this.showSelectPanel("Irk Sec",btns);
    },
    _announceAttrib(msg){
        const a={0x01:"EARTH",0x02:"WATER",0x04:"FIRE",0x08:"WIND",0x10:"LIGHT",0x20:"DARK"};
        this.setGameStatus("Ozellik sec");
        const btns=[];for(const[v,n]of Object.entries(a)){if((msg.available||0)&parseInt(v))btns.push({label:n,callback:()=>WS.sendResponse(141,{attribute:parseInt(v)})});}
        this.showSelectPanel("Ozellik Sec",btns);
    },
    _announceCard(msg){
        this.setGameStatus("Kart ilan et");
        this.showSelectPanel("Kart Ilan Et",[{label:"Dark Magician",callback:()=>WS.sendResponse(142,{code:46986414})},{label:"Blue-Eyes",callback:()=>WS.sendResponse(142,{code:89631139})}]);
    },
    _announceNumber(msg){
        this.setGameStatus("Sayi sec");
        this.showSelectPanel("Sayi Sec",(msg.numbers||[]).map((n,i)=>({label:`${n}`,callback:()=>WS.sendResponse(143,{index:i})})));
    },
    _rps(){
        this.setGameStatus("Tas Kagit Makas");
        this.showSelectPanel("TKM",[{label:"Tas",callback:()=>WS.sendResponse(132,{choice:1})},{label:"Kagit",callback:()=>WS.sendResponse(132,{choice:2})},{label:"Makas",callback:()=>WS.sendResponse(132,{choice:3})}]);
    },
};
