import asyncio
from typing import Any

import httpx
from fastapi import APIRouter, Depends, HTTPException, Query, status

from app.core.auth import require_api_auth
from app.core.config import settings
from app.db import storage
from app.schemas.auth import SauthCaptureRequest, SauthLogin
from app.schemas.minecraft import (
    FriendActionRequest,
    FriendMarkRequest,
    FriendReplyRequest,
    RoomCreateRequest,
    RoomEnterRequest,
    RoomKickRequest,
    RoomLeaveRequest,
    RoomListRequest,
    RoomRawRequest,
    RoomSearchRequest,
    RoomUpdateRequest,
    UpstreamCallRequest,
)
from app.services.minecraft import (
    ALLOWED_UPSTREAM_PREFIXES,
    MinecraftClient,
    UpstreamPathError,
)
from app.services.sauth_capture import capture_sauth
from app.utils.pe_auth import McAuthError, PeAuth


router = APIRouter(prefix="/minecraft", tags=["minecraft"])


ENDPOINT_CATALOG = [
    {"group": "auth", "method": "POST", "path": "/minecraft/login", "description": "提交 sauth 完成 Minecraft 认证"},
    {"group": "auth", "method": "POST", "path": "/minecraft/capture", "description": "从本机启动器或游戏进程捕获 sauth"},
    {"group": "auth", "method": "GET", "path": "/minecraft/session", "description": "查询本机 Minecraft 会话"},
    {"group": "profile", "method": "GET", "path": "/minecraft/profile", "description": "当前账号资料"},
    {"group": "friends", "method": "GET", "path": "/minecraft/friends", "description": "好友列表"},
    {"group": "friends", "method": "GET", "path": "/minecraft/friends/detail", "description": "好友详情列表"},
    {"group": "friends", "method": "GET", "path": "/minecraft/friends/search", "description": "按名字、邮箱或玩家编号搜索"},
    {"group": "friends", "method": "GET", "path": "/minecraft/friends/{target_id}/detail", "description": "单个玩家公开资料"},
    {"group": "friends", "method": "GET", "path": "/minecraft/friends/groups", "description": "好友分组"},
    {"group": "friends", "method": "GET", "path": "/minecraft/friends/groups/relations", "description": "好友分组关系"},
    {"group": "friends", "method": "POST", "path": "/minecraft/friends/groups", "description": "创建好友分组"},
    {"group": "friends", "method": "PATCH", "path": "/minecraft/friends/groups/{group_id}", "description": "编辑好友分组"},
    {"group": "friends", "method": "DELETE", "path": "/minecraft/friends/groups/{group_id}", "description": "删除好友分组"},
    {"group": "friends", "method": "GET", "path": "/minecraft/friends/requests", "description": "收到的好友申请"},
    {"group": "friends", "method": "POST", "path": "/minecraft/friends/{target_id}/request", "description": "发送好友申请"},
    {"group": "friends", "method": "POST", "path": "/minecraft/friends/requests/{target_id}/reply", "description": "同意或拒绝好友申请"},
    {"group": "friends", "method": "POST", "path": "/minecraft/friends/{target_id}/mark", "description": "修改好友备注"},
    {"group": "friends", "method": "POST", "path": "/minecraft/friends/online-status", "description": "批量查询在线状态"},
    {"group": "friends", "method": "GET", "path": "/minecraft/friends/playing-rooms", "description": "好友正在玩的房间"},
    {"group": "friends", "method": "GET", "path": "/minecraft/friends/recent-games", "description": "好友最近游戏"},
    {"group": "rooms", "method": "GET", "path": "/minecraft/rooms/current", "description": "当前用户所在房间"},
    {"group": "rooms", "method": "GET", "path": "/minecraft/rooms/friends-playing", "description": "好友正在玩的房间"},
    {"group": "rooms", "method": "GET", "path": "/minecraft/rooms/recommended", "description": "推荐房间"},
    {"group": "rooms", "method": "GET", "path": "/minecraft/rooms/recommended/personalized", "description": "个性化推荐房间"},
    {"group": "rooms", "method": "GET", "path": "/minecraft/rooms/slogan-config", "description": "房间口号配置"},
    {"group": "rooms", "method": "GET", "path": "/minecraft/rooms/search", "description": "按关键词搜索房间"},
    {"group": "rooms", "method": "POST", "path": "/minecraft/rooms/search", "description": "按原始参数搜索房间"},
    {"group": "rooms", "method": "POST", "path": "/minecraft/rooms/waterfall", "description": "房间瀑布流"},
    {"group": "rooms", "method": "POST", "path": "/minecraft/rooms/recent-resources", "description": "最近游玩的资源"},
    {"group": "rooms", "method": "POST", "path": "/minecraft/rooms/res-ids", "description": "按类型列出资源 ID"},
    {"group": "rooms", "method": "POST", "path": "/minecraft/rooms/by-res", "description": "按资源 ID 列出房间"},
    {"group": "rooms", "method": "POST", "path": "/minecraft/rooms/multi-info", "description": "批量查询房间信息"},
    {"group": "rooms", "method": "GET", "path": "/minecraft/rooms/{room_id}", "description": "房间详情"},
    {"group": "rooms", "method": "GET", "path": "/minecraft/rooms/{room_id}/members", "description": "房间成员（room-with-name + 批量玩家资料）"},
    {"group": "rooms", "method": "GET", "path": "/minecraft/rooms/{room_id}/chat-group", "description": "房间聊天群 ID"},
    {"group": "rooms", "method": "POST", "path": "/minecraft/rooms", "description": "创建房间（原始 payload）"},
    {"group": "rooms", "method": "PATCH", "path": "/minecraft/rooms/{room_id}", "description": "更新房间（原始 payload）"},
    {"group": "rooms", "method": "POST", "path": "/minecraft/rooms/{room_id}/enter", "description": "进入房间（原始 payload）"},
    {"group": "rooms", "method": "POST", "path": "/minecraft/rooms/{room_id}/leave", "description": "离开房间"},
    {"group": "rooms", "method": "POST", "path": "/minecraft/rooms/{room_id}/kick", "description": "踢出房间成员（原始 payload）"},
    {"group": "rooms", "method": "POST", "path": "/minecraft/rooms/{room_id}/match", "description": "房间匹配（原始 payload）"},
    {"group": "lobby", "method": "GET", "path": "/minecraft/lobby/collections", "description": "大厅收藏列表"},
    {"group": "lobby", "method": "POST", "path": "/minecraft/lobby/collections", "description": "添加大厅收藏"},
    {"group": "lobby", "method": "POST", "path": "/minecraft/lobby/collections/delete", "description": "删除大厅收藏"},
    {"group": "lobby", "method": "GET", "path": "/minecraft/lobby/backups", "description": "大厅备份列表"},
    {"group": "lobby", "method": "POST", "path": "/minecraft/lobby/backups", "description": "创建大厅备份"},
    {"group": "lobby", "method": "GET", "path": "/minecraft/lobby/rank", "description": "大厅排行"},
    {"group": "lobby", "method": "POST", "path": "/minecraft/lobby/rank/scores", "description": "按 UID 查询排行分数"},
    {"group": "lobby", "method": "GET", "path": "/minecraft/lobby/competitive-item", "description": "大厅竞技条目"},
    {"group": "lobby", "method": "POST", "path": "/minecraft/lobby/resources/search", "description": "搜索大厅资源"},
    {"group": "lobby", "method": "POST", "path": "/minecraft/lobby/resources/by-id", "description": "按 ID 批量查询大厅资源"},
    {"group": "raw", "method": "POST", "path": "/minecraft/upstream", "description": "白名单上游原始调用"},
    {"group": "meta", "method": "GET", "path": "/minecraft/endpoints", "description": "本服务接口目录"},
]


@router.post("/login")
async def minecraft_login(payload: SauthLogin, username: str = Depends(require_api_auth)) -> dict[str, Any]:
    pe_auth = PeAuth(payload.sauth_json)
    try:
        await pe_auth.auth()
        sead, user_id = pe_auth.get_sead_and_id()
    except (httpx.HTTPError, McAuthError, ValueError, KeyError) as exc:
        storage.log_action("mc_login_failed", {"username": username, "error": str(exc)})
        raise HTTPException(status.HTTP_400_BAD_REQUEST, f"Minecraft 登录失败: {exc}") from exc
    storage.save_token(user_id, sead, username)
    storage.log_action("mc_login", {"user_id": user_id, "username": username})
    return {"statusCode": 200, "user_id": user_id, "sead": sead, "username": username}


@router.get("/session")
async def minecraft_session(username: str = Depends(require_api_auth)):
    token = storage.get_token(username)
    return {
        "authenticated": bool(token),
        "user_id": token["user_id"] if token else None,
        "updated_at": token["updated_at"] if token else None,
    }


@router.post("/capture")
async def capture_local_sauth(
    payload: SauthCaptureRequest | None = None,
    username: str = Depends(require_api_auth),
) -> dict[str, Any]:
    request = payload or SauthCaptureRequest()
    try:
        result = await asyncio.to_thread(
            capture_sauth,
            request.pid,
            request.process_name,
            request.max_bytes,
        )
    except (OSError, RuntimeError) as exc:
        storage.log_action("capture_sauth_failed", {"username": username, "error": str(exc)})
        raise HTTPException(status.HTTP_400_BAD_REQUEST, str(exc)) from exc
    if result is None:
        raise HTTPException(
            status.HTTP_404_NOT_FOUND,
            "未找到发烧启动器或 Minecraft 进程，请先启动官方客户端并完成登录",
        )
    if not result.sauth:
        raise HTTPException(
            status.HTTP_404_NOT_FOUND,
            f"已扫描 {result.scanned_bytes / 1024 / 1024:.1f} MiB，未找到完整 sauth；"
            "请确认游戏已登录，必要时以管理员身份启动本服务",
        )
    storage.log_action(
        "capture_sauth",
        {
            "username": username,
            "pid": result.pid,
            "process_name": result.process_name,
            "scanned_bytes": result.scanned_bytes,
            "matched_offsets": result.matched_offsets,
        },
    )
    return {
        "pid": result.pid,
        "process_name": result.process_name,
        "sauth": result.sauth,
        "scanned_bytes": result.scanned_bytes,
        "matched_offsets": result.matched_offsets,
    }


def _client_for_user(username: str) -> MinecraftClient:
    token = storage.get_token(username)
    if not token:
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, "尚未登录 Minecraft 账号")
    return MinecraftClient(str(token["user_id"]), str(token["sead"]))


async def _invoke(operation: str, factory, *, username: str | None = None, action: str | None = None):
    try:
        result = await factory()
    except UpstreamPathError as exc:
        raise HTTPException(status.HTTP_400_BAD_REQUEST, str(exc)) from exc
    except ValueError as exc:
        raise HTTPException(status.HTTP_400_BAD_REQUEST, str(exc)) from exc
    except httpx.HTTPStatusError as exc:
        raise HTTPException(
            status.HTTP_502_BAD_GATEWAY,
            f"{operation}失败: 上游返回 HTTP {exc.response.status_code}",
        ) from exc
    except (httpx.HTTPError, RuntimeError) as exc:
        raise HTTPException(status.HTTP_502_BAD_GATEWAY, f"{operation}失败: {exc}") from exc
    if action and username:
        storage.log_action(action, {"username": username})
    return result


@router.get("/profile")
async def profile(username: str = Depends(require_api_auth)):
    client = _client_for_user(username)
    return await _invoke("获取账号资料", client.self_detail)


@router.get("/friends")
async def friends(username: str = Depends(require_api_auth)):
    client = _client_for_user(username)
    return await _invoke("获取好友", client.all_friends)


@router.get("/friends/detail")
async def friends_detail(username: str = Depends(require_api_auth)):
    client = _client_for_user(username)
    return await _invoke("获取好友详情", client.all_friends_detail)


@router.get("/friends/search")
async def search(name: str | None = None, user_id: str | None = None, username: str = Depends(require_api_auth)):
    if not name and not user_id:
        raise HTTPException(status.HTTP_400_BAD_REQUEST, "请输入名字/邮箱或玩家编号")
    client = _client_for_user(username)
    if user_id:
        return await _invoke("搜索玩家", lambda: client.search_by_id(user_id))
    return await _invoke("搜索玩家", lambda: client.search_by_name(name or ""))


@router.get("/friends/groups")
async def friend_groups(username: str = Depends(require_api_auth)):
    client = _client_for_user(username)
    return await _invoke("获取好友分组", client.friend_groups)


@router.get("/friends/groups/relations")
async def friend_group_relations(username: str = Depends(require_api_auth)):
    client = _client_for_user(username)
    return await _invoke("获取好友分组关系", client.friend_group_relations)


@router.post("/friends/groups")
async def add_friend_group(payload: RoomRawRequest, username: str = Depends(require_api_auth)):
    client = _client_for_user(username)
    return await _invoke(
        "创建好友分组",
        lambda: client.add_friend_group(payload.payload),
        username=username,
        action="add_friend_group",
    )


@router.patch("/friends/groups/{group_id}")
async def edit_friend_group(
    group_id: str,
    payload: RoomRawRequest,
    username: str = Depends(require_api_auth),
):
    client = _client_for_user(username)
    body = dict(payload.payload)
    body.setdefault("group_id", group_id)
    return await _invoke(
        "编辑好友分组",
        lambda: client.edit_friend_group(body),
        username=username,
        action="edit_friend_group",
    )


@router.delete("/friends/groups/{group_id}")
async def delete_friend_group(group_id: str, username: str = Depends(require_api_auth)):
    client = _client_for_user(username)
    return await _invoke(
        "删除好友分组",
        lambda: client.delete_friend_group({"group_id": group_id}),
        username=username,
        action="delete_friend_group",
    )


@router.get("/friends/requests")
async def friend_requests(username: str = Depends(require_api_auth)):
    client = _client_for_user(username)
    return await _invoke("获取好友申请", client.friend_applies)


@router.post("/friends/online-status")
async def friend_online_status(payload: dict[str, Any], username: str = Depends(require_api_auth)):
    client = _client_for_user(username)
    return await _invoke("查询在线状态", lambda: client.online_status(payload))


@router.get("/friends/count")
async def friend_count(username: str = Depends(require_api_auth)):
    client = _client_for_user(username)
    return await _invoke("查询好友数量", client.friend_count)


@router.get("/friends/playing-rooms")
async def friends_playing_rooms(username: str = Depends(require_api_auth)):
    client = _client_for_user(username)
    return await _invoke("获取好友房间", client.friend_playing_rooms)


@router.get("/friends/recent-games")
async def friends_recent_games(username: str = Depends(require_api_auth)):
    client = _client_for_user(username)
    return await _invoke("获取好友最近游戏", client.friend_recent_games)


@router.get("/friends/offline-recommend-mods")
async def friends_offline_recommend_mods(username: str = Depends(require_api_auth)):
    client = _client_for_user(username)
    return await _invoke("获取离线推荐", client.friend_offline_recommend_mods)


@router.get("/friends/{target_id}/detail")
async def friend_detail(target_id: str, username: str = Depends(require_api_auth)):
    client = _client_for_user(username)
    return await _invoke("获取玩家资料", lambda: client.user_detail(target_id))


@router.post("/friends/{target_id}/request")
async def request_friend(
    target_id: str,
    payload: FriendActionRequest | None = None,
    username: str = Depends(require_api_auth),
):
    request = payload or FriendActionRequest()
    resolved_target = request.target_id or target_id
    client = _client_for_user(username)
    if request.payload:
        return await _invoke(
            "发送好友申请",
            lambda: client.upstream(settings.mc_friend_apply_path, request.payload or {}),
            username=username,
            action="friend_request",
        )
    return await _invoke(
        "发送好友申请",
        lambda: client.apply_friend(
            resolved_target,
            request.message,
            add_type=request.add_type,
            apply_source=request.apply_source,
            add_ui=request.add_ui,
            in_game=request.in_game,
        ),
        username=username,
        action="friend_request",
    )


@router.post("/friends/requests/{target_id}/reply")
async def reply_friend_request(
    target_id: str,
    payload: FriendReplyRequest,
    username: str = Depends(require_api_auth),
):
    client = _client_for_user(username)
    return await _invoke(
        "回应好友申请",
        lambda: client.reply_friend_apply(target_id, payload.agree, payload.payload),
        username=username,
        action="friend_reply",
    )


@router.post("/friends/{target_id}/mark")
async def mark_friend(
    target_id: str,
    payload: FriendMarkRequest,
    username: str = Depends(require_api_auth),
):
    client = _client_for_user(username)
    return await _invoke(
        "修改好友备注",
        lambda: client.change_friend_mark(target_id, payload.mark, payload.payload),
        username=username,
        action="friend_mark",
    )


@router.post("/friends/add")
async def add_friend(payload: FriendActionRequest, username: str = Depends(require_api_auth)):
    if payload.target_id is None:
        raise HTTPException(status.HTTP_400_BAD_REQUEST, "缺少 target_id")
    client = _client_for_user(username)
    if payload.payload:
        return await _invoke(
            "添加好友",
            lambda: client.upstream(settings.mc_friend_apply_path, payload.payload or {}),
            username=username,
            action="add_friend",
        )
    return await _invoke(
        "添加好友",
        lambda: client.apply_friend(
            payload.target_id,
            payload.message,
            add_type=payload.add_type,
            apply_source=payload.apply_source,
            add_ui=payload.add_ui,
            in_game=payload.in_game,
        ),
        username=username,
        action="add_friend",
    )


@router.delete("/friends/{target_id}")
async def remove_friend(target_id: str, username: str = Depends(require_api_auth)):
    client = _client_for_user(username)
    return await _invoke(
        "删除好友",
        lambda: client.remove_friend(target_id),
        username=username,
        action="remove_friend",
    )


# Room and lobby APIs ------------------------------------------------------


@router.get("/rooms/current")
async def current_room(username: str = Depends(require_api_auth)):
    client = _client_for_user(username)
    return await _invoke("获取当前房间", client.current_room)


@router.get("/rooms/friends-playing")
async def room_friends_playing(username: str = Depends(require_api_auth)):
    client = _client_for_user(username)
    return await _invoke("获取好友房间", client.friend_playing_rooms)


@router.get("/rooms/recommended")
async def recommended_rooms(username: str = Depends(require_api_auth)):
    client = _client_for_user(username)
    return await _invoke("获取推荐房间", client.recommended_rooms)


@router.get("/rooms/recommended/personalized")
async def personalized_rooms(username: str = Depends(require_api_auth)):
    client = _client_for_user(username)
    return await _invoke("获取个性化推荐", client.personalized_recommendations)


@router.get("/rooms/slogan-config")
async def room_slogan_config(username: str = Depends(require_api_auth)):
    client = _client_for_user(username)
    return await _invoke("获取房间口号配置", client.room_slogan_config)


@router.get("/rooms/search")
async def search_rooms(
    keyword: str = "",
    page: int = Query(1, ge=1),
    size: int = Query(10, ge=1, le=50),
    username: str = Depends(require_api_auth),
):
    client = _client_for_user(username)
    payload = {"keyword": keyword, "page": page, "size": size}
    return await _invoke("搜索房间", lambda: client.search_rooms(payload))


@router.post("/rooms/search")
async def search_rooms_raw(payload: RoomSearchRequest, username: str = Depends(require_api_auth)):
    client = _client_for_user(username)
    body = dict(payload.payload or {})
    body.setdefault("keyword", payload.keyword)
    body.setdefault("page", payload.page)
    body.setdefault("size", payload.size)
    return await _invoke("搜索房间", lambda: client.search_rooms(body))


@router.post("/rooms/waterfall")
async def room_waterfall(payload: RoomListRequest, username: str = Depends(require_api_auth)):
    client = _client_for_user(username)
    body = dict(payload.payload)
    body.setdefault("page", payload.page)
    body.setdefault("size", payload.size)
    return await _invoke("获取房间瀑布流", lambda: client.room_waterfall(body))


@router.post("/rooms/recent-resources")
async def recent_room_resources(payload: RoomListRequest, username: str = Depends(require_api_auth)):
    client = _client_for_user(username)
    body = dict(payload.payload)
    body.setdefault("page", payload.page)
    body.setdefault("size", payload.size)
    return await _invoke("获取最近游玩资源", lambda: client.recent_room_resources(body))


@router.post("/rooms/res-ids")
async def room_res_ids(payload: RoomRawRequest, username: str = Depends(require_api_auth)):
    client = _client_for_user(username)
    return await _invoke("获取资源 ID", lambda: client.res_ids_by_type(payload.payload))


@router.post("/rooms/by-res")
async def rooms_by_res(payload: RoomRawRequest, username: str = Depends(require_api_auth)):
    client = _client_for_user(username)
    return await _invoke("按资源查询房间", lambda: client.rooms_by_res_id(payload.payload))


@router.post("/rooms/multi-info")
async def room_multi_info(payload: RoomRawRequest, username: str = Depends(require_api_auth)):
    client = _client_for_user(username)
    return await _invoke("批量查询房间", lambda: client.room_multi_info(payload.payload))


@router.post("/rooms")
async def create_room(payload: RoomCreateRequest, username: str = Depends(require_api_auth)):
    client = _client_for_user(username)
    return await _invoke(
        "创建房间",
        lambda: client.create_room(payload.payload),
        username=username,
        action="create_room",
    )


@router.get("/rooms/{room_id}")
async def room_detail(room_id: str, username: str = Depends(require_api_auth)):
    client = _client_for_user(username)
    return await _invoke("获取房间详情", lambda: client.room_detail(room_id))


@router.get("/rooms/{room_id}/members")
async def room_members(room_id: str, username: str = Depends(require_api_auth)):
    client = _client_for_user(username)
    return await _invoke("获取房间成员", lambda: client.room_members(room_id))


@router.get("/rooms/{room_id}/chat-group")
async def room_chat_group(room_id: str, username: str = Depends(require_api_auth)):
    client = _client_for_user(username)
    return await _invoke("获取房间聊天群", lambda: client.room_chat_group(room_id))


@router.patch("/rooms/{room_id}")
async def update_room(room_id: str, payload: RoomUpdateRequest, username: str = Depends(require_api_auth)):
    client = _client_for_user(username)
    return await _invoke(
        "更新房间",
        lambda: client.update_room(room_id, payload.payload),
        username=username,
        action="update_room",
    )


@router.post("/rooms/{room_id}/enter")
async def enter_room(room_id: str, payload: RoomEnterRequest, username: str = Depends(require_api_auth)):
    client = _client_for_user(username)
    return await _invoke(
        "进入房间",
        lambda: client.enter_room(room_id, payload.payload),
        username=username,
        action="enter_room",
    )


@router.post("/rooms/{room_id}/leave")
async def leave_room(room_id: str, payload: RoomLeaveRequest | None = None, username: str = Depends(require_api_auth)):
    client = _client_for_user(username)
    body = payload.payload if payload else {}
    return await _invoke(
        "离开房间",
        lambda: client.leave_room(room_id, body),
        username=username,
        action="leave_room",
    )


@router.post("/rooms/{room_id}/kick")
async def kick_room_member(room_id: str, payload: RoomKickRequest, username: str = Depends(require_api_auth)):
    client = _client_for_user(username)
    body = dict(payload.payload)
    if payload.target_id is not None:
        body.setdefault("target_role_id", str(payload.target_id))
    return await _invoke(
        "踢出房间成员",
        lambda: client.kick_room_member(room_id, body),
        username=username,
        action="kick_room_member",
    )


@router.post("/rooms/{room_id}/match")
async def match_room(room_id: str, payload: RoomRawRequest, username: str = Depends(require_api_auth)):
    client = _client_for_user(username)
    body = dict(payload.payload)
    body.setdefault("room_id", room_id)
    return await _invoke("匹配房间", lambda: client.match_room(body), username=username, action="match_room")


# Lobby APIs ---------------------------------------------------------------


@router.get("/lobby/collections")
async def lobby_collections(username: str = Depends(require_api_auth)):
    client = _client_for_user(username)
    return await _invoke("获取大厅收藏", client.lobby_collections)


@router.post("/lobby/collections")
async def add_lobby_collection(payload: RoomRawRequest, username: str = Depends(require_api_auth)):
    client = _client_for_user(username)
    return await _invoke(
        "添加大厅收藏",
        lambda: client.add_lobby_collection(payload.payload),
        username=username,
        action="add_lobby_collection",
    )


@router.post("/lobby/collections/delete")
async def delete_lobby_collection(payload: RoomRawRequest, username: str = Depends(require_api_auth)):
    client = _client_for_user(username)
    return await _invoke(
        "删除大厅收藏",
        lambda: client.delete_lobby_collection(payload.payload),
        username=username,
        action="delete_lobby_collection",
    )


@router.get("/lobby/backups")
async def lobby_backups(username: str = Depends(require_api_auth)):
    client = _client_for_user(username)
    return await _invoke("获取大厅备份", client.lobby_backups)


@router.post("/lobby/backups")
async def create_lobby_backup(payload: RoomRawRequest, username: str = Depends(require_api_auth)):
    client = _client_for_user(username)
    return await _invoke(
        "创建大厅备份",
        lambda: client.create_lobby_backup(payload.payload),
        username=username,
        action="create_lobby_backup",
    )


@router.get("/lobby/rank")
async def lobby_rank(username: str = Depends(require_api_auth)):
    client = _client_for_user(username)
    return await _invoke("获取大厅排行", client.lobby_rank)


@router.post("/lobby/rank/scores")
async def lobby_rank_scores(payload: RoomRawRequest, username: str = Depends(require_api_auth)):
    client = _client_for_user(username)
    return await _invoke("查询排行分数", lambda: client.lobby_rank_scores(payload.payload))


@router.get("/lobby/competitive-item")
async def competitive_item(username: str = Depends(require_api_auth)):
    client = _client_for_user(username)
    return await _invoke("获取竞技条目", client.competitive_item)


@router.post("/lobby/resources/search")
async def search_lobby_resources(payload: RoomRawRequest, username: str = Depends(require_api_auth)):
    client = _client_for_user(username)
    return await _invoke("搜索大厅资源", lambda: client.search_lobby_resources(payload.payload))


@router.post("/lobby/resources/by-id")
async def search_lobby_by_id(payload: RoomRawRequest, username: str = Depends(require_api_auth)):
    client = _client_for_user(username)
    return await _invoke("查询大厅资源", lambda: client.search_lobby_by_id_list(payload.payload))


@router.post("/upstream")
async def upstream(payload: UpstreamCallRequest, username: str = Depends(require_api_auth)):
    client = _client_for_user(username)
    return await _invoke(
        "调用上游接口",
        lambda: client.upstream(payload.path, payload.payload),
        username=username,
        action="upstream_call",
    )


@router.get("/endpoints")
async def endpoints(username: str = Depends(require_api_auth)):
    return {
        "upstream_base": settings.mc_api_base,
        "allowed_prefixes": list(ALLOWED_UPSTREAM_PREFIXES),
        "local_endpoints": ENDPOINT_CATALOG,
        "raw_call": {
            "method": "POST",
            "path": "/minecraft/upstream",
            "body": {"path": "/user-allfriends", "payload": {}},
        },
    }
