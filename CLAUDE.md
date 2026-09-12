# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project overview

A local-only Project Management MVP: a single-user (MVP) Kanban board with drag-and-drop, served as one app. Next.js is built to static output and served by FastAPI, which also owns all persistence (SQLite) and the AI chat integration (OpenRouter). See `AGENTS.md` for full business requirements and `docs/PLAN.md` for the phased implementation plan (source of truth for feature sequencing — don't jump ahead of it without user approval). `docs/DATABASE.md` documents the schema rationale.

Auth is hardcoded to username `user` / password `password` for the MVP; the schema supports multiple users but only one board per user is used.

## Commands

### Backend (run from repo root; `backend/` and `backend/app/` are Python packages, so tests import via `backend.app.main`)
```bash
python3 -m pytest backend/tests -q                       # all backend tests
python3 -m pytest backend/tests/test_board_api.py -q      # single file
python3 -m uvicorn backend.app.main:app --reload --port 8000  # run backend only (no static frontend unless frontend/out exists)
```
Backend deps: `pip install -r backend/requirements.txt` (or `uv pip install -r backend/requirements.txt`, matching the Dockerfile).

### Frontend (run from `frontend/`)
```bash
npm run dev          # dev server
npm run build         # production build -> frontend/out (static export, consumed by backend)
npm run lint
npm run test          # == test:unit (Vitest)
npm run test:unit:watch
npm run test:e2e      # Playwright
npm run test:all      # unit + e2e
```
To run a single Vitest test file: `npx vitest run src/lib/kanban.test.ts`.

### Full app (Docker)
```bash
scripts/start.sh   # builds image, runs container on :8000, picks up root .env
scripts/stop.sh
```
The Dockerfile multi-stage builds the frontend (`next build` → static export in `frontend/out`) then copies it into the Python image; FastAPI serves it via `StaticFiles` mounted at `/`. If `frontend/out` doesn't exist, the backend falls back to an inline "Hello" HTML page — useful when iterating on the backend alone.

## Architecture

### Backend (`backend/app/`)
Split into three modules by concern; there's still no ORM or dependency-injection framework, just plain module-level functions:
- **`db.py`** — all SQLite persistence (raw `sqlite3`, no ORM). Tables: `users`, `boards`, `board_columns`, `board_cards`. `init_db()` creates tables and seeds the hardcoded `user`/`password` row on startup (via `main.py`'s `lifespan`). `get_or_create_user_board()` lazily creates a user's board (and default 5-column/8-card layout from `DEFAULT_COLUMNS`/`DEFAULT_CARDS`) on first access. `get_connection()` is a `@contextmanager` that always commits-or-rolls-back and closes the connection — never open `sqlite3.connect()` directly elsewhere. `replace_board_state()` fully validates the incoming board (`validate_board_state()` — checks for duplicate/orphaned/missing card ids, non-empty titles, etc.) before deleting and rewriting `board_columns`/`board_cards` for that board in one connection. Never persist an unvalidated payload.
- **`ai.py`** — the OpenRouter integration. `call_openrouter()` hits OpenRouter (`openai/gpt-oss-120b`) with a plain `urllib` POST (no SDK). `OPENROUTER_API_KEY` is read from the root `.env` via a minimal hand-rolled `load_env()` (not python-dotenv). `build_board_prompt()` embeds the full current board JSON + chat history and requires the model to return structured JSON (`{"response": ..., "board_update": {...}|omitted}`); `parse_ai_board_response()`/`validate_ai_board_update()` strictly validate that shape. Treat model output as untrusted input — validation happens here, but the actual mutation still goes through `db.replace_board_state()`.
- **`main.py`** — thin FastAPI wiring: `lifespan` calls `db.init_db()` on startup, routes call into `db`/`ai` by module-qualified reference (`db.get_or_create_user_board(...)`, `ai.call_openrouter(...)`, etc. — not `from .db import x`, so tests can monkeypatch the function on its defining module). Routes: `GET /api/health`, `GET /api/ai/test` (quick OpenRouter smoke test), `POST /api/ai/board`, `GET/PUT /api/board?user=...` (user passed as a query param, not real auth), and the `/` static mount.
- **Board serialization contract**: the wire format is always `{"columns": [{id, title, cardIds: [...]}], "cards": {cardId: {id, title, details}}}` — columns hold ordering via `cardIds`, cards are a flat lookup map. This exact shape is shared by `GET/PUT /api/board`, the AI's `board_update`, and the frontend's `BoardData` type (`frontend/src/lib/kanban.ts`). Keep both sides in sync if it changes.
- **Tests monkeypatch at the defining module**, not `main`: `backend/tests/test_board_api.py` does `monkeypatch.setattr(db, "DB_DIR"/"DB_PATH", ...)` for DB isolation and `monkeypatch.setattr(ai, "call_openrouter", fake)` to stub the AI call. If you move a function to a different module, update these patch targets accordingly.

### Frontend (`frontend/src/`)
- `lib/kanban.ts` — pure board logic and the canonical `BoardData`/`Column`/`Card` types. `moveCard()` is the core drag-and-drop reducer (handles same-column reorder, cross-column move, and dropping onto an empty column placeholder via the `-empty` id suffix convention). Keep new board logic here rather than in components, and prefer testing it as pure functions.
- `components/KanbanBoard.tsx` — the stateful orchestrator: loads the board from `GET /api/board` on mount, wires `@dnd-kit` drag events through `moveCard()`, and persists board changes via `PUT /api/board`. Saving is debounced (400ms) and single-flight: every board change updates `pendingBoardRef` immediately, but only one `PUT` is ever in flight (`isSavingRef`); a change that arrives mid-save is picked up right after the in-flight one finishes, so the request sent always reflects the latest board and responses can't land out of order. A pending save is also flushed immediately on unmount (e.g. logout) so it isn't lost to the debounce timer being cleared. Also owns the AI chat sidebar state (`chatMessages`, calls `POST /api/ai/board`) and applies any returned `board` directly to state.
- `components/KanbanColumn.tsx`, `KanbanCard.tsx`, `KanbanCardPreview.tsx`, `NewCardForm.tsx` — presentational/interaction pieces used by `KanbanBoard`.
- Next.js is configured for static export (`next build` → `out/`) since FastAPI serves the build output directly; there's no Next.js server runtime in production.

### Data flow for AI-driven board edits
User message → `KanbanBoard` posts to `/api/ai/board` with prompt + history → backend serializes current board, prompts OpenRouter for structured JSON → backend validates `board_update` → if present, `replace_board_state()` persists it and the response includes the new authoritative `board` → frontend replaces local state with the server's returned board (not a locally-computed merge).

## Working conventions (from `AGENTS.md`)
- Keep it simple: no over-engineering, no unnecessary defensive programming, no speculative features.
- Use current/idiomatic library versions and patterns.
- No emojis, anywhere (code, docs, commit messages, UI).
- When debugging, find the root cause before attempting a fix — don't guess-and-check.
- `docs/PLAN.md` gates implementation order; don't build ahead of the approved phase without checking with the user.
- App color scheme (if touching UI): Accent Yellow `#ecad0a`, Blue Primary `#209dd7`, Purple Secondary `#753991`, Dark Navy `#032147`, Gray Text `#888888`.

## Detailed Plan

@docs/PLAN.md