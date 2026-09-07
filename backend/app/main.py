import json
import os
import re
import sqlite3
from pathlib import Path
from typing import Any
from urllib import error as urllib_error
from urllib import request as urllib_request

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
OPENROUTER_MODEL = "openai/gpt-oss-120b"
OPENROUTER_URL = "https://openrouter.ai/api/v1/chat/completions"
ENV_FILE = BASE_DIR / ".env"


def load_env() -> None:
    if not ENV_FILE.exists():
        return

    for line in ENV_FILE.read_text(encoding="utf-8").splitlines():
        stripped = line.strip()
        if not stripped or stripped.startswith("#") or "=" not in stripped:
            continue

        key, value = stripped.split("=", 1)
        os.environ.setdefault(key.strip(), value.strip().strip('"').strip("'"))


def get_openrouter_api_key() -> str:
    load_env()
    api_key = os.getenv("OPENROUTER_API_KEY")
    if not api_key:
        raise RuntimeError("OPENROUTER_API_KEY is missing. Add it to the project .env file.")
    return api_key


def normalize_ai_prompt(prompt: str) -> str:
    normalized = prompt.strip()
    normalized = re.sub(r"(?<=\d)\s*\+\s*(?=\d)", " + ", normalized)
    normalized = re.sub(r"(?<=\d)\s+(?=\d)", " + ", normalized)
    return normalized


def call_openrouter(prompt: str) -> str:
    api_key = get_openrouter_api_key()
    payload = {
        "model": OPENROUTER_MODEL,
        "messages": [{"role": "user", "content": prompt}],
    }

    request = urllib_request.Request(
        OPENROUTER_URL,
        data=json.dumps(payload).encode("utf-8"),
        headers={
            "Authorization": f"Bearer {api_key}",
            "Content-Type": "application/json",
            "HTTP-Referer": "http://localhost:8000",
            "X-Title": "PM MVP",
        },
        method="POST",
    )

    try:
        with urllib_request.urlopen(request, timeout=30) as response:
            body = response.read().decode("utf-8")
    except urllib_error.HTTPError as exc:
        error_details = exc.read().decode("utf-8", errors="replace")
        raise RuntimeError(f"OpenRouter request failed: {error_details}") from exc
    except urllib_error.URLError as exc:
        raise RuntimeError(f"OpenRouter is unavailable: {exc.reason}") from exc

    response_data = json.loads(body)
    choices = response_data.get("choices") or []
    if not choices:
        error = response_data.get("error")
        if error:
            raise RuntimeError(str(error))
        raise RuntimeError("OpenRouter response did not include any choices.")

    content = choices[0].get("message", {}).get("content")
    if isinstance(content, list):
        text_parts = []
        for item in content:
            if isinstance(item, dict):
                text_value = item.get("text") or item.get("content")
                if isinstance(text_value, str):
                    text_parts.append(text_value)
        content = "".join(text_parts)

    if not isinstance(content, str) or not content.strip():
        raise RuntimeError("OpenRouter response did not include readable text content.")

    return content.strip()


def build_board_prompt(user_prompt: str, history: list[dict[str, Any]], board: dict[str, Any]) -> str:
    serialized_history = json.dumps(history, ensure_ascii=False)
    serialized_board = json.dumps(board, ensure_ascii=False)
    return (
        "You are helping manage a Kanban board. "
        "Return valid JSON only. "
        "Use this exact schema: {\"response\": string, \"board_update\": {\"columns\": [...], \"cards\": {...}}}. "
        "The board_update field is optional and should only be included when the user asks for a board change. "
        "Current board JSON: "
        f"{serialized_board}. "
        "conversation history: "
        f"{serialized_history}. "
        f"User prompt: {user_prompt}."
    )


def validate_ai_board_update(board_update: Any) -> dict[str, Any]:
    if board_update is None:
        return {}
    if not isinstance(board_update, dict):
        raise ValueError("AI board update must be an object.")

    columns = board_update.get("columns")
    cards = board_update.get("cards")

    if columns is not None:
        if not isinstance(columns, list):
            raise ValueError("AI board update columns must be a list.")
        for column in columns:
            if not isinstance(column, dict):
                raise ValueError("AI board column entries must be objects.")
            missing = {"id", "title", "cardIds"} - set(column)
            if missing:
                raise ValueError("AI board column entries are missing required fields.")
            if not isinstance(column["id"], str) or not isinstance(column["title"], str):
                raise ValueError("AI board columns require a string id and title.")
            if not isinstance(column["cardIds"], list):
                raise ValueError("AI board column cardIds must be a list.")

    if cards is not None:
        if not isinstance(cards, dict):
            raise ValueError("AI board cards must be an object keyed by card id.")
        for card_id, card in cards.items():
            if not isinstance(card_id, str):
                raise ValueError("AI board card ids must be strings.")
            if not isinstance(card, dict):
                raise ValueError("AI board card entries must be objects.")
            if set(card) < {"id", "title", "details"}:
                raise ValueError("AI board cards require id, title, and details fields.")

    if columns is None and cards is not None:
        raise ValueError("AI board updates must include the full columns list when cards are present.")
    if columns is not None and cards is None:
        raise ValueError("AI board updates must include the cards object when columns are present.")

    return board_update


def parse_ai_board_response(raw_response: str) -> dict[str, Any]:
    try:
        payload = json.loads(raw_response)
    except json.JSONDecodeError as exc:
        raise ValueError("AI response was not valid JSON.") from exc

    if not isinstance(payload, dict):
        raise ValueError("AI response must be a structured JSON object.")

    response_text = payload.get("response")
    if not isinstance(response_text, str) or not response_text.strip():
        raise ValueError("AI response must include a non-empty string 'response' field.")

    board_update = payload.get("board_update")
    validated_update = validate_ai_board_update(board_update)

    return {"response": response_text.strip(), "board_update": validated_update if board_update is not None else None}


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


@app.get("/api/ai/test")
async def test_ai(prompt: str = Query("2 + 2", min_length=1)) -> dict[str, Any]:
    normalized_prompt = normalize_ai_prompt(prompt)
    try:
        response = call_openrouter(normalized_prompt)
        return {"ok": True, "model": OPENROUTER_MODEL, "prompt": normalized_prompt, "response": response}
    except Exception as exc:  # pragma: no cover - exercised via HTTP tests
        raise HTTPException(status_code=503, detail=str(exc)) from exc


@app.post("/api/ai/board")
async def ai_board(body: dict[str, Any], user: str = Query(..., min_length=1)) -> dict[str, Any]:
    if not isinstance(body, dict):
        raise HTTPException(status_code=400, detail="AI request payload must be a JSON object.")

    prompt = body.get("prompt")
    if not isinstance(prompt, str) or not prompt.strip():
        raise HTTPException(status_code=400, detail="AI request must include a non-empty prompt string.")

    history = body.get("history", [])
    if not isinstance(history, list):
        raise HTTPException(status_code=400, detail="AI request history must be a list when provided.")

    _, board_id = get_or_create_user_board(user)
    board_state = serialize_board(board_id)
    model_prompt = build_board_prompt(prompt, history, board_state)

    try:
        raw_response = call_openrouter(model_prompt)
    except Exception as exc:  # pragma: no cover - exercised via HTTP tests
        raise HTTPException(status_code=503, detail=str(exc)) from exc

    try:
        parsed = parse_ai_board_response(raw_response)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=f"AI response was not a valid structured JSON payload: {exc}") from exc

    response_text = parsed["response"]
    payload = {"response": response_text}

    if parsed.get("board_update") is not None:
        payload["board"] = replace_board_state(user, parsed["board_update"])
    else:
        payload["board"] = serialize_board(board_id)

    return payload


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
