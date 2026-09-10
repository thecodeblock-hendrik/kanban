# Code Review and Refactoring Plan

## Scope
This review focuses on stability and performance improvements for the current MVP codebase. The goal is to reduce risk, improve data consistency, and make the app easier to maintain as the project grows.

This document is intentionally ordered as a step-by-step plan so the refactoring work can be done in a controlled sequence without changing the product behavior in an unsafe way.

---

## Step 1: Stabilize persistence and database writes

### Recommendation
Refactor the board persistence flow in the backend so it is transactional, safer under failures, and less destructive.

### Files involved
- backend/app/main.py

### Why this is first
This is the most critical area for stability because it controls the source of truth for the board. If the persistence flow is fragile, downstream UI issues and data-loss risk will be much harder to manage.

### Planned changes
- Review and refactor `replace_board_state()`.
- Move database updates into a single transaction.
- Validate incoming board payloads before deleting existing state.
- Check for missing or invalid card references before commit.
- Ensure duplicate IDs and bad column/card relationships are rejected early.
- Keep DB initialization separate from regular read/write logic so the request path is idempotent and less side-effect-heavy.

### Expected outcome
- Safer writes
- Better protection against partial data corruption
- More predictable behavior under error conditions

### Test gate before moving to next step
- Run backend persistence tests covering board creation, update, and data integrity.
- Verify the default board is still returned correctly for the user.
- Verify a malformed or invalid board payload is rejected before DB mutation.
- Confirm the existing backend test suite still passes for the touched API paths.

---

## Step 2: Reduce autosave churn and stale overwrites in the frontend

### Recommendation
Refactor the board save logic so updates are serialized and debounced instead of saved on every state change.

### Files involved
- frontend/src/components/KanbanBoard.tsx

### Why this is second
The frontend is currently saving after every board mutation. This creates both performance overhead and a race condition risk when multiple updates happen quickly.

### Planned changes
- Review the effect that triggers board persistence on every render-driven board change.
- Add debouncing or a controlled save queue to reduce redundant writes.
- Avoid sending a new request for every keystroke in column rename or every card drag event.
- Consider a request versioning strategy so the newest state wins if requests overlap.
- Only persist after the user action is considered settled, where appropriate.

### Expected outcome
- Lower network traffic
- More stable UI behavior during fast actions
- Better protection against stale state overrides

### Test gate before moving to next step
- Run frontend tests covering board state update behavior after rapid consecutive changes.
- Verify the save flow does not produce stale overwrites during fast interactions.
- Confirm there are no regressions in board rendering after debounced or queued updates.
- Validate that no critical UI tests fail after the autosave changes.

---

## Step 3: Simplify and harden the board update logic

### Recommendation
Refactor the board move logic into clearer, explicit state transitions with stronger edge-case handling.

### Files involved
- frontend/src/lib/kanban.ts

### Why this is third
The move logic is currently compact but becomes harder to reason about as the board grows. It is important to make this logic explicit before features become more complex.

### Planned changes
- Review `moveCard()` and isolate the different move scenarios:
  - same-column reorder
  - cross-column move
  - drop onto empty column
  - drop to end of column
- Add failing regression tests for edge cases.
- Validate missing IDs and invalid moves before updating the state.
- Prefer a small reducer or clearly segmented logic rather than one large mutation function.

### Expected outcome
- More predictable drag-and-drop behavior
- Easier debugging for reorder issues
- Reduced chance of hidden ordering bugs

### Test gate before moving to next step
- Run the board-state unit tests covering same-column reorder and cross-column move behavior.
- Add new regression tests for empty-column drop behavior and invalid move handling.
- Confirm drag-and-drop operations still keep card ordering and column membership consistent.
- Ensure the updated logic passes the dedicated kanban test suite.

---

## Step 4: Improve render efficiency and reduce unnecessary re-renders

### Recommendation
Refactor the board components so they avoid unnecessary work on each state change, especially in larger boards.

### Files involved
- frontend/src/components/KanbanBoard.tsx
- frontend/src/components/KanbanColumn.tsx
- frontend/src/components/KanbanCard.tsx

### Why this is fourth
The current app is small, but the render path is likely to become noisy as card count and UI complexity increase. This is a good time to reduce churn before it becomes a performance issue.

### Planned changes
- Memoize expensive derived values such as lookup maps and filtered card arrays.
- Review callback identity to avoid unnecessary child re-renders.
- Consider whether board-level state updates can be narrowed to only the necessary column/card section.
- Keep drag-related handlers stable when possible.
- Reevaluate whether all board columns need to re-render after a small state change.

### Expected outcome
- Better responsiveness
- Reduced CPU usage during drag and edit interactions
- Cleaner component behavior as the board scales

### Test gate before moving to next step
- Run frontend test suite for rendering and board interactions.
- Check for no performance regressions during simple drag and rename interactions.
- Validate that new memoization or callback changes do not break expected UI behavior.
- Confirm the board continues to render correctly across multiple re-renders.

---

## Step 5: Refine the AI integration boundaries and error handling

### Recommendation
Create a more explicit AI client boundary and make error handling more structured and stable.

### Files involved
- backend/app/main.py

### Why this is fifth
The AI layer is the most external dependency in the app. It needs predictable error categories and a clear contract with the rest of the application.

### Planned changes
- Centralize OpenRouter access behind a dedicated client helper.
- Standardize provider error handling for:
  - auth failure
  - timeout/network failure
  - rate limiting
  - malformed response
- Add retry/backoff for transient failures.
- Make the AI response validation stricter and clearer.
- Separate “AI responded but did not create a valid board update” from “AI service is unavailable.”

### Expected outcome
- More stable AI workflows
- Better user-facing error messaging
- Easier debugging when the provider is down or the model output changes

### Test gate before moving to next step
- Run backend tests covering AI endpoint success and failure flows.
- Verify malformed AI output returns a clean 400 response.
- Verify provider outages return a clear 503 or actionable error message.
- Ensure previously valid AI update flows continue to pass after the refactor.

---

## Step 6: Add stricter validation for board payloads and AI-generated board updates

### Recommendation
Refactor validation logic so malformed board state is rejected before it reaches the database or the frontend.

### Files involved
- backend/app/main.py

### Why this is sixth
This is a high-value safety improvement. Validation is currently present, but it should be more explicit and complete because invalid state is one of the highest-risk causes of UI or persistence breakage.

### Planned changes
- Validate column structure, card structure, and card IDs before any database writes.
- Reject payloads with duplicate IDs or orphaned card references.
- Ensure AI-generated updates cannot accidentally omit required fields or create invalid board shapes.
- Add consistency checks across cards and column order.

### Expected outcome
- Fewer invalid board states
- Better reliability of backend processing
- Easier to debug AI-generated payload anomalies

### Test gate before moving to next step
- Run backend API tests for invalid board payload rejection.
- Verify the AI update endpoint rejects incomplete or malformed board updates.
- Verify valid board payloads still persist correctly after validation changes.
- Confirm no database consistency regressions are introduced.

---

## Step 7: Improve user input behavior for column editing and card creation

### Recommendation
Refactor form and input flows so they are less likely to generate noisy updates or accidental edits.

### Files involved
- frontend/src/components/KanbanColumn.tsx
- frontend/src/components/NewCardForm.tsx

### Why this is seventh
The form interactions are functional, but they trigger immediate state updates and do not include any buffering or validation beyond basic empty checks.

### Planned changes
- Review whether column title editing should commit after blur or debounce instead of on every keystroke.
- Keep form state local until a save action is confirmed.
- Add lightweight validation for empty or whitespace-only titles.
- Validate the card add flow before state mutation.

### Expected outcome
- Better editing experience
- Reduced unnecessary state churn
- Lower chance of accidental invalid entries

### Test gate before moving to next step
- Run the frontend test suite for card creation and column editing flows.
- Verify empty titles, whitespace-only input, and canceled actions behave correctly.
- Confirm the UI remains stable when users quickly add cards or rename columns.
- Add regression checks for input edge cases before proceeding.

---

## Step 8: Strengthen automated regression coverage around failures and edge cases

### Recommendation
Expand tests to cover the failure boundaries that are most likely to break at runtime.

### Files involved
- backend/tests/test_board_api.py
- frontend/src/lib/kanban.test.ts

### Why this is eighth
The current tests cover happy paths well, but the highest-risk cases are often malformed payloads, out-of-order writes, and edge-case drag moves.

### Planned changes
- Add tests for malformed AI payloads.
- Add tests for invalid board payloads sent to the API.
- Add tests for empty-column moves and reorder edge cases.
- Add tests for missing card references and partial board updates.
- Add tests for provider failure and timeout handling.

### Expected outcome
- Better protection against regressions
- Safer refactoring work later
- More confidence when making changes to critical logic

### Test gate before moving to next step
- Run all relevant backend and frontend tests.
- Add and run edge-case regression tests for malformed payloads, invalid moves, and provider failures.
- Ensure the test suite clearly covers the failure conditions identified during earlier steps.
- Require a green run before continuing to architecture cleanup.

---

## Step 9: Separate responsibilities more cleanly between API, data access, and UI state

### Recommendation
Refactor the backend and frontend to make ownership of data validation and mutation rules clearer.

### Files involved
- backend/app/main.py
- frontend/src/components/KanbanBoard.tsx
- frontend/src/lib/kanban.ts

### Why this is ninth
The MVP has a straightforward architecture, but the responsibilities are currently mixed together. That makes the code harder to extend safely.

### Planned changes
- Keep board mutation rules in one clear place.
- Keep persistence logic separate from request validation.
- Keep local UI state transitions focused on view updates, not server-side persistence concerns.
- Make the API contract explicit and consistent.

### Expected outcome
- Easier maintenance
- Reduced accidental coupling between layers
- Cleaner future feature work

### Test gate before moving to next step
- Run the full relevant backend and frontend test suite.
- Verify no regressions were introduced by moving responsibilities or cleaning up shared logic.
- Confirm the API contract still matches the UI expectations.
- Only proceed after the refactor passes the full relevant test pass.

---

## Step 10: Final cleanup and performance check

### Recommendation
After core refactors are complete, run targeted regression checks and performance pass.

### Files involved
- backend/app/main.py
- frontend/src/components/*
- frontend/src/lib/kanban.ts

### Why this is last
This step ensures the refactoring work did not introduce new regressions or hidden performance issues.

### Planned changes
- Run backend tests for API and persistence behavior.
- Run frontend tests for board logic and reorder behavior.
- Test repeated drag operations and rapid rename inputs.
- Check whether autosave, DnD, and board loads remain responsive.
- Review for redundant effect calls, repeated data transforms, and avoidable renders.

### Expected outcome
- Refactoring is validated
- Performance remains acceptable
- Stability risk is reduced before additional feature work

### Final test gate before considering the refactor complete
- Run the full backend and frontend test suites relevant to the board workflow.
- Confirm all new regression tests pass.
- Confirm the app still works for the primary flow: load board, edit cards, drag cards, rename columns, and use AI board updates.
- Only mark the refactor complete after this final green test run.

---

## Suggested implementation sequence

1. Backend transaction safety and validation
2. Frontend autosave and request deduplication
3. Drag-and-drop logic hardening
4. Render optimization
5. AI client robustness
6. Input behavior cleanup
7. Regression tests
8. Architecture cleanup
9. Final verification

---

## Notes
- This plan intentionally keeps changes incremental and testable.
- The most critical path is persistence correctness before UI optimization.
- The current codebase is a strong MVP, but the refactor should focus on eliminating the highest-risk reliability issues first rather than making broad redesign changes.
