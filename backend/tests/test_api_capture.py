from fastapi.testclient import TestClient

from app.api import minecraft as minecraft_api
from app.core.config import settings
from app.db import storage
from app.main import create_app
from app.services.sauth_capture import CaptureResult


def test_capture_endpoint_returns_sauth(tmp_path, monkeypatch):
    monkeypatch.setattr(storage, "DB_PATH", tmp_path / "capture.sqlite")
    monkeypatch.setattr(
        minecraft_api,
        "capture_sauth",
        lambda pid, process_name, max_bytes: CaptureResult(
            pid=1234,
            process_name="Minecraft.Windows.exe",
            sauth={
                "client_login_sn": "sn",
                "udid": "udid",
                "deviceid": "device",
                "sdkuid": "sdk",
                "sessionid": "session",
            },
            scanned_bytes=1024,
            matched_offsets=1,
        ),
    )
    client = TestClient(create_app())
    token = client.post(
        "/authorize/access-key", json={"access_key": settings.access_key}
    ).json()["access_token"]

    response = client.post(
        "/minecraft/capture",
        headers={"Authorization": f"Bearer {token}"},
        json={"pid": 1234},
    )

    assert response.status_code == 200
    assert response.json()["sauth"]["client_login_sn"] == "sn"
