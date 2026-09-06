from pathlib import Path

from fastapi.testclient import TestClient

from backend.app.main import app


ROOT_DIR = Path(__file__).resolve().parents[2]
FRONTEND_BUILD_DIR = ROOT_DIR / "frontend" / "out"


def test_health_endpoint() -> None:
    client = TestClient(app)
    response = client.get("/api/health")

    assert response.status_code == 200
    assert response.json() == {"status": "ok", "service": "pm-mvp-backend"}


def test_root_serves_generated_frontend_build() -> None:
    assert FRONTEND_BUILD_DIR.exists(), "Frontend static build directory should exist before serving it at /"
    index_file = FRONTEND_BUILD_DIR / "index.html"
    assert index_file.exists(), "Frontend static index.html should exist before serving it at /"

    client = TestClient(app)
    response = client.get("/")

    assert response.status_code == 200
    assert "Kanban Studio" in response.text
