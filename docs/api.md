# Minecraft Link API 完整接口文档

本文档对应本项目的 FastAPI 后端。服务默认监听：

```text
http://127.0.0.1:8000
```

交互式文档：

```text
http://127.0.0.1:8000/docs
http://127.0.0.1:8000/openapi.json
```

仓库内的 OpenAPI 快照：

```text
docs/openapi.json
```

## 1. 认证模型

本服务有两层认证，彼此独立：

```text
访问密钥 -> 本机 JWT
JWT + sauth -> Minecraft 会话（sead + user_id）
```

### 1.1 访问密钥换取 JWT

```http
POST /authorize/access-key
Content-Type: application/json
```

```json
{
  "access_key": "YOUR_ACCESS_KEY"
}
```

成功响应：

```json
{
  "stage": "mc-login",
  "access_token": "<JWT>",
  "token_type": "bearer",
  "username": "guest",
  "message": "访问密钥验证成功"
}
```

之后所有 `/minecraft/*` 接口都需要：

```http
Authorization: Bearer <JWT>
```

### 1.2 sauth 登录 Minecraft

```http
POST /minecraft/login
Authorization: Bearer <JWT>
Content-Type: application/json
```

```json
{
  "sauth_json": {
    "client_login_sn": "<CLIENT_LOGIN_SN>",
    "udid": "<UDID>",
    "deviceid": "<DEVICE_ID>",
    "sdkuid": "<SDK_UID>",
    "sessionid": "<SESSION_ID>"
  }
}
```

服务端会完成以下链路并把 `sead` 与 `user_id` 保存到本机 SQLite：

```text
create_ticket
-> login/ticket
-> x19/sdk/uni_sauth
-> pe-authentication
-> sead + user_id
```

成功响应：

```json
{
  "statusCode": 200,
  "user_id": "<MINECRAFT_ENTITY_ID>",
  "sead": "<SEAD>",
  "username": "guest"
}
```

`sead` 是后续社交、房间和大厅请求的签名种子。不要把它写入日志、提交到 Git 或发送给第三方。

### 1.4 自动捕获 sauth

```http
POST /minecraft/capture
Authorization: Bearer <JWT>
Content-Type: application/json
```

请求体可以为空，或指定进程：

```json
{
  "pid": 1234,
  "process_name": "FeverGamesInstaller.exe",
  "max_bytes": 1073741824
}
```

返回：

```json
{
  "pid": 1234,
  "process_name": "FeverGamesInstaller.exe",
  "sauth": {
    "client_login_sn": "<CLIENT_LOGIN_SN>",
    "udid": "<UDID>",
    "deviceid": "<DEVICE_ID>",
    "sdkuid": "<SDK_UID>",
    "sessionid": "<SESSION_ID>"
  },
  "scanned_bytes": 1073741824,
  "matched_offsets": 1
}
```

捕获顺序：

```text
FeverGamesInstaller.exe
-> Minecraft.Windows.exe
-> FeverGamesWeb.exe
```

本机实测完整 `sauth` 位于 `FeverGamesInstaller.exe` 进程内存，启动器需要保持运行。若进程以管理员权限运行，本服务也需要管理员权限。

### 1.5 查询 Minecraft 会话

```http
GET /minecraft/session
Authorization: Bearer <JWT>
```

```json
{
  "authenticated": true,
  "user_id": "<MINECRAFT_ENTITY_ID>",
  "updated_at": "2026-11-03 08:00:00"
}
```

## 2. 本地接口总览

### 2.1 认证与账号

| 方法 | 路径 | 说明 |
| --- | --- | --- |
| `POST` | `/authorize/access-key` | 验证访问密钥并签发 JWT |
| `POST` | `/minecraft/login` | 提交 `sauth_json` 完成 Minecraft 认证 |
| `POST` | `/minecraft/capture` | 从本机进程捕获 `sauth` |
| `GET` | `/minecraft/session` | 查询本机 Minecraft 会话 |
| `GET` | `/minecraft/profile` | 当前账号资料 |

### 2.2 好友与社交

| 方法 | 路径 | 说明 | 验证状态 |
| --- | --- | --- | --- |
| `GET` | `/minecraft/friends` | 好友列表 | 已实测 |
| `GET` | `/minecraft/friends/detail` | 好友详情列表 | 已实测 |
| `GET` | `/minecraft/friends/search?name=...` | 按名字或邮箱搜索 | 已实测 |
| `GET` | `/minecraft/friends/search?user_id=...` | 按玩家编号搜索 | 已实测 |
| `GET` | `/minecraft/friends/{target_id}/detail` | 单个玩家公开资料 | 已实测 |
| `GET` | `/minecraft/friends/groups` | 好友分组 | 已实测 |
| `GET` | `/minecraft/friends/groups/relations` | 好友分组关系 | 已实测 |
| `POST` | `/minecraft/friends/groups` | 创建好友分组（原始 payload） | 路径已确认，未执行 |
| `PATCH` | `/minecraft/friends/groups/{group_id}` | 编辑好友分组（原始 payload） | 路径已确认，未执行 |
| `DELETE` | `/minecraft/friends/groups/{group_id}` | 删除好友分组（原始 payload） | 路径已确认，未执行 |
| `GET` | `/minecraft/friends/requests` | 收到的好友申请 | 已实测 |
| `POST` | `/minecraft/friends/{target_id}/request` | 发送好友申请 | 路径已确认，字段兼容层 |
| `POST` | `/minecraft/friends/requests/{target_id}/reply` | 同意/拒绝申请 | 路径已确认，字段兼容层 |
| `POST` | `/minecraft/friends/{target_id}/mark` | 修改好友备注 | 路径已确认，字段兼容层 |
| `POST` | `/minecraft/friends/online-status` | 批量查询在线状态 | 路径已确认，payload 透传 |
| `GET` | `/minecraft/friends/count` | 好友数量 | 路径已确认，返回可能为空 |
| `GET` | `/minecraft/friends/playing-rooms` | 好友正在玩的房间 | 已实测 |
| `GET` | `/minecraft/friends/recent-games` | 好友最近游戏 | 路径已发现 |
| `GET` | `/minecraft/friends/offline-recommend-mods` | 离线推荐 | 路径已发现 |
| `POST` | `/minecraft/friends/add` | 添加好友兼容入口 | 保留旧前端入口 |
| `DELETE` | `/minecraft/friends/{target_id}` | 删除好友 | 已切换到实际路径，字段兼容层 |

好友申请示例：

```http
POST /minecraft/friends/1234567890/request
Authorization: Bearer <JWT>
Content-Type: application/json
```

```json
{
  "message": "你好，一起玩吗？",
  "add_type": 0,
  "apply_source": 0,
  "add_ui": 0,
  "in_game": false
}
```

如果客户端版本使用不同的申请字段，可以直接传原始 payload：

```json
{
  "payload": {
    "fid": "1234567890",
    "target_role_id": "1234567890",
    "verify_msg": "你好"
  }
}
```

删除好友示例：

```http
DELETE /minecraft/friends/1234567890
Authorization: Bearer <JWT>
```

服务端会调用实际观测到的 `/user-del-friend/`，并同时放入 `fid`、`target_role_id` 与 `role_id` 兼容字段。删除属于写操作，文档和自动化测试不会对真实好友执行。

### 2.3 房间与大厅

| 方法 | 路径 | 说明 | 验证状态 |
| --- | --- | --- | --- |
| `GET` | `/minecraft/rooms/current` | 当前用户所在房间 | 已实测 |
| `GET` | `/minecraft/rooms/friends-playing` | 好友正在玩的房间 | 已实测 |
| `GET` | `/minecraft/rooms/recommended` | 推荐房间 | 已实测 |
| `GET` | `/minecraft/rooms/recommended/personalized` | 个性化推荐 | 已实测 |
| `GET` | `/minecraft/rooms/slogan-config` | 房间口号配置 | 已实测 |
| `GET` | `/minecraft/rooms/search?keyword=...` | 关键词搜索房间 | 已实测 |
| `POST` | `/minecraft/rooms/search` | 原始参数搜索房间 | 已实现 |
| `POST` | `/minecraft/rooms/waterfall` | 房间瀑布流 | 路径已确认，参数待补 |
| `POST` | `/minecraft/rooms/recent-resources` | 最近游玩资源 | 路径已确认，参数待补 |
| `POST` | `/minecraft/rooms/res-ids` | 按类型列出资源 ID | 已实测空查询 |
| `POST` | `/minecraft/rooms/by-res` | 按资源 ID 列出房间 | 已实测空查询 |
| `POST` | `/minecraft/rooms/multi-info` | 批量查询房间信息 | 路径已确认 |
| `GET` | `/minecraft/rooms/{room_id}` | 房间详情 | 已实测路径，错误房间返回 `12015` |
| `GET` | `/minecraft/rooms/{room_id}/members` | 房间成员 | 已实测路径，错误房间返回 `16` |
| `GET` | `/minecraft/rooms/{room_id}/chat-group` | 房间聊天群 ID | 路径已确认 |
| `POST` | `/minecraft/rooms` | 创建房间（原始 payload） | 路径已发现，未执行 |
| `PATCH` | `/minecraft/rooms/{room_id}` | 更新房间（原始 payload） | 路径已发现，未执行 |
| `POST` | `/minecraft/rooms/{room_id}/enter` | 进入房间（原始 payload） | 路径已发现，未执行 |
| `POST` | `/minecraft/rooms/{room_id}/leave` | 离开房间 | 路径已发现，未执行 |
| `POST` | `/minecraft/rooms/{room_id}/kick` | 踢出成员（原始 payload） | 路径已发现，未执行 |
| `POST` | `/minecraft/rooms/{room_id}/match` | 房间匹配（原始 payload） | 路径已发现，未执行 |
| `GET` | `/minecraft/lobby/collections` | 大厅收藏 | 已实测 |
| `POST` | `/minecraft/lobby/collections` | 添加大厅收藏 | 路径已发现，未执行 |
| `POST` | `/minecraft/lobby/collections/delete` | 删除大厅收藏 | 路径已发现，未执行 |
| `GET` | `/minecraft/lobby/backups` | 大厅备份列表 | 路径当前返回 404，保留透传 |
| `POST` | `/minecraft/lobby/backups` | 创建大厅备份 | 路径已发现，未执行 |
| `GET` | `/minecraft/lobby/rank` | 大厅排行 | 已实测，返回服务端密钥错误 |
| `POST` | `/minecraft/lobby/rank/scores` | 按 UID 查询分数 | 已实测，返回组件不存在 |
| `GET` | `/minecraft/lobby/competitive-item` | 竞技条目 | 已实测 |
| `POST` | `/minecraft/lobby/resources/search` | 搜索大厅资源 | 已实测 |
| `POST` | `/minecraft/lobby/resources/by-id` | 按 ID 查询大厅资源 | 路径已确认，参数待补 |

#### 当前房间

```http
GET /minecraft/rooms/current
Authorization: Bearer <JWT>
```

没有加入房间时，上游通常返回：

```json
{
  "code": 0,
  "message": "正常返回",
  "details": "",
  "entity": null
}
```

#### 搜索房间

```http
GET /minecraft/rooms/search?keyword=生存&page=1&size=20
Authorization: Bearer <JWT>
```

前端会把纯数字关键词当作房间号，直接调用
`GET /minecraft/rooms/{room_id}`；只有文本关键词才调用大厅搜索接口。

对应上游：

```text
POST /online-lobby-room/query/search-by-name-v2
```

搜索请求 payload：

```json
{
  "keyword": "生存",
  "page": 1,
  "size": 20
}
```

响应通常包含：

```json
{
  "code": 0,
  "message": "正常返回",
  "details": "",
  "entities": [],
  "total": 0
}
```

#### 房间详情与成员

```http
GET /minecraft/rooms/ROOM_ID
Authorization: Bearer <JWT>
```

```http
GET /minecraft/rooms/ROOM_ID/members
Authorization: Bearer <JWT>
```

房间详情使用 transfer 服务的按房间名查询接口：

```text
POST https://g79mcltransfer.minecraft.cn/room-with-name
body: {"name": "ROOM_ID"}
```

`room-with-name` 返回的 `list[0]` 包含 `rid`、`name`、`hid`、`cnt`、`cap`
和 `members`。其中 `hid` 是房主 UID，`members` 是成员 UID 数组。

成员接口会继续用这些 UID 调用：

```text
POST /user-else-detail-many
body: {"is_need_recharge_benefit": 0, "uids": [UID, ...]}
```

`uids` 需要是数组；传逗号拼接字符串只会返回第一个玩家。
`room_id` 建议按字符串传递，避免 19 位数字在 JavaScript 中丢失精度。

#### 创建、更新、进入、离开

这些接口属于写操作，客户端字段会随版本变化，因此本地接口接受原始 `payload`：

```http
POST /minecraft/rooms
Authorization: Bearer <JWT>
Content-Type: application/json
```

```json
{
  "payload": {
    "room_name": "我的房间",
    "room_type": 0,
    "room_second_type": 0,
    "max_player_count": 10,
    "slogan": "来和我一起玩吧！"
  }
}
```

```http
PATCH /minecraft/rooms/ROOM_ID
Authorization: Bearer <JWT>
Content-Type: application/json
```

```json
{
  "payload": {
    "room_name": "新房间名",
    "slogan": "新的口号"
  }
}
```

```http
POST /minecraft/rooms/ROOM_ID/enter
POST /minecraft/rooms/ROOM_ID/leave
```

进入房间的字段通常包含 `room_id`、`owner_id`、`server_id`、`room_type` 等；具体字段以当前客户端版本为准。服务端会自动补 `room_id`。

### 2.4 原始上游调用

```http
POST /minecraft/upstream
Authorization: Bearer <JWT>
Content-Type: application/json
```

```json
{
  "path": "/online-lobby-room/query/get-slogan-config",
  "payload": {}
}
```

该接口会：

1. 校验路径必须在白名单前缀内；
2. 使用当前 Minecraft `sead` 生成 `user-token`；
3. 只向配置的 `MC_API_BASE` 发送请求；
4. 原样返回上游 JSON。

允许的前缀：

```text
/user-
/friend-
/friend-group/
/online-lobby-
/pe/
/pe-item/
/message
/messages
/item/
/achievement/
/switch-main-city/
/get-recent-chat-msgs
/ngpush-send-item-push
/pe-client-js-class
/interconn/web/
```

该入口用于覆盖尚未封装成独立路由的客户端接口。它不接受完整 URL，避免把本机签名请求转发到任意外部主机。

### 2.5 接口目录

```http
GET /minecraft/endpoints
Authorization: Bearer <JWT>
```

返回本地接口目录、上游基地址和原始调用白名单。该接口适合前端动态展示能力，也可用于核对本文档与运行中版本是否一致。

## 3. 上游接口清单

### 3.1 已实测的好友接口

```text
POST /user-allfriends
POST /user-allfriends-with-detail
POST /user-search-friend
POST /user-detail
POST /user-detail/query/other
POST /friend-group/get_group
POST /friend-group/get_group_relation
```

请求头：

```http
user-token: <UserTokenCodec 生成>
user-id: <MINECRAFT_ENTITY_ID>
content-type: application/json
```

### 3.2 好友写操作与关系接口

以下路径来自运行中客户端的 Python 服务层字符串和 HTTP 路由表：

```text
POST /user-apply-friend/
POST /user-reply-friend/
POST /user-del-friend/
POST /user-change-friend-mark
POST /user-online-status
POST /user-addme-friends/
POST /friend-play-recent-game
POST /friend-offline-recommend-mods
POST /friend-ship/get-page-friends-with-sort
POST /friend-ship/get-friends-number
POST /friend-ship/get-together-recent-player
POST /friend-ship/intimacy-list
POST /friend-ship/intimacy-buildable
POST /friend-ship/intimacy-user-detail
POST /friend-ship/get-message-mute
POST /friend-ship/set-message-mute
```

这些接口的参数结构尚未全部逐字段实测。`/minecraft/friends/*` 提供了常用封装，其他接口可以通过 `/minecraft/upstream` 直接调用。

### 3.3 房间与大厅接口

运行中客户端出现的完整路径：

```text
POST /online-lobby-room/query/user-room
POST /online-lobby-room/query/friend-playing-room
POST /online-lobby-room/query/get-recommend-list
POST /online-lobby-room/query/get-personalise-recommend-list
POST /online-lobby-room/query/get-slogan-config
POST /online-lobby-room/query/list-res-id-by-type
POST /online-lobby-room/query/list-room-by-res-id
POST /online-lobby-room/query/recent-play-res-list
POST /online-lobby-room/query/search-by-name-v2
POST /online-lobby-room/query/water-fall
POST /room-with-name  (transfer: https://g79mcltransfer.minecraft.cn)
POST /user-else-detail-many
POST /online-lobby-room/get-multi-room-info
POST /online-lobby-room/get-room-chat-group-id
POST /online-lobby-room/update
POST /online-lobby-room
POST /online-lobby-room-enter/
POST /online-lobby-room-enter/leave-room
POST /online-lobby-room-match
POST /online-lobby-member-kick
POST /online-lobby-collection
POST /online-lobby-collection/get-list
POST /online-lobby-collection/delete
POST /online-lobby-backup/create
POST /online-lobby-backup/query/list-by-user
POST /online-lobby-competitive/query/item
POST /online-lobby-rank
POST /online-lobby-rank/query/get-score-by-uids
POST /pe/team/get-chat-group-id
POST /pe-item/query/search-lobby-res-by-keyword
POST /pe-item/query/search-lobby-by-id-list
```

### 3.4 启动器接口

启动器使用另一套基地址和 `sid`，不属于 Minecraft `sauth` 会话：

```text
base: https://loadingbaycn.webapp.163.com
POST /app/v1/login
GET  /app/v1/login/state
GET  /app/v1/login/ws_token
POST /app/v1/game_library/app/startup
POST /app/v1/game_library/ticket
```

启动器日志和二进制中还确认了：

```text
POST /app/v1/friend/request
POST /app/v1/friend/request/list
POST /app/v1/friend/request/approve
POST /app/v1/friend/request/reject
POST /app/v1/friend/list
POST /app/v1/friend/cancel
POST /app/v1/user/search
POST /app/v1/user/game_account
POST /app/v1/user/game_account/list
POST /app/v1/user/online_status
POST /app/v1/message_box/messages
POST /app/v1/message_box/unread
```

这些接口使用启动器 `Authorization: Bearer <sid>`，当前项目没有把它们暴露为本机路由，避免把启动器会话与 Minecraft 会话混用。启动器登录链详见 [launcher-auth.md](launcher-auth.md)。

## 4. 响应约定

上游接口通常返回以下结构：

```json
{
  "code": 0,
  "message": "正常返回",
  "details": "",
  "entity": {},
  "entities": [],
  "total": 0
}
```

字段说明：

| 字段 | 说明 |
| --- | --- |
| `code` | 上游业务状态码，`0` 通常表示成功 |
| `message` | 可读消息 |
| `details` | 调试或附加信息 |
| `entity` | 单对象结果 |
| `entities` | 列表结果 |
| `total` | 列表总数 |

常见业务码：

| code | 含义 |
| --- | --- |
| `0` | 成功 |
| `4` | 参数为空 |
| `10` | 请先登录 |
| `12` | 参数错误 |
| `13` | 操作失败 |
| `16` | 目标找不到 |
| `111` | 回应好友请求失败 |
| `112` | 删除好友请求失败 |
| `2100` | 操作过于频繁 |
| `12015` | 无法找到该房间 |

本服务对上游 HTTP 4xx/5xx 返回本地 `502`；对路径白名单错误返回本地 `400`；对缺少 Minecraft 会话返回本地 `401`。

## 5. 逆向结论与证据边界

### 5.1 sauth 来源

已确认：

```text
完整 sauth 位于 FeverGamesInstaller.exe 进程内存
Minecraft.Windows.exe 进程内存未命中
```

因此自动捕获器优先扫描启动器，再回退到游戏进程。该结论来自本机运行态内存扫描和实际登录验证。

### 5.2 好友接口

好友列表、好友详情、玩家搜索、玩家公开资料和好友分组已通过真实会话请求验证。`online_status` 字段在当前响应中为空，前端显示“未知”而不是猜测在线状态。

### 5.3 房间接口

游戏 UI 的 `/create-party`、`/invite-to-party` 和 `/party-modal/*` 是原生 bridge/facet 路由，不是 HTTP 路径。房间 HTTP 路径来自运行中 `Minecraft.Windows.exe` 的 Python 服务层字符串和请求路由表，随后通过真实会话对只读接口进行了探测：

```text
/online-lobby-room/query/user-room                  -> code 0
/online-lobby-room/query/friend-playing-room        -> code 0
/online-lobby-room/query/get-recommend-list         -> code 0
/online-lobby-room/query/get-personalise-recommend-list -> code 0
/online-lobby-room/query/get-slogan-config          -> code 0
/online-lobby-room/query/list-res-id-by-type        -> code 0
/online-lobby-room/query/list-room-by-res-id        -> code 0
/online-lobby-room/query/search-by-name-v2          -> code 0
https://g79mcltransfer.minecraft.cn/room-with-name   -> code 0（list[0] 含成员 UID）
/user-else-detail-many                              -> code 0（uids 传数组时返回完整成员资料）
```

`/online-lobby-room/get` 和 `/online-lobby-member/query/list-by-room-id` 在当前客户端版本里不能稳定按房间号返回数据，房间详情改用 transfer 服务的 `/room-with-name`。

写操作接口（创建、更新、进入、离开、踢人、匹配）没有在真实账号上执行，文档只标注路径和原始 payload 透传能力。

### 5.4 静态与运行态边界

`Minecraft.Windows.exe` 的静态字符串没有直接暴露这些完整 HTTP 路径；运行态内存中的 Python 服务层保留了路径和参数名。因此本文把“路径已发现”和“已实测”分开标注，不把未执行过的写接口描述为已验证。

## 6. 已知限制

1. 添加好友、回应申请、删除好友的字段在不同客户端版本中可能变化；本项目同时发送兼容字段，仍建议用 `/minecraft/upstream` 对照客户端实际请求。
2. 房间创建、更新、进入、离开、踢人和匹配接口使用原始 payload 透传，未对真实账号执行破坏性测试。
3. 上游可能返回 `2100 操作过于频繁`，不要高频轮询；前端应按需刷新。
4. `/online-lobby-status`、`/online-lobby-backup/query/list-by-user`、`/user-social-setting/get` 在本次会话中返回 404，未作为稳定接口承诺。
5. `/user-friends-cnt` 当前返回空响应；本地路由保留，但不应依赖固定 JSON 结构。
6. 本服务只应使用自己的账号数据。`sauth`、`sead`、JWT 和好友隐私数据不要提交到仓库或发送给第三方。

## 7. 开发与验证

```powershell
# 后端测试
.\.venv313\Scripts\python.exe -m pytest backend -q

# 前端构建
cd frontend
npm run build
```

当前测试覆盖：

- 访问密钥和 JWT；
- sauth 捕获端点；
- PE 认证编解码；
- 好友列表/详情路由；
- 房间路由与搜索 payload；
- 上游路径白名单；
- 接口目录。

真实好友和房间请求需要有效的本机 Minecraft 会话。测试不会对真实好友执行删除，也不会创建或进入真实房间。
