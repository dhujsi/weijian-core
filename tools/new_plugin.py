from __future__ import annotations

import argparse
import re
from pathlib import Path


PLUGIN_TEMPLATE = '''from __future__ import annotations

__version__ = "0.1.0"


def register(registry) -> None:
    registry.register_frontend_page(
        title="{display_name}",
        route="/ui/ext/{plugin_name}",
        view_type="template",
        source="web/index.html",
        order=100,
    )

    async def on_command(service, user_id: int, text: str) -> bool:
        if text.strip() != "{trigger_cmd}":
            return False
        await service._reply(user_id, "[{plugin_name}] 插件命中")
        return True

    registry.register_rule("{plugin_name}_cmd", on_command)
'''


HTML_TEMPLATE = '''<div style="padding: 16px;">
  <h2 style="margin: 0 0 12px;">{display_name}</h2>
  <p style="margin: 0 0 10px; color: #6b7280;">这是由脚手架创建的插件页面（template 模式）。</p>
  <div style="padding: 12px; border: 1px solid #e5e7eb; border-radius: 10px; background: #fff;">
    <p style="margin: 0 0 8px;">测试指令：</p>
    <code style="display: inline-block; background: #f3f4f6; border-radius: 6px; padding: 4px 8px;">{trigger_cmd}</code>
  </div>
</div>
'''


README_TEMPLATE = '''# {display_name}

由 `tools/new_plugin.py` 生成。

## 快速开始

1. 按需修改 `plugin.py` 里的触发词和业务逻辑
2. 打开 `/ui/plugins`，点击重载本插件
3. 访问插件页面：`/ui/ext/{plugin_name}`
'''


def normalize_plugin_name(name: str) -> str:
    n = name.strip().lower().replace("-", "_")
    n = re.sub(r"[^a-z0-9_]", "", n)
    n = re.sub(r"_+", "_", n).strip("_")
    if not n:
        raise ValueError("插件名为空或非法，请使用字母/数字/下划线")
    if not n[0].isalpha():
        n = f"p_{n}"
    return n


def build_display_name(plugin_name: str) -> str:
    return " ".join(part.capitalize() for part in plugin_name.split("_"))


def main() -> None:
    parser = argparse.ArgumentParser(description="创建 weijian 插件脚手架")
    parser.add_argument("name", help="插件名（建议英文字母/数字/下划线）")
    parser.add_argument("--trigger", default="插件测试", help="默认测试指令")
    parser.add_argument("--force", action="store_true", help="目录已存在时覆盖写入")
    args = parser.parse_args()

    plugin_name = normalize_plugin_name(args.name)
    display_name = build_display_name(plugin_name)
    trigger_cmd = args.trigger.strip() or "插件测试"

    root = Path(__file__).resolve().parents[1]
    plugin_dir = root / "plugins" / plugin_name
    web_dir = plugin_dir / "web"

    if plugin_dir.exists() and not args.force:
        raise SystemExit(f"插件目录已存在：{plugin_dir}，如需覆盖请加 --force")

    web_dir.mkdir(parents=True, exist_ok=True)

    (plugin_dir / "plugin.py").write_text(
        PLUGIN_TEMPLATE.format(
            plugin_name=plugin_name,
            display_name=display_name,
            trigger_cmd=trigger_cmd,
        ),
        encoding="utf-8",
    )
    (web_dir / "index.html").write_text(
        HTML_TEMPLATE.format(
            display_name=display_name,
            trigger_cmd=trigger_cmd,
        ),
        encoding="utf-8",
    )
    (plugin_dir / "README.md").write_text(
        README_TEMPLATE.format(
            plugin_name=plugin_name,
            display_name=display_name,
        ),
        encoding="utf-8",
    )

    print(f"[ok] 插件已创建: {plugin_dir}")
    print(f"[next] 1) 修改 {plugin_dir / 'plugin.py'}")
    print("[next] 2) 打开 /ui/plugins 重载插件")
    print(f"[next] 3) 访问 /ui/ext/{plugin_name}")


if __name__ == "__main__":
    main()
