# Frontend agent guide

## Purpose
This directory contains the Next.js frontend for the project management MVP. It is the existing demo implementation of the Kanban board and is meant to be evolved into a fully integrated app that is served by the Python FastAPI backend.

## Current stack
- Next.js 16
- React 19
- TypeScript
- Vitest for unit tests
- Playwright for browser-level tests
- @dnd-kit for drag-and-drop interactions
- Tailwind CSS for styling

## Project layout
- app/
  - App entry points and page route definitions.
  - The root page currently renders the Kanban board directly.
- components/
  - UI components for the board, columns, cards, and forms.
  - The board logic is implemented in a client component and is the main interaction point for drag-and-drop behavior.
- lib/
  - Core Kanban logic such as the board model, card movement behavior, and helper functions.
  - This is the most likely place for pure logic tests and reusable rules.
- test/
  - Shared test setup and global test configuration.
- public/
  - Static assets if needed for the app.

## Important current implementation notes
- The board is currently a local, in-memory React state model.
- Board data is defined in the initial data structure and moved through helper functions in lib/kanban.ts.
- The drag-and-drop behavior is handled with @dnd-kit and is wired through KanbanBoard.tsx.
- Column renaming, card creation, and card deletion are handled in the main board component rather than a separate store.
- The app currently assumes a standalone frontend demo and does not yet integrate with a backend API or auth flow.

## Testing commands
- npm run test
- npm run test:unit
- npm run test:e2e
- npm run build
- npm run lint

## Testing conventions
- Prefer testing real user-visible behavior over implementation details.
- Keep test coverage focused on board behavior, card flow, and user interaction outcomes.
- Use the existing Vitest and Testing Library setup for component behavior checks.

## Working rules for future changes
- Keep the MVP simple and avoid over-engineering.
- Preserve the current board structure unless a later phase specifically changes it.
- When introducing backend integration, keep the board data contract explicit and simple.
- Do not add unnecessary abstraction layers before the persistence and AI requirements are in place.

## Main files to review first
- src/app/page.tsx
- src/components/KanbanBoard.tsx
- src/components/KanbanColumn.tsx
- src/lib/kanban.ts
- src/components/KanbanBoard.test.tsx

## Expected evolution path
The frontend will eventually be:
- gated behind a login screen
- served from the backend at /
- backed by API calls instead of local-only state
- extended with an AI chat sidebar that can update the board through structured responses

Keep the implementation incremental and aligned with the approved project plan.
