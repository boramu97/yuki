// Yuki — D3 App

(function() {
    let myTeam = -1, myName = "", oppName = "Rakip", turnCount = 0;

    // Lobi
    document.getElementById("btn-quick-match").onclick = async () => {
        myName = document.getElementById("player-name").value.trim() || "Duelist";
        UI.setStatus("Baglaniliyor...");
        try { await WS.connect(); WS.quickMatch(myName); } catch(e) { UI.setStatus("Sunucu baglanamadi!"); }
    };
    document.getElementById("btn-create-room").onclick = async () => {
        myName = document.getElementById("player-name").value.trim() || "Duelist";
        UI.setStatus("Baglaniliyor...");
        try { await WS.connect(); WS.createRoom(myName); } catch(e) { UI.setStatus("Sunucu baglanamadi!"); }
    };
    document.getElementById("btn-join-room").onclick = async () => {
        myName = document.getElementById("player-name").value.trim() || "Duelist";
        const rid = document.getElementById("room-code").value.trim();
        if (!rid) { UI.setStatus("Oda kodu gir!"); return; }
        UI.setStatus("Baglaniliyor...");
        try { await WS.connect(); WS.joinRoom(myName, rid); } catch(e) { UI.setStatus("Sunucu baglanamadi!"); }
    };
    document.getElementById("mp-auto-pass")?.addEventListener("change",(e)=>{UI.autoPassChain=e.target.checked});

    // WebSocket
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
            UI.log(`\u2501\u2501 Tur ${turnCount} (${p(msg.player)}) \u2501\u2501`,"important");
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
            if(cname&&to===0x10)UI.log(`${cname} \u2192 Mezarlik`,"move",code);
            else if(cname&&to===0x20)UI.log(`${cname} \u2192 Surgun`,"move",code);
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
})();
