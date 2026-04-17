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

    document.getElementById("nav-adventures").onclick = async () => {
        UI.showScreen("adventures-screen");
        // Düello Adası ilerleme çubuğu için veri çek
        try { await ensureConnected(); WS.getAdventures(); } catch(e) {}
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
    WS.on("hand_sync",(d)=>{
        // Motor otoriteli el snapshot'i — event-driven takipten bagimsiz olarak
        // el state'ini tamamen yeniler. Desync imkansiz hale gelir.
        if (!d.hands) return;
        for (const t of ["0","1"]) {
            const team = +t;
            const cards = d.hands[t] || [];
            const h = Field.cards[team].hand;
            h.length = 0;
            for (const c of cards) {
                h.push({
                    code: c.code || 0,
                    position: 0,
                    card_name: c.card_name || "",
                    card_atk: c.card_atk,
                    card_def: c.card_def,
                    card_type: c.card_type || 0,
                });
            }
        }
        Field.render();
    });
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

    // Macera yolu renderer — 9 dugumlu roguelike patika
    WS.on("adventures",(d)=>{
        const adv=d.adventures?.duel_island;
        if(!adv) return;
        const nodes=adv.nodes||[];
        const completed=adv.completed||[];
        renderIslandPath(nodes, completed);
        // Hub tile ilerleme cubugu
        const hubLbl=document.getElementById("island-progress-label");
        const hubFill=document.getElementById("island-progress-fill");
        const total=nodes.length||9;
        const doneCount=completed.length;
        const pct=Math.round((doneCount/total)*100);
        if(hubLbl) hubLbl.textContent = doneCount>=total?"Tamamlandı":`Aşama ${doneCount}/${total}`;
        if(hubFill) hubFill.style.width = pct+"%";
    });

    // Gizem teklifi geldi — modal'i doldur
    WS.on("mystery_offer",(d)=>{
        openGizemModal(d.adventure, d.node, d.cards||[]);
    });
    WS.on("mystery_claimed",(d)=>{
        UI.log(`Gizem kart alindi!`);
        closeGizemModal();
        try { WS.getAdventures(); } catch(e) {}
    });

    // Dükkân teklifi geldi
    WS.on("shop_offer",(d)=>{
        openDukkanModal(d.adventure, d.node, d.cards||[], d.purchased||[], d.dust||0);
    });
    WS.on("shop_bought",(d)=>{
        // Bakiyeyi guncelle, kart sold durumuna gec
        const wallet=document.getElementById("dukkan-wallet");
        if (wallet) { wallet.textContent = d.dust; wallet.classList.add("pulse"); setTimeout(()=>wallet.classList.remove("pulse"), 600); }
        const el=document.querySelector(`#dukkan-cards .shop-item[data-code="${d.code}"]`);
        if (el) el.classList.add("sold");
        dukkanRefreshAffordability();
    });
    WS.on("shop_left",(d)=>{
        closeDukkanModal();
        try { WS.getAdventures(); } catch(e) {}
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
            const con=msg.controller;
            // Kartın su anki konumu (location) szone olabilir — motor dahili olarak tasir
            if(msg.location===0x08){
                const ex=Field.cards[con]?.szone[msg.sequence];
                if(ex){ex.position=0x1;ex.code=code;ex.card_name=cname||ex.card_name;ex.card_type=msg.card_type||ex.card_type;}
            }
            // triggering_location = kartın orijinal konumu (chain'e girmeden once)
            // Elden aktiflestirildi ama motor MSG_MOVE gondermez — elden silmemiz gerekiyor
            const trigLoc=msg.triggering_location||0;
            if(trigLoc===0x02){
                const h=Field.cards[con]?.hand;
                if(h){const i=h.findIndex(c=>c.code===code);if(i>=0)h.splice(i,1);}
            }
            Field.render();
        }
        else if(name==="MSG_SHUFFLE_HAND"){
            // Motor eli yeniden gonderdi — el state'ini tamamen yenile
            // Motor dogruluk kaynagidir, verisine guveniriz
            const h=Field.cards[msg.player].hand;
            const cards=msg.cards||[];
            h.length=0;
            for(const c of cards){
                if(typeof c==="object") h.push({code:c.code||0,position:0,card_name:c.card_name||"",card_atk:c.card_atk,card_def:c.card_def,card_type:c.card_type||0});
                else h.push({code:c||0,position:0,card_name:"",card_type:0});
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

    // ===== MACERA PATİKA RENDERER =====
    // 9 düğümlü roguelike yolu dinamik olarak oluşturur.
    // DOM sırası bottom-to-top (column-reverse), yani index 0 = alttaki ilk kart.
    const NODE_ICONS = {
        "Rex": "&#x1F996;",
        "Weevil": "&#x1FAB2;",
        "Mai": "&#x1F985;",
        "Joey": "&#x1F3B2;",
        "Pegasus": "&#x1F441;",
    };
    const NODE_TOOLTIPS = {
        "mystery": "3 kart sunulur · birini koleksiyonuna kat",
        "shop": "5 kart · %50 toz indirimiyle al",
    };
    function nodeIcon(node){
        if (node.type==="duel"||node.type==="boss") return NODE_ICONS[node.bot] || "&#x2694;";
        if (node.type==="mystery") return "&#x2753;";
        if (node.type==="shop") return "&#x1F4B0;";
        return "&#x25CF;";
    }
    function nodeLabel(node){
        if (node.type==="mystery") return "Gizem";
        if (node.type==="shop") return "Dükkân";
        if (node.type==="boss") return node.bot_name || "Boss";
        return node.bot || "";
    }
    function nodeTooltip(node){
        if (node.type==="mystery" || node.type==="shop") return NODE_TOOLTIPS[node.type];
        return (node.bot_name||"") + (node.dust?` · ${node.dust} toz`:"");
    }
    function segmentState(a, b){
        if (a==="done" && b==="done") return "done";
        if (a==="done" && b==="current") return "active";
        if (a==="current" && b==="locked") return "upcoming";
        return "locked";
    }
    function renderIslandPath(nodes, completed){
        const host=document.getElementById("path-scroll");
        if (!host) return;
        // SVG gradient definition (bir kez)
        let defs=document.getElementById("pathGradDefs");
        if (!defs){
            host.insertAdjacentHTML("afterbegin",
                `<svg id="pathGradDefs" width="0" height="0" style="position:absolute;pointer-events:none"><defs>`+
                `<linearGradient id="gradGold" x1="0%" y1="100%" x2="0%" y2="0%">`+
                `<stop offset="0%" stop-color="#c9a646" stop-opacity="0.8"/>`+
                `<stop offset="50%" stop-color="#ffe78a" stop-opacity="1"/>`+
                `<stop offset="100%" stop-color="#c9a646" stop-opacity="0.8"/>`+
                `</linearGradient></defs></svg>`);
        }
        // Once tum row'lari sil
        host.querySelectorAll(".path-row").forEach(el=>el.remove());
        // Durum hesapla
        const states = nodes.map((_,i)=>{
            if (completed.includes(i)) return "done";
            // Current: ilk "locked" olmayan ve "done" olmayan — yani completed.length == i
            if (i === completed.length) return "current";
            return "locked";
        });
        // DOM: index 0 ilk gelir (visual alt), son index en sonda (visual üst)
        nodes.forEach((node,i)=>{
            const st = states[i];
            // up segment = i to i+1; down = i-1 to i
            const stAbove = i+1 < states.length ? states[i+1] : null;
            const stBelow = i-1 >= 0 ? states[i-1] : null;
            const upClass = stAbove ? segmentState(st, stAbove) : "none";
            const downClass = stBelow ? segmentState(stBelow, st) : "none";
            const isBoss = node.type === "boss";
            const rowClass = "path-row" + (isBoss ? " terminus" : "");
            const vbH = isBoss ? 260 : 200;
            const upY = isBoss ? null : 50;
            const downYTop = isBoss ? (260-55) : 150;
            // SVG connector
            let svgInner = "";
            if (downClass !== "none") svgInner += `<path class="connector-line ${downClass}" d="M 50 ${vbH} L 50 ${downYTop}"/>`;
            if (upClass !== "none" && upY !== null) svgInner += `<path class="connector-line ${upClass}" d="M 50 50 L 50 0"/>`;
            // Node HTML
            const halos = st==="current" ? `<span class="path-node-halo"></span><span class="path-node-halo d1"></span><span class="path-node-halo d2"></span>` : "";
            const check = st==="done" ? `<span class="path-node-check">&#10003;</span>` : "";
            const nodeClass = `path-node type-${node.type} ${st}`;
            const tip = nodeTooltip(node);
            const label = nodeLabel(node);
            const bossCrown = isBoss ? `<div class="boss-crown">◈ · Final · ◈</div>` : "";
            const bossSubtitle = isBoss ? `<span class="boss-subtitle">Kale Efendisi</span>` : "";
            const html = `<div class="${rowClass}" data-node="${i}" data-type="${node.type}" data-state="${st}">`+
                `<svg class="row-connector" viewBox="0 0 100 ${vbH}" preserveAspectRatio="none">${svgInner}</svg>`+
                bossCrown +
                `<button class="${nodeClass}"${(st==="locked"||st==="done")?" disabled":""}>`+
                    halos +
                    `<span class="path-node-icon">${nodeIcon(node)}</span>`+
                    `<span class="path-node-label">${label}</span>`+
                    bossSubtitle +
                    check +
                    `<span class="path-node-tooltip">${tip}</span>`+
                `</button>`+
                `</div>`;
            host.insertAdjacentHTML("beforeend", html);
        });
        // Click handler: aktif (current) olanlara
        host.querySelectorAll(".path-row").forEach(row=>{
            const idx = parseInt(row.dataset.node, 10);
            const type = row.dataset.type;
            const state = row.dataset.state;
            if (state === "locked") return;
            if (state === "done") return; // tekrar girme yasak
            const btn = row.querySelector(".path-node");
            if (!btn) return;
            btn.addEventListener("click", async () => {
                try { await ensureConnected(); } catch(e) { return; }
                if (type === "duel" || type === "boss") {
                    WS.playAdventure("duel_island", idx);
                } else if (type === "mystery") {
                    WS.mysteryOffer("duel_island", idx);
                } else if (type === "shop") {
                    WS.shopOffer("duel_island", idx);
                }
            });
        });
        // Üst ilerleme göstergesi
        const fill=document.getElementById("island-progress-fill");
        const cnt=document.getElementById("island-progress-count");
        const pct=Math.round((completed.length/nodes.length)*100);
        if (fill) fill.style.width = pct+"%";
        if (cnt) cnt.textContent = `${completed.length} / ${nodes.length}`;
    }

    // ===== GİZEM MODAL =====
    let _gizemState = { adventure: "", node: 0, selected: null };
    function openGizemModal(adventure, node, cards) {
        _gizemState = { adventure, node, selected: null };
        const host = document.getElementById("gizem-cards");
        host.innerHTML = "";
        cards.forEach(c => {
            const el = document.createElement("button");
            el.className = "choice-card";
            el.dataset.code = c.code;
            el.innerHTML =
                `<div class="choice-card-art"><img src="https://images.ygoprodeck.com/images/cards/${c.code}.jpg" alt=""></div>`+
                `<div class="choice-card-name">${c.card_name||""}</div>`;
            el.addEventListener("click", () => {
                host.querySelectorAll(".choice-card").forEach(x=>x.classList.remove("selected"));
                el.classList.add("selected");
                host.classList.add("has-selected");
                _gizemState.selected = c.code;
                const btn = document.getElementById("gizem-take");
                const hint = document.getElementById("gizem-hint");
                btn.disabled = false;
                hint.style.display = "none";
            });
            host.appendChild(el);
        });
        // Reset state
        document.getElementById("gizem-take").disabled = true;
        document.getElementById("gizem-hint").style.display = "";
        host.classList.remove("has-selected");
        document.getElementById("gizem-overlay").classList.add("active");
    }
    function closeGizemModal() {
        document.getElementById("gizem-overlay").classList.remove("active");
    }

    // ===== DÜKKÂN MODAL =====
    let _dukkanState = { adventure: "", node: 0 };
    function openDukkanModal(adventure, node, cards, purchased, dust) {
        _dukkanState = { adventure, node };
        document.getElementById("dukkan-wallet").textContent = dust;
        const host = document.getElementById("dukkan-cards");
        host.innerHTML = "";
        cards.forEach(c => {
            const isSold = purchased.includes(c.code);
            const el = document.createElement("div");
            el.className = "shop-item" + (isSold ? " sold" : "");
            el.dataset.code = c.code;
            el.dataset.price = c.price;
            el.innerHTML =
                `<div class="shop-item-art"><img src="https://images.ygoprodeck.com/images/cards/${c.code}.jpg" alt=""></div>`+
                `<div class="shop-item-name">${c.card_name||""}</div>`+
                `<div class="shop-item-price">`+
                    `<span class="price-old">${c.price_original} toz</span>`+
                    `<span class="price-new">${c.price}<span class="currency">toz</span></span>`+
                `</div>`+
                `<button class="btn-buy">${isSold?"Alındı":"Al"}</button>`;
            if (!isSold) {
                el.querySelector(".btn-buy").addEventListener("click", () => {
                    WS.shopBuy(adventure, node, c.code);
                });
            }
            host.appendChild(el);
        });
        dukkanRefreshAffordability();
        document.getElementById("dukkan-overlay").classList.add("active");
    }
    function closeDukkanModal() {
        document.getElementById("dukkan-overlay").classList.remove("active");
    }
    function dukkanRefreshAffordability() {
        const wallet = parseInt(document.getElementById("dukkan-wallet").textContent, 10) || 0;
        document.querySelectorAll("#dukkan-cards .shop-item").forEach(el => {
            if (el.classList.contains("sold")) {
                el.querySelector(".btn-buy").disabled = true;
                el.querySelector(".btn-buy").textContent = "Alındı";
                return;
            }
            const price = parseInt(el.dataset.price, 10);
            const btn = el.querySelector(".btn-buy");
            if (wallet < price) {
                el.classList.add("too-expensive");
                btn.disabled = true;
                btn.textContent = "Yetersiz";
            } else {
                el.classList.remove("too-expensive");
                btn.disabled = false;
                btn.textContent = "Al";
            }
        });
    }
    // Modal butonlari
    document.getElementById("gizem-leave")?.addEventListener("click", () => closeGizemModal());
    document.getElementById("gizem-take")?.addEventListener("click", () => {
        if (_gizemState.selected == null) return;
        WS.mysteryClaim(_gizemState.adventure, _gizemState.node, _gizemState.selected);
    });
    document.getElementById("dukkan-leave")?.addEventListener("click", () => {
        // Sadece ayrıl — node henuz tamamlanmadi (tekrar girilebilir)
        closeDukkanModal();
    });
    document.getElementById("dukkan-continue")?.addEventListener("click", () => {
        WS.shopLeave(_dukkanState.adventure, _dukkanState.node);
    });

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
