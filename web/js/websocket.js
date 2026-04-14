// Yuki — WebSocket baglanti yonetimi

const WS = {
    socket: null,
    connected: false,
    handlers: {},  // action -> callback

    connect(url) {
        return new Promise((resolve, reject) => {
            const proto = location.protocol === 'https:' ? 'wss:' : 'ws:';
            const wsUrl = proto === 'wss:'
                ? `${proto}//${location.host}/ws`
                : `${proto}//${location.hostname}:8765`;
            this.socket = new WebSocket(url || wsUrl);

            this.socket.onopen = () => {
                this.connected = true;
                console.log("[WS] Baglandi");
                resolve();
            };

            this.socket.onclose = () => {
                this.connected = false;
                console.log("[WS] Baglanti kapandi");
                if (this.handlers["disconnect"]) this.handlers["disconnect"]();
            };

            this.socket.onerror = (e) => {
                console.error("[WS] Hata:", e);
                reject(e);
            };

            this.socket.onmessage = (event) => {
                try {
                    const data = JSON.parse(event.data);
                    const action = data.action;
                    if (this.handlers[action]) {
                        this.handlers[action](data);
                    }
                } catch (e) {
                    console.error("[WS] Parse hatasi:", e);
                }
            };
        });
    },

    send(data) {
        if (this.connected && this.socket) {
            this.socket.send(JSON.stringify(data));
        }
    },

    on(action, callback) {
        this.handlers[action] = callback;
    },

    // Auth metodlari
    register(username, password) {
        this.send({ action: "register", username, password });
    },

    login(username, password) {
        this.send({ action: "login", username, password });
    },

    auth(token) {
        this.send({ action: "auth", token });
    },

    // Kisayol metodlari
    createRoom(deck) {
        this.send({ action: "create_room", deck });
    },

    joinRoom(roomId, deck) {
        this.send({ action: "join_room", room_id: roomId, deck });
    },

    quickMatch(deck) {
        this.send({ action: "quick_match", deck });
    },

    sendResponse(msgType, data) {
        this.send({ action: "response", msg_type: msgType, data });
    },

    // Koleksiyon metodlari
    getCollection() {
        this.send({ action: "get_collection" });
    },

    getDecks() {
        this.send({ action: "get_decks" });
    },

    saveDeck(slot, name, cards) {
        this.send({ action: "save_deck", slot, name, cards });
    },

    craftCard(code) {
        this.send({ action: "craft_card", code });
    },

    disenchantCard(code) {
        this.send({ action: "disenchant_card", code });
    },

    playVsBot(bot, deck) {
        this.send({ action: "play_vs_bot", bot, deck });
    },
};
