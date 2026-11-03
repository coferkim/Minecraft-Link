from fastapi.testclient import TestClient

from app.core.config import settings
from app.db import storage
from app.main import create_app


def _client(tmp_path, monkeypatch) -> TestClient:
    monkeypatch.setattr(storage, "DB_PATH", tmp_path / "test.sqlite")
    return TestClient(create_app())


def test_access_key_returns_usable_jwt(tmp_path, monkeypatch):
    client = _client(tmp_path, monkeypatch)
    response = client.post("/authorize/access-key", json={"access_key": settings.access_key})

    assert response.status_code == 200
    payload = response.json()
    assert payload["stage"] == "mc-login"
    assert payload["token_type"] == "bearer"

    session = client.get(
        "/minecraft/session",
        headers={"Authorization": f"Bearer {payload['access_token']}"},
    )
    assert session.status_code == 200
    assert session.json()["authenticated"] is False


def test_access_key_rejects_invalid_key(tmp_path, monkeypatch):
    client = _client(tmp_path, monkeypatch)
    response = client.post("/authorize/access-key", json={"access_key": "wrong"})
    assert response.status_code == 401


def test_local_register_and_login_routes_are_not_available(tmp_path, monkeypatch):
    client = _client(tmp_path, monkeypatch)

    assert client.post("/authorize/register", json={"username": "user", "password": "password123"}).status_code == 404
    assert client.post("/authorize/login", json={"username": "user", "password": "password123"}).status_code == 404

    paths = client.get("/openapi.json").json()["paths"]
    assert "/authorize/register" not in paths
    assert "/authorize/login" not in paths


def test_minecraft_token_is_scoped_by_local_username(tmp_path, monkeypatch):
    client = _client(tmp_path, monkeypatch)
    token = client.post(
        "/authorize/access-key", json={"access_key": settings.access_key}
    ).json()["access_token"]
    headers = {"Authorization": f"Bearer {token}"}

    storage.save_token("minecraft-entity-1", "sead-value", "guest")
    session = client.get("/minecraft/session", headers=headers)

    assert session.status_code == 200
    assert session.json() == {
        "authenticated": True,
        "user_id": "minecraft-entity-1",
        "updated_at": session.json()["updated_at"],
    }
