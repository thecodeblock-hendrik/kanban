# Database approach

## Overview

This project uses SQLite as the local persistence layer for the MVP. SQLite is a good fit because the app runs locally in Docker, the data volume is small, and the database can be created automatically if it does not exist.

## Design principles

- Keep the schema simple and explicit.
- Support future multi-user expansion without changing the model drastically.
- Align the schema with the MVP rules: single login user now, but database ready for more users later.
- Model board state as normalized tables rather than serializing the entire board as one blob.

## Tables

### users
Stores real, independently registered user identities.

Fields:
- id
- username
- password_hash (salted PBKDF2-HMAC-SHA256, hex-encoded)
- salt (random 16-byte hex string, unique per user)
- created_at

Passwords are never stored in plaintext. `db.hash_password()`/`db.verify_password()` handle hashing and verification; `db.create_user()` and `db.authenticate_user()` back the `/api/auth/register` and `/api/auth/login` routes.

### boards
Stores each user's project board(s). A user can own any number of boards.

Fields:
- id
- user_id
- name
- created_at
- updated_at

Every board route (`GET/POST /api/boards`, `PATCH/DELETE /api/boards/{id}`, `GET/PUT /api/board`, `POST /api/ai/board`) enforces ownership via `db.get_board_owned()`: a board only ever resolves for the user that owns it, returning 404 otherwise.

### board_columns
Stores the board's columns and their order.

Fields:
- id
- board_id
- title
- position
- created_at

This supports renaming columns while preserving ordering.

### board_cards
Stores each card and where it sits in the board.

Fields:
- id
- board_id
- column_id
- title
- details
- due_date (nullable ISO date string, e.g. `2026-01-15`)
- priority (`low` | `medium` | `high`, default `medium`)
- position
- created_at
- updated_at

Card movement is represented by updating `column_id` and `position`. `due_date`/`priority` are optional on write (defaulting to `null`/`medium`) so older payloads without them remain valid.

## Default board layout

The MVP board uses this default set of columns:

1. Backlog
2. Discovery
3. In Progress
4. Review
5. Done

These can be renamed by the user later without changing the underlying model contract.

## Why this structure

This approach keeps the schema understandable and easy to test:

- board state remains queryable
- card movement is straightforward
- column rename is a small update
- future backend APIs can read and write board state cleanly
- SQLite is easy to initialize and maintain in a local Docker app

## MVP status

This schema was the point of sign-off before Part 6 (backend persistence) began, and it held unchanged through the MVP (Parts 1-10): the `users` and `boards` tables were designed to support multiple users and multiple boards per user from the start, so no migration was needed when that scope was approved for Part 11/12 (see `docs/PLAN.md`) beyond adding a `salt` column to `users` for password hashing.
