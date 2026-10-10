import os
import sqlite3
from flask import Flask, request, jsonify, g

app = Flask(__name__)
DB_PATH = os.environ.get("DB_PATH", "leaderboard.db")
MAX_SECONDS = 365 * 24 * 3600   # chặn số giờ vô lý


def get_db():
    if "db" not in g:
        g.db = sqlite3.connect(DB_PATH)
        g.db.row_factory = sqlite3.Row
    return g.db


@app.teardown_appcontext
def close_db(exc):
    db = g.pop("db", None)
    if db is not None:
        db.close()


def init_db():
    conn = sqlite3.connect(DB_PATH)
    conn.execute("""
        CREATE TABLE IF NOT EXISTS players (
            player_id  TEXT PRIMARY KEY,
            name       TEXT NOT NULL,
            seconds    INTEGER NOT NULL,
            realm      TEXT NOT NULL,
            updated_at TEXT DEFAULT CURRENT_TIMESTAMP
        )
    """)
    conn.commit()
    conn.close()


init_db()


@app.get("/")
def home():
    return jsonify(ok=True, msg="Learning Hub leaderboard API")


@app.post("/submit")
def submit():
    d = request.get_json(silent=True) or {}

    player_id = str(d.get("player_id", "")).strip()[:64]
    if not player_id:
        return jsonify(ok=False, error="missing player_id"), 400

    try:
        seconds = int(d.get("seconds", 0))
    except (TypeError, ValueError):
        return jsonify(ok=False, error="bad seconds"), 400
    seconds = max(0, min(seconds, MAX_SECONDS))

    name = str(d.get("name", "Ẩn danh")).strip()[:30] or "Ẩn danh"
    realm = str(d.get("realm", ""))[:40]

    db = get_db()
    db.execute("""
        INSERT INTO players (player_id, name, seconds, realm)
        VALUES (?, ?, ?, ?)
        ON CONFLICT(player_id) DO UPDATE SET
            name = excluded.name,
            seconds = excluded.seconds,
            realm = excluded.realm,
            updated_at = CURRENT_TIMESTAMP
    """, (player_id, name, seconds, realm))
    db.commit()
    return jsonify(ok=True)


@app.get("/top")
def top():
    rows = get_db().execute(
        "SELECT name, seconds, realm FROM players "
        "ORDER BY seconds DESC LIMIT 20"
    ).fetchall()
    return jsonify([dict(r) for r in rows])


if __name__ == "__main__":
    app.run(debug=False)