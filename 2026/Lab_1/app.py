from flask import Flask, render_template
from flask_socketio import SocketIO, emit

app = Flask(__name__)
app.config["SECRET_KEY"] = "secret"

socketio = SocketIO(app, cors_allowed_origins="*")

ROWS = 60
COLS = 100

# Створення поля 100x60
grid = [[0 for _ in range(COLS)] for _ in range(ROWS)]


@app.get("/")
def index():
    return render_template("index.html")


@socketio.on("connect")
def handle_connect():

    active_cells = []

    for row in range(ROWS):
        for col in range(COLS):

            if grid[row][col] == 1:
                active_cells.append({
                    "row": row,
                    "col": col
                })

    emit("state_init", {
        "rows": ROWS,
        "cols": COLS,
        "active": active_cells
    })


@socketio.on("toggle_cell")
def handle_toggle_cell(payload):

    row = payload.get("row")
    col = payload.get("col")

    # Перевірка типу координат
    if not isinstance(row, int) or not isinstance(col, int):

        emit("server_error", {
            "message": "Invalid coordinates type"
        })

        return

    # Перевірка виходу за межі поля
    if row < 0 or row >= ROWS or col < 0 or col >= COLS:

        emit("server_error", {
            "message": "Coordinates out of bounds"
        })

        return

    # Перемикання стану клітинки
    grid[row][col] = 1 - grid[row][col]

    # Відправка всім клієнтам
    emit("cell_updated", {
        "row": row,
        "col": col,
        "state": grid[row][col]
    }, broadcast=True)


if __name__ == "__main__":
    socketio.run(app, debug=True)
