# weijian-core

> 版本里程碑：`v0.3-mvp-webui-hotreload`

面向 NapCat（OneBot11）私聊场景的最小可运行框架：

- 私聊消息闭环（WS 入站、HTTP 回发）
- 笔记与提醒（SQLite）
- WebUI 管理页面（中文）
- 插件热重载（单插件/全量）
- 前端半插件化（动态菜单 + `template/iframe`）

---

## 1. 项目现状（当前能力）

### 1.1 消息与业务能力

- 私聊回显：未命中任何规则时回原文
- 笔记：
	- `记一下 xxx`
	- `我最近记了什么`
- 提醒：
	- 绝对/相对时间解析（如 `1分钟后提醒我 喝水`）
	- `我有哪些提醒`
	- `我今天有什么提醒`
	- `取消提醒 <id>`
	- `清空已完成提醒`
- 调度器：周期扫描 `pending` 提醒并触发

### 1.2 WebUI 与管理接口

- WebUI 地址：`http://127.0.0.1:8018/ui`
- 页面：
	- `GET /ui`（总览）
	- `GET /ui/notes`
	- `GET /ui/reminders`
	- `GET /ui/plugins`
- 管理接口（需 `X-Admin-Token`）：
	- `POST /admin/reload_plugins`
	- `POST /admin/reload_plugin/{name}`
	- `POST /admin/reminders/{reminder_id}/cancel`
	- `POST /admin/reminders/cleanup_done`

### 1.3 插件能力（后端 + 前端）

- 后端插件约定：`plugins/<plugin_name>/plugin.py`
- 插件入口：`register(registry)`
- 已支持：
	- `registry.register_rule(...)`
	- `registry.register_frontend_page(...)`
- 动态前端路由：`/ui/ext/{ext_path:path}`
- 页面展示模式：
	- `template`：插件目录内 HTML 片段
	- `iframe`：外部页面嵌入

---

## 2. 架构概览

- 主入口：`src/main.py`
- 配置：`src/core/config.py`（读取 `.env`）
- NapCat 连接：
	- WS 入站：`src/connectors/napcat/ws_server.py`
	- HTTP 回发：`src/connectors/napcat/http_client.py`
- 核心服务：`src/core/message_service.py`
- 存储：`src/core/storage.py`（SQLite）
- 插件管理：`src/core/plugin_manager.py`
- WebUI：`src/api/webui_app.py` + `src/api/templates/*.html`

---

## 3. 快速启动

### 3.1 安装依赖

- `pip install -r requirements.txt`

### 3.2 配置环境

复制 `.env.example` 为 `.env`，至少确认：

- `NAPCAT_HTTP_BASE`
- `NAPCAT_HTTP_TOKEN`
- `NAPCAT_WS_HOST` / `NAPCAT_WS_PORT`
- `WEBUI_HOST` / `WEBUI_PORT`
- `ADMIN_TOKEN`

### 3.3 启动

- `python src/main.py`

启动后访问：`http://127.0.0.1:8018/ui`

### 3.4 Docker 部署（推荐 NAS 场景）

当前仓库内 `docker-compose.yml` 已支持 `NapCat + weijian-core` 双服务一键部署。

#### A) 启动全套服务（Docker）

1. 确认 `.env` 中以下配置：
	- `PUID` / `PGID`
	- `NAPCAT_HTTP_TOKEN`（与 NapCat 一致）
	- `BOT_QQ`（用于生成 NapCat onebot 配置文件名）
2. （推荐）先自动生成 NapCat 配置：
	- `python tools/gen_napcat_config.py`
	- 如需覆盖：`python tools/gen_napcat_config.py --force`
3. 首次构建并启动：`docker compose up -d --build`
4. 检查状态：`docker compose ps`

说明：

- NapCat HTTP 对外映射为 `13001:3000`
- weijian WebUI 对外映射为 `8018:8018`
- weijian WS 对外映射为 `8095:8095`
- `docker compose config` 已可通过，当前 compose 配置可用。

自动配置脚本默认会写入：

- `napcat_data/config/onebot11_<BOT_QQ>.json`
- HTTP Server：`0.0.0.0:3000`
- WebSocket Client：`ws://weijian-core:8095/`
- token：取 `.env` 的 `NAPCAT_HTTP_TOKEN`

服务间通信在 compose 内部网络进行：

- `weijian-core -> napcat` 使用 `http://napcat:3000`

#### B) 插件热更新（Docker 内）

- `docker-compose.yml` 已挂载：
	- `./plugins:/app/plugins`
	- `./data:/app/data`
- 所以你在宿主机改 `plugins/`，容器内可立即看到
- 改完后重载插件：
	- WebUI：`/ui/plugins`
	- 或命令：`python tools/reload_plugin.py <plugin_name> --token <ADMIN_TOKEN>`

#### C) 插件开发工作流（推荐）

- NapCat 与 weijian-core 均在 Docker 常驻
- 开发机（VS Code）只修改 `plugins/<name>/`
- 通过 `/ui/plugins` 或 `tools/reload_plugin.py` 重载

> 这种方式最适合你当前目标：NAS 稳定运行框架，VS Code 新窗口专注插件开发。

---

## 4. 插件开发（推荐流程）

详细文档见：`docs/PLUGIN_DEV_GUIDE.md`

### 4.1 一键创建插件脚手架

- `python tools/new_plugin.py weather_helper`
- `python tools/new_plugin.py weather_helper --trigger "天气测试"`
- `python tools/new_plugin.py weather_helper --force`

会自动生成：

- `plugins/<name>/plugin.py`
- `plugins/<name>/web/index.html`
- `plugins/<name>/README.md`

### 4.2 开发与验证

1. 修改插件代码（`plugin.py` / `web/*.html`）
2. 进入 `/ui/plugins` 重载插件
   - 或命令：`python tools/reload_plugin.py <name> --token <ADMIN_TOKEN>`
3. 验证：
	 - 消息规则是否生效
	 - 菜单是否出现
	 - 页面 `/ui/ext/<name>` 是否可用

---

## 5. 运维与测试文档

- 插件开发指南：`docs/PLUGIN_DEV_GUIDE.md`
- 新聊天速查：`docs/PLUGIN_CHAT_BOOTSTRAP.md`
- 插件最小说明：`plugins/README.md`
- 运行排障：`RUNBOOK.md`
- 测试清单：`TEST_CHECKLIST.md`
- 变更记录：`CHANGELOG.md`

---

## 6. 说明

- 时间展示统一为 `Asia/Shanghai`
- 当前定位是“稳定内核 + 快速插件迭代”
- 适合部署到 NAS 后，日常在 VS Code 仅开发插件
