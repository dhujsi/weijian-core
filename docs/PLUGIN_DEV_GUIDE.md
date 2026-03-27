# weijian 插件开发文档

> 面向目标：框架部署到 NAS 后，日常开发只需在 VS Code 新开窗口写插件。

## 1. 总览

当前项目已支持：

- 后端插件热重载（单插件 / 全量）
- 插件消息规则注册（命令匹配、业务逻辑）
- 插件后台调度任务注册（如提醒轮询）
- 前端半插件化（插件可注册菜单与页面扩展点）

核心能力入口：

- 插件目录：`plugins/<plugin_name>/plugin.py`
- 插件管理页：`/ui/plugins`
- 管理接口：
  - `POST /admin/reload_plugin/{name}`
  - `POST /admin/reload_plugins`
- 插件前端动态路由：`/ui/ext/{ext_path:path}`

---

## 2. 目录规范

每个插件一个目录：

```text
plugins/
  demo_echo/
    plugin.py
    web/
      demo_echo.html
```

最小必需文件：

- `plugin.py`
  - 必须提供 `register(registry)` 函数

推荐可选文件：

- `web/*.html`
  - 前端 `template` 模式时的页面片段

---

## 3. 插件最小示例

```python
from __future__ import annotations

__version__ = "0.1.0"


def register(registry) -> None:
    async def on_demo(service, user_id: int, text: str) -> bool:
        if text.strip() != "插件测试":
            return False
        await service._reply(user_id, "[demo] 命中")
        return True

    registry.register_rule("demo_rule", on_demo)
```

说明：

- 命中后返回 `True`：停止后续规则匹配
- 未命中返回 `False`：继续后续规则

---

## 4. `registry` API（当前版本）

### 4.1 `register_rule(rule_name, handler)`

注册消息处理规则。

- `rule_name: str` 规则名（插件内建议唯一）
- `handler` 建议签名：
  - `handler(service, user_id: int, text: str) -> bool | Awaitable[bool]`

`service` 为 `MessageService` 实例，常用能力：

- `await service._reply(user_id, message)`：回消息

> 建议仅使用约定能力，避免依赖内部未稳定实现。

### 4.2 `register_frontend_page(...)`

注册前端扩展点（半插件化）。

```python
registry.register_frontend_page(
    title="Demo Echo",
    route="/ui/ext/demo_echo",
    view_type="template",   # template 或 iframe
    source="web/demo_echo.html",
    order=10,
)
```

参数说明：

- `title`: 菜单显示名
- `route`: 页面路由，建议 `/ui/ext/<plugin_name>`
- `view_type`:
  - `template`：读取插件目录内 HTML
  - `iframe`：嵌入外部页面
- `source`:
  - `template`：插件目录相对路径，如 `web/page.html`
  - `iframe`：完整 URL
- `order`: 菜单排序，越小越靠前

### 4.3 `register_scheduler(scheduler_name, handler)`

注册插件后台调度任务。

- `scheduler_name: str` 调度器名称（插件内建议唯一）
- `handler` 建议签名：
  - `handler(service) -> None | Awaitable[None]`

说明：

- 调度器会在服务启动时与 Web/WS 一起运行。
- 插件重载时会先卸载旧调度器，再注册新调度器。
- 若调度器内部使用循环，需自行控制间隔（例如 `await asyncio.sleep(10)`）。

---

## 5. 前端扩展模式建议

### 模式 A：`template`（推荐起步）

适合：管理页、小工具页、配置页。

优点：

- 实现快
- 无独立前端构建流程
- 与主 UI 样式可快速统一

注意：

- `source` 必须在插件目录内（框架已做路径边界校验）

### 模式 B：`iframe`

适合：已有独立前端应用、复杂交互页面。

优点：

- 前后端彻底解耦
- 插件可独立部署升级

注意：

- 需要考虑 iframe 页面可达性、鉴权和跨域策略

---

## 6. 热重载机制

### 6.1 首次加载（load）

- 扫描 `plugins/*/plugin.py`
- 执行 `register(registry)`
- 注册规则与前端扩展点

### 6.2 重载（reload）

- 卸载旧规则与旧前端扩展点
- 重新导入插件模块并注册
- 失败时尝试回滚旧版本（保持服务可用）

### 6.3 页面操作

在 `/ui/plugins`：

- 可重载单个插件
- 可重载全部插件

---

## 7. NAS 开发工作流（推荐）

目标：框架稳定运行，插件独立迭代。

1. NAS 上常驻运行主服务（`src/main.py`）
2. 本地/远程 VS Code 新开窗口，仅打开插件目录
3. 修改 `plugins/<name>/plugin.py` 或 `web/*.html`
4. 在 `/ui/plugins` 点击重载（或调用 admin 接口）
5. 立即验证功能

建议：

- 每个插件一个独立目录、独立版本号（`__version__`）
- 每次改动都通过“单插件重载”验证
- 稳定后再做“全量重载”回归

### 7.0 新聊天窗口最短路径（只看这段即可开工）

1. 创建插件骨架：`python tools/new_plugin.py my_plugin`
2. 修改：`plugins/my_plugin/plugin.py`
3. 如有页面，修改：`plugins/my_plugin/web/index.html`
4. 打开 `/ui/plugins`，重载 `my_plugin`
5. 验证：
  - 发送测试命令是否命中
  - `/ui/ext/my_plugin` 是否可访问

> 完成以上 5 步，即可在新聊天窗口独立进行插件迭代。

### 7.1 一键创建插件脚手架（推荐）

项目已提供脚手架脚本：`tools/new_plugin.py`

示例：

- 创建插件：`python tools/new_plugin.py weather_helper`
- 指定测试触发词：`python tools/new_plugin.py weather_helper --trigger "天气测试"`
- 已存在目录时覆盖：`python tools/new_plugin.py weather_helper --force`

脚本会自动生成：

- `plugins/<name>/plugin.py`
- `plugins/<name>/web/index.html`
- `plugins/<name>/README.md`

生成后只需：

1. 修改 `plugin.py` 业务逻辑
2. 打开 `/ui/plugins` 重载插件
3. 访问 `/ui/ext/<name>` 验证页面

### 7.2 命令行重载插件（调试提效）

项目提供：`tools/reload_plugin.py`

- 重载单插件：`python tools/reload_plugin.py demo_echo --token <ADMIN_TOKEN>`
- 重载全部插件：`python tools/reload_plugin.py all --token <ADMIN_TOKEN>`

可选参数：

- `--base`：管理接口地址，默认 `http://127.0.0.1:8018`
- `--token`：`X-Admin-Token`

在 Docker 部署下，只要 WebUI 端口映射可访问，也可直接用该脚本调试。

---

## 8. 配置与鉴权

关键环境变量见 `.env.example`：

- `WEBUI_HOST` / `WEBUI_PORT`
- `ADMIN_TOKEN`
- `NAPCAT_HTTP_BASE` / `NAPCAT_HTTP_TOKEN`

管理接口使用请求头：

- `X-Admin-Token: <ADMIN_TOKEN>`

未通过鉴权返回 `401`。

---

## 9. 常见问题

### 9.1 插件显示 `error`

排查：

- `plugin.py` 是否语法错误
- 是否缺少 `register(registry)`
- 依赖是否可用

### 9.2 命令无响应

排查：

- 规则是否返回 `True`
- 匹配条件是否正确
- 重载是否成功（看 `/ui/plugins` 和日志）

### 9.3 插件菜单不出现

排查：

- 是否调用了 `register_frontend_page`
- `route` 是否以 `/ui/ext/` 开头（建议）
- 插件是否已重载成功

### 9.4 `template` 页面打不开

排查：

- `source` 文件是否存在于插件目录内
- 路径是否写为相对路径（如 `web/demo_echo.html`）

---

## 10. 最佳实践

- 插件只做“业务扩展”，不要改核心框架逻辑
- 保持 `register()` 幂等、可重复执行
- 单插件内规则命名统一前缀（如 `weather_...`）
- 对外部依赖失败要兜底并记录日志
- 前端页面先用 `template` 跑通，再考虑 `iframe` 独立化

### 10.1 完成定义（DoD）

提交一个插件改动前，建议满足：

- [ ] `/ui/plugins` 可看到插件，且状态为 `loaded`
- [ ] 单插件重载返回 `ok=true`
- [ ] 规则命令可命中并返回预期消息
- [ ] 如有前端页，`/ui/ext/<plugin_name>` 可访问
- [ ] 关键场景已按 `TEST_CHECKLIST.md` 过一遍

---

## 11. 参考文件

- `plugins/README.md`
- `plugins/demo_echo/plugin.py`
- `plugins/demo_echo/web/demo_echo.html`
- `src/core/plugin_manager.py`
- `src/api/webui_app.py`
- `tools/new_plugin.py`
- `docs/PLUGIN_CHAT_BOOTSTRAP.md`

---

## 12. 给新聊天窗口的标准提示词（可复制）

```text
你现在是 weijian 项目的插件开发助手。请严格按以下约束工作：

1) 仅在 plugins/<plugin_name>/ 下修改，非必要不要改 src/ 核心代码。
2) 插件入口必须是 register(registry)。
3) 规则使用 registry.register_rule("<plugin>_...", handler)。
4) 如需页面，使用 registry.register_frontend_page(..., view_type="template"|"iframe", ...)。
5) 开发后给出验证步骤：/ui/plugins 重载、命令命中、/ui/ext/<plugin> 页面访问。
6) 输出请用中文，先给最小可运行版本，再给可选增强项。

当前任务：<在这里填你的插件需求>
```
