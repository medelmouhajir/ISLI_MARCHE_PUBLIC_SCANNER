from fastapi.testclient import TestClient

from app.main import app


client = TestClient(app)


def test_health_endpoint() -> None:
    response = client.get("/health")
    assert response.status_code == 200
    assert response.json() == {"status": "ok"}


def test_manifest_endpoint() -> None:
    response = client.get("/.well-known/isli-manifest")
    assert response.status_code == 200
    manifest = response.json()
    assert manifest["isli_version"] == "2.0"
    assert "tools" in manifest
    assert len(manifest["tools"]) == 3
