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
            goHome();
        } else {
            setAuthStatus(d.message, true);
        }
    });

    WS.on("auth_result", (d) => {
        if (d.success) {
            myName = d.username;
            goHome();
        } else {
            // Token gecersiz — login ekranina don
            localStorage.removeItem("yuki_token");
            localStorage.removeItem("yuki_username");
            UI.showScreen("auth-screen");
        }
    });

    // ===== ANA SAYFA =====
    function goHome() {
        document.getElementById("home-username").textContent = myName;
        UI.showScreen("home-screen");
    }

    document.getElementById("nav-duel").onclick = () => {
        UI.showScreen("lobby");
    };

    document.getElementById("btn-back-home").onclick = () => {
        UI.showScreen("home-screen");
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

    WS.on("duel_start",()=>{
        UI.showScreen("duel"); Field.init(myTeam);
        document.getElementById("self-name").textContent=myName;
        document.getElementById("self-initial").textContent=myName.charAt(0).toUpperCase();
        document.getElementById("opp-name").textContent=oppName;
        document.getElementById("opp-initial").textContent=oppName.charAt(0).toUpperCase();
        document.getElementById("self-lp").textContent="8000";
        document.getElementById("opp-lp").textContent="8000";
        UI.setGameStatus("Duello basladi!");
        UI.log("Duello basladi!","important");
    });

    WS.on("info",(d)=>{if(d.msg) handleInfo(d.msg)});
    WS.on("select",(d)=>{if(d.msg){console.log("[SELECT]",d.msg.name,"type="+d.msg.type,"player="+d.msg.player);UI.handleSelect(d.msg);}});
    WS.on("retry",()=>{UI.log("Gecersiz, tekrar sec!","damage");if(UI.currentSelect)UI.handleSelect(UI.currentSelect)});
    WS.on("duel_end",(d)=>{
        const w=d.winner===myTeam;
        document.getElementById("result-text").textContent=w?"ZAFER":"MAGLUP";
        document.getElementById("result-text").style.color=w?"#e8c840":"#9a6aba";
        UI.showScreen("result");
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
            Field.summonCard(msg);
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
            if(msg.location===0x08){const ex=Field.cards[msg.controller]?.szone[msg.sequence];if(ex){ex.position=0x1;ex.code=code;ex.card_name=cname||ex.card_name;ex.card_type=msg.card_type||ex.card_type;Field.render();}}
        }
        else if(name==="MSG_FLIPSUMMONING"){Field.summonCard(msg);UI.log(`Flip: ${cname}`,"summon",code)}
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
                // Bağlanamadı — login ekranında kal
            }
        }
    })();
})();
