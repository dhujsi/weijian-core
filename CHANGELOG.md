# CHANGELOG

## v0.3-mvp-webui-hotreload (2026-03-25)

本次已完成：

- 新增最小 WebUI：
  - `GET /ui` Dashboard
  - `GET /ui/plugins`
  - `GET /ui/ext/notes`（插件页面）
  - `GET /ui/ext/reminders`（插件页面）
- 新增管理接口：
  - `POST /admin/reload_plugins`
  - `POST /admin/reload_plugin/{name}`
  - `POST /admin/reminders/{id}/cancel`
  - `POST /admin/reminders/cleanup_done`
- 新增最小插件热重载能力：
  - 插件目录约定 `plugins/<name>/plugin.py`
  - `register(registry)` 注册规则
  - `scan/load/reload/reload_all/list` 管理能力
- 维持现有私聊消息闭环与提醒调度能力不变。
- 时间展示继续使用 `Asia/Shanghai`。
