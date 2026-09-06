import json
import sqlite3
from pathlib import Path
from typing import Any

from fastapi import FastAPI, HTTPException, Query
from fastapi.responses import HTMLResponse, JSONResponse
from fastapi.staticfiles import StaticFiles

BASE_DIR = Path(__file__).resolve().parents[2]
DB_DIR = BASE_DIR / "data"
DB_PATH = DB_DIR / "pm.db"
FRONTEND_BUILD_DIR = BASE_DIR / "frontend" / "out"

DEFAULT_COLUMNS = [
    {"id": "col-backlog", "title": "Backlog", "cardIds": ["card-1", "card-2"]},
    {"id": "col-discovery", "title": "Discovery", "cardIds": ["card-3"]},
    {"id": "col-progress", "title": "In Progress", "cardIds": ["card-4", "card-5"]},
    {"id": "col-review", "title": "Review", "cardIds": ["card-6"]},
    {"id": "col-done", "title": "Done", "cardIds": ["card-7", "card-8"]},
]

DEFAULT_CARDS = {
    "card-1": {"id": "card-1", "title": "Align roadmap themes", "details": "Draft quarterly themes with impact statements and metrics."},
    "card-2": {"id": "card-2", "title": "Gather customer signals", "details": "Review support tags, sales notes, and churn feedback."},
    "card-3": {"id": "card-3", "title": "Prototype analytics view", "details": "Sketch initial dashboard layout and key drill-downs."},
    "card-4": {"id": "card-4", "title": "Refine status language", "details": "Standardize column labels and tone across the board."},
    "card-5": {"id": "card-5", "title": "Design card layout", "details": "Add hierarchy and spacing for scanning dense lists."},
    "card-6": {"id": "card-6", "title": "QA micro-interactions", "details": "Verify hover, focus, and loading states."},
    "card-7": {"id": "card-7", "title": "Ship marketing page", "details": "Final copy approved and asset pack delivered."},
    "card-8": {"id": "card-8", "title": "Close onboarding sprint", "details": "Document release notes and share internally."},
}

app = FastAPI(title="PM MVP Backend")


def get_connection() -> sqlite3.Connection:
    DB_DIR.mkdir(parents=True, exist_ok=True)
    connection = sqlite3.connect(DB_PATH)
    connection.row_factory = sqlite3.Row
    return connection


def init_db() -> None:
    DB_DIR.mkdir(parents=True, exist_ok=True)
    with get_connection() as connection:
        connection.execute(
            """
            CREATE TABLE IF NOT EXISTS users (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                username TEXT NOT NULL UNIQUE,
                password_hash TEXT NOT NULL,
                created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
            )
            """
        )
        connection.execute(
            """
            CREATE TABLE IF NOT EXISTS boards (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER NOT NULL,
                name TEXT NOT NULL DEFAULT 'Project Board',
                created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
                updated_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY(user_id) REFERENCES users(id)
            )
            """
        )
        connection.execute(
            """
            CREATE TABLE IF NOT EXISTS board_columns (
                id TEXT PRIMARY KEY,
                board_id INTEGER NOT NULL,
                title TEXT NOT NULL,
                position INTEGER NOT NULL,
                FOREIGN KEY(board_id) REFERENCES boards(id)
            )
            """
        )
        connection.execute(
            """
            CREATE TABLE IF NOT EXISTS board_cards (
                id TEXT PRIMARY KEY,
                board_id INTEGER NOT NULL,
                column_id TEXT NOT NULL,
                title TEXT NOT NULL,
                details TEXT NOT NULL DEFAULT '',
                position INTEGER NOT NULL,
                FOREIGN KEY(board_id) REFERENCES boards(id),
                FOREIGN KEY(column_id) REFERENCES board_columns(id)
            )
            """
        )
        connection.execute(
            "INSERT OR IGNORE INTO users (username, password_hash) VALUES (?, ?)",
            ("user", "password"),
        )
        connection.commit()


def get_or_create_user_board(username: str) -> tuple[int, int]:
    init_db()
    with get_connection() as connection:
        user = connection.execute(
            "SELECT id FROM users WHERE username = ?",
            (username,),
        ).fetchone()
        if user is None:
            raise HTTPException(status_code=404, detail="User not found")

        board = connection.execute(
            "SELECT id FROM boards WHERE user_id = ? ORDER BY id ASC LIMIT 1",
            (user["id"],),
        ).fetchone()

        if board is not None:
            return user["id"], board["id"]

        cursor = connection.execute(
            "INSERT INTO boards (user_id, name) VALUES (?, ?)",
            (user["id"], "Project Board"),
        )
        board_id = cursor.lastrowid

        for index, column in enumerate(DEFAULT_COLUMNS):
            connection.execute(
                "INSERT INTO board_columns (id, board_id, title, position) VALUES (?, ?, ?, ?)",
                (column["id"], board_id, column["title"], index),
            )
            for card_index, card_id in enumerate(column["cardIds"]):
                card = DEFAULT_CARDS[card_id]
                connection.execute(
                    "INSERT INTO board_cards (id, board_id, column_id, title, details, position) VALUES (?, ?, ?, ?, ?, ?)",
                    (card["id"], board_id, column["id"], card["title"], card["details"], card_index),
                )

        connection.commit()
        return user["id"], board_id


def serialize_board(board_id: int) -> dict[str, Any]:
    init_db()
    with get_connection() as connection:
        columns = connection.execute(
            "SELECT id, title FROM board_columns WHERE board_id = ? ORDER BY position ASC",
            (board_id,),
        ).fetchall()

        cards = connection.execute(
            "SELECT id, column_id, title, details FROM board_cards WHERE board_id = ? ORDER BY position ASC",
            (board_id,),
        ).fetchall()

        card_lookup: dict[str, dict[str, str]] = {}
        for card in cards:
            card_lookup[card["id"]] = {
                "id": card["id"],
                "title": card["title"],
                "details": card["details"],
            }

        column_payload = []
        for column in columns:
            column_card_ids = [
                row["id"]
                for row in cards
                if row["column_id"] == column["id"]
            ]
            column_payload.append(
                {
                    "id": column["id"],
                    "title": column["title"],
                    "cardIds": column_card_ids,
                }
            )

    return {"columns": column_payload, "cards": card_lookup}


def replace_board_state(username: str, board_state: dict[str, Any]) -> dict[str, Any]:
    init_db()
    _, board_id = get_or_create_user_board(username)

    with get_connection() as connection:
        connection.execute("DELETE FROM board_cards WHERE board_id = ?", (board_id,))
        connection.execute("DELETE FROM board_columns WHERE board_id = ?", (board_id,))

        columns = board_state.get("columns", [])
        cards = board_state.get("cards", {})

        for position, column in enumerate(columns):
            column_id = column["id"]
            title = column["title"]
            connection.execute(
                "INSERT INTO board_columns (id, board_id, title, position) VALUES (?, ?, ?, ?)",
                (column_id, board_id, title, position),
            )

        for column in columns:
            column_id = column["id"]
            for position, card_id in enumerate(column.get("cardIds", [])):
                card = cards.get(card_id)
                if card is None:
                    continue
                connection.execute(
                    "INSERT INTO board_cards (id, board_id, column_id, title, details, position) VALUES (?, ?, ?, ?, ?, ?)",
                    (card_id, board_id, column_id, card["title"], card.get("details", ""), position),
                )

        connection.execute(
            "UPDATE boards SET updated_at = CURRENT_TIMESTAMP WHERE id = ?",
            (board_id,),
        )
        connection.commit()

    return serialize_board(board_id)


@app.on_event("startup")
async def startup_event() -> None:
    init_db()


@app.get("/api/health")
async def healthcheck() -> JSONResponse:
    return JSONResponse({"status": "ok", "service": "pm-mvp-backend"})


@app.get("/api/board")
async def get_board(user: str = Query(..., min_length=1)) -> dict[str, Any]:
    _, board_id = get_or_create_user_board(user)
    return {"user": user, "board": serialize_board(board_id)}


@app.put("/api/board")
async def update_board(body: dict[str, Any], user: str = Query(..., min_length=1)) -> dict[str, Any]:
    if not isinstance(body, dict):
        raise HTTPException(status_code=400, detail="Board payload must be a JSON object")

    board = replace_board_state(user, body)
    return {"user": user, "board": board}


if FRONTEND_BUILD_DIR.exists():
    app.mount("/", StaticFiles(directory=str(FRONTEND_BUILD_DIR), html=True), name="frontend")
else:

    @app.get("/", response_class=HTMLResponse)
    async def read_root() -> HTMLResponse:
        return HTMLResponse(
            """
            <html>
                <head>
                    <title>PM MVP</title>
                    <meta charset="utf-8" />
                </head>
                <body>
                    <h1>PM MVP</h1>
                    <p>Hello from the FastAPI backend.</p>
                </body>
            </html>
            """
        )
