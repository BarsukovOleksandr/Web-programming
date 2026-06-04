const socket = io();

const gridElement = document.getElementById("grid");

let rows = 0;
let cols = 0;

const totalNode = document.getElementById("total");
const filledNode = document.getElementById("filled");
const percentNode = document.getElementById("percent");
const entropyNode = document.getElementById("entropy");

function renderStats(stats) {

    totalNode.textContent = String(stats.total);
    filledNode.textContent = String(stats.filled);

    percentNode.textContent =
        `${stats.percent.toFixed(2)}%`;

    entropyNode.textContent =
        stats.entropy.toFixed(4);
}


// Створення сітки
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

            // Обробка кліку
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


// Оновлення клітинки
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


// Початкова синхронізація
socket.on("state_init", (payload) => {

    renderStats(payload.stats);
    createGrid(payload.rows, payload.cols);

    payload.active.forEach(cell => {

        updateCell(cell.row, cell.col, 1);

    });

});


// Оновлення клітинки від сервера
socket.on("cell_updated", (payload) => {

    updateCell(
        payload.row,
        payload.col,
        payload.state
    );

});


// Обробка помилок
socket.on("server_error", (payload) => {

    alert(payload.message);

});

socket.on("stats_updated", (stats) => { 
    renderStats(stats); 
});