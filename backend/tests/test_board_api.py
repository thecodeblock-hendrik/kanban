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


def test_board_is_created_for_default_user() -> None:
    client = TestClient(app)
    response = client.get("/api/board?user=user")

    assert response.status_code == 200
    data = response.json()
    assert data["user"] == "user"
    assert len(data["board"]["columns"]) == 5
    assert len(data["board"]["cards"]) > 0


def test_board_persists_updated_state() -> None:
    client = TestClient(app)

    original = client.get("/api/board?user=user").json()["board"]
    updated = {
        "columns": [
            {"id": "col-backlog", "title": "Backlog Updated", "cardIds": ["persisted-card"]},
            {"id": "col-discovery", "title": "Discovery", "cardIds": []},
            {"id": "col-progress", "title": "In Progress", "cardIds": []},
            {"id": "col-review", "title": "Review", "cardIds": []},
            {"id": "col-done", "title": "Done", "cardIds": []},
        ],
        "cards": {
            "persisted-card": {
                "id": "persisted-card",
                "title": "Persisted card",
                "details": "Saved in the database",
            }
        },
    }

    put_response = client.put("/api/board?user=user", json=updated)
    assert put_response.status_code == 200

    persisted = client.get("/api/board?user=user").json()["board"]
    assert persisted["columns"][0]["title"] == "Backlog Updated"
    assert persisted["cards"]["persisted-card"]["title"] == "Persisted card"
    assert persisted["cards"]["persisted-card"]["details"] == "Saved in the database"

    assert original["columns"][0]["title"] != persisted["columns"][0]["title"]


def test_invalid_board_update_does_not_mutate_existing_state() -> None:
    client = TestClient(app)
    original = client.get("/api/board?user=user").json()["board"]
    invalid = {
        "columns": [
            {"id": "col-backlog", "title": "Changed", "cardIds": ["missing-card"]},
            *original["columns"][1:],
        ],
        "cards": original["cards"],
    }

    response = client.put("/api/board?user=user", json=invalid)

    assert response.status_code == 400
    assert "missing cards" in response.json()["detail"]
    assert client.get("/api/board?user=user").json()["board"] == original


def test_duplicate_column_and_card_references_are_rejected() -> None:
    client = TestClient(app)
    original = client.get("/api/board?user=user").json()["board"]

    duplicate_column = {
        "columns": [original["columns"][0], original["columns"][0]],
        "cards": original["cards"],
    }
    response = client.put("/api/board?user=user", json=duplicate_column)
    assert response.status_code == 400
    assert "Duplicate board column id" in response.json()["detail"]

    duplicate_card = {
        "columns": [
            {"id": "col-backlog", "title": "Backlog", "cardIds": ["card-1", "card-1"]},
            *original["columns"][1:],
        ],
        "cards": original["cards"],
    }
    response = client.put("/api/board?user=user", json=duplicate_card)
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
    def fake_call_openrouter(prompt: str) -> str:
        assert "conversation history" in prompt
        assert "Rename the backlog" in prompt
        return json.dumps(
            {
                "response": "Updated the backlog column title.",
                "board_update": {
                    "columns": [
                        {"id": "col-backlog", "title": "Launch Queue", "cardIds": ["card-1", "card-2"]},
                        {"id": "col-discovery", "title": "Discovery", "cardIds": ["card-3"]},
                        {"id": "col-progress", "title": "In Progress", "cardIds": ["card-4", "card-5"]},
                        {"id": "col-review", "title": "Review", "cardIds": ["card-6"]},
                        {"id": "col-done", "title": "Done", "cardIds": ["card-7", "card-8"]},
                    ],
                    "cards": {
                        "card-1": {"id": "card-1", "title": "Align roadmap themes", "details": "Draft quarterly themes with impact statements and metrics."},
                        "card-2": {"id": "card-2", "title": "Gather customer signals", "details": "Review support tags, sales notes, and churn feedback."},
                        "card-3": {"id": "card-3", "title": "Prototype analytics view", "details": "Sketch initial dashboard layout and key drill-downs."},
                        "card-4": {"id": "card-4", "title": "Refine status language", "details": "Standardize column labels and tone across the board."},
                        "card-5": {"id": "card-5", "title": "Design card layout", "details": "Add hierarchy and spacing for scanning dense lists."},
                        "card-6": {"id": "card-6", "title": "QA micro-interactions", "details": "Verify hover, focus, and loading states."},
                        "card-7": {"id": "card-7", "title": "Ship marketing page", "details": "Final copy approved and asset pack delivered."},
                        "card-8": {"id": "card-8", "title": "Close onboarding sprint", "details": "Document release notes and share internally."},
                    },
                },
            }
        )

    monkeypatch.setattr(ai, "call_openrouter", fake_call_openrouter)

    client = TestClient(app)
    response = client.post(
        "/api/ai/board?user=user",
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
    monkeypatch.setattr(ai, "call_openrouter", lambda prompt: '{"response": 123}')

    client = TestClient(app)
    response = client.post("/api/ai/board?user=user", json={"prompt": "Rename the column."})

    assert response.status_code == 400
    assert "structured" in response.json()["detail"].lower()
