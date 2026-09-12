# Project plan and execution checklist

## Project goals

Build a local MVP project management app with:
- hardcoded sign-in flow for "user" / "password"
- one Kanban board per user
- drag-and-drop editing of cards and columns
- Dockerized local deployment
- Python FastAPI backend with SQLite persistence
- frontend served statically from the backend
- AI chat sidebar connected through OpenRouter with structured board update support

This document is the execution plan and must be treated as the source of truth for implementation order. No code work should proceed beyond the approved plan unless the user explicitly approves the next phase.

---

## Part 1: Planning and documentation

### Objective
Prepare the project structure and execution plan with clear checkpoints, quality gates, and technical documentation so the implementation can proceed safely and predictably.

### Checklist
- [ ] Review the project requirements and constraints in [AGENTS.md](../AGENTS.md)
- [ ] Review the existing frontend demo in [frontend](../frontend)
- [ ] Review the existing backend and script scaffolding conventions in [backend/AGENTS.md](../backend/AGENTS.md) and [scripts/AGENTS.md](../scripts/AGENTS.md)
- [ ] Enrich this document with detailed per-part checklists, validation steps, and success criteria
- [ ] Create [frontend/AGENTS.md](../frontend/AGENTS.md) describing the current frontend architecture, dependencies, and testing setup
- [ ] Confirm the plan with the user before starting any implementation work

### Validation
- The plan clearly explains all major phases and sequencing
- The frontend AGENTS file maps the existing code and testing setup in a way that helps future agents work safely
- The user has explicitly approved the plan before moving to Part 2

### Success criteria
- [ ] [docs/PLAN.md](PLAN.md) contains a full implementation roadmap
- [ ] [frontend/AGENTS.md](../frontend/AGENTS.md) exists and accurately reflects the current frontend codebase
- [ ] User approval is captured before implementation begins

---

## Part 2: Scaffolding the local app stack

### Objective
Create the Docker, backend, and script foundation so the app can run locally and expose a basic health endpoint before the Kanban logic is added.

### Checklist
- [ ] Create Docker configuration for the app container
- [ ] Set up the Python project for FastAPI in [backend](../backend)
- [ ] Configure the project to use uv as the package manager in the container
- [ ] Create start/stop scripts in [scripts](../scripts) for Mac, Windows, and Linux
- [ ] Add a minimal hello-world route at the API layer
- [ ] Serve a basic static page at / to confirm the app runs locally
- [ ] Verify local startup with container or local Python runtime
- [ ] Confirm both a static HTML response and a basic API response work

### Tests
- API smoke test: GET / returns HTML successfully
- API smoke test: GET /api/health or equivalent returns a success payload
- Docker startup check: app starts without error

### Success criteria
- [ ] Local app boots without crashing
- [ ] Root path responds with HTML
- [ ] Basic API endpoint responds with a valid JSON payload
- [ ] Scripts can be used to start and stop the app consistently

---

## Part 3: Frontend integration and static serving

### Objective
Ensure the existing Kanban demo is built into a production-ready frontend and served from the backend at /.

### Checklist
- [ ] Confirm the existing Next.js frontend from [frontend](../frontend) builds correctly
- [ ] Configure static build output to be consumed by the backend
- [ ] Update backend serving logic so / serves the frontend app
- [ ] Preserve the board UI and ability to rename columns, drag cards, and add/delete cards
- [ ] Keep the app running locally with the correct static asset path behavior
- [ ] Run unit and integration tests for frontend behavior

### Tests
- Next.js build succeeds
- Frontend unit tests pass for Kanban behavior
- Playwright or integration tests confirm the board renders at /

### Success criteria
- [ ] The demo Kanban board is visible at the root URL
- [ ] Frontend can be served from the backend without requiring separate dev servers
- [ ] Core board behaviors remain intact after build integration

---

## Part 4: Fake sign-in experience

### Objective
Add the initial login flow and logout behavior required by the MVP, using dummy credentials only.

### Checklist
- [ ] Add login screen that appears before the board is visible
- [ ] Implement hardcoded auth using username "user" and password "password"
- [ ] Protect the Kanban route so unauthenticated users cannot access it
- [ ] Allow logout from the authenticated state
- [ ] Preserve the board after successful login
- [ ] Add tests covering login success, incorrect credentials, and logout

### Tests
- Valid credentials allow access to Kanban
- Invalid credentials block access and show an error state
- Logged-out user is redirected back to login
- Auth state is preserved correctly during session flow

### Success criteria
- [ ] User must log in before seeing the Kanban board
- [ ] Dummy credentials behave as required for the MVP
- [ ] The app supports a clean logout flow

---

## Part 5: Database modeling and schema sign-off

### Objective
Design the persistence model needed for a multi-user Kanban board and capture it in docs before backend implementation begins.

### Checklist
- [ ] Define the data model for users, kanban boards, columns, and cards
- [ ] Decide how board state is represented in SQLite tables or JSON storage
- [ ] Capture the schema in a JSON file under [docs](../docs)
- [ ] Document assumptions for future multi-user support while staying within the MVP constraints
- [ ] Present the schema to the user for sign-off before backend persistence work starts

### Tests
- Schema design is internally consistent
- Board model supports card movement, column renaming, and user scoping
- Documented schema matches planned API behavior

### Success criteria
- [ ] A clear database schema is in place before implementation
- [ ] User approves the planned persistence model
- [ ] Implementation can proceed without schema ambiguity

---

## Part 6: Backend persistence and API routes

### Objective
Add the backend routes and persistence logic to read and manipulate the board for a given user, creating the SQLite database automatically when missing.

### Checklist
- [ ] Implement SQLite database initialization and migrations or schema bootstrap
- [ ] Create user-aware board storage logic
- [ ] Add API routes to load the current board for the signed-in user
- [ ] Add API routes to update column titles and card movement
- [ ] Add API routes to create, edit, and delete cards
- [ ] Ensure board changes are persisted immediately and reliably
- [ ] Add backend unit tests covering the major CRUD and board mutation flows

### Tests
- Database creates automatically when not present
- Fetching board state returns current data for the active user
- Renaming a column persists correctly
- Moving a card persists to the correct column and index
- Adding and deleting cards works as expected
- Board operations do not leak data between users

### Success criteria
- [ ] Database file is created automatically if missing
- [ ] API routes support all required Kanban mutations
- [ ] Backend unit tests cover the critical persistence behavior

---

## Part 7: Frontend and backend integration

### Objective
Replace the demo-only state with real API-backed persistence so the board reflects the backend and stays synced across refreshes.

### Checklist
- [ ] Connect the frontend to the backend API for board fetch and mutation requests
- [ ] Replace local state logic with API-backed load/save behavior
- [ ] Keep the login flow and authenticated user context aligned with backend user data
- [ ] Ensure the board refreshes after moves, edits, creations, and deletions
- [ ] Add end-to-end tests covering the persisted board flow

### Tests
- Frontend loads the initial board from API
- Drag-and-drop updates persist
- Column rename persists
- Add/edit/delete card flows persist
- Board state remains consistent after refresh

### Success criteria
- [ ] The produced board is no longer local-only state
- [ ] The app behaves as a real persistent Kanban board
- [ ] Data integrity remains stable under normal user actions

---

## Part 8: AI connectivity via OpenRouter

### Objective
Add a simple, reliable backend integration to OpenRouter and validate it with a known test input before wiring it into the Kanban workflow.

### Checklist
- [ ] Configure the backend to read OpenRouter credentials from the project env file
- [ ] Add a minimal call to the configured model using a simple prompt such as "2 + 2"
- [ ] Confirm JSON or text responses are handled correctly
- [ ] Log and surface response errors clearly when the provider is unavailable
- [ ] Confirm the AI provider connection works in the local environment

### Tests
- Simple prompt returns a valid response from the model
- Network/config problems fail gracefully with an actionable error
- Response parsing works for expected JSON or text payloads

### Success criteria
- [ ] OpenRouter connectivity is verified using a simple prompt
- [ ] The backend can make AI requests without manual workarounds
- [ ] AI errors are visible and diagnosable

---

## Part 9: Structured AI board interaction

### Objective
Provide the AI with board state plus user context and require structured output that can include both a conversational response and optional board updates.

### Checklist
- [ ] Send the current board JSON plus the user prompt to the model
- [ ] Include conversation history in the AI request payload
- [ ] Define a structured response format with fields such as response text and optional board updates
- [ ] Parse and validate the LLM output before applying changes
- [ ] Apply only valid board modifications derived from the LLM response
- [ ] Add tests for both normal and invalid structured outputs

### Tests
- AI response with no board changes still returns a sensible answer
- AI response with a valid board update modifies the board correctly
- Invalid or malformed structured output is rejected safely
- Previous conversation context is included in the prompt payload

### Success criteria
- [ ] The LLM receives the project board state in a consistent format
- [ ] Structured outputs are parsed securely and deterministically
- [ ] Optional AI-driven board changes can be applied without breaking state

---

## Part 10: AI chat sidebar and automatic refresh

### Objective
Deliver the final user-facing chat experience: a sidebar UI that can ask the AI about the board, apply structured updates, and refresh automatically when the board changes.

### Checklist
- [ ] Build a sidebar chat widget in the frontend
- [ ] Send the user message to the backend AI endpoint
- [ ] Display the AI reply in the chat interface
- [ ] Allow the backend to update the board when the structured response includes changes
- [ ] Refresh the frontend view automatically after AI-driven board updates
- [ ] Ensure the UI remains responsive while preserving existing board functionality
- [ ] Add end-to-end tests for a full AI conversation and board update path

### Tests
- Chat message is submitted and response is displayed
- AI update to the board triggers a refresh in the UI
- User sees updated columns/cards after the AI modifies the board
- No broken state when the AI chooses not to update the board

### Success criteria
- [ ] Sidebar AI chat is working in the application
- [ ] Structured AI edits update the board automatically when applicable
- [ ] Final app matches the business requirement of an AI-assisted Kanban board

---

## Final verification checklist

Before closing the project, verify the following:
- [ ] Frontend, backend, and Docker all work together locally
- [ ] Login is enforced with the correct dummy credentials
- [ ] Kanban persistence behaves correctly for the active user
- [ ] AI connectivity works through OpenRouter
- [ ] Structured AI output can update or answer about the board
- [ ] The user can interact with the app through the final UI without developer-only workarounds

This sequence maintains the required design approval gates, keeps the MVP simple, and minimizes risk by validating each major implementation layer before adding the next one.

---

## Post-MVP expansion (approved by user on 2026-09-12)

The MVP above is single-user and single-board. The user has explicitly approved expanding scope beyond the MVP to a multi-user, multi-board project management application. This section gates that expanded work the same way Parts 1-10 gated the MVP.

## Part 11: Real user accounts

### Objective
Replace the single hardcoded `user`/`password` login with real, database-backed user accounts so multiple people can each have their own login.

### Checklist
- [x] Add password hashing (salted, e.g. PBKDF2) to the `users` table instead of storing plaintext
- [x] Add `POST /api/auth/register` to create a new account (unique username, minimum password rules)
- [x] Add `POST /api/auth/login` to verify credentials against stored hashes
- [x] Migrate any existing local database so the seeded `user`/`password` account still logs in after the hashing change
- [x] Update the frontend sign-in screen to call the real auth endpoints instead of checking a hardcoded constant
- [x] Add a registration screen/flow reachable from sign-in
- [x] Add backend tests for register/login success and failure paths (duplicate username, wrong password, missing fields)

### Tests
- Registering a new user persists a hashed (never plaintext) password
- Logging in with correct credentials succeeds; incorrect credentials fail with a clear error
- Duplicate username registration is rejected
- Existing seeded `user`/`password` account keeps working after migration

### Success criteria
- [x] Any number of real accounts can register and log in
- [x] No plaintext passwords are stored
- [x] Existing MVP login flow keeps working for the default account

---

## Part 12: Multiple boards per user

### Objective
Let each user own multiple named Kanban boards instead of exactly one, with a way to switch between them.

### Checklist
- [x] Add board-scoped API routes: list a user's boards, create a board, rename a board, delete a board, get/update one board's state by id
- [x] Enforce board ownership (a user can only read/write their own boards) in every board route
- [x] Add a board switcher UI (list boards, create new, rename, delete, select active board)
- [x] Update the AI chat endpoint to operate on the currently selected board id
- [x] Update `docs/DATABASE.md` if the schema or ownership rules change
- [x] Add backend tests for board CRUD and ownership enforcement (user A cannot read/write user B's board)
- [x] Add frontend tests for switching boards and creating/deleting boards

### Tests
- A new user has zero boards until they create one (or a default board is created on first login)
- Creating a board makes it appear in that user's board list only
- Renaming and deleting a board persists and does not affect other boards
- A user cannot fetch, update, or delete another user's board (403/404)
- Switching boards in the UI loads the correct board's columns and cards

### Success criteria
- [x] Users can create, rename, delete, and switch between multiple boards
- [x] Board data never leaks across users or boards
- [x] The AI chat sidebar operates on the correct, currently-selected board

---

## Final verification checklist (post-MVP)

- [x] Multiple real user accounts can register, log in, and log out independently
- [x] Each user can create, rename, delete, and switch between multiple boards
- [x] Board and card data is fully isolated per user and per board
- [x] All new backend routes have unit test coverage, including ownership/negative cases
- [x] Frontend integration/e2e tests cover registration, login, board switching, and board CRUD
- [x] `docs/DATABASE.md` and `CLAUDE.md` are updated to describe the new schema and auth flow