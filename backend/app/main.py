"""FastAPI app: routing, static frontend serving, and startup wiring.

Persistence lives in db.py, the OpenRouter/AI integration lives in ai.py.
"""

from contextlib import asynccontextmanager
from pathlib import Path
from typing import Any

from fastapi import FastAPI, HTTPException, Query
from fastapi.responses import HTMLResponse, JSONResponse
from fastapi.staticfiles import StaticFiles

from . import ai, db

BASE_DIR = Path(__file__).resolve().parents[2]
FRONTEND_BUILD_DIR = BASE_DIR / "frontend" / "out"


@asynccontextmanager
async def lifespan(app: FastAPI):
    db.init_db()
    yield


app = FastAPI(title="PM MVP Backend", lifespan=lifespan)


@app.get("/api/health")
async def healthcheck() -> JSONResponse:
    return JSONResponse({"status": "ok", "service": "pm-mvp-backend"})


@app.get("/api/ai/test")
async def test_ai(prompt: str = Query("2 + 2", min_length=1)) -> dict[str, Any]:
    normalized_prompt = ai.normalize_ai_prompt(prompt)
    try:
        response = ai.call_openrouter(normalized_prompt)
        return {"ok": True, "model": ai.OPENROUTER_MODEL, "prompt": normalized_prompt, "response": response}
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

    _, board_id = db.get_or_create_user_board(user)
    board_state = db.serialize_board(board_id)
    model_prompt = ai.build_board_prompt(prompt, history, board_state)

    try:
        raw_response = ai.call_openrouter(model_prompt)
    except Exception as exc:  # pragma: no cover - exercised via HTTP tests
        raise HTTPException(status_code=503, detail=str(exc)) from exc

    try:
        parsed = ai.parse_ai_board_response(raw_response)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=f"AI response was not a valid structured JSON payload: {exc}") from exc

    response_text = parsed["response"]
    payload = {"response": response_text}

    if parsed.get("board_update") is not None:
        try:
            payload["board"] = db.replace_board_state(user, parsed["board_update"])
        except ValueError as exc:
            raise HTTPException(status_code=400, detail=f"AI board update was invalid: {exc}") from exc
    else:
        payload["board"] = db.serialize_board(board_id)

    return payload


@app.get("/api/board")
async def get_board(user: str = Query(..., min_length=1)) -> dict[str, Any]:
    _, board_id = db.get_or_create_user_board(user)
    return {"user": user, "board": db.serialize_board(board_id)}


@app.put("/api/board")
async def update_board(body: dict[str, Any], user: str = Query(..., min_length=1)) -> dict[str, Any]:
    if not isinstance(body, dict):
        raise HTTPException(status_code=400, detail="Board payload must be a JSON object")

    try:
        board = db.replace_board_state(user, body)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
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
