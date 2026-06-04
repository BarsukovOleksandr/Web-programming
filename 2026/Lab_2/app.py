from math import log2
from threading import Lock
import logging

from flask import Flask, render_template
from flask_socketio import SocketIO, emit

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

app = Flask(__name__)
app.config["SECRET_KEY"] = "secret"

socketio = SocketIO(app, cors_allowed_origins="*")

ROWS = 60
COLS = 100

grid = [[0 for _ in range(COLS)] for _ in range(ROWS)]


class InMemoryCache:
    def __init__(self):
        self._values = {}
        self._lock = Lock()

    def get(self, key, default=None):
        with self._lock:
            return self._values.get(key, default)

    def set(self, key, value):
        with self._lock:
            self._values[key] = value
            return value

    def delete(self, key):
        with self._lock:
            self._values.pop(key, None)

    def clear(self):
        with self._lock:
            self._values.clear()

    def get_or_set(self, key, factory):
        with self._lock:
            if key not in self._values:
                self._values[key] = factory()
            return self._values[key]


cache = InMemoryCache()


def compute_entropy(active: int, total: int) -> float:
    if total <= 0:
        return 0.0

    p_active = active / total
    p_inactive = 1.0 - p_active

    entropy = 0.0

    if p_inactive > 0:
        entropy -= p_inactive * log2(p_inactive)

    if p_active > 0:
        entropy -= p_active * log2(p_active)

    return entropy


def build_stats_snapshot():
    active = sum(sum(row) for row in grid)
    total = ROWS * COLS

    logger.info(
        "Recomputing stats cache: active=%s total=%s",
        active,
        total
    )

    percent = (active / total) * 100 if total else 0

    return {
        "total": total,
        "filled": active,
        "percent": percent,
        "entropy": compute_entropy(active, total)
    }


cache.set("grid_stats", build_stats_snapshot())


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
        "active": active_cells,
        "stats": cache.get_or_set(
            "grid_stats",
            build_stats_snapshot
        )
    })


@socketio.on("toggle_cell")
def handle_toggle_cell(payload):

    row = payload.get("row")
    col = payload.get("col")

    if not isinstance(row, int) or not isinstance(col, int):
        emit("server_error", {
            "message": "Invalid coordinates type"
        })
        return

    if row < 0 or row >= ROWS or col < 0 or col >= COLS:
        emit("server_error", {
            "message": "Coordinates out of bounds"
        })
        return

    grid[row][col] = 1 - grid[row][col]

    emit("cell_updated", {
        "row": row,
        "col": col,
        "state": grid[row][col]
    }, broadcast=True)

    stats_snapshot = cache.set(
        "grid_stats",
        build_stats_snapshot()
    )

    emit(
        "stats_updated",
        stats_snapshot,
        broadcast=True
    )


if __name__ == "__main__":
    socketio.run(app, debug=True)