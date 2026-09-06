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
Stores user identities for future multi-user support.

Fields:
- id
- username
- password_hash
- created_at

### boards
Stores a user's project board(s).

Fields:
- id
- user_id
- name
- created_at
- updated_at

For the MVP, each signed-in user will have one board, but the schema supports multiple boards if needed later.

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
- position
- created_at
- updated_at

Card movement is represented by updating `column_id` and `position`.

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

This schema is a design proposal for Part 5 and is the point of sign-off before Part 6 begins. The backend will not be built against a different schema after approval.
