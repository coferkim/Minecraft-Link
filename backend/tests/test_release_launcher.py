from fastapi import FastAPI
from fastapi.testclient import TestClient

from launcher import create_web_app


def test_packaged_web_app_serves_frontend_and_mounts_api(tmp_path):
    (tmp_path / "index.html").write_text("<main>Minecraft-Link</main>", encoding="utf-8")
    (tmp_path / "minecraft-link.svg").write_text("<svg></svg>", encoding="utf-8")
    api = FastAPI()

    @api.get("/healthz")
    def healthz():
        return {"ok": True}

    client = TestClient(create_web_app(api, tmp_path))

    assert "Minecraft-Link" in client.get("/").text
    assert client.get("/minecraft-link.svg").status_code == 200
    assert client.get("/api/healthz").json() == {"ok": True}
