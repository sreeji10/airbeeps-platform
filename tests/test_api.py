from fastapi.testclient import TestClient

from airbeeps_api.main import app


client = TestClient(app)


def test_health_check() -> None:
    response = client.get("/health")
    assert response.status_code == 200
    assert response.json() == {"status": "ok"}


def test_create_chat_run() -> None:
    payload = {
        "project_id": "proj_1",
        "message": "Summarize dataset context",
        "dataset_ids": ["dataset_a"],
        "tool_names": ["echo"],
    }
    response = client.post("/v1/chat/runs", json=payload)
    data = response.json()
    assert response.status_code == 200
    assert data["status"] == "completed"
    assert data["used_tools"] == ["echo"]
    assert len(data["retrieval"]) >= 1


def test_ingest_dataset() -> None:
    payload = {
        "project_id": "proj_1",
        "dataset_id": "dataset_a",
        "files": ["docs/intro.md", "docs/setup.pdf"],
    }
    response = client.post("/v1/datasets/ingest", json=payload)
    data = response.json()
    assert response.status_code == 200
    assert data["status"] == "accepted"
    assert data["accepted_files"] == 2
