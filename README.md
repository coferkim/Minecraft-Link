<div align="center">
  <img src="frontend/public/minecraft-link.svg" width="96" height="96" alt="Minecraft-Link 图标" />
  <h1>Minecraft-Link</h1>
  <p>网易版 Minecraft 基岩版客户端接口桥接器</p>
</div>

Minecraft-Link 将本机已登录的 Minecraft 客户端会话连接到本地 API，提供好友、玩家资料和联机房间查询，并附带可视化控制台与接口文档。本项目为非官方社区项目，请只在自己的设备和获授权的账号上使用。

## 快速开始

### 启动

1. 安装 Python 和 Node.js，并确保命令行可以使用 `python`（或 `py`）、`node` 和 `npm`。
2. 在 Windows 上双击项目根目录的 `start.cmd`。
3. 首次启动会自动准备后端和前端依赖，在项目根目录创建 `.env`，并生成随机签名密钥；完成后会打开 Web 控制台。
4. 保持启动窗口开启，关闭该窗口会停止 Web 和 API 服务。

| 服务 | 地址 |
| --- | --- |
| Web 控制台 | http://127.0.0.1:8958 |
| API 基地址 | http://127.0.0.1:8959 |

### 登录 Minecraft 账号

1. 先通过发烧启动器登录网易版 Minecraft，并保持启动器或游戏进程运行。
2. 打开 Web 控制台，在访问密钥页面输入密钥。首次启动默认密钥为 `ferkim`；如已修改 `.env`，请使用 `ACCESS_KEY` 对应的值。
3. 选择“本机读取”，点击“读取登录凭据”。页面会显示捕获到的 sauth JSON；确认后点击“登录并进入控制台”。也可以选择“手动输入”粘贴 sauth JSON。
4. 登录成功后，可从侧边栏查看好友、搜索玩家、查询房间和查阅 API 文档。

sauth、sead 和访问令牌都属于敏感凭据。请勿分享、截图公开或提交到 Git。自动读取失败时，确认启动器仍处于登录状态；若启动器以管理员身份运行，请也以管理员身份启动 Minecraft-Link。

## API 文档

- [完整本地 API 文档](docs/api.md)：认证方式、参数、响应示例、好友和房间接口、原始上游调用及已知限制。
- [OpenAPI JSON](docs/openapi.json)：供 API 客户端或文档工具导入的接口定义。
- Web 控制台内也可在侧边栏打开“API 文档”，按分类搜索接口并查看参数、响应示例和 cURL 命令。

### 接口速览

除访问密钥验证外，`/minecraft/*` 接口使用 `Authorization: Bearer <access_token>`。`access_token` 通过 `POST /authorize/access-key` 获取；Minecraft 相关接口还需要先通过 `POST /minecraft/login` 建立客户端会话。

| 方法 | 路径 | 用途 |
| --- | --- | --- |
| `POST` | `/authorize/access-key` | 验证本地访问密钥并获取令牌 |
| `POST` | `/minecraft/capture` | 从本机启动器或游戏进程读取 sauth |
| `POST` | `/minecraft/login` | 使用 sauth 登录 Minecraft 会话 |
| `GET` | `/minecraft/session` | 查询当前会话状态 |
| `GET` | `/minecraft/profile` | 查询当前玩家资料 |
| `GET` | `/minecraft/friends` | 获取好友列表 |
| `GET` | `/minecraft/friends/search` | 按名字或 UID 搜索玩家 |
| `POST` | `/minecraft/friends/{target_id}/request` | 发送好友申请 |
| `GET` | `/minecraft/rooms/search` | 搜索联机房间 |
| `GET` | `/minecraft/rooms/{room_id}` | 查询房间详情 |
| `GET` | `/minecraft/rooms/{room_id}/members` | 查询房间成员 |
| `POST` | `/minecraft/upstream` | 调用白名单内尚未封装的上游接口 |
| `GET` | `/minecraft/endpoints` | 获取本地接口目录 |

### 获取访问令牌

```bash
curl -X POST http://127.0.0.1:8959/authorize/access-key \
  -H "Content-Type: application/json" \
  -d '{"access_key":"ferkim"}'
```

在请求中使用响应里的令牌：

```http
Authorization: Bearer <access_token>
```

好友、房间等接口的完整参数和调用示例见 [docs/api.md](docs/api.md)。

## 配置与安全

- `.env` 保存本地访问密钥和服务配置；启动时生成的随机 `SECRET_KEY` 用于签发令牌，请勿删除或公开。
- 默认访问密钥是 `ferkim`。需要修改时，编辑 `.env` 中的 `ACCESS_KEY`，然后重启服务。
- Web 与 API 默认只监听 `127.0.0.1`，不应直接暴露到公网。
- 不要将 `.env`、sauth、sead 或访问令牌提交到版本库。

## 许可

[MIT License](LICENSE)
