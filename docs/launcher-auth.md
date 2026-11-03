# 网易发烧游戏启动器登录链

本文记录本机 `FeverGamesInstaller.exe` 的启动器登录与 `sauth` 来源，作为自动捕获器的实现依据。这里只描述本机已登录会话的读取方式，不保存或重放账号密码。

本项目 Minecraft 社交、房间与大厅接口的完整清单见 [api.md](api.md)。

## 组件

```text
C:\Program Files\FeverGames\1.18.45.8\
├── FeverGamesInstaller.exe   启动器主进程
├── FeverGamesWeb.exe         CEF 页面进程
├── NtUniSdkBase.dll          UniSDK 登录/票据
├── NtUniSdkMpay.dll          mpay 登录
└── mpay.dll

C:\FeverGame\MCBedrock\
├── Minecraft.Windows.exe     游戏进程
├── NtUniSdkBase.dll
└── ...
```

## 启动器 API

从启动器日志和二进制字符串确认：

```text
base: https://loadingbaycn.webapp.163.com
POST /app/v1/login
GET  /app/v1/login/state?url=%2F
GET  /app/v1/login/ws_token
POST /app/v1/game_library/app/startup
POST /app/v1/game_library/ticket
```

`POST /app/v1/login` 成功响应包含：

```json
{
  "sid": "<启动器会话 token>",
  "id": "<用户短 ID>",
  "name": "<昵称>",
  "account_id": "<账号 ID>",
  "account_name": "<登录邮箱>",
  "redirect_url": "/"
}
```

后续请求使用：

```http
Authorization: Bearer <sid>
```

## 本机会话位置

启动器把登录态写入：

```text
HKEY_CURRENT_USER\SOFTWARE\FeverGames\FeverGamesInstaller\data
  token    REG_SZ    @ByteArray(<base64 JSON>)
  sdkuid   REG_SZ
```

`token` 解码后是启动器账号信息与 `sid`。该会话会过期，过期后需要重新在官方启动器登录。

## 游戏启动参数

启动器二进制包含：

```text
--unisdk-ticket=%1
--start_from_launcher=1
```

启动器将游戏票据交给 `Minecraft.Windows.exe`，启动器侧的 UniSDK 完成
`uni_sauth`，生成 `sauth`；游戏再使用该对象完成 `pe-authentication`，得到好友接口使用的 `sead` 与 `entity_id`。

## 为什么捕获启动器内存

`sauth` 不是启动器 `POST /app/v1/login` 的直接响应字段，而是启动器侧 UniSDK 认证链生成的对象。实际扫描确认完整对象位于 `FeverGamesInstaller.exe` 进程内存中；`Minecraft.Windows.exe` 可能只接收并使用它。与其复刻账号密码登录、短信/扫码校验和风控，读取本机已登录启动器进程中的完整对象更稳定。

自动捕获器查找以下字段：

```text
client_login_sn
udid
deviceid
sdkuid
sessionid
```

支持直接 JSON、`sauth_json` 外层包装，以及进程内存中的多组候选。捕获结果只保存在本机，随后交给本项目的 `POST /minecraft/login`。

本机实测扫描 `Minecraft.Windows.exe` 1 GiB 未命中，扫描 `FeverGamesInstaller.exe` 1 GiB 命中完整对象，包含
`client_login_sn`、`udid`、`deviceid`、`sdkuid`、`sessionid` 等字段。

## 使用条件

1. 官方启动器已登录。
2. 启动器保持运行。
3. 游戏可以打开；捕获器先扫描启动器，未命中时再回退到游戏进程。
4. 若启动器或游戏以管理员权限启动，捕获器也需要管理员权限。

## 相关实现

- `backend/app/services/sauth_capture.py`：Windows 进程枚举、内存读取、JSON 候选提取
- `backend/tools/capture_sauth.py`：命令行捕获入口
- `backend/app/api/minecraft.py`：`POST /minecraft/capture`
- `frontend/src/components/McLogin.vue`：登录窗口中的“抓取 sauth”按钮
