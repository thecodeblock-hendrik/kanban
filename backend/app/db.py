"""SQLite persistence for the Kanban board."""

import hashlib
import hmac
import os
import sqlite3
from contextlib import contextmanager
from pathlib import Path
from typing import Any

from fastapi import HTTPException

PBKDF2_ITERATIONS = 100_000
DEFAULT_SEED_USERNAME = "user"
DEFAULT_SEED_PASSWORD = "password"
VALID_PRIORITIES = {"low", "medium", "high"}
DEFAULT_PRIORITY = "medium"

BASE_DIR = Path(__file__).resolve().parents[2]
DB_DIR = BASE_DIR / "data"
DB_PATH = DB_DIR / "pm.db"

DEFAULT_COLUMNS = [
    {"id": "col-backlog", "title": "Backlog", "cardIds": ["card-1"]},
    {"id": "col-discovery", "title": "Discovery", "cardIds": []},
    {"id": "col-progress", "title": "In Progress", "cardIds": ["card-2"]},
    {"id": "col-review", "title": "Review", "cardIds": []},
    {"id": "col-done", "title": "Done", "cardIds": ["card-3"]},
]

DEFAULT_CARDS = {
    "card-1": {"id": "card-1", "title": "Example card: Align roadmap themes", "details": "This is an example card to show how the board works. Draft quarterly themes with impact statements and metrics."},
    "card-2": {"id": "card-2", "title": "Example card: Refine status language", "details": "This is an example card to show how the board works. Standardize column labels and tone across the board."},
    "card-3": {"id": "card-3", "title": "Example card: Ship marketing page", "details": "This is an example card to show how the board works. Final copy approved and asset pack delivered."},
}


def hash_password(password: str, salt: str | None = None) -> tuple[str, str]:
    if salt is None:
        salt = os.urandom(16).hex()
    digest = hashlib.pbkdf2_hmac("sha256", password.encode("utf-8"), salt.encode("utf-8"), PBKDF2_ITERATIONS)
    return digest.hex(), salt


def verify_password(password: str, password_hash: str, salt: str) -> bool:
    candidate, _ = hash_password(password, salt)
    return hmac.compare_digest(candidate, password_hash)


@contextmanager
def get_connection():
    connection = sqlite3.connect(DB_PATH)
    connection.row_factory = sqlite3.Row
    try:
        yield connection
        connection.commit()
    except Exception:
        connection.rollback()
        raise
    finally:
        connection.close()


def init_db() -> None:
    DB_DIR.mkdir(parents=True, exist_ok=True)
    with get_connection() as connection:
        connection.execute(
            """
            CREATE TABLE IF NOT EXISTS users (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                username TEXT NOT NULL UNIQUE,
                password_hash TEXT NOT NULL,
                salt TEXT NOT NULL DEFAULT '',
                created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
            )
            """
        )
        existing_columns = {
            row["name"] for row in connection.execute("PRAGMA table_info(users)").fetchall()
        }
        if "salt" not in existing_columns:
            connection.execute("ALTER TABLE users ADD COLUMN salt TEXT NOT NULL DEFAULT ''")
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
                due_date TEXT,
                priority TEXT NOT NULL DEFAULT 'medium',
                position INTEGER NOT NULL,
                FOREIGN KEY(board_id) REFERENCES boards(id),
                FOREIGN KEY(column_id) REFERENCES board_columns(id)
            )
            """
        )
        card_columns = {
            row["name"] for row in connection.execute("PRAGMA table_info(board_cards)").fetchall()
        }
        if "due_date" not in card_columns:
            connection.execute("ALTER TABLE board_cards ADD COLUMN due_date TEXT")
        if "priority" not in card_columns:
            connection.execute(
                f"ALTER TABLE board_cards ADD COLUMN priority TEXT NOT NULL DEFAULT '{DEFAULT_PRIORITY}'"
            )
        seed_password_hash, seed_salt = hash_password(DEFAULT_SEED_PASSWORD)
        connection.execute(
            "INSERT OR IGNORE INTO users (username, password_hash, salt) VALUES (?, ?, ?)",
            (DEFAULT_SEED_USERNAME, seed_password_hash, seed_salt),
        )
        seed_user = connection.execute(
            "SELECT id, salt FROM users WHERE username = ?",
            (DEFAULT_SEED_USERNAME,),
        ).fetchone()
        if seed_user is not None and not seed_user["salt"]:
            connection.execute(
                "UPDATE users SET password_hash = ?, salt = ? WHERE id = ?",
                (seed_password_hash, seed_salt, seed_user["id"]),
            )
        connection.commit()


def create_user(username: str, password: str) -> int:
    username = username.strip()
    if not username:
        raise ValueError("Username must not be empty.")
    if not password or len(password) < 4:
        raise ValueError("Password must be at least 4 characters.")

    password_hash, salt = hash_password(password)
    with get_connection() as connection:
        existing = connection.execute(
            "SELECT id FROM users WHERE username = ?",
            (username,),
        ).fetchone()
        if existing is not None:
            raise ValueError(f"Username already exists: {username}")

        cursor = connection.execute(
            "INSERT INTO users (username, password_hash, salt) VALUES (?, ?, ?)",
            (username, password_hash, salt),
        )
        connection.commit()
        return cursor.lastrowid


def authenticate_user(username: str, password: str) -> int:
    with get_connection() as connection:
        user = connection.execute(
            "SELECT id, password_hash, salt FROM users WHERE username = ?",
            (username,),
        ).fetchone()

    if user is None or not verify_password(password, user["password_hash"], user["salt"]):
        raise ValueError("Invalid username or password.")

    return user["id"]


def get_user_id(username: str) -> int:
    with get_connection() as connection:
        user = connection.execute(
            "SELECT id FROM users WHERE username = ?",
            (username,),
        ).fetchone()
    if user is None:
        raise HTTPException(status_code=404, detail="User not found")
    return user["id"]


def _seed_default_board(
    connection: sqlite3.Connection, user_id: int, name: str, include_example_cards: bool = True
) -> int:
    cursor = connection.execute(
        "INSERT INTO boards (user_id, name) VALUES (?, ?)",
        (user_id, name),
    )
    board_id = cursor.lastrowid

    for index, column in enumerate(DEFAULT_COLUMNS):
        connection.execute(
            "INSERT INTO board_columns (id, board_id, title, position) VALUES (?, ?, ?, ?)",
            (f"{column['id']}-{board_id}", board_id, column["title"], index),
        )
        if not include_example_cards:
            continue
        for card_index, card_id in enumerate(column["cardIds"]):
            card = DEFAULT_CARDS[card_id]
            connection.execute(
                "INSERT INTO board_cards (id, board_id, column_id, title, details, due_date, priority, position) VALUES (?, ?, ?, ?, ?, ?, ?, ?)",
                (
                    f"{card['id']}-{board_id}",
                    board_id,
                    f"{column['id']}-{board_id}",
                    card["title"],
                    card["details"],
                    None,
                    DEFAULT_PRIORITY,
                    card_index,
                ),
            )

    return board_id


def list_boards(user_id: int) -> list[dict[str, Any]]:
    with get_connection() as connection:
        boards = connection.execute(
            "SELECT id, name, created_at, updated_at FROM boards WHERE user_id = ? ORDER BY id ASC",
            (user_id,),
        ).fetchall()
    return [dict(board) for board in boards]


def create_board(user_id: int, name: str) -> dict[str, Any]:
    name = name.strip()
    if not name:
        raise ValueError("Board name must not be empty.")

    with get_connection() as connection:
        board_id = _seed_default_board(connection, user_id, name, include_example_cards=False)
        connection.commit()
        board = connection.execute(
            "SELECT id, name, created_at, updated_at FROM boards WHERE id = ?",
            (board_id,),
        ).fetchone()
    return dict(board)


def get_or_create_user_board(username: str) -> tuple[int, int]:
    """Return (user_id, board_id), creating the user's first board if none exists."""
    user_id = get_user_id(username)
    with get_connection() as connection:
        board = connection.execute(
            "SELECT id FROM boards WHERE user_id = ? ORDER BY id ASC LIMIT 1",
            (user_id,),
        ).fetchone()
        if board is not None:
            return user_id, board["id"]

        board_id = _seed_default_board(connection, user_id, "Project Board")
        connection.commit()
        return user_id, board_id


def get_board_owned(board_id: int, user_id: int) -> dict[str, Any]:
    with get_connection() as connection:
        board = connection.execute(
            "SELECT id, user_id, name, created_at, updated_at FROM boards WHERE id = ?",
            (board_id,),
        ).fetchone()
    if board is None or board["user_id"] != user_id:
        raise HTTPException(status_code=404, detail="Board not found")
    return dict(board)


def rename_board(board_id: int, user_id: int, name: str) -> dict[str, Any]:
    name = name.strip()
    if not name:
        raise ValueError("Board name must not be empty.")

    get_board_owned(board_id, user_id)
    with get_connection() as connection:
        connection.execute(
            "UPDATE boards SET name = ?, updated_at = CURRENT_TIMESTAMP WHERE id = ?",
            (name, board_id),
        )
        connection.commit()
        board = connection.execute(
            "SELECT id, name, created_at, updated_at FROM boards WHERE id = ?",
            (board_id,),
        ).fetchone()
    return dict(board)


def delete_board(board_id: int, user_id: int) -> None:
    get_board_owned(board_id, user_id)
    with get_connection() as connection:
        connection.execute("DELETE FROM board_cards WHERE board_id = ?", (board_id,))
        connection.execute("DELETE FROM board_columns WHERE board_id = ?", (board_id,))
        connection.execute("DELETE FROM boards WHERE id = ?", (board_id,))
        connection.commit()


def serialize_board(board_id: int) -> dict[str, Any]:
    with get_connection() as connection:
        columns = connection.execute(
            "SELECT id, title FROM board_columns WHERE board_id = ? ORDER BY position ASC",
            (board_id,),
        ).fetchall()

        cards = connection.execute(
            "SELECT id, column_id, title, details, due_date, priority FROM board_cards WHERE board_id = ? ORDER BY position ASC",
            (board_id,),
        ).fetchall()

        card_lookup: dict[str, dict[str, str]] = {}
        for card in cards:
            card_lookup[card["id"]] = {
                "id": card["id"],
                "title": card["title"],
                "details": card["details"],
                "dueDate": card["due_date"],
                "priority": card["priority"],
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


def validate_board_state(board_state: Any) -> tuple[list[dict[str, Any]], dict[str, dict[str, Any]]]:
    if not isinstance(board_state, dict):
        raise ValueError("Board payload must be an object.")

    columns = board_state.get("columns")
    cards = board_state.get("cards")
    if not isinstance(columns, list):
        raise ValueError("Board columns must be a list.")
    if not isinstance(cards, dict):
        raise ValueError("Board cards must be an object keyed by card id.")

    column_ids: set[str] = set()
    referenced_card_ids: set[str] = set()
    for column in columns:
        if not isinstance(column, dict):
            raise ValueError("Board columns must be objects.")
        if not {"id", "title", "cardIds"}.issubset(column):
            raise ValueError("Board columns require id, title, and cardIds fields.")
        column_id = column["id"]
        if not isinstance(column_id, str) or not column_id:
            raise ValueError("Board column ids must be non-empty strings.")
        if column_id in column_ids:
            raise ValueError(f"Duplicate board column id: {column_id}")
        if not isinstance(column["title"], str) or not column["title"].strip():
            raise ValueError("Board column titles must be non-empty strings.")
        if not isinstance(column["cardIds"], list):
            raise ValueError("Board column cardIds must be lists.")
        column_ids.add(column_id)

        for card_id in column["cardIds"]:
            if not isinstance(card_id, str) or not card_id:
                raise ValueError("Board card references must be non-empty strings.")
            if card_id in referenced_card_ids:
                raise ValueError(f"Card appears more than once on the board: {card_id}")
            referenced_card_ids.add(card_id)

    for card_id, card in cards.items():
        if not isinstance(card_id, str) or not card_id:
            raise ValueError("Board card ids must be non-empty strings.")
        if not isinstance(card, dict):
            raise ValueError("Board cards must be objects.")
        if card.get("id") != card_id:
            raise ValueError(f"Board card id does not match its key: {card_id}")
        if not isinstance(card.get("title"), str):
            raise ValueError(f"Board card title must be a string: {card_id}")
        if "details" in card and not isinstance(card["details"], str):
            raise ValueError(f"Board card details must be a string: {card_id}")
        if "dueDate" in card and card["dueDate"] is not None and not isinstance(card["dueDate"], str):
            raise ValueError(f"Board card dueDate must be a string or null: {card_id}")
        if "priority" in card and card["priority"] not in VALID_PRIORITIES:
            raise ValueError(f"Board card priority must be one of {sorted(VALID_PRIORITIES)}: {card_id}")

    missing_cards = referenced_card_ids - set(cards)
    if missing_cards:
        raise ValueError(f"Board references missing cards: {sorted(missing_cards)}")
    orphaned_cards = set(cards) - referenced_card_ids
    if orphaned_cards:
        raise ValueError(f"Board contains unassigned cards: {sorted(orphaned_cards)}")

    return columns, cards


def replace_board_state(board_id: int, user_id: int, board_state: dict[str, Any]) -> dict[str, Any]:
    columns, cards = validate_board_state(board_state)
    get_board_owned(board_id, user_id)

    with get_connection() as connection:
        connection.execute("DELETE FROM board_cards WHERE board_id = ?", (board_id,))
        connection.execute("DELETE FROM board_columns WHERE board_id = ?", (board_id,))

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
                    "INSERT INTO board_cards (id, board_id, column_id, title, details, due_date, priority, position) VALUES (?, ?, ?, ?, ?, ?, ?, ?)",
                    (
                        card_id,
                        board_id,
                        column_id,
                        card["title"],
                        card.get("details", ""),
                        card.get("dueDate"),
                        card.get("priority", DEFAULT_PRIORITY),
                        position,
                    ),
                )

        connection.execute(
            "UPDATE boards SET updated_at = CURRENT_TIMESTAMP WHERE id = ?",
            (board_id,),
        )
        connection.commit()

    return serialize_board(board_id)
