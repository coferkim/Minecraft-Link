from __future__ import annotations

import base64
import json
import uuid
from typing import Any

import httpx

from app.utils.mc_auth_toolkit import PeAuthCodec, PeAuthSignCodec


ENGINE_VERSION = "3.8.43.296051"
PATCH_VERSION = "3.8.44.296250"
ENGINE_MAGIC = "e0cd6efb2c8e2260ac1a4f226277538f"
PATCH_MAGIC = "a39e7f98b9c673b52f74e5c24c8aa5902b3e7ca013bb30a74d822579860c042b"


class McAuthError(RuntimeError):
    pass


class PeAuth:
    def __init__(self, sauth: dict[str, Any], timeout: float = 15.0):
        self.data = sauth
        self.client_login_sn = str(sauth.get("client_login_sn", ""))
        self.udid = str(sauth.get("udid", ""))
        self.device_id = str(sauth.get("deviceid", sauth.get("device_id", "")))
        self.sdkuid = str(sauth.get("sdkuid", ""))
        self.ip = ""
        self.aim_info: dict[str, Any] = {}
        self.timeout = timeout
        self.auth_result: dict[str, Any] | None = None

    async def _post_form(self, url: str, form: dict[str, Any]) -> dict[str, Any]:
        async with httpx.AsyncClient(timeout=self.timeout) as client:
            response = await client.post(url, data=form)
            response.raise_for_status()
            try:
                return response.json()
            except Exception as exc:
                raise McAuthError(f"响应不是 JSON: {response.text[:200]}") from exc

    async def _get_ticket(self) -> str:
        response = await self._post_form(
            "https://service.mkey.163.com/mpay/api/users/create_ticket",
            {
                "device_id": self.device_id,
                "game_id": "aecglf6ee4aaaarz-g-a50",
                "token": self.data.get("sessionid", ""),
            },
        )
        if "ticket" not in response:
            raise McAuthError(f"create_ticket 失败: {response}")
        return str(response["ticket"])

    async def _get_a50_token(self) -> str:
        response = await self._post_form(
            "https://service.mkey.163.com/mpay/api/users/login/ticket",
            {
                "cv": "c4.16.0",
                "app_channel": "a50_sdk_cn",
                "device_id": self.device_id,
                "game_id": "aecfrxodyqaaaajp-g-x19",
                "ticket": await self._get_ticket(),
            },
        )
        user = response.get("user")
        if not user:
            raise McAuthError(f"ticket login 失败: {response}")
        self.ip = user.get("pc_ext_info", {}).get("src_client_ip", "")
        return str(user["token"])

    async def _get_x19_uni_sauth(self) -> tuple[str, str]:
        session_id = await self._get_a50_token()
        self.aim_info = {"aim": self.ip, "country": "CN", "tz": "+0800", "tzid": ""}
        response = await self._post_form(
            "https://mgbsdk.matrix.netease.com/x19/sdk/uni_sauth",
            {
                "gameid": "x19",
                "login_channel": "netease",
                "app_channel": "a50_sdk_cn",
                "platform": "pc",
                "sdkuid": self.sdkuid,
                "sessionid": session_id,
                "sdk_version": "4.16.0",
                "udid": self.udid,
                "deviceid": self.device_id,
                "client_login_sn": self.client_login_sn,
                "gas_token": "",
                "source_platform": "pc",
                "ip": self.ip,
                "get_access_token": "1",
                "aim_info": json.dumps(self.aim_info, separators=(",", ":")),
                "lang": "zh",
            },
        )
        try:
            login_json = json.loads(base64.b64decode(response["unisdk_login_json"]))
            return str(login_json["oauth2"]["access_token"]), session_id
        except Exception as exc:
            raise McAuthError(f"uni_sauth 解析失败: {response}") from exc

    def _make_pe_auth_base(self, access_token: str, session_id: str) -> dict[str, Any]:
        seed = str(uuid.uuid4())
        message = f"{ENGINE_VERSION}{ENGINE_MAGIC}{PATCH_VERSION}{PATCH_MAGIC}{seed}"
        sa_data = {
            "app_channel": "a50_sdk_cn",
            "app_ver": PATCH_VERSION,
            "device_model": "Win32",
            "emulator": 0,
            "first_udid": self.udid,
            "is_guest": 0,
            "launcher_type": "PE_C++",
            "network": "",
            "os_name": "windows",
            "os_ver": "10.0.26200",
            "root": False,
            "sdk_ver": "4.16.0",
            "start_type": "default",
            "tdid": "",
            "udid": self.udid,
        }
        return {
            "engine_version": ENGINE_VERSION,
            "extra_param": "extra",
            "message": message,
            "patch_version": PATCH_VERSION,
            "pay_channel": "netease",
            "sa_data": json.dumps(sa_data, ensure_ascii=False, separators=(",", ":")),
            "sauth_json": {
                "access_token": access_token,
                "aim_info": json.dumps(self.aim_info, ensure_ascii=False, separators=(",", ":")),
                "app_channel": "a50_sdk_cn",
                "client_login_sn": self.client_login_sn,
                "deviceid": self.device_id,
                "gameid": "x19",
                "gas_token": "",
                "get_access_token": "1",
                "ip": self.ip,
                "login_channel": "netease",
                "platform": "pc",
                "sdk_version": "4.16.0",
                "sdkuid": self.sdkuid,
                "sessionid": session_id,
                "source_platform": "pc",
                "tdid": "",
                "udid": self.udid,
            },
            "seed": seed,
            "sign": PeAuthSignCodec.generate(message),
        }

    async def auth(self) -> dict[str, Any]:
        access_token, session_id = await self._get_x19_uni_sauth()
        body = PeAuthCodec.encrypt(self._make_pe_auth_base(access_token, session_id))
        async with httpx.AsyncClient(timeout=self.timeout) as client:
            response = await client.post(
                "https://g79obtapigtcoregray.minecraft.cn/pe-authentication",
                content=body.encode("ascii"),
            )
            response.raise_for_status()
        packet = PeAuthCodec.decrypt(response.text)
        if packet.plain_json is None:
            raise McAuthError("pe-authentication 返回无法解析的响应")
        if isinstance(packet.plain_json, dict) and packet.plain_json.get("entity") is None:
            code = packet.plain_json.get("code")
            message = packet.plain_json.get("message") or packet.plain_json.get("msg") or "上游拒绝认证"
            raise McAuthError(f"pe-authentication 失败: {message}" + (f" (code {code})" if code else ""))
        self.auth_result = packet.plain_json
        return packet.plain_json

    def get_sead_and_id(self) -> tuple[str, str]:
        response = self.auth_result or {}
        entity = response.get("entity")
        if not entity or "token" not in entity or "entity_id" not in entity:
            raise McAuthError(f"pe-authentication 缺少 entity 数据: {response}")
        return str(entity["token"]), str(entity["entity_id"])
