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


def test_list_workspaces_requires_auth() -> None:
    response = client.get("/v1/workspaces")
    assert response.status_code == 401


def test_list_projects_requires_auth() -> None:
    response = client.get("/v1/projects", params={"workspace_id": "workspace_1"})
    assert response.status_code == 401


def test_list_chat_sessions_requires_auth() -> None:
    response = client.get(
        "/v1/chat/sessions",
        params={"workspace_id": "workspace_1", "project_id": "project_1"},
    )
    assert response.status_code == 401


def test_list_jobs_requires_auth() -> None:
    response = client.get("/v1/jobs", params={"workspace_id": "workspace_1"})
    assert response.status_code == 401


def test_list_datasets_requires_auth() -> None:
    response = client.get("/v1/datasets", params={"workspace_id": "workspace_1"})
    assert response.status_code == 401
