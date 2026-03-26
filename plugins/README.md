# 插件说明（最小）

## 1. 目录约定

每个插件一个目录：

- `plugins/<plugin_name>/plugin.py`

示例：

- `plugins/demo_echo/plugin.py`

## 2. `register(registry)` 最小写法

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

## 3. `registry.register_rule` 参数说明

- `rule_name: str`
  - 规则名（建议在插件内唯一）
- `handler: Callable`
  - 签名建议：`handler(service, user_id: int, text: str) -> bool | Awaitable[bool]`
  - 返回 `True` 表示已命中并处理，后续不再继续匹配
  - 返回 `False` 表示未命中，继续后续规则

## 3.1 `registry.register_frontend_page`（前端半插件化）

插件可额外注册一个前端页面扩展点，WebUI 会自动把它加入导航菜单。

```python
registry.register_frontend_page(
    title="Demo Echo",
    route="/ui/ext/demo_echo",
    view_type="template",  # template 或 iframe
    source="web/demo_echo.html",  # template: 插件目录内相对路径；iframe: 外部URL
    order=10,
)
```

参数说明：

- `title: str`
  - 菜单显示名称
- `route: str`
  - 插件页面路由，建议使用 `/ui/ext/<plugin_name>`
- `view_type: str`
  - `template`：读取插件目录内 HTML 片段并嵌入统一壳页面
  - `iframe`：在统一壳页面中以 iframe 加载 `source` URL
- `source: str`
  - `template` 模式下：插件目录相对路径（如 `web/demo_echo.html`）
  - `iframe` 模式下：完整 URL
- `order: int`
  - 菜单排序，越小越靠前

当前后端会提供：

- 动态路由：`/ui/ext/{ext_path:path}`
- 动态菜单注入：核心页面导航会自动显示插件菜单项

## 4. 热重载流程（load/reload/unload）

- `load`
  - 首次加载插件，调用 `register(registry)` 注册规则
- `reload`
  - 先卸载旧规则，再导入新 `plugin.py` 并重新注册
  - 同时卸载并重新注册前端扩展点
  - 若重载失败，管理器会尽量回滚旧规则，保持服务可用
- `unload`
  - 当前最小实现未单独提供 HTTP 卸载接口
  - 可通过插件管理器内部 `unregister_plugin_rules(plugin)` 完成规则卸载

## 5. 常见错误与排查

### 5.1 重复注册
- 现象：同一消息触发多次
- 原因：未正确卸载旧规则或插件重复加载
- 排查：看日志前缀 `[plugin]`，确认 `rules unregistered` 与 `rule registered` 次数

### 5.2 导入失败
- 现象：`/ui/plugins` 显示 `status=error`
- 原因：`plugin.py` 语法错误、依赖缺失、`register` 不存在
- 排查：查看 `[plugin] load failed` / `[plugin] reload failed` 日志堆栈

### 5.3 规则未命中
- 现象：发送测试文本无插件响应
- 原因：条件不匹配、返回值恒 `False`
- 排查：
  - 确认文本与规则条件一致
  - 确认 handler 命中后返回 `True`
  - 查看 `[plugin] rule matched` 是否出现
