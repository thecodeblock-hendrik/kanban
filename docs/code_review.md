# Code Review

Reviewed: 2026-09-11

## Architecture Overview

The project follows a clean monorepo design: Python FastAPI backend serving a statically-exported Next.js frontend from a single Docker container. The separation of concerns is well-structured — `main.py` handles routing, `db.py` handles persistence, `ai.py` handles OpenRouter integration, and the frontend owns all UI logic.

The single-container approach is practical for an MVP. Static export of the frontend eliminates the need for a separate Node.js runtime in production.

## Backend

### `main.py` (122 lines)

**Good**: Clean route definitions, proper HTTP status codes, typed return values. The `lifespan` context manager for startup is idiomatic FastAPI.

**Issues**:

- **No input sanitization on AI prompt** (line 49-51): The user prompt is extracted from the request body and passed directly to the AI system prompt. There is no sanitization or length limit, allowing prompt injection attacks. A user could craft a prompt that overrides the system instructions.
- **`body: dict[str, Any]`** (lines 45, 92): FastAPI will accept any JSON object here. Using a Pydantic model would provide automatic validation, serialization, and OpenAPI schema documentation. The manual type checks at lines 46-55 replicate what Pydantic does for free.
- **No rate limiting**: All endpoints are unprotected. A simple abuse case: spam `POST /api/ai/board` to exhaust the OpenRouter API quota.
- **Stale `board_id` variable** (line 80): After calling `replace_board_state`, the code falls back to `serialize_board(board_id)` using the original `board_id` from line 57. This works because `replace_board_state` returns the serialized board directly, but the variable name shadowing is confusing.

### `db.py` (273 lines)

**Good**: The `get_connection()` context manager is clean — commit on success, rollback on exception, always close. The `validate_board_state` function is thorough, checking duplicates, orphans, and missing references. Transaction safety in `replace_board_state` (delete-then-insert) prevents partial writes.

**Issues**:

- **Plaintext password** (line 100): `password_hash` column stores `"password"` as a literal string. The column name is misleading — it is not a hash. For the MVP this is acceptable, but the column should be renamed to `password` or the value should actually be hashed.
- **`get_or_create_user_board` creates boards for unknown users** (lines 105-141): If `user is None` it raises 404, but if the user exists with no board it silently creates one with default data. This means any username that exists in the `users` table (including the seeded `"user"`) will get a fresh board on first access. This is the intended MVP behavior but is worth noting — there is no concept of "board not yet created."
- **N+1-like pattern in `serialize_board`** (lines 166-170): For each column, it filters the full `cards` list to find card IDs belonging to that column. With 5 columns and 8 cards this is fine, but with large boards a dictionary keyed by `column_id` would be more efficient.
- **`serialize_board` card ordering** (lines 151-153): Cards are ordered by `position` globally, but `column_card_ids` (lines 166-170) filters by `column_id` without re-sorting by position. The order happens to be correct because cards are inserted in position order per column, but this is fragile — a future bug could break card ordering silently.
- **No indexes**: The `board_cards` table has no index on `board_id` or `column_id`. For the MVP dataset size this is irrelevant, but would be a problem at scale.

### `ai.py` (172 lines)

**Good**: The prompt construction is clear and structured. The response parser handles both text content and list-format content from OpenRouter. The `validate_ai_board_update` function is thorough about rejecting partial updates (columns without cards or vice versa).

**Issues**:

- **`validate_ai_board_update` returns `{}` for `None` input** (line 116): When `board_update is None`, the function returns `{}` (empty dict). Back in `main.py:74`, the check `if parsed.get("board_update") is not None` evaluates to `True` (because `{}` is not `None`), causing `replace_board_state` to be called with an empty dict. This dict passes `validate_board_state` in `db.py` but represents an empty board — columns and cards would both be empty lists/dicts, wiping the board. This is a **bug**: a `None` board_update should not trigger a replacement. The fix: return `None` instead of `{}` on line 116, or change the check in `main.py` to `if parsed.get("board_update")`.
- **Hand-rolled `.env` loader** (lines 18-28): `load_env()` parses `.env` files manually. It does not handle quoted values containing `=`, multi-line values, or `export` prefixes. This works for the single-key case but is fragile. The `setdefault` call also means environment variables set before the call take precedence, which is correct but undocumented.
- **No conversation truncation** (line 98-111): `build_board_prompt` includes the full conversation history in every request. As conversations grow, this will eventually exceed the model's context window. A truncation strategy (last N messages or token limit) is needed.
- **AI prompt includes full board JSON** (line 107): Every AI call sends the entire board state serialized as JSON in the prompt. For large boards this wastes tokens. A more efficient approach would be to describe only the relevant columns/cards.
- **Single API key** (line 33): The OpenRouter API key is loaded from `.env` at request time via `load_env()`. This means every API call re-reads the `.env` file from disk. The key should be loaded once at startup and cached.
- **`normalize_ai_prompt` only handles `+`** (lines 39-43): The regex normalization for arithmetic only handles `+` operators. This is only used by the `/api/ai/test` smoke test endpoint and is not a concern for production use.

## Frontend

### `page.tsx` (106 lines)

**Good**: Clean auth gate pattern. The form uses proper `<label>` associations and `autoComplete` attributes for accessibility.

**Issues**:

- **Client-side-only authentication** (line 18): Credentials are checked in JavaScript against hardcoded constants. The password is visible in the source code (viewable via browser DevTools). Any user can bypass auth by calling the API directly with `?user=user` — the backend has no auth middleware. This is acceptable for the MVP per requirements, but the README should document this limitation.
- **No session management**: Authentication state is held in React state only. A page refresh logs the user out. The test at `KanbanBoard.test.tsx:211` (login, add card, logout, login, verify card) passes because the mock server persists data, but in the real app the user would need to re-authenticate after refresh. This is acceptable for MVP.

### `KanbanBoard.tsx` (401 lines)

**Good**: The debounced single-flight save pattern (lines 74-146) is well-designed. Using refs for `pendingBoardRef` and `isSavingRef` avoids stale closure issues. The flush-on-unmount cleanup prevents lost saves. The AI chat integration is clean — send prompt + history, apply returned board directly.

**Issues**:

- **Component is too large** (401 lines): This component handles board loading, board saving, drag-and-drop, column renaming, card creation, card deletion, and AI chat. It should be split into smaller components or a custom hook (e.g., `useBoardPersistence`, `useAiChat`).
- **No confirmation for card deletion** (line 208-225): `handleDeleteCard` removes the card immediately with no undo or confirmation dialog. A misclick permanently loses the card.
- **AI chat error message is generic** (line 266-268): The catch block shows "I couldn't process that request. Please try again." for all errors, including network failures and 400/503 responses. The actual error message from the server is discarded.
- **No Enter-to-send** for AI chat: The textarea (line 379) does not handle Enter key submission. Users must click the Send button.
- **`cardsById` memo is unnecessary** (line 154): `useMemo(() => board.cards, [board.cards])` creates a new reference every time `board` changes, providing no memoization benefit. It could be removed since `board.cards` is already used directly.
- **Chat history grows unbounded**: `chatMessages` state accumulates every message. Combined with the backend's lack of conversation truncation, this will eventually cause performance issues.
- **Race condition between AI board update and manual save**: If the user makes a manual edit and then receives an AI board update, the AI response replaces the board entirely via `setBoard(data.board)` (line 262). Any manual changes made between the AI request and response are lost. The single-flight save pattern does not protect against this because the AI update bypasses the save queue.

### `kanban.ts` (171 lines)

**Good**: The `moveCard` function handles all edge cases: same-column reorder, cross-column move, drop onto empty column, and drop onto column placeholder. The `-empty` suffix convention for column drop zones is a clean abstraction.

**Issues**:

- **`createId` collision risk** (lines 167-171): Uses `Math.random()` combined with `Date.now()`. While collisions are unlikely in practice, `crypto.randomUUID()` (available in modern browsers and Node.js) would be deterministic and collision-free.
- **Duplicated initial data**: `initialData` here must stay in sync with `DEFAULT_COLUMNS` and `DEFAULT_CARDS` in `db.py`. Any change to one must be manually mirrored in the other.

### `KanbanColumn.tsx` (74 lines)

**Good**: Clean component with proper `useDroppable` integration. The empty column state is a nice UX touch.

**Minor**: The column title `<input>` (line 45) has no blur handler or keyboard shortcut to confirm the edit. Every keystroke triggers a board update via `onRename`. This works because of the debounced save, but a confirm-on-blur pattern would be more conventional.

### `KanbanCard.tsx` (53 lines)

**Good**: Clean sortable card with proper accessibility attributes. The delete button has a descriptive `aria-label`.

**Issue**: No confirmation before deletion. See `KanbanBoard.tsx` note above.

### `NewCardForm.tsx` (75 lines)

**Good**: Simple, focused component. Proper form validation (requires non-empty title). Reset on cancel and submit.

**Minor**: The form could benefit from auto-focusing the title input when opened.

### Styling

**Good**: Consistent use of CSS custom properties for theming. The color scheme from `AGENTS.md` is faithfully implemented. Tailwind CSS v4 is used idiomatically. The glassmorphism header (`backdrop-blur`, `bg-white/80`) is visually polished.

**Issue**: The `globals.css` imports Tailwind via `@import "tailwindcss"` which is the Tailwind v4 syntax. This is correct for the installed version.

## Security

| Issue | Severity | Location | Notes |
|-------|----------|----------|-------|
| Plaintext password in DB | High | `db.py:100` | Column named `password_hash` but stores plaintext |
| Client-side auth only | Medium | `page.tsx:18` | Backend has no auth middleware |
| No API rate limiting | Medium | All routes | AI endpoints can be abused to exhaust API quota |
| Prompt injection | Medium | `ai.py:98-111` | User input embedded directly in system prompt |
| No CSRF protection | Low | All POST/PUT | Acceptable for API-only backend |

## Testing

### Backend Tests

**Good**: 9 tests covering board CRUD, validation, AI endpoints, and error handling. Test isolation via `monkeypatch` redirecting DB to `tmp_path` is clean. AI calls are properly stubbed.

**Gaps**:
- No tests for `validate_ai_board_update` in isolation
- No test for the `None` board_update bug (line 116 of `ai.py`)
- No test for concurrent board updates
- No test for large board payloads

### Frontend Tests

**Good**: 12 unit tests covering board load/save, rapid update deduplication, column operations, card CRUD, AI chat flow, and full auth flow. The mock server pattern (lines 15-24 of `KanbanBoard.test.tsx`) is well-designed.

**Gaps**:
- No tests for `KanbanCard`, `KanbanColumn`, or `NewCardForm` in isolation
- No tests for drag-and-drop behavior (only the result is tested)
- No edge case tests for `moveCard` (e.g., dropping a card onto itself)

### E2E Tests

**Good**: 5 Playwright tests covering the critical path: sign-in, board load, card add, drag-and-drop, and column rename persistence.

**Gap**: No tests for AI chat flow in E2E.

## Docker

**Good**: Two-stage build keeps the final image small (Node for build only, Python for runtime). `uv` for fast dependency installation. `PYTHONDONTWRITEBYTECODE=1` and `PYTHONUNBUFFERED=1` are set correctly.

**Issues**:
- **No health check**: The Dockerfile has no `HEALTHCHECK` instruction. Adding `HEALTHCHECK CMD curl -f http://localhost:8000/api/health` would improve container orchestration.
- **No `.dockerignore`**: The build context includes `node_modules/`, `data/`, `.git/`, and other unnecessary files. A `.dockerignore` would speed up builds.
- **`npm install` instead of `npm ci`** (line 6): `npm install` can modify `package-lock.json` in the Docker build. `npm ci` is the correct choice for reproducible builds.

## Positive Observations

1. **Save deduplication pattern**: The single-flight, debounced save with pending queue is a well-engineered solution to a common real-time sync problem. It prevents race conditions without complex state management.

2. **Validation depth**: Both frontend and backend validate board state thoroughly. The backend checks for duplicate IDs, orphaned cards, missing references, and type correctness.

3. **Test isolation**: Backend tests use `tmp_path` + `monkeypatch` for database isolation. Frontend tests mock `fetch` globally with a controllable `serverBoard` variable. Both patterns are clean and reliable.

4. **Code organization**: The backend is split into three focused modules (`main`, `db`, `ai`) with clear responsibilities. The frontend follows a standard Next.js layout with components, lib, and tests.

5. **Consistent coding style**: Both Python and TypeScript code follow consistent formatting, naming conventions, and import ordering throughout the project.

## Recommendations

### Priority 1 — Must Fix

1. **Fix the `None` board_update bug** in `ai.py:116`. Change `return {}` to `return None`, or change the check in `main.py:74` to `if parsed.get("board_update")`. Without this fix, an AI response without a `board_update` field could wipe the board.

2. **Add `.dockerignore`** excluding `node_modules/`, `data/`, `.git/`, `frontend/out/`, `*.db`.

### Priority 2 — Should Fix

3. **Split `KanbanBoard.tsx`** into smaller components or custom hooks. The 401-line component handles too many concerns.

4. **Add card deletion confirmation** — a simple `confirm()` dialog or inline undo toast.

5. **Add conversation history truncation** in `build_board_prompt` to prevent exceeding the model's context window.

6. **Use Pydantic models** for API request/response types in `main.py` instead of manual dict checks.

7. **Replace `npm install` with `npm ci`** in the Dockerfile for reproducible builds.

### Priority 3 — Nice to Have

8. **Add a `HEALTHCHECK`** instruction to the Dockerfile.

9. **Add indexes** on `board_cards(board_id)` and `board_cards(column_id)` for future scalability.

10. **Replace `Math.random()` in `createId`** with `crypto.randomUUID()` for guaranteed uniqueness.

11. **Cache the OpenRouter API key** at startup instead of re-reading `.env` on every request.

12. **Add a `.dockerignore`** file.

13. **Deduplicate initial data** between `kanban.ts` and `db.py` (e.g., share a JSON file).

14. **Add Enter-to-send** for the AI chat textarea.
