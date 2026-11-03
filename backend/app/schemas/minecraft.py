from __future__ import annotations

from typing import Any

from pydantic import BaseModel, Field


class UpstreamCallRequest(BaseModel):
    path: str = Field(min_length=1, max_length=240)
    payload: dict[str, Any] = Field(default_factory=dict)


class FriendActionRequest(BaseModel):
    target_id: str | int | None = None
    message: str = Field(default="", max_length=500)
    add_type: int | str = 0
    apply_source: int | str = 0
    add_ui: int | str = 0
    in_game: bool = False
    payload: dict[str, Any] | None = None


class FriendReplyRequest(BaseModel):
    target_id: str | int | None = None
    agree: bool
    payload: dict[str, Any] | None = None


class FriendMarkRequest(BaseModel):
    target_id: str | int
    mark: str = Field(default="", max_length=100)
    payload: dict[str, Any] | None = None


class RoomRawRequest(BaseModel):
    payload: dict[str, Any] = Field(default_factory=dict)


class RoomCreateRequest(RoomRawRequest):
    pass


class RoomUpdateRequest(RoomRawRequest):
    pass


class RoomEnterRequest(RoomRawRequest):
    pass


class RoomLeaveRequest(RoomRawRequest):
    pass


class RoomKickRequest(RoomRawRequest):
    target_id: str | int | None = None


class RoomSearchRequest(BaseModel):
    keyword: str = Field(default="", max_length=120)
    page: int = Field(default=1, ge=1)
    size: int = Field(default=10, ge=1, le=50)
    payload: dict[str, Any] | None = None


class RoomListRequest(BaseModel):
    page: int = Field(default=1, ge=1)
    size: int = Field(default=10, ge=1, le=50)
    payload: dict[str, Any] = Field(default_factory=dict)
