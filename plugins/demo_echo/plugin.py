from __future__ import annotations

__version__ = "0.2.0"


def register(registry) -> None:
    registry.register_frontend_page(
        title="Demo Echo",
        route="/ui/ext/demo_echo",
        view_type="template",
        source="web/demo_echo.html",
        order=10,
    )

    async def on_demo(service, user_id: int, text: str) -> bool:
        cmd = "插件测试"
        if text.strip() != cmd:
            return False
        await service._reply(user_id, "[demo_echo] 插件命中")
        return True

    registry.register_rule("demo_echo_rule", on_demo)
