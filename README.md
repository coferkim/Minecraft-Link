<div align="center">
  <img src="frontend/public/minecraft-link.svg" width="96" height="96" alt="Minecraft-Link 图标" />
  <h1>Minecraft-Link</h1>
  <p>网易版 Minecraft 基岩版客户端接口桥接器</p>
</div>

Minecraft-Link 将本机已登录的 Minecraft 客户端会话连接到本地 API，提供好友、玩家资料和联机房间查询，并附带可视化控制台与接口文档。本项目为非官方社区项目，请只在自己的设备和获授权的账号上使用。

## 下载使用

从 [GitHub Releases](https://github.com/coferkim/Minecraft-Link/releases/latest) 下载 `Minecraft-Link-Windows-x64.zip`。普通使用不需要安装 Python、Node.js 或其他运行环境。

1. 将 ZIP 解压到有写入权限的文件夹，不要直接在压缩软件内运行。
2. 双击解压目录中的 `start.cmd`。启动器会在同一窗口显示实时日志，并自动打开 Web 控制台。
3. 保持命令行窗口开启以运行服务；关闭窗口或按 `Ctrl+C` 会停止服务。
4. 首次运行会在程序目录生成 `.env`、`data` 和 `logs`。访问密钥默认为 `ferkim`，签名密钥会随机生成并保存在 `.env` 中。

运行日志同时显示在命令行窗口，并写入 `logs/minecraft-link.log`。配置和数据保存在程序目录；升级前请备份 `.env` 和 `data`。

| 服务 | 地址 |
| --- | --- |
| Web 控制台 | http://127.0.0.1:8958 |
| API 基地址 | http://127.0.0.1:8959 |

默认只监听本机回环地址，不要将端口直接暴露到公网。

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

## 从源码运行

源码启动适用于开发和修改项目，需要本机安装 Python、Node.js 与 npm。Windows 用户可运行项目根目录的 `start.cmd`，脚本会准备依赖并启动服务。日常使用建议下载上方 Releases 的免环境压缩包。

## 配置与安全

- `.env` 保存本地访问密钥和服务配置；启动时生成的随机 `SECRET_KEY` 用于签发令牌，请勿删除或公开。
- 默认访问密钥是 `ferkim`。需要修改时，编辑 `.env` 中的 `ACCESS_KEY`，然后重启服务。
- Web 与 API 默认只监听 `127.0.0.1`，不应直接暴露到公网。
- 不要将 `.env`、sauth、sead 或访问令牌提交到版本库。

## 许可

[MIT License](LICENSE)
