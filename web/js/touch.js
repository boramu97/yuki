// Yuki — Touch Interactions
// Motor panel swipe, kart long-press preview

(function() {
    // ===== MOTOR PANEL SWIPE =====
    const panel = document.getElementById("motor-panel");
    const handle = document.getElementById("mp-swipe-handle");
    if (panel && handle) {
        let startY = 0, startX = 0, dragging = false;

        handle.addEventListener("pointerdown", (e) => {
            startY = e.clientY;
            startX = e.clientX;
            dragging = true;
            handle.setPointerCapture(e.pointerId);
            e.preventDefault();
        });

        handle.addEventListener("pointermove", (e) => {
            if (!dragging) return;
            const isLandscape = window.matchMedia("(orientation: landscape)").matches
                && window.innerHeight <= 500;
            if (isLandscape) {
                const dx = e.clientX - startX;
                if (dx > 40) { panel.classList.add("minimized"); dragging = false; }
                else if (dx < -40) { panel.classList.remove("minimized"); dragging = false; }
            } else {
                const dy = e.clientY - startY;
                if (dy > 40) { panel.classList.add("minimized"); dragging = false; }
                else if (dy < -40) { panel.classList.remove("minimized"); dragging = false; }
            }
        });

        handle.addEventListener("pointerup", () => { dragging = false; });
        handle.addEventListener("pointercancel", () => { dragging = false; });
    }

    // ===== KART LONG-PRESS PREVIEW =====
    let pressTimer = null, pressTarget = null;

    document.addEventListener("pointerdown", (e) => {
        const card = e.target.closest(".hand-card, .card-face");
        if (!card) return;
        pressTarget = card;
        pressTimer = setTimeout(() => {
            const code = card.dataset?.code || card.querySelector("img")?.src?.match(/\/(\d+)\.jpg/)?.[1];
            if (code && code !== "0") {
                document.getElementById("preview-img").src =
                    `https://images.ygoprodeck.com/images/cards/${code}.jpg`;
                document.getElementById("card-preview-overlay").classList.add("active");
            }
            pressTarget = null;
        }, 400);
    });

    document.addEventListener("pointerup", () => {
        clearTimeout(pressTimer);
        pressTarget = null;
    });

    document.addEventListener("pointermove", (e) => {
        if (pressTarget && (Math.abs(e.movementX) > 5 || Math.abs(e.movementY) > 5)) {
            clearTimeout(pressTimer);
            pressTarget = null;
        }
    });

    document.addEventListener("pointercancel", () => {
        clearTimeout(pressTimer);
        pressTarget = null;
    });
})();
