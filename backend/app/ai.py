"""OpenRouter integration for AI-driven board updates."""

import json
import os
import re
from pathlib import Path
from typing import Any
from urllib import error as urllib_error
from urllib import request as urllib_request

BASE_DIR = Path(__file__).resolve().parents[2]
ENV_FILE = BASE_DIR / ".env"

OPENROUTER_MODEL = "openai/gpt-oss-120b"
OPENROUTER_URL = "https://openrouter.ai/api/v1/chat/completions"


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
            if not {"id", "title", "details"}.issubset(card):
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
