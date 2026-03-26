# 插件开发速查（新聊天窗口专用）

> 目标：开一个新聊天窗口，直接开始写插件，不翻全项目。

## 1) 先做这 5 步

1. 创建骨架
   - `python tools/new_plugin.py my_plugin`
2. 改后端逻辑
   - `plugins/my_plugin/plugin.py`
3. 改前端页面（可选）
   - `plugins/my_plugin/web/index.html`
4. 重载插件
   - WebUI: `/ui/plugins` -> 重载 `my_plugin`
   - 或命令：`python tools/reload_plugin.py my_plugin --token <ADMIN_TOKEN>`
5. 验证
   - 发测试命令看是否命中
   - 打开 `/ui/ext/my_plugin`

## 2) 最小插件模板

```python
from __future__ import annotations

__version__ = "0.1.0"


def register(registry) -> None:
    registry.register_frontend_page(
        title="My Plugin",
        route="/ui/ext/my_plugin",
        view_type="template",
        source="web/index.html",
        order=100,
    )

    async def on_cmd(service, user_id: int, text: str) -> bool:
        if text.strip() != "我的测试命令":
            return False
        await service._reply(user_id, "[my_plugin] 命中")
        return True

    registry.register_rule("my_plugin_cmd", on_cmd)
```

## 3) 新聊天窗口提示词（复制即用）

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

## 4) DoD（完成定义）

- [ ] `/ui/plugins` 状态 `loaded`
- [ ] 重载接口返回 `ok=true`
- [ ] 测试命令命中
- [ ] 页面可访问（如有）
- [ ] 过一遍 `TEST_CHECKLIST.md` 关键项
