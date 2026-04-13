// Yuki — WebSocket baglanti yonetimi

const WS = {
    socket: null,
    connected: false,
    handlers: {},  // action -> callback

    connect(url) {
        return new Promise((resolve, reject) => {
            this.socket = new WebSocket(url || `ws://${location.hostname}:8765`);

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

    // Kisayol metodlari
    createRoom(name, deck) {
        this.send({ action: "create_room", name, deck });
    },

    joinRoom(name, roomId, deck) {
        this.send({ action: "join_room", name, room_id: roomId, deck });
    },

    quickMatch(name, deck) {
        this.send({ action: "quick_match", name, deck });
    },

    sendResponse(msgType, data) {
        this.send({ action: "response", msg_type: msgType, data });
    },
};
