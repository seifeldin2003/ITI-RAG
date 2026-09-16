from fastapi.testclient import TestClient

from app.main import app


def test_health_happy_path():
    with TestClient(app) as client:  # triggers lifespan startup
        resp = client.get("/health")
        assert resp.status_code == 200
        body = resp.json()
        assert body["status"] == "ok"
        assert body["chunks_indexed"] and body["chunks_indexed"] > 0


def test_query_happy_path():
    with TestClient(app) as client:
        resp = client.post("/query", json={"question": "my car won't start"})
        assert resp.status_code == 200
        body = resp.json()
        assert isinstance(body["answer"], str) and body["answer"]
        assert isinstance(body["sources"], list)


def test_query_invalid_input_rejected():
    with TestClient(app) as client:
        # Empty question violates QueryRequest's min_length=1 -> FastAPI/pydantic
        # should reject this before it ever reaches the route body.
        resp = client.post("/query", json={"question": ""})
        assert resp.status_code == 422


def test_query_missing_field_rejected():
    with TestClient(app) as client:
        resp = client.post("/query", json={})
        assert resp.status_code == 422
