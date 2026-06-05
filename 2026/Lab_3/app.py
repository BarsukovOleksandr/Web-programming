from math import log2
from threading import Lock
import json
import logging
from pathlib import Path

from flask import send_from_directory
from flask import Flask, render_template, jsonify, request
from flask_socketio import SocketIO, emit
from pywebpush import webpush, WebPushException


logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

app = Flask(__name__)
app.config["SECRET_KEY"] = "secret"

@app.route("/service-worker.js")
def service_worker():
    return send_from_directory(".", "service-worker.js")

socketio = SocketIO(app, cors_allowed_origins="*")

ROWS = 60
COLS = 100

grid = [[0 for _ in range(COLS)] for _ in range(ROWS)]

VAPID_PUBLIC_KEY = "BKt8dX-OSQ0mcgkbzpM3LGCd5FPlnItLFiT8v1GUEkTGY6zquy3S_436SF1toGRtFSeD7bbwqlefjQtmUbSCkkU"
VAPID_PRIVATE_KEY = "sYusFYg8-gAW4Q5DsWczGUZ3eaTK5XQZG8rK9vHWxH4"
VAPID_CLAIMS = {
    "sub": "mailto:admin@example.com"
}

SUBSCRIPTIONS_FILE = Path("subscriptions.json")


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

    def get_or_set(self, key, factory):
        with self._lock:
            if key not in self._values:
                self._values[key] = factory()
            return self._values[key]


cache = InMemoryCache()


def load_subscriptions():
    if not SUBSCRIPTIONS_FILE.exists():
        return {}

    with open(SUBSCRIPTIONS_FILE, "r", encoding="utf-8") as file:
        return json.load(file)


def save_subscriptions(subscriptions):
    with open(SUBSCRIPTIONS_FILE, "w", encoding="utf-8") as file:
        json.dump(subscriptions, file, indent=4)


subscriptions = load_subscriptions()


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


@app.get("/manifest.json")
def manifest():
    return app.send_static_file("manifest.json")


@app.get("/api/push/public-key")
def public_key():
    return jsonify({
        "publicKey": VAPID_PUBLIC_KEY
    })


@app.post("/api/push/subscribe")
def subscribe():
    subscription = request.get_json()

    subscriptions[subscription["endpoint"]] = subscription
    save_subscriptions(subscriptions)

    return jsonify({
        "status": "subscribed"
    })


@app.post("/api/push/unsubscribe")
def unsubscribe():
    payload = request.get_json()
    endpoint = payload.get("endpoint")

    if endpoint in subscriptions:
        subscriptions.pop(endpoint)
        save_subscriptions(subscriptions)

    return jsonify({
        "status": "unsubscribed"
    })


def send_launch_push():
    payload = json.dumps({
        "title": "Collaborative Grid",
        "body": "Новий клієнт підключився до системи"
    })

    invalid = []

    for endpoint, subscription in subscriptions.items():
        try:
            webpush(
                subscription_info=subscription,
                data=payload,
                vapid_private_key=VAPID_PRIVATE_KEY,
                vapid_claims=VAPID_CLAIMS
            )
        except WebPushException:
            invalid.append(endpoint)

    for endpoint in invalid:
        subscriptions.pop(endpoint, None)

    save_subscriptions(subscriptions)


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


@socketio.on("announce_launch")
def handle_announce_launch():
    send_launch_push()


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
