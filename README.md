<div align="center">
  <img src="frontend/public/minecraft-link.svg" width="112" height="112" alt="Minecraft-Link 图标" />
  <h1>Minecraft-Link</h1>
  <p>面向网易《我的世界》中国版的本地客户端 API 桥接器</p>
  <p>
    <a href="#功能">功能</a> ·
    <a href="#快速开始">快速开始</a> ·
    <a href="#登录方式">登录方式</a> ·
    <a href="#接口文档">接口文档</a> ·
    <a href="#开发与测试">开发与测试</a>
  </p>
  <p>
    <a href="https://github.com/coferkim/Minecraft-Link/blob/main/LICENSE">MIT License</a>
    · Python / FastAPI
    · Vue 3
  </p>
</div>

Minecraft-Link 将本机已登录的网易版 Minecraft 基岩版客户端会话连接到本地 API，并提供一个用于查看好友、玩家资料和联机房间的 Web 控制台。服务默认只监听本机地址，前端通过同源 `/api` 访问 FastAPI。

> 本项目为非官方社区项目，与网易、Microsoft 或 Mojang Studios 无隶属关系。上游接口为非公开接口，可能随客户端版本变化。请仅在自己的设备和获授权的账号上使用。

## 功能

| 模块 | 功能 |
| --- | --- |
| 本地访问验证 | 使用本地访问密钥建立控制台会话，并通过 JWT 保护 Minecraft API |
| 客户端登录 | 从本机已登录的发烧启动器尝试捕获 `sauth`，也可手动提交 `sauth` JSON；不要求在网页输入网易账号密码 |
| 好友与玩家 | 查看好友、在线状态和资料；搜索玩家、处理好友申请、添加好友及编辑备注 |
| 联机房间 | 查询好友正在玩的房间、按房间号查询详情，并查看房主、成员和玩家资料 |
| API 控制台 | 使用自定义接口目录查看请求参数、响应说明与示例 |
| 本地记录 | 在本机 SQLite 中保存必要的会话状态和操作记录 |

## 快速开始

### 环境要求

- Windows 10 或更新版本
- Python 3.13
- Node.js 20 或更新版本及 npm

### 安装

```powershell
git clone https://github.com/coferkim/Minecraft-Link.git
cd Minecraft-Link

py -3.13 -m venv .venv313
.\.venv313\Scripts\python.exe -m pip install -r backend\requirements.txt

Copy-Item .env.example .env
```

编辑 `.env`，为 `ACCESS_KEY` 和 `SECRET_KEY` 设置仅本机使用的值。可用下面的命令生成随机密钥：

```powershell
python -c "import secrets; print(secrets.token_urlsafe(48))"
```

然后双击 `start.cmd`，或在 PowerShell 中运行：

```powershell
.\start.ps1
```

启动脚本会启动 FastAPI 和 Vue 开发服务器，并打开控制台：

| 服务 | 地址 |
| --- | --- |
| Web 控制台 | http://127.0.0.1:5173 |
| FastAPI | http://127.0.0.1:8000 |
| 健康检查 | http://127.0.0.1:8000/healthz |

首次启动时脚本会安装前端 npm 依赖。Python 后端依赖需按上面的步骤预先安装。运行日志写入根目录 `logs/`。

## 登录方式

1. 在控制台输入本地访问密钥。
2. 启动并登录网易发烧游戏启动器，再在账号登录页尝试自动读取 `sauth`；也可以从可信的本地来源手动提交 `sauth` JSON。
3. 完成 Minecraft 会话认证后即可进入控制台。

自动捕获依赖本机 Windows 进程读取权限。若启动器以管理员身份运行，可能需要以相同权限启动服务。捕获工具不会读取网易账号密码；`sauth`、`sead` 和 JWT 都属于敏感会话凭据，不要分享、提交到 Git 或写入公开日志。

也可以单独运行捕获工具：

```powershell
Set-Location backend
..\.venv313\Scripts\python.exe tools\capture_sauth.py
```

## 接口文档

- [完整本地 API 文档](docs/api.md)
- [启动器认证与 sauth 来源说明](docs/launcher-auth.md)
- [OpenAPI 快照](docs/openapi.json)
- 登录后在控制台侧边栏打开“API 文档”查看接口目录。
- 服务运行时可访问 http://127.0.0.1:8000/docs 查看 FastAPI 生成的交互式文档。

接口按认证、好友与玩家、房间与大厅、原始上游调用等类别组织。除访问密钥验证接口外，Minecraft 接口需要在请求头中携带 `Authorization: Bearer <JWT>`。完整路径、参数和响应示例以 API 文档为准。

## 项目结构

```text
backend/
  app/api/          本地 API 路由
  app/core/         配置与本地鉴权
  app/services/     Minecraft 请求与 sauth 捕获
  app/db/           SQLite 存储
  tools/            独立命令行工具
  tests/            后端测试
frontend/
  src/components/   Vue 控制台与页面组件
  public/           图标等静态资源
  tests/            Playwright 浏览器测试
docs/               API 与认证流程文档
start.cmd           Windows 一键启动入口
start.ps1           服务检查与启动脚本
```

## 开发与测试

后端测试：

```powershell
Set-Location backend
..\.venv313\Scripts\python.exe -m pytest -q
```

前端构建与浏览器测试：

```powershell
Set-Location frontend
npm install
npx playwright install chromium
npm run build
npm run test:e2e
```

浏览器测试使用模拟接口数据，不会登录或修改真实 Minecraft 账号。真实登录及上游接口调用需要有效的本机客户端会话。

## 安全说明

- `.env`、本地数据库、运行日志、虚拟环境和依赖目录不会纳入版本控制。
- 示例配置中的密钥仅用于开发演示。部署或共享运行环境前，必须设置自己的 `ACCESS_KEY` 和 `SECRET_KEY`。
- 服务默认绑定 `127.0.0.1`，设计用途是本机访问；不要未经额外鉴权、TLS 和网络隔离就将服务暴露到公网。
- 玩家资料及上游响应可能包含个人信息。请遵守适用的法律、平台规则和账号授权范围。

## 反馈与许可

问题反馈与功能建议请提交到 [GitHub Issues](https://github.com/coferkim/Minecraft-Link/issues)。

本项目使用 [MIT License](LICENSE)。
