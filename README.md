# Google Refresh Token 生成器

离线桌面工具，用于生成 Google Play Android Developer API 的 Refresh Token。无需部署服务器，本地运行，一键授权。

## 功能特点

- 纯本地运行，无需服务器部署
- 自动检测运行环境，支持**自动模式**（Python 服务转发）和**手动模式**（浏览器直接提交）
- 固定 Scope：`https://www.googleapis.com/auth/androidpublisher`
- 历史记录本地存储，方便回溯
- 支持 Windows / macOS（Intel + Apple Silicon）

## 下载

前往 [GitHub Releases](../../releases) 或 [Actions 构建产物](../../actions) 下载对应平台版本：

| 平台 | 文件名 | 说明 |
|------|--------|------|
| Windows | `GoogleRefreshToken-Windows` | 单个 `.exe` 文件，双击运行 |
| Mac Intel | `GoogleRefreshToken-Mac-Intel` | `.app.zip`，解压后双击运行 |
| Mac Apple Silicon (M1/M2/M3) | `GoogleRefreshToken-Mac-ARM` | `.app.zip`，解压后双击运行 |

## 使用方法

### 前置准备

1. **创建 Google Cloud 项目**：前往 [Google Cloud Console](https://console.cloud.google.com/) 创建项目

2. **启用 Android Publisher API**：进入 [API 库](https://console.cloud.google.com/apis/library)，搜索并启用 **Google Play Android Developer API**

3. **创建 OAuth 客户端**：
   - 进入 [凭据页面](https://console.cloud.google.com/apis/credentials)
   - 点击「创建凭据」→「OAuth 客户端 ID」
   - 应用类型选择 **Web应用**
   - 在「已获授权的重定向 URI」中添加：`http://localhost:19527/callback`
   - 记录下 `client_id` 和 `client_secret`

4. **发布状态改为正式**：在 Google Play Console 中将应用的发布状态改为正式（生产轨道）

### 操作步骤

1. 双击运行程序（Windows 为 `.exe`，Mac 为 `.app`）
2. 浏览器自动打开工具页面
3. 填入 `Client ID`、`Client Secret` 和 `重定向 URI`
4. 点击「生成授权链接」，在浏览器中使用**公司主体创建的 Google 账号**登录并授权
5. 授权成功后，工具自动获取 Refresh Token

### Mac 首次打开

由于应用未经 Apple 签名，首次打开需：

1. 按住 **Control** 点击 `.app` → 选择「打开」
2. 在弹窗中点击「打开」确认
3. 之后即可正常双击运行

## 项目结构

```
google-refresh-token-app/
├── .github/
│   └── workflows/
│       └── build.yml       # GitHub Actions CI/CD（Windows + Mac 双平台构建）
├── .gitignore
├── build.bat               # Windows 本地打包脚本
├── index.html              # 前端界面（双模式自动切换）
└── main.py                 # Python 本地服务器 + API 转发
```

## 本地开发与打包

### 运行（开发模式）

```bash
python main.py
```

浏览器会自动打开 `http://localhost:19527`。

### Windows 本地打包

双击 `build.bat`，或手动执行：

```bash
pip install pyinstaller
pyinstaller --onefile --windowed --name "GoogleRefreshToken" --add-data "index.html;." main.py
```

### Mac 本地打包

```bash
pip install pyinstaller
pyinstaller --onedir --windowed --name "GoogleRefreshToken" --add-data "index.html:." main.py
```

> Mac 的 `--add-data` 分隔符是 `:`，Windows 是 `;`。

## 技术说明

- **双模式设计**：页面加载时检测 ` /api/ping`，如 Python 服务可用则进入自动模式（通过 `/api/exchange` 在后端转发 token 请求，绕过 CORS），否则回退为手动模式（浏览器 form POST + 手动粘贴 JSON）
- **端口自动检测**：默认端口 19527，如被占用自动递增寻找可用端口（最多尝试 20 个），并通过 `/api/config` 告知前端实际端口
- **HTML 外置加载**：`main.py` 优先从同目录 `index.html` 文件加载页面，便于更新 UI 而无需重新打包

## 常见问题

**Q: 浏览器打开显示 403 错误？**
A: 端口被其他服务占用。程序会自动切换可用端口，请确认 Google Console 中配置的 redirect_uri 端口与页面提示一致。

**Q: Mac 提示「无法打开，因为它来自身份不明的开发者」？**
A: 按住 Control 点击 `.app` → 选择「打开」→ 确认即可。这是 macOS 对未签名应用的安全机制。

**Q: 授权后浏览器跳转页面报错？**
A: 这是正常的。授权成功后页面会显示「授权成功」，请回到工具页面查看结果。

**Q: 没有获取到 refresh_token？**
A: 确保 Google Console 中的 OAuth 客户端类型是「Web应用」，并且发布状态已改为正式。如果之前已授权过，需要再次授权（勾选 prompt=consent 强制重新授权）。
