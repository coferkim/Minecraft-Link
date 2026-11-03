from fastapi.testclient import TestClient

from app.api import minecraft as minecraft_api
from app.core.security import create_access_token
from app.db import storage
from app.main import create_app
from app.services.minecraft import UpstreamPathError, validate_upstream_path


class FakeClient:
    def __init__(self):
        self.calls = []

    async def current_room(self):
        return {"code": 0, "entity": None}

    async def search_rooms(self, payload):
        self.calls.append(("search_rooms", payload))
        return {"code": 0, "entities": [], "total": 0}

    async def apply_friend(self, target_id, message, **kwargs):
        self.calls.append(("apply_friend", target_id, message, kwargs))
        return {"code": 0, "entity": None}

    async def upstream(self, path, payload):
        self.calls.append(("upstream", path, payload))
        return {"code": 0, "entity": None}

    async def room_detail(self, room_id):
        self.calls.append(("room_detail", room_id))
        return {"code": 0, "entity": None}


def _client(tmp_path, monkeypatch):
    monkeypatch.setattr(storage, "DB_PATH", tmp_path / "extended.sqlite")
    app = create_app()
    headers = {"Authorization": f"Bearer {create_access_token('guest')}"}
    return TestClient(app), headers


def test_room_routes_and_search_payload(tmp_path, monkeypatch):
    client, headers = _client(tmp_path, monkeypatch)
    fake = FakeClient()
    monkeypatch.setattr(minecraft_api, "_client_for_user", lambda username: fake)

    current = client.get("/minecraft/rooms/current", headers=headers)
    assert current.status_code == 200
    assert current.json()["code"] == 0

    search = client.get(
        "/minecraft/rooms/search?keyword=test&page=2&size=8",
        headers=headers,
    )
    assert search.status_code == 200
    assert fake.calls[-1] == (
        "search_rooms",
        {"keyword": "test", "page": 2, "size": 8},
    )


def test_friend_request_uses_path_target(tmp_path, monkeypatch):
    client, headers = _client(tmp_path, monkeypatch)
    fake = FakeClient()
    monkeypatch.setattr(minecraft_api, "_client_for_user", lambda username: fake)

    response = client.post(
        "/minecraft/friends/123/request",
        headers=headers,
        json={"message": "hello"},
    )

    assert response.status_code == 200
    assert fake.calls[-1][0:3] == ("apply_friend", "123", "hello")


def test_upstream_path_allowlist():
    assert validate_upstream_path("/online-lobby-room/query/user-room") == (
        "/online-lobby-room/query/user-room"
    )
    for bad in ("http://example.com", "//example.com", "/unknown/path", "/user-../x"):
        try:
            validate_upstream_path(bad)
        except UpstreamPathError:
            pass
        else:
            raise AssertionError(f"path should be rejected: {bad}")


def test_endpoint_catalog_is_available(tmp_path, monkeypatch):
    client, headers = _client(tmp_path, monkeypatch)
    response = client.get("/minecraft/endpoints", headers=headers)
    assert response.status_code == 200
    payload = response.json()
    assert payload["local_endpoints"]
    assert "/minecraft/rooms/current" in {
        item["path"] for item in payload["local_endpoints"]
    }
