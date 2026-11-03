from __future__ import annotations

from typing import Any

import httpx

from app.core.config import settings
from app.utils.mc_auth_toolkit import UserTokenCodec


# These prefixes cover the social, lobby, team and room APIs observed in the
# running Minecraft client. The generic proxy is intentionally limited to the
# configured upstream host and this path surface.
ALLOWED_UPSTREAM_PREFIXES = (
    "/user-",
    "/friend-",
    "/friend-group/",
    "/online-lobby-",
    "/pe/",
    "/pe-item/",
    "/message",
    "/messages",
    "/item/",
    "/achievement/",
    "/switch-main-city/",
    "/get-recent-chat-msgs",
    "/ngpush-send-item-push",
    "/pe-client-js-class",
    "/interconn/web/",
)


class UpstreamPathError(ValueError):
    pass


def validate_upstream_path(path: str) -> str:
    path = str(path or "").strip()
    if not path.startswith("/") or path.startswith("//"):
        raise UpstreamPathError("上游路径必须以单个 / 开头")
    if len(path) > 240:
        raise UpstreamPathError("上游路径过长")
    if any(token in path for token in ("://", "..", "\\", "\r", "\n")):
        raise UpstreamPathError("上游路径包含非法字符")
    if not any(path.startswith(prefix) for prefix in ALLOWED_UPSTREAM_PREFIXES):
        raise UpstreamPathError("该上游路径不在白名单内")
    return path


class MinecraftClient:
    def __init__(self, user_id: str, sead: str):
        self.user_id = str(user_id)
        self.sead = str(sead)

    async def post(self, path: str, payload: dict[str, Any] | None = None) -> dict[str, Any]:
        path = validate_upstream_path(path)
        token, body_text = UserTokenCodec.generate_for_json(self.sead, path, payload or {})
        headers = {
            "user-token": token,
            "user-id": self.user_id,
            "content-type": "application/json",
        }
        async with httpx.AsyncClient(timeout=settings.mc_accept_timeout) as client:
            response = await client.post(
                settings.mc_api_base + path,
                headers=headers,
                content=body_text.encode("utf-8"),
            )
            response.raise_for_status()
            if not response.text.strip():
                return {"code": 0, "message": "空响应", "entity": None, "raw": ""}
            try:
                return response.json()
            except Exception as exc:
                raise RuntimeError(f"上游响应不是 JSON: {response.text[:200]}") from exc

    async def post_transfer(
        self,
        path: str,
        payload: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        path = str(path or "").strip()
        if not path.startswith("/") or path.startswith("//") or "://" in path:
            raise UpstreamPathError("transfer 路径必须是单个 / 开头的相对路径")
        token, body_text = UserTokenCodec.generate_for_json(self.sead, path, payload or {})
        headers = {
            "user-token": token,
            "user-id": self.user_id,
            "content-type": "application/json",
        }
        async with httpx.AsyncClient(timeout=settings.mc_accept_timeout) as client:
            response = await client.post(
                settings.mc_transfer_base + path,
                headers=headers,
                content=body_text.encode("utf-8"),
            )
            response.raise_for_status()
            if not response.text.strip():
                return {"code": 0, "message": "空响应", "list": []}
            try:
                return response.json()
            except Exception as exc:
                raise RuntimeError(f"transfer 响应不是 JSON: {response.text[:200]}") from exc

    async def upstream(self, path: str, payload: dict[str, Any] | None = None) -> dict[str, Any]:
        return await self.post(path, payload or {})

    # Friend and user APIs -------------------------------------------------

    async def all_friends(self) -> dict[str, Any]:
        return await self.post("/user-allfriends", {"with_game_state": False, "with_dynamic_head_img": 1})

    async def all_friends_detail(self) -> dict[str, Any]:
        return await self.post(settings.mc_friend_detail_path, {})

    async def search_by_name(self, name: str) -> dict[str, Any]:
        return await self.post("/user-search-friend", {"name_or_mail": name})

    async def search_by_id(self, user_id: str | int) -> dict[str, Any]:
        user_id = str(user_id)
        return await self.post("/user-search-friend", {"name_or_mail": user_id, "role_id": int(user_id)})

    async def self_detail(self) -> dict[str, Any]:
        detail = await self.post("/user-detail", {"role_id": int(self.user_id)})
        entity = detail.get("entity")
        if detail.get("code", 0) not in (0, 200) or not isinstance(entity, dict):
            return detail

        # /user-detail.level is the launcher level, not the PE growth level.
        warning = "游戏资料暂未同步，账号等级暂不显示。"
        try:
            public = await self.post(
                settings.mc_user_multi_detail_path,
                {"is_need_recharge_benefit": 0, "uids": [int(self.user_id)]},
            )
        except (httpx.HTTPError, RuntimeError):
            return {**detail, "profile_details_warning": warning}
        rows = public.get("entities")
        if public.get("code", 0) not in (0, 200) or not isinstance(rows, list):
            return {**detail, "profile_details_warning": warning}
        player = next(
            (
                row for row in rows
                if isinstance(row, dict)
                and str(row.get("id", row.get("uid", row.get("entity_id", "")))) == self.user_id
            ),
            None,
        )
        if player is None:
            return {**detail, "profile_details_warning": warning}
        fields = (
            "headImage", "headImageType", "frame_id", "pe_growth",
            "recharge_vip_level", "recharge_benefit_level",
        )
        return {**detail, "entity": {**entity, **{key: player[key] for key in fields if key in player}}}

    async def user_detail(self, target_id: str | int) -> dict[str, Any]:
        return await self.post("/user-detail/query/other", {"role_id": int(target_id)})

    async def online_status(self, payload: dict[str, Any]) -> dict[str, Any]:
        return await self.post("/user-online-status", payload)

    async def friend_count(self, payload: dict[str, Any] | None = None) -> dict[str, Any]:
        return await self.post("/user-friends-cnt", payload or {})

    async def friend_groups(self) -> dict[str, Any]:
        return await self.post("/friend-group/get_group", {})

    async def friend_group_relations(self) -> dict[str, Any]:
        return await self.post("/friend-group/get_group_relation", {})

    async def add_friend_group(self, payload: dict[str, Any]) -> dict[str, Any]:
        return await self.post("/friend-group/add_group", payload)

    async def edit_friend_group(self, payload: dict[str, Any]) -> dict[str, Any]:
        return await self.post("/friend-group/edit_group", payload)

    async def delete_friend_group(self, payload: dict[str, Any]) -> dict[str, Any]:
        return await self.post("/friend-group/del_group", payload)

    async def friend_applies(self, payload: dict[str, Any] | None = None) -> dict[str, Any]:
        return await self.post("/user-addme-friends/", payload or {})

    async def apply_friend(
        self,
        target_id: str | int,
        message: str = "",
        *,
        add_type: int | str = 0,
        apply_source: int | str = 0,
        add_ui: int | str = 0,
        in_game: bool = False,
    ) -> dict[str, Any]:
        target = str(target_id)
        # The client-side method accepts a friend/role id and builds these
        # fields. Extra aliases keep the wrapper compatible with observed
        # client versions while the upstream API is still being verified.
        payload: dict[str, Any] = {
            "fid": target,
            "target_role_id": target,
            "role_id": int(target) if target.isdigit() else target,
            "verify_msg": message,
            "add_type": add_type,
            "apply_source": apply_source,
            "add_ui": add_ui,
            "in_game": in_game,
        }
        return await self.post(settings.mc_friend_apply_path, payload)

    async def reply_friend_apply(
        self,
        target_id: str | int,
        agree: bool,
        payload: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        body = dict(payload or {})
        body.setdefault("fid", str(target_id))
        body.setdefault("target_role_id", str(target_id))
        body.setdefault("agree", bool(agree))
        return await self.post(settings.mc_friend_reply_path, body)

    async def change_friend_mark(
        self,
        target_id: str | int,
        mark: str,
        payload: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        body = dict(payload or {})
        body.setdefault("fid", str(target_id))
        body.setdefault("target_role_id", str(target_id))
        body.setdefault("role_id", int(target_id) if str(target_id).isdigit() else str(target_id))
        body.setdefault("mark", mark)
        return await self.post("/user-change-friend-mark", body)

    async def add_friend(self, target_id: str | int, message: str = "") -> dict[str, Any]:
        return await self.apply_friend(target_id, message)

    async def remove_friend(self, target_id: str | int, payload: dict[str, Any] | None = None) -> dict[str, Any]:
        body = dict(payload or {})
        body.setdefault("fid", str(target_id))
        body.setdefault("target_role_id", str(target_id))
        body.setdefault("role_id", int(target_id) if str(target_id).isdigit() else str(target_id))
        return await self.post(settings.mc_remove_friend_path, body)

    async def friend_playing_rooms(self, payload: dict[str, Any] | None = None) -> dict[str, Any]:
        return await self.post("/online-lobby-room/query/friend-playing-room", payload or {})

    async def friend_recent_games(self, payload: dict[str, Any] | None = None) -> dict[str, Any]:
        return await self.post("/friend-play-recent-game", payload or {})

    async def friend_offline_recommend_mods(self, payload: dict[str, Any] | None = None) -> dict[str, Any]:
        return await self.post("/friend-offline-recommend-mods", payload or {})

    # Room and lobby APIs --------------------------------------------------

    async def current_room(self, payload: dict[str, Any] | None = None) -> dict[str, Any]:
        return await self.post("/online-lobby-room/query/user-room", payload or {})

    async def recommended_rooms(self, payload: dict[str, Any] | None = None) -> dict[str, Any]:
        return await self.post("/online-lobby-room/query/get-recommend-list", payload or {})

    async def personalized_recommendations(self, payload: dict[str, Any] | None = None) -> dict[str, Any]:
        return await self.post("/online-lobby-room/query/get-personalise-recommend-list", payload or {})

    async def room_slogan_config(self, payload: dict[str, Any] | None = None) -> dict[str, Any]:
        return await self.post("/online-lobby-room/query/get-slogan-config", payload or {})

    async def search_rooms(self, payload: dict[str, Any]) -> dict[str, Any]:
        return await self.post("/online-lobby-room/query/search-by-name-v2", payload)

    async def room_waterfall(self, payload: dict[str, Any]) -> dict[str, Any]:
        return await self.post("/online-lobby-room/query/water-fall", payload)

    async def recent_room_resources(self, payload: dict[str, Any]) -> dict[str, Any]:
        return await self.post("/online-lobby-room/query/recent-play-res-list", payload)

    async def res_ids_by_type(self, payload: dict[str, Any]) -> dict[str, Any]:
        return await self.post("/online-lobby-room/query/list-res-id-by-type", payload)

    async def rooms_by_res_id(self, payload: dict[str, Any]) -> dict[str, Any]:
        return await self.post("/online-lobby-room/query/list-room-by-res-id", payload)

    async def room_multi_info(self, payload: dict[str, Any]) -> dict[str, Any]:
        return await self.post("/online-lobby-room/get-multi-room-info", payload)

    async def room_detail(self, room_id: str | int, payload: dict[str, Any] | None = None) -> dict[str, Any]:
        body = dict(payload or {})
        body.setdefault("name", str(room_id))
        result = await self.post_transfer(settings.mc_room_lookup_path, body)
        rooms = result.get("list")
        if isinstance(rooms, list) and rooms:
            room = dict(rooms[0]) if isinstance(rooms[0], dict) else {}
            room.setdefault("rid", room.get("rid", room_id))
            room.setdefault("room_id", room.get("rid"))
            room.setdefault("room_name", room.get("name"))
            room.setdefault("player_count", room.get("cnt"))
            room.setdefault("max_player_count", room.get("cap"))
            members = room.get("members") if isinstance(room.get("members"), list) else []
            return {**result, "entity": room, "members": members}
        return result

    async def room_members(self, room_id: str | int, payload: dict[str, Any] | None = None) -> dict[str, Any]:
        room = await self.room_detail(room_id, payload)
        entity = room.get("entity") if isinstance(room.get("entity"), dict) else {}
        member_ids = entity.get("members") if isinstance(entity.get("members"), list) else []
        if not member_ids:
            return {**room, "entity": {**entity, "members": []}, "members": []}
        details = await self.post(
            settings.mc_user_multi_detail_path,
            {"is_need_recharge_benefit": 0, "uids": member_ids},
        )
        entities = details.get("entities")
        if not isinstance(entities, list):
            entities = details.get("list") if isinstance(details.get("list"), list) else []
        return {**details, "entity": {**entity, "members": entities}, "members": entities}

    async def room_chat_group(self, room_id: str | int, payload: dict[str, Any] | None = None) -> dict[str, Any]:
        body = dict(payload or {})
        body.setdefault("room_id", str(room_id))
        return await self.post("/online-lobby-room/get-room-chat-group-id", body)

    async def create_room(self, payload: dict[str, Any]) -> dict[str, Any]:
        return await self.post("/online-lobby-room", payload)

    async def update_room(self, room_id: str | int, payload: dict[str, Any] | None = None) -> dict[str, Any]:
        body = dict(payload or {})
        body.setdefault("room_id", str(room_id))
        return await self.post("/online-lobby-room/update", body)

    async def enter_room(self, room_id: str | int, payload: dict[str, Any] | None = None) -> dict[str, Any]:
        body = dict(payload or {})
        body.setdefault("room_id", str(room_id))
        return await self.post("/online-lobby-room-enter/", body)

    async def leave_room(self, room_id: str | int, payload: dict[str, Any] | None = None) -> dict[str, Any]:
        body = dict(payload or {})
        body.setdefault("room_id", str(room_id))
        return await self.post("/online-lobby-room-enter/leave-room", body)

    async def kick_room_member(self, room_id: str | int, payload: dict[str, Any]) -> dict[str, Any]:
        body = dict(payload)
        body.setdefault("room_id", str(room_id))
        return await self.post("/online-lobby-member-kick", body)

    async def match_room(self, payload: dict[str, Any]) -> dict[str, Any]:
        return await self.post("/online-lobby-room-match", payload)

    async def lobby_collections(self, payload: dict[str, Any] | None = None) -> dict[str, Any]:
        return await self.post("/online-lobby-collection/get-list", payload or {})

    async def add_lobby_collection(self, payload: dict[str, Any]) -> dict[str, Any]:
        return await self.post("/online-lobby-collection", payload)

    async def delete_lobby_collection(self, payload: dict[str, Any]) -> dict[str, Any]:
        return await self.post("/online-lobby-collection/delete", payload)

    async def lobby_backups(self, payload: dict[str, Any] | None = None) -> dict[str, Any]:
        return await self.post("/online-lobby-backup/query/list-by-user", payload or {})

    async def create_lobby_backup(self, payload: dict[str, Any]) -> dict[str, Any]:
        return await self.post("/online-lobby-backup/create", payload)

    async def lobby_rank(self, payload: dict[str, Any] | None = None) -> dict[str, Any]:
        return await self.post("/online-lobby-rank", payload or {})

    async def lobby_rank_scores(self, payload: dict[str, Any]) -> dict[str, Any]:
        return await self.post("/online-lobby-rank/query/get-score-by-uids", payload)

    async def competitive_item(self, payload: dict[str, Any] | None = None) -> dict[str, Any]:
        return await self.post("/online-lobby-competitive/query/item", payload or {})

    async def search_lobby_resources(self, payload: dict[str, Any]) -> dict[str, Any]:
        return await self.post("/pe-item/query/search-lobby-res-by-keyword", payload)

    async def search_lobby_by_id_list(self, payload: dict[str, Any]) -> dict[str, Any]:
        return await self.post("/pe-item/query/search-lobby-by-id-list", payload)
