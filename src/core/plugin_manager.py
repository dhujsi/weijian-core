from __future__ import annotations

import importlib.util
import sys
import traceback
from dataclasses import dataclass
from pathlib import Path
from types import ModuleType
from typing import Any

from core.message_service import MessageService, RuleHandler


@dataclass
class PluginRuntime:
    name: str
    status: str
    version: str
    error: str
    module: ModuleType | None = None


class PluginRegistry:
    def __init__(self, plugin_name: str, message_service: MessageService) -> None:
        self._plugin_name = plugin_name
        self._message_service = message_service

    def register_rule(self, rule_name: str, handler: RuleHandler) -> None:
        self._message_service.register_plugin_rule(
            plugin_name=self._plugin_name,
            rule_name=rule_name,
            handler=handler,
        )


class PluginManager:
    def __init__(self, plugins_dir: str | Path, message_service: MessageService) -> None:
        self._plugins_dir = Path(plugins_dir)
        self._plugins_dir.mkdir(parents=True, exist_ok=True)
        self._message_service = message_service
        self._runtime: dict[str, PluginRuntime] = {}

    def _plugin_file(self, name: str) -> Path:
        return self._plugins_dir / name / "plugin.py"

    def scan_plugins(self) -> list[str]:
        names: list[str] = []
        for child in sorted(self._plugins_dir.iterdir()):
            if not child.is_dir():
                continue
            if (child / "plugin.py").exists():
                names.append(child.name)
                self._runtime.setdefault(
                    child.name,
                    PluginRuntime(name=child.name, status="discovered", version="", error=""),
                )
        return names

    def _import_plugin_module(self, name: str) -> ModuleType:
        file_path = self._plugin_file(name)
        if not file_path.exists():
            raise FileNotFoundError(f"plugin file not found: {file_path}")

        module_name = f"weijian_plugins.{name}.plugin"
        if module_name in sys.modules:
            del sys.modules[module_name]

        spec = importlib.util.spec_from_file_location(module_name, file_path)
        if spec is None or spec.loader is None:
            raise RuntimeError(f"cannot import plugin: {name}")

        module = importlib.util.module_from_spec(spec)
        sys.modules[module_name] = module
        spec.loader.exec_module(module)
        return module

    def load_plugin(self, name: str) -> dict[str, Any]:
        try:
            module = self._import_plugin_module(name)
            register = getattr(module, "register", None)
            if not callable(register):
                raise RuntimeError("register(registry) not found")

            self._message_service.unregister_plugin_rules(name)
            registry = PluginRegistry(plugin_name=name, message_service=self._message_service)
            register(registry)

            version = str(getattr(module, "__version__", ""))
            self._runtime[name] = PluginRuntime(
                name=name,
                status="loaded",
                version=version,
                error="",
                module=module,
            )
            print(f"[plugin] loaded: {name}, version={version or '-'}")
            return {"ok": True, "message": f"loaded {name}"}
        except Exception as exc:
            self._runtime[name] = PluginRuntime(
                name=name,
                status="error",
                version="",
                error=str(exc),
                module=None,
            )
            print(f"[plugin] load failed: {name}, err={exc}")
            print(traceback.format_exc())
            return {"ok": False, "message": f"load failed: {name}: {exc}"}

    def reload_plugin(self, name: str) -> dict[str, Any]:
        old_runtime = self._runtime.get(name)
        old_rules = self._message_service.unregister_plugin_rules(name)

        try:
            module = self._import_plugin_module(name)
            register = getattr(module, "register", None)
            if not callable(register):
                raise RuntimeError("register(registry) not found")

            registry = PluginRegistry(plugin_name=name, message_service=self._message_service)
            register(registry)

            version = str(getattr(module, "__version__", ""))
            self._runtime[name] = PluginRuntime(
                name=name,
                status="loaded",
                version=version,
                error="",
                module=module,
            )
            print(f"[plugin] reloaded: {name}, version={version or '-'}")
            return {"ok": True, "message": f"reloaded {name}"}
        except Exception as exc:
            if old_runtime is not None and old_runtime.module is not None:
                self._runtime[name] = old_runtime
                self._message_service.restore_plugin_rules(name, old_rules)
                self._runtime[name].error = f"reload failed, old active: {exc}"
                print(f"[plugin] reload failed, rollback active: {name}, err={exc}")
                print(traceback.format_exc())
                return {"ok": False, "message": f"reload failed, old active: {name}: {exc}"}

            self._runtime[name] = PluginRuntime(
                name=name,
                status="error",
                version="",
                error=str(exc),
                module=None,
            )
            print(f"[plugin] reload failed: {name}, err={exc}")
            print(traceback.format_exc())
            return {"ok": False, "message": f"reload failed: {name}: {exc}"}

    def reload_all(self) -> dict[str, Any]:
        names = self.scan_plugins()
        if not names:
            return {"ok": True, "message": "no plugins found"}

        ok_count = 0
        fail_count = 0
        for name in names:
            runtime = self._runtime.get(name)
            if runtime and runtime.status == "loaded":
                res = self.reload_plugin(name)
            else:
                res = self.load_plugin(name)
            if res.get("ok"):
                ok_count += 1
            else:
                fail_count += 1

        msg = f"reload all finished: ok={ok_count}, failed={fail_count}"
        print(f"[plugin] {msg}")
        return {"ok": fail_count == 0, "message": msg}

    def list_plugins(self) -> list[dict[str, str]]:
        self.scan_plugins()
        items: list[dict[str, str]] = []
        for name in sorted(self._runtime.keys()):
            info = self._runtime[name]
            items.append(
                {
                    "name": info.name,
                    "status": info.status,
                    "version": info.version,
                    "error": info.error,
                }
            )
        return items
