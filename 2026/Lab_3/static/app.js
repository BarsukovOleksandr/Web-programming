const socket = io();

const gridElement = document.getElementById("grid");

let rows = 0;
let cols = 0;

const totalNode = document.getElementById("total");
const filledNode = document.getElementById("filled");
const percentNode = document.getElementById("percent");
const entropyNode = document.getElementById("entropy");

const swStateNode = document.getElementById("sw-state");
const networkStateNode = document.getElementById("network-state");
const pushStateNode = document.getElementById("push-state");

function renderStats(stats) {

    totalNode.textContent = String(stats.total);
    filledNode.textContent = String(stats.filled);

    percentNode.textContent =
        `${stats.percent.toFixed(2)}%`;

    entropyNode.textContent =
        stats.entropy.toFixed(4);
}

function updateNetworkState() {
    networkStateNode.textContent =
        navigator.onLine ? "Online" : "Offline";
}

window.addEventListener("online", updateNetworkState);
window.addEventListener("offline", updateNetworkState);

updateNetworkState();

function createGrid(r, c) {

    rows = r;
    cols = c;

    gridElement.innerHTML = "";

    for (let row = 0; row < rows; row++) {

        for (let col = 0; col < cols; col++) {

            const cell = document.createElement("button");

            cell.className = "cell";

            cell.dataset.row = row;
            cell.dataset.col = col;

            cell.addEventListener("click", () => {

                socket.emit("toggle_cell", {
                    row: row,
                    col: col
                });

            });

            gridElement.appendChild(cell);
        }
    }
}

function updateCell(row, col, state) {

    const index = row * cols + col;

    const cell = gridElement.children[index];

    if (!cell) return;

    if (state === 1) {
        cell.classList.add("active");
    } else {
        cell.classList.remove("active");
    }
}

socket.on("state_init", (payload) => {

    renderStats(payload.stats);
    createGrid(payload.rows, payload.cols);

    payload.active.forEach(cell => {
        updateCell(cell.row, cell.col, 1);
    });

});

socket.on("cell_updated", (payload) => {

    updateCell(
        payload.row,
        payload.col,
        payload.state
    );

});

socket.on("server_error", (payload) => {
    alert(payload.message);
});

socket.on("stats_updated", (stats) => {
    renderStats(stats);
});

async function registerServiceWorker() {

    if (!("serviceWorker" in navigator)) {
        swStateNode.textContent = "Service Worker не підтримується";
        return;
    }

    try {

        const registration = await navigator.serviceWorker.register(
            "/service-worker.js"
        );

        swStateNode.textContent =
            `SW активний: ${registration.scope}`;

        if (registration.waiting) {
            registration.waiting.postMessage({
                type: "SKIP_WAITING"
            });
        }

        navigator.serviceWorker.addEventListener(
            "controllerchange",
            () => {
                window.location.reload();
            }
        );

        socket.emit("announce_launch");

    } catch (error) {

        swStateNode.textContent =
            `SW помилка: ${error.message}`;
    }
}

function urlBase64ToUint8Array(base64String) {

    const padding = "=".repeat(
        (4 - (base64String.length % 4)) % 4
    );

    const base64 = (base64String + padding)
        .replace(/-/g, "+")
        .replace(/_/g, "/");

    const rawData = window.atob(base64);

    return Uint8Array.from(
        [...rawData].map((char) => char.charCodeAt(0))
    );
}

async function subscribePush() {

    const permission =
        await Notification.requestPermission();

    if (permission !== "granted") {
        pushStateNode.textContent =
            "Push-дозвіл не надано";
        return;
    }

    const registration =
        await navigator.serviceWorker.ready;

    const response =
        await fetch("/api/push/public-key");

    const data = await response.json();

    const subscription =
        await registration.pushManager.subscribe({
            userVisibleOnly: true,
            applicationServerKey:
                urlBase64ToUint8Array(data.publicKey)
        });

    await fetch("/api/push/subscribe", {
        method: "POST",
        headers: {
            "Content-Type": "application/json"
        },
        body: JSON.stringify(subscription)
    });

    pushStateNode.textContent =
        "Push-підписка активна";
}

document
    .getElementById("subscribe-btn")
    .addEventListener("click", subscribePush);

registerServiceWorker();
