from fastapi.testclient import TestClient

from airbeeps_api.main import app


client = TestClient(app)


def test_health_check() -> None:
    response = client.get("/health")
    assert response.status_code == 200
    assert response.json() == {"status": "ok"}


def test_chat_session_requires_auth() -> None:
    payload = {
        "workspace_id": "workspace_1",
        "project_id": "project_1",
        "title": "New chat",
    }
    response = client.post("/v1/chat/sessions", json=payload)
    assert response.status_code == 401


def test_ingest_dataset() -> None:
    payload = {
        "workspace_id": "workspace_1",
        "project_id": "proj_1",
        "dataset_id": "dataset_a",
    }
    response = client.post("/v1/datasets/ingest", json=payload)
    assert response.status_code == 401
