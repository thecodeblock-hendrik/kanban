# Code Review

Full-repo review of `backend/` and `frontend/` (state as of commit `dfee079`,
2026-09-11). Findings are ranked most-severe first. Each includes the
concrete failure scenario and a proposed action.

**Status:** Findings 1-5 (High and Medium severity) have been fixed and
verified — backend pytest suite (10/10), frontend Vitest suite (16/16),
`next build`, and ESLint all pass. Findings 6-7 (Low severity) are left
open as documented improvements, not yet actioned.

## 1. Autosave can silently persist a stale board (lost update) — FIXED

**File:** `frontend/src/components/KanbanBoard.tsx:71-103`

The save effect fires a new `PUT /api/board` on every `board` state change,
with no debounce and no cancellation of in-flight requests:

```tsx
useEffect(() => {
  if (!isLoaded) return;
  const saveId = ++saveSequenceRef.current;
  const saveBoard = async () => {
    const response = await fetch(`/api/board?user=...`, { method: "PUT", body: JSON.stringify(board), ... });
    if (saveId !== saveSequenceRef.current) return; // only suppresses the error banner
    ...
  };
  void saveBoard();
}, [board, isLoaded, username]);
```

`saveSequenceRef` only decides whether to update the `error` state for a
*response* that arrives late — it does not stop the underlying `fetch` from
being sent, and it does not stop an older request from finishing (and
writing to the DB) after a newer one. Fast successive edits (typing a column
title character-by-character, or several quick drags) each launch an
independent PUT with the board snapshot at that instant. Network/server
timing is not guaranteed to preserve send order, so an older PUT can
complete *after* a newer one and overwrite it in SQLite. The UI keeps
showing the newest state (it's driven by local `board` state, not the
server response), so the user sees no error — the regression is silent and
only surfaces on next reload, when the server returns the stale version.

This is a documented tradeoff in `CLAUDE.md` ("drop stale/out-of-order save
*responses*... rather than a debounce"), but that only protects the error
banner, not the data itself.

**Proposed action:** Serialize saves — chain each save on the previous
save's promise (or maintain a single in-flight request and queue only the
latest pending board), so at most one PUT is in flight and it always
reflects the latest `board`. A debounce (see finding 5) reduces how often
this triggers but doesn't remove the race by itself; sequencing is the
actual fix.

## 2. SQLite connections are opened but never closed — FIXED

**File:** `backend/app/main.py:201-205` (`get_connection`), used at
lines 209, 265, 304, 403.

```python
def get_connection() -> sqlite3.Connection:
    connection = sqlite3.connect(DB_PATH)
    connection.row_factory = sqlite3.Row
    return connection
```

Every call site uses `with get_connection() as connection:`. `sqlite3`'s
context manager only commits/rolls back the transaction on exit — it does
**not** call `connection.close()`. Every request to `/api/board`,
`/api/ai/board`, plus `init_db()` at startup, opens a brand-new SQLite
connection/file handle that is then only released whenever CPython's
refcounting GC happens to collect it. Under sustained traffic this leaks
file descriptors and DB handles, and increases the odds of `database is
locked` / `too many open files` errors, especially since finding 1 can
already cause several concurrent writers to the same file.

**Proposed action:** Either call `connection.close()` in a `finally` block
around each `with get_connection() as connection:` use, or centralize
access behind a single module-level connection / a small helper that closes
explicitly (e.g. `contextlib.closing(get_connection())`).

## 3. AI board-update field validation uses the wrong set comparison — FIXED

**File:** `backend/app/main.py:163-172` (`validate_ai_board_update`)

```python
for card_id, card in cards.items():
    ...
    if set(card) < {"id", "title", "details"}:
        raise ValueError("AI board cards require id, title, and details fields.")
```

The intent is "reject a card that is missing a required field." `set(card)
< {"id","title","details"}` is a *proper subset* test, which only catches
the case where `card`'s keys are entirely a subset of the three required
keys. If the AI response includes any extra/unexpected key (e.g. an
`"assignee"` field a model hallucinates), `set(card)` is no longer a subset
at all, so the condition is `False` and a card missing `"details"` (or
`"title"`) passes validation silently. The correct check is "required keys
are a subset of the card's keys": `if not {"id", "title",
"details"}.issubset(card):`.

In practice this is masked today because `replace_board_state()` later runs
the stricter `validate_board_state()`, which independently checks `id` and
`title`, and defaults a missing `details` to `""` — so nothing crashes. But
the AI-specific validation layer is silently broken and gives false
assurance that malformed AI payloads are being rejected at that stage.

**Proposed action:** Fix the check to
`if not {"id", "title", "details"}.issubset(card):`.

## 4. `data/pm.db` is committed to the git repository — FIXED

**File:** `data/pm.db` (tracked), `.gitignore` (no `data/` entry)

```
$ git ls-files data/
data/pm.db
```

The live SQLite database — including the seeded `users` row
(`username=user, password_hash=password`) — is checked into version
control. Every local run mutates this file, so it will show up as a dirty
tracked file after any manual testing, get committed by accident, and bloat
repo history with binary diffs. It also means "creating a new db if it
doesn't exist" (per `AGENTS.md`) is undermined — the repo ships with a
pre-existing one.

**Proposed action:** Add `data/` (or `data/*.db`) to `.gitignore` and
`git rm --cached data/pm.db`.

## 5. Every keystroke triggers a full board rewrite — FIXED

**File:** `frontend/src/components/KanbanBoard.tsx:71-103`,
`frontend/src/components/KanbanColumn.tsx:45-50`

The column-title `<input>` calls `onRename` on every `onChange`, which
updates `board` state, which re-triggers the save effect (no debounce).
Each save is a full `PUT /api/board` that server-side does a `DELETE` +
re-`INSERT` of every column and card row for that board
(`backend/app/main.py:399-432`). Renaming a column to a 15-character title
fires ~15 full board round-trips and 15 full table rewrites, and widens the
race window described in finding 1.

**Proposed action:** Debounce the save effect (e.g. 300-500ms of
inactivity) in addition to the sequencing fix in finding 1.

## 6. `password_hash` is a misleadingly-named, unused, plaintext column

**File:** `backend/app/main.py:213-219`, `258-260`;
`frontend/src/app/page.tsx:6-7`

```python
connection.execute(
    "INSERT OR IGNORE INTO users (username, password_hash) VALUES (?, ?)",
    ("user", "password"),
)
```

The column is named `password_hash` but stores the literal plaintext
string `"password"`. No backend endpoint ever reads or verifies this
column — there is no login route. The frontend's actual login gate
(`page.tsx`) checks a completely separate hardcoded pair,
`VALID_USERNAME`/`VALID_PASSWORD`, entirely client-side, disconnected from
this DB value. The column is dead weight today, and its name would mislead
a future contributor into thinking a real hash is being verified somewhere.

**Proposed action:** Either wire it up to actual verification (hash with
e.g. `passlib`/`hashlib` + a real login endpoint) or, while it stays
unused, rename the column to `password` and note in `docs/DATABASE.md`
that it is currently unused scaffolding for future multi-user auth.

## 7. `@app.on_event("startup")` is a deprecated FastAPI API

**File:** `backend/app/main.py:435-437`

```python
@app.on_event("startup")
async def startup_event() -> None:
    init_db()
```

`requirements.txt` pins `fastapi>=0.115.0`. Since FastAPI 0.93,
`on_event` is deprecated in favor of the `lifespan` context-manager
parameter to `FastAPI(...)`, and modern FastAPI emits a deprecation
warning for it. This violates the project's own stated convention:

> `CLAUDE.md` (Working conventions): "Use current/idiomatic library
> versions and patterns."
> `AGENTS.md` (Coding standards): "Use latest versions of libraries and
> idiomatic approaches as of today."

**Proposed action:** Replace with a `lifespan` async context manager:

```python
from contextlib import asynccontextmanager

@asynccontextmanager
async def lifespan(app: FastAPI):
    init_db()
    yield

app = FastAPI(title="PM MVP Backend", lifespan=lifespan)
```

---

## Summary table

| # | Severity | File | Issue | Status |
|---|----------|------|-------|--------|
| 1 | High | `frontend/src/components/KanbanBoard.tsx` | Unserialized autosave can persist a stale board (silent data loss) | Fixed |
| 2 | High | `backend/app/main.py` | SQLite connections never closed (resource leak) | Fixed |
| 3 | Medium | `backend/app/main.py` | Wrong subset check lets malformed AI cards through validation | Fixed |
| 4 | Medium | `data/pm.db` | Live database file committed to git | Fixed |
| 5 | Medium | `frontend/src/components/KanbanBoard.tsx` | No debounce — full board rewrite per keystroke | Fixed |
| 6 | Low | `backend/app/main.py:213-219,258-260` | `password_hash` is unused, plaintext, and misleadingly named | Open |
| 7 | Low | `backend/app/main.py:435-437` | Deprecated `on_event("startup")` instead of `lifespan` | Open |

## Fix notes (findings 1-5)

- **1 & 5 (autosave race + no debounce):** Replaced the per-change
  `saveSequenceRef` counter with a single-flight save queue: every board
  change updates `pendingBoardRef` immediately, but the actual `PUT` is
  debounced 400ms and only one save can be in flight at a time (`isSavingRef`).
  If a change arrives while a save is running, it's picked up automatically
  once that save finishes, so the request sent is always the latest board and
  requests can never complete out of order. A save is also flushed
  immediately on unmount (e.g. logout) so in-progress edits aren't lost to
  the debounce timer being cleared — this is covered by the existing
  "keeps the board state after logout and login" test.
- **2 (unclosed connections):** `get_connection()` is now a
  `@contextmanager` that commits (or rolls back on exception) and always
  calls `connection.close()` in a `finally` block. Call sites are unchanged.
- **3 (wrong subset check):** `set(card) < {...}` → `not {...}.issubset(card)`.
- **4 (db committed to git):** Added `data/*.db` to `.gitignore` and ran
  `git rm --cached data/pm.db` (file kept locally, untracked going forward).

Verified with: `python3 -m pytest backend/tests -q` (10 passed),
`npm run test:unit` (16 passed), `npm run lint` (clean), `npm run build`
(succeeds, no TypeScript errors).
