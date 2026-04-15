// Yuki — D3 App

(function() {
    let myTeam = -1, myName = "", oppName = "Rakip", turnCount = 0;

    // ===== AUTH =====
    const authUsername = document.getElementById("auth-username");
    const authPassword = document.getElementById("auth-password");
    const authStatus = document.getElementById("auth-status");

    function setAuthStatus(msg, isError) {
        authStatus.textContent = msg;
        authStatus.className = "status " + (isError ? "error" : "success");
    }

    async function ensureConnected() {
        if (!WS.connected) {
            await WS.connect();
        }
    }

    document.getElementById("btn-login").onclick = async () => {
        const u = authUsername.value.trim();
        const p = authPassword.value;
        if (!u || !p) { setAuthStatus("Kullanici adi ve sifre gir", true); return; }
        try {
            await ensureConnected();
            WS.login(u, p);
        } catch(e) { setAuthStatus("Sunucuya baglanilamadi!", true); }
    };

    document.getElementById("btn-register").onclick = async () => {
        const u = authUsername.value.trim();
        const p = authPassword.value;
        if (!u || !p) { setAuthStatus("Kullanici adi ve sifre gir", true); return; }
        try {
            await ensureConnected();
            WS.register(u, p);
        } catch(e) { setAuthStatus("Sunucuya baglanilamadi!", true); }
    };

    // Enter ile giris yap
    authPassword.addEventListener("keydown", (e) => {
        if (e.key === "Enter") document.getElementById("btn-login").click();
    });

    WS.on("register_result", (d) => {
        if (d.success) {
            setAuthStatus("Kayit basarili! Giris yapabilirsin.", false);
        } else {
            setAuthStatus(d.message, true);
        }
    });

    WS.on("login_result", (d) => {
        if (d.success) {
            myName = d.username;
            localStorage.setItem("yuki_token", d.token);
            localStorage.setItem("yuki_username", d.username);
            if (d.active_deck_slot !== undefined) Collection.activeDeckSlot = d.active_deck_slot;
            goHome();
        } else {
            setAuthStatus(d.message, true);
        }
    });

    WS.on("auth_result", (d) => {
        if (d.success) {
            myName = d.username;
            if (d.active_deck_slot !== undefined) Collection.activeDeckSlot = d.active_deck_slot;
            goHome();
        } else {
            // Token gecersiz — login ekranina don
            localStorage.removeItem("yuki_token");
            localStorage.removeItem("yuki_username");
            UI.showScreen("auth-screen");
        }
    });

    // ===== ANA SAYFA =====
    function getActiveDeck() {
        try {
            const raw = localStorage.getItem("yuki_active_deck");
            if (raw) { const d = JSON.parse(raw); if (d.length === 40) return d; }
        } catch(e) {}
        return undefined;
    }

    function goHome() {
        document.getElementById("home-username").textContent = myName;
        UI.showScreen("home-screen");
    }

    document.getElementById("nav-duel").onclick = () => {
        UI.showScreen("lobby");
    };

    document.getElementById("nav-collection").onclick = () => {
        Collection.open();
    };

    document.getElementById("nav-adventures").onclick = () => {
        UI.showScreen("adventures-screen");
    };

    document.getElementById("btn-back-home").onclick = () => {
        UI.showScreen("home-screen");
    };

    document.getElementById("btn-back-adventures").onclick = () => {
        UI.showScreen("home-screen");
    };

    // Macera menusunden alt ekranlara
    document.getElementById("banner-training").onclick = () => {
        UI.showScreen("training-screen");
    };
    document.getElementById("banner-duel-island").onclick = async () => {
        UI.showScreen("duel-island-screen");
        try { await ensureConnected(); WS.getAdventures(); } catch(e) {}
    };
    document.getElementById("btn-back-training").onclick = () => {
        UI.showScreen("adventures-screen");
    };
    document.getElementById("btn-back-island").onclick = () => {
        UI.showScreen("adventures-screen");
    };

    document.getElementById("btn-back-collection").onclick = () => {
        UI.showScreen("home-screen");
    };

    // Maceralar — bot seçimi
    document.querySelectorAll(".adv-card").forEach(card => {
        card.addEventListener("click", async () => {
            const bot = card.dataset.bot;
            try {
                await ensureConnected();
                WS.playVsBot(bot);
            } catch(e) {
                // bağlantı hatası
            }
        });
    });

    document.getElementById("btn-back-home-result").onclick = () => {
        Field.init(0); turnCount = 0;
        goHome();
    };

    document.getElementById("btn-logout").onclick = () => {
        localStorage.removeItem("yuki_token");
        localStorage.removeItem("yuki_username");
        myName = "";
        if (WS.connected && WS.socket) {
            WS.socket.close();
            WS.connected = false;
        }
        UI.showScreen("auth-screen");
    };

    // ===== LOBİ =====
    document.getElementById("btn-quick-match").onclick = async () => {
        UI.setStatus("Eslestiriliyor...");
        try { await ensureConnected(); WS.quickMatch(); } catch(e) { UI.setStatus("Sunucu baglanamadi!"); }
    };
    document.getElementById("btn-create-room").onclick = async () => {
        UI.setStatus("Oda olusturuluyor...");
        try { await ensureConnected(); WS.createRoom(); } catch(e) { UI.setStatus("Sunucu baglanamadi!"); }
    };
    document.getElementById("btn-join-room").onclick = async () => {
        const rid = document.getElementById("room-code").value.trim();
        if (!rid) { UI.setStatus("Oda kodu gir!"); return; }
        UI.setStatus("Katiliniyor...");
        try { await ensureConnected(); WS.joinRoom(rid); } catch(e) { UI.setStatus("Sunucu baglanamadi!"); }
    };
    document.getElementById("mp-auto-pass")?.addEventListener("change",(e)=>{UI.autoPassChain=e.target.checked});

    // ===== WebSocket Events =====
    WS.on("room_created",(d)=>{document.getElementById("waiting-room-id").textContent=d.room_id;myTeam=d.team;UI.showScreen("waiting")});
    WS.on("room_joined",(d)=>{myTeam=d.team});
    WS.on("player_joined",(d)=>{oppName=d.name;UI.log(d.name+" katildi!","important")});
    WS.on("player_left",(d)=>{UI.log(d.name+" ayrildi")});

    WS.on("duel_start",(d)=>{
        UI.showScreen("duel"); Field.init(myTeam);
        document.getElementById("self-name").textContent=myName;
        document.getElementById("self-initial").textContent=myName.charAt(0).toUpperCase();
        document.getElementById("opp-name").textContent=oppName;
        document.getElementById("opp-initial").textContent=oppName.charAt(0).toUpperCase();
        document.getElementById("self-lp").textContent="8000";
        document.getElementById("opp-lp").textContent="8000";
        // Tema arkaplan
        const duelEl=document.getElementById("duel");
        duelEl.classList.remove("theme-toon");
        if(d&&d.theme==="toon") duelEl.classList.add("theme-toon");
        UI.setGameStatus("Duello basladi!");
        UI.log("Duello basladi!","important");
    });

    document.getElementById("btn-surrender").onclick=()=>{
        if(confirm("Teslim olmak istediginize emin misiniz?")) WS.surrender();
    };

    WS.on("info",(d)=>{if(d.msg) handleInfo(d.msg)});
    WS.on("select",(d)=>{if(d.msg){console.log("[SELECT]",d.msg.name,"type="+d.msg.type,"player="+d.msg.player);UI.handleSelect(d.msg);}});
    WS.on("retry",()=>{UI.log("Gecersiz, tekrar sec!","damage");if(UI.currentSelect)UI.handleSelect(UI.currentSelect)});
    WS.on("duel_end",(d)=>{
        const w=d.winner===myTeam;
        document.getElementById("result-text").textContent=w?"ZAFER":"MAGLUP";
        document.getElementById("result-text").style.color=w?"#e8c840":"#9a6aba";
        // Odul gosterimi
        const rbox=document.getElementById("reward-box");
        const rdet=document.getElementById("reward-details");
        if(d.reward && d.reward.dust){
            rbox.style.display="";
            let html=`<div class="reward-dust">+${d.reward.dust} Toz</div>`;
            if(d.reward.cards && d.reward.cards.length)
                html+=`<div class="reward-cards">${d.reward.cards.length} yeni kart koleksiyonuna eklendi!</div>`;
            rdet.innerHTML=html;
        } else {
            rbox.style.display="none";
        }
        UI.showScreen("result");
    });

    // Turnuva ilerlemesi — harita uzerinde butonlar
    WS.on("adventures",(d)=>{
        const map=document.getElementById("island-map");
        const adv=d.adventures?.duel_island;
        if(!adv) return;
        // Eski butonlari temizle (img haric)
        map.querySelectorAll(".stage").forEach(el=>el.remove());
        const completed=adv.completed||[];
        const icons=["&#x1F996;","&#x1FAB2;","&#x1F985;","&#x1F3B2;","&#x1F441;"];
        const labels=["1. Tur","2. Tur","3. Tur","4. Tur","Final"];
        // Harita uzerinde konumlar (% cinsinden — sahilden kaleye yol)
        const positions=[
            {top:82, left:72},  // Rex — sahil (sag alt)
            {top:65, left:28},  // Weevil — orman/bataklik (sol)
            {top:48, left:62},  // Mai — orta sag
            {top:35, left:38},  // Joey — arena/daglara yakin
            {top:14, left:50},  // Kaiba — kale (ust orta)
        ];
        adv.stages.forEach((st,i)=>{
            const done=completed.includes(i);
            const unlocked=i===0||completed.includes(i-1);
            const cls=done?"stage done":unlocked?"stage unlocked":"stage locked";
            const el=document.createElement("div");
            el.className=cls;
            el.dataset.stage=i;
            el.style.top=positions[i].top+"%";
            el.style.left=positions[i].left+"%";
            el.innerHTML=`<div class="stage-icon">${icons[i]}</div>`
                +`<div class="stage-label">${labels[i]}</div>`
                +`<div class="stage-name">${st.bot_name}</div>`
                +`<div class="stage-reward">${st.dust} toz + ${st.cards} kart</div>`
                +(done?`<div class="stage-check">&#x2713;</div>`:"");
            if(unlocked||done){
                el.addEventListener("click",async()=>{
                    try{await ensureConnected();WS.playAdventure("duel_island",i);}catch(e){}
                });
            }
            map.appendChild(el);
        });
    });

    WS.on("error",(d)=>{UI.setStatus(d.message)});
    WS.on("disconnect",()=>{UI.setStatus("Baglanti koptu")});

    function p(player){return player===myTeam?myName:oppName}

    function handleInfo(msg) {
        const name=msg.name, cname=msg.card_name||"", code=msg.code||0;

        if(name==="MSG_NEW_TURN"){
            turnCount++; Field.setTurn(turnCount);
            UI.log(`━━ Tur ${turnCount} (${p(msg.player)}) ━━`,"important");
            UI.setGameStatus("Rakibin hamlesini bekle...");
            UI.hideMotorPanel();
        }
        else if(name==="MSG_NEW_PHASE") Field.setPhase(msg.phase);
        else if(name==="MSG_DRAW"){
            Field.addToHand(msg.player,msg.cards||[]);
            if(msg.player===myTeam)(msg.cards||[]).forEach(c=>{if(c.card_name)UI.log(`Cektin: ${c.card_name}`,"",c.code)});
            else UI.log(`${oppName} ${(msg.cards||[]).length} kart cekti`);
        }
        else if(name==="MSG_MOVE"){
            Field.moveCard(code,msg.from||{},msg.to||{},{card_name:cname,card_atk:msg.card_atk,card_def:msg.card_def,card_type:msg.card_type});
            const to=msg.to?.location||0;
            if(cname&&to===0x10)UI.log(`${cname} → Mezarlik`,"move",code);
            else if(cname&&to===0x20)UI.log(`${cname} → Surgun`,"move",code);
        }
        else if(name==="MSG_SUMMONING"||name==="MSG_SPSUMMONING"){
            Field.summonCard(msg, name==="MSG_SUMMONING");
            UI.log(`${name==="MSG_SUMMONING"?"Cagrildi":"Ozel Cagri"}: ${cname}`,"summon",code);
        }
        else if(name==="MSG_SET"){
            const z=(msg.location||0x04)===0x04?"mzone":"szone";
            Field.cards[msg.controller][z][msg.sequence]={code,position:msg.position||0x8,card_name:cname,card_type:msg.card_type||0};
            const h=Field.cards[msg.controller].hand;const i=h.findIndex(c=>c.code===code);if(i>=0)h.splice(i,1);
            Field.render(); UI.log(`${p(msg.controller)} kart set etti`,"move");
        }
        else if(name==="MSG_POS_CHANGE"){
            const loc=msg.location||0x04;
            const zone=loc===0x04?"mzone":loc===0x08?"szone":null;
            if(zone){const z=Field.cards[msg.controller]?.[zone];if(z&&z[msg.sequence]){z[msg.sequence].position=msg.position;Field.render();}}
        }
        else if(name==="MSG_DAMAGE"){Field.damageLP(msg.player,msg.amount);UI.log(`${p(msg.player)} -${msg.amount} LP`,"damage")}
        else if(name==="MSG_RECOVER"){Field.recoverLP(msg.player,msg.amount);UI.log(`${p(msg.player)} +${msg.amount} LP`)}
        else if(name==="MSG_PAY_LPCOST"){Field.damageLP(msg.player,msg.amount);UI.log(`${p(msg.player)} ${msg.amount} LP odedi`,"damage")}
        else if(name==="MSG_ATTACK")UI.log(`${p(msg.attacker_controller)} saldiriyor!`,"important");
        else if(name==="MSG_BATTLE")UI.log(`ATK ${msg.attacker_atk} vs ${msg.target_atk}`);
        else if(name==="MSG_CHAINING"){
            UI.log(`Aktiflestirildi: ${cname}`,"spell",code);
            if(msg.location===0x08){
                // Szone'daki karti guncelle (yuz yukari cevir)
                const ex=Field.cards[msg.controller]?.szone[msg.sequence];
                if(ex){ex.position=0x1;ex.code=code;ex.card_name=cname||ex.card_name;ex.card_type=msg.card_type||ex.card_type;Field.render();}
            } else if(msg.location===0x02){
                // Elden aktiflestirildi — motor karti szone'a tasidi, elden sil
                const h=Field.cards[msg.controller]?.hand;
                if(h){const i=h.findIndex(c=>c.code===code);if(i>=0)h.splice(i,1);Field.render();}
            }
        }
        else if(name==="MSG_SHUFFLE_HAND"){
            // Motor eli yeniden gonderdi — el state'ini tamamen yenile
            const h=Field.cards[msg.player].hand;
            const cards=msg.cards||[];
            // Sahada olan kartlarin code'larini topla (cross-zone dogrulama)
            const onField=new Set();
            const pdata=Field.cards[msg.player];
            for(const s of Object.values(pdata.mzone||{})) if(s&&s.code) onField.add(s.code);
            for(const s of Object.values(pdata.szone||{})) if(s&&s.code) onField.add(s.code);
            h.length=0;
            for(const c of cards){
                const cc=typeof c==="object"?(c.code||0):(c||0);
                if(cc && onField.has(cc)){console.warn("[SHUFFLE_HAND] Skipping card already on field:",cc); continue;}
                if(typeof c==="object") h.push({code:c.code||0,position:0,card_name:c.card_name||"",card_atk:c.card_atk,card_def:c.card_def,card_type:c.card_type||0});
                else h.push({code:cc,position:0,card_name:"",card_type:0});
            }
            Field.render();
        }
        else if(name==="MSG_FLIPSUMMONING"){Field.summonCard(msg, false);UI.log(`Flip: ${cname}`,"summon",code)}
        else if(name==="MSG_LPUPDATE")Field.updateLP(msg.player,msg.lp);
        else if(name==="MSG_STAT_UPDATE"){const c=Field.getCardAt(msg.controller,msg.location,msg.sequence);if(c){c.card_atk=msg.card_atk;c.card_def=msg.card_def;Field.render();}}
        else if(name==="MSG_ADD_COUNTER"){Field.addCounter(msg.controller,msg.location,msg.sequence,msg.counter_type,msg.count);const c=Field.getCardAt(msg.controller,msg.location,msg.sequence);UI.log(`${c?.card_name||""} +${msg.count} sayac`,"spell",c?.code)}
        else if(name==="MSG_REMOVE_COUNTER"){Field.removeCounter(msg.controller,msg.location,msg.sequence,msg.counter_type,msg.count);const c=Field.getCardAt(msg.controller,msg.location,msg.sequence);UI.log(`${c?.card_name||""} -${msg.count} sayac`,"move",c?.code)}
        else if(name==="MSG_EQUIP")UI.log("Techizat edildi","spell");
        else if(name==="MSG_TOSS_COIN"){const r=(msg.results||[]).map(v=>v?"Yazi":"Tura").join(", ");UI.log(`Yazi/Tura: ${r}`)}
        else if(name==="MSG_TOSS_DICE")UI.log(`Zar: ${(msg.results||[]).join(", ")}`);
    }

    // ===== OTOMATIK GİRİŞ =====
    // Sayfa açılınca localStorage'da token varsa otomatik doğrula
    (async function autoLogin() {
        const token = localStorage.getItem("yuki_token");
        if (token) {
            try {
                await ensureConnected();
                WS.auth(token);
            } catch(e) {
                UI.showScreen("auth-screen");
            }
        } else {
            UI.showScreen("auth-screen");
        }
    })();
})();
