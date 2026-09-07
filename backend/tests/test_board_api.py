from fastapi.testclient import TestClient
import pytest

from backend.app import main


@pytest.fixture(autouse=True)
def isolated_database(tmp_path, monkeypatch):
    monkeypatch.setattr(main, "DB_DIR", tmp_path)
    monkeypatch.setattr(main, "DB_PATH", tmp_path / "pm.db")


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


def test_ai_test_endpoint_returns_model_response(monkeypatch) -> None:
    def fake_call_openrouter(prompt: str) -> str:
        assert prompt == "2 + 2"
        return "4"

    monkeypatch.setattr(main, "call_openrouter", fake_call_openrouter)

    client = TestClient(app)
    response = client.get("/api/ai/test?prompt=2+2")

    assert response.status_code == 200
    payload = response.json()
    assert payload["ok"] is True
    assert payload["response"] == "4"
    assert payload["model"] == main.OPENROUTER_MODEL


def test_ai_test_endpoint_reports_actionable_errors(monkeypatch) -> None:
    def fake_call_openrouter(prompt: str) -> str:
        raise RuntimeError("OPENROUTER_API_KEY is missing. Add it to the project .env file.")

    monkeypatch.setattr(main, "call_openrouter", fake_call_openrouter)

    client = TestClient(app)
    response = client.get("/api/ai/test?prompt=2+2")

    assert response.status_code == 503
    assert "OPENROUTER_API_KEY" in response.json()["detail"]
