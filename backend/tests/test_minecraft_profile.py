import asyncio

import httpx
import pytest

from app.core.config import settings
from app.services.minecraft import MinecraftClient


def own_detail():
    return {
        "code": 0,
        "entity": {
            "entity_id": 900000,
            "name": "Test player",
            "head_image": "https://example.test/own-avatar.png",
            "level": 1,
            "signature": "Test signature",
        },
    }


def test_profile_enriches_game_growth_and_matches_the_account_uid(monkeypatch):
    client = MinecraftClient("900000", "test-only-token")
    detail = own_detail()
    calls = []

    async def post(path, payload):
        calls.append((path, payload))
        if path == "/user-detail":
            return detail
        return {
            "code": 0,
            "entities": [
                {"id": 777777, "pe_growth": {"lv": 99}},
                {
                    "id": 900000,
                    "headImage": "https://example.test/game-avatar.png",
                    "pe_growth": {"lv": 36, "exp": 1549},
                    "frame_id": "https://example.test/frame.png",
                    "recharge_vip_level": 3,
                    "name": "Do not replace the account name",
                },
            ],
        }

    monkeypatch.setattr(client, "post", post)
    result = asyncio.run(client.self_detail())
    assert calls == [
        ("/user-detail", {"role_id": 900000}),
        (settings.mc_user_multi_detail_path, {"is_need_recharge_benefit": 0, "uids": [900000]}),
    ]
    assert result["entity"]["pe_growth"]["lv"] == 36
    assert result["entity"]["headImage"] == "https://example.test/game-avatar.png"
    assert result["entity"]["frame_id"] == "https://example.test/frame.png"
    assert result["entity"]["name"] == detail["entity"]["name"]
    assert result["entity"]["level"] == 1
    assert "pe_growth" not in detail["entity"]


@pytest.mark.parametrize("batch", [
    {"code": 500},
    {"code": 0, "entities": []},
    {"code": 0, "entities": [{"id": 777777, "pe_growth": {"lv": 99}}]},
    {"code": 0, "entities": None},
])
def test_missing_game_profile_preserves_self_detail_and_reports_warning(monkeypatch, batch):
    client = MinecraftClient("900000", "test-only-token")
    detail = own_detail()

    async def post(path, payload):
        return detail if path == "/user-detail" else batch

    monkeypatch.setattr(client, "post", post)
    result = asyncio.run(client.self_detail())
    assert result["entity"] == detail["entity"]
    assert result["profile_details_warning"]
    assert "pe_growth" not in result["entity"]


def test_batch_network_failure_does_not_hide_available_account_data(monkeypatch):
    client = MinecraftClient("900000", "test-only-token")
    detail = own_detail()

    async def post(path, payload):
        if path == "/user-detail":
            return detail
        raise httpx.ReadTimeout("test-only timeout")

    monkeypatch.setattr(client, "post", post)
    result = asyncio.run(client.self_detail())
    assert result["entity"]["head_image"] == detail["entity"]["head_image"]
    assert result["profile_details_warning"]


def test_rejected_self_profile_does_not_request_batch_details(monkeypatch):
    client = MinecraftClient("900000", "test-only-token")
    calls = []

    async def post(path, payload):
        calls.append(path)
        return {"code": 401, "message": "test-only rejected"}

    monkeypatch.setattr(client, "post", post)
    assert asyncio.run(client.self_detail())["code"] == 401
    assert calls == ["/user-detail"]
