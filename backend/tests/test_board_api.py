import json

from fastapi.testclient import TestClient
import pytest

from backend.app import ai, db, main


@pytest.fixture(autouse=True)
def isolated_database(tmp_path, monkeypatch):
    monkeypatch.setattr(db, "DB_DIR", tmp_path)
    monkeypatch.setattr(db, "DB_PATH", tmp_path / "pm.db")
    db.init_db()


app = main.app


def _get_board(client: TestClient, user: str = "user") -> dict:
    return client.get(f"/api/board?user={user}").json()


def test_board_is_created_for_default_user() -> None:
    client = TestClient(app)
    response = client.get("/api/board?user=user")

    assert response.status_code == 200
    data = response.json()
    assert data["user"] == "user"
    assert "boardId" in data
    assert len(data["board"]["columns"]) == 5
    assert len(data["board"]["cards"]) > 0


def test_board_persists_updated_state() -> None:
    client = TestClient(app)

    initial = _get_board(client)
    board_id = initial["boardId"]
    original = initial["board"]
    backlog_id = original["columns"][0]["id"]

    updated = {
        "columns": [
            {"id": backlog_id, "title": "Backlog Updated", "cardIds": ["persisted-card"]},
            *[
                {"id": column["id"], "title": column["title"], "cardIds": []}
                for column in original["columns"][1:]
            ],
        ],
        "cards": {
            "persisted-card": {
                "id": "persisted-card",
                "title": "Persisted card",
                "details": "Saved in the database",
            }
        },
    }

    put_response = client.put(f"/api/board?user=user&boardId={board_id}", json=updated)
    assert put_response.status_code == 200

    persisted = _get_board(client)["board"]
    assert persisted["columns"][0]["title"] == "Backlog Updated"
    assert persisted["cards"]["persisted-card"]["title"] == "Persisted card"
    assert persisted["cards"]["persisted-card"]["details"] == "Saved in the database"

    assert original["columns"][0]["title"] != persisted["columns"][0]["title"]


def test_invalid_board_update_does_not_mutate_existing_state() -> None:
    client = TestClient(app)
    initial = _get_board(client)
    board_id = initial["boardId"]
    original = initial["board"]
    backlog_id = original["columns"][0]["id"]
    invalid = {
        "columns": [
            {"id": backlog_id, "title": "Changed", "cardIds": ["missing-card"]},
            *original["columns"][1:],
        ],
        "cards": original["cards"],
    }

    response = client.put(f"/api/board?user=user&boardId={board_id}", json=invalid)

    assert response.status_code == 400
    assert "missing cards" in response.json()["detail"]
    assert _get_board(client)["board"] == original


def test_duplicate_column_and_card_references_are_rejected() -> None:
    client = TestClient(app)
    initial = _get_board(client)
    board_id = initial["boardId"]
    original = initial["board"]
    backlog_id = original["columns"][0]["id"]
    first_card_id = original["columns"][0]["cardIds"][0]

    duplicate_column = {
        "columns": [original["columns"][0], original["columns"][0]],
        "cards": original["cards"],
    }
    response = client.put(f"/api/board?user=user&boardId={board_id}", json=duplicate_column)
    assert response.status_code == 400
    assert "Duplicate board column id" in response.json()["detail"]

    duplicate_card = {
        "columns": [
            {"id": backlog_id, "title": "Backlog", "cardIds": [first_card_id, first_card_id]},
            *original["columns"][1:],
        ],
        "cards": original["cards"],
    }
    response = client.put(f"/api/board?user=user&boardId={board_id}", json=duplicate_card)
    assert response.status_code == 400
    assert "appears more than once" in response.json()["detail"]


def test_ai_test_endpoint_returns_model_response(monkeypatch) -> None:
    def fake_call_openrouter(prompt: str) -> str:
        assert prompt == "2 + 2"
        return "4"

    monkeypatch.setattr(ai, "call_openrouter", fake_call_openrouter)

    client = TestClient(app)
    response = client.get("/api/ai/test?prompt=2+2")

    assert response.status_code == 200
    payload = response.json()
    assert payload["ok"] is True
    assert payload["response"] == "4"
    assert payload["model"] == ai.OPENROUTER_MODEL


def test_ai_test_endpoint_reports_actionable_errors(monkeypatch) -> None:
    def fake_call_openrouter(prompt: str) -> str:
        raise RuntimeError("OPENROUTER_API_KEY is missing. Add it to the project .env file.")

    monkeypatch.setattr(ai, "call_openrouter", fake_call_openrouter)

    client = TestClient(app)
    response = client.get("/api/ai/test?prompt=2+2")

    assert response.status_code == 503
    assert "OPENROUTER_API_KEY" in response.json()["detail"]


def test_ai_board_endpoint_accepts_valid_structured_response(monkeypatch) -> None:
    client = TestClient(app)
    initial = _get_board(client)
    board_id = initial["boardId"]
    original = initial["board"]

    def fake_call_openrouter(prompt: str) -> str:
        assert "conversation history" in prompt
        assert "Rename the backlog" in prompt
        updated_columns = [dict(column) for column in original["columns"]]
        updated_columns[0]["title"] = "Launch Queue"
        return json.dumps(
            {
                "response": "Updated the backlog column title.",
                "board_update": {
                    "columns": updated_columns,
                    "cards": original["cards"],
                },
            }
        )

    monkeypatch.setattr(ai, "call_openrouter", fake_call_openrouter)

    response = client.post(
        f"/api/ai/board?user=user&boardId={board_id}",
        json={
            "prompt": "Rename the backlog to Launch Queue.",
            "history": [
                {"role": "user", "content": "hello"},
                {"role": "assistant", "content": "hi"},
            ],
        },
    )

    assert response.status_code == 200
    payload = response.json()
    assert payload["response"] == "Updated the backlog column title."
    assert payload["board"]["columns"][0]["title"] == "Launch Queue"


def test_ai_board_endpoint_rejects_malformed_structured_response(monkeypatch) -> None:
    client = TestClient(app)
    board_id = _get_board(client)["boardId"]
    monkeypatch.setattr(ai, "call_openrouter", lambda prompt: '{"response": 123}')

    response = client.post(f"/api/ai/board?user=user&boardId={board_id}", json={"prompt": "Rename the column."})

    assert response.status_code == 400
    assert "structured" in response.json()["detail"].lower()


def test_ai_board_endpoint_rejects_unowned_board(monkeypatch) -> None:
    client = TestClient(app)
    client.post("/api/auth/register", json={"username": "other", "password": "hunter2"})
    other_board_id = _get_board(client, user="other")["boardId"]

    monkeypatch.setattr(ai, "call_openrouter", lambda prompt: '{"response": "hi"}')
    response = client.post(f"/api/ai/board?user=user&boardId={other_board_id}", json={"prompt": "hi"})

    assert response.status_code == 404


# --- Auth ---


def test_register_creates_new_user() -> None:
    client = TestClient(app)
    response = client.post("/api/auth/register", json={"username": "alice", "password": "wonderland"})

    assert response.status_code == 200
    assert response.json()["user"]["username"] == "alice"


def test_register_rejects_duplicate_username() -> None:
    client = TestClient(app)
    client.post("/api/auth/register", json={"username": "alice", "password": "wonderland"})
    response = client.post("/api/auth/register", json={"username": "alice", "password": "different"})

    assert response.status_code == 400


def test_register_rejects_short_password() -> None:
    client = TestClient(app)
    response = client.post("/api/auth/register", json={"username": "alice", "password": "abc"})

    assert response.status_code == 400


def test_login_succeeds_with_correct_credentials() -> None:
    client = TestClient(app)
    client.post("/api/auth/register", json={"username": "alice", "password": "wonderland"})

    response = client.post("/api/auth/login", json={"username": "alice", "password": "wonderland"})

    assert response.status_code == 200
    assert response.json()["user"]["username"] == "alice"


def test_login_fails_with_wrong_password() -> None:
    client = TestClient(app)
    client.post("/api/auth/register", json={"username": "alice", "password": "wonderland"})

    response = client.post("/api/auth/login", json={"username": "alice", "password": "wrong"})

    assert response.status_code == 401


def test_login_fails_for_unknown_user() -> None:
    client = TestClient(app)
    response = client.post("/api/auth/login", json={"username": "ghost", "password": "whatever"})

    assert response.status_code == 401


def test_seeded_default_user_can_log_in() -> None:
    client = TestClient(app)
    response = client.post("/api/auth/login", json={"username": "user", "password": "password"})

    assert response.status_code == 200


# --- Boards CRUD ---


def test_list_boards_creates_default_board_for_new_user() -> None:
    client = TestClient(app)
    response = client.get("/api/boards?user=user")

    assert response.status_code == 200
    boards = response.json()["boards"]
    assert len(boards) == 1
    assert boards[0]["name"] == "Project Board"


def test_create_board_adds_second_board() -> None:
    client = TestClient(app)
    client.get("/api/boards?user=user")

    response = client.post("/api/boards?user=user", json={"name": "Marketing"})
    assert response.status_code == 200
    assert response.json()["board"]["name"] == "Marketing"

    boards = client.get("/api/boards?user=user").json()["boards"]
    assert len(boards) == 2
    assert {board["name"] for board in boards} == {"Project Board", "Marketing"}


def test_rename_board_persists() -> None:
    client = TestClient(app)
    board_id = _get_board(client)["boardId"]

    response = client.patch(f"/api/boards/{board_id}?user=user", json={"name": "Renamed"})
    assert response.status_code == 200

    boards = client.get("/api/boards?user=user").json()["boards"]
    assert boards[0]["name"] == "Renamed"


def test_delete_board_removes_it() -> None:
    client = TestClient(app)
    board_id = _get_board(client)["boardId"]
    second = client.post("/api/boards?user=user", json={"name": "Second"}).json()["board"]

    response = client.delete(f"/api/boards/{second['id']}?user=user")
    assert response.status_code == 200

    boards = client.get("/api/boards?user=user").json()["boards"]
    assert [board["id"] for board in boards] == [board_id]


def test_boards_are_isolated_between_users() -> None:
    client = TestClient(app)
    client.post("/api/auth/register", json={"username": "bob", "password": "builder1"})

    user_board_id = _get_board(client, user="user")["boardId"]
    bob_board_id = _get_board(client, user="bob")["boardId"]

    assert user_board_id != bob_board_id

    user_boards = client.get("/api/boards?user=user").json()["boards"]
    bob_boards = client.get("/api/boards?user=bob").json()["boards"]
    assert [board["id"] for board in user_boards] == [user_board_id]
    assert [board["id"] for board in bob_boards] == [bob_board_id]


def test_user_cannot_read_another_users_board() -> None:
    client = TestClient(app)
    client.post("/api/auth/register", json={"username": "bob", "password": "builder1"})
    bob_board_id = _get_board(client, user="bob")["boardId"]

    response = client.get(f"/api/board?user=user&boardId={bob_board_id}")
    assert response.status_code == 404


def test_user_cannot_update_another_users_board() -> None:
    client = TestClient(app)
    client.post("/api/auth/register", json={"username": "bob", "password": "builder1"})
    bob_board = _get_board(client, user="bob")
    bob_board_id = bob_board["boardId"]

    response = client.put(f"/api/board?user=user&boardId={bob_board_id}", json=bob_board["board"])
    assert response.status_code == 404


def test_user_cannot_rename_or_delete_another_users_board() -> None:
    client = TestClient(app)
    client.post("/api/auth/register", json={"username": "bob", "password": "builder1"})
    bob_board_id = _get_board(client, user="bob")["boardId"]

    rename_response = client.patch(f"/api/boards/{bob_board_id}?user=user", json={"name": "Hijacked"})
    assert rename_response.status_code == 404

    delete_response = client.delete(f"/api/boards/{bob_board_id}?user=user")
    assert delete_response.status_code == 404
