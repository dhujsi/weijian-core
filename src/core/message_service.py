from __future__ import annotations

import asyncio
from collections.abc import Awaitable, Callable
from typing import Any

from connectors.napcat.http_client import NapCatHttpClient
from core.storage import SQLiteStore


RuleHandler = Callable[["MessageService", int, str], bool | Awaitable[bool]]
SchedulerHandler = Callable[["MessageService"], Awaitable[None] | None]


class MessageService:
    def __init__(self, napcat_http: NapCatHttpClient, store: SQLiteStore) -> None:
        self._napcat_http = napcat_http
        self._store = store
        self._plugin_rules: dict[str, list[dict[str, Any]]] = {}
        self._plugin_schedulers: dict[str, list[dict[str, Any]]] = {}
        self._scheduler_running = False
        self._scheduler_last_error: str | None = None

    def register_plugin_rule(self, plugin_name: str, rule_name: str, handler: RuleHandler) -> None:
        items = self._plugin_rules.setdefault(plugin_name, [])
        items.append({"name": rule_name, "handler": handler})
        print(f"[plugin] rule registered: plugin={plugin_name}, rule={rule_name}")

    def unregister_plugin_rules(self, plugin_name: str) -> list[dict[str, Any]]:
        removed = self._plugin_rules.pop(plugin_name, [])
        if removed:
            print(f"[plugin] rules unregistered: plugin={plugin_name}, count={len(removed)}")
        return removed

    def restore_plugin_rules(self, plugin_name: str, rules: list[dict[str, Any]]) -> None:
        self._plugin_rules[plugin_name] = rules
        print(f"[plugin] rules restored: plugin={plugin_name}, count={len(rules)}")

    def plugin_rules_count(self) -> int:
        return sum(len(v) for v in self._plugin_rules.values())

    def register_plugin_scheduler(
        self,
        plugin_name: str,
        scheduler_name: str,
        handler: SchedulerHandler,
    ) -> None:
        items = self._plugin_schedulers.setdefault(plugin_name, [])
        items.append({"name": scheduler_name, "handler": handler})
        print(f"[plugin] scheduler registered: plugin={plugin_name}, scheduler={scheduler_name}")

    def unregister_plugin_schedulers(self, plugin_name: str) -> list[dict[str, Any]]:
        removed = self._plugin_schedulers.pop(plugin_name, [])
        if removed:
            print(f"[plugin] schedulers unregistered: plugin={plugin_name}, count={len(removed)}")
        return removed

    def restore_plugin_schedulers(self, plugin_name: str, schedulers: list[dict[str, Any]]) -> None:
        self._plugin_schedulers[plugin_name] = schedulers
        print(f"[plugin] schedulers restored: plugin={plugin_name}, count={len(schedulers)}")

    def plugin_schedulers_count(self) -> int:
        return sum(len(v) for v in self._plugin_schedulers.values())

    def scheduler_status(self) -> dict[str, str]:
        return {
            "running": "yes" if self._scheduler_running else "no",
            "last_error": self._scheduler_last_error or "",
        }

    async def _run_plugin_scheduler(
        self,
        plugin_name: str,
        scheduler_name: str,
        handler: SchedulerHandler,
    ) -> None:
        print(
            f"[scheduler] plugin scheduler started: plugin={plugin_name}, scheduler={scheduler_name}"
        )
        try:
            result = handler(self)
            if asyncio.iscoroutine(result):
                await result
        except Exception as exc:
            self._scheduler_last_error = f"{plugin_name}.{scheduler_name}: {exc}"
            print(
                "[scheduler] plugin scheduler error: "
                f"plugin={plugin_name}, scheduler={scheduler_name}, err={exc}"
            )

    async def _run_plugin_rules(self, user_id: int, text: str) -> bool:
        for plugin_name, rules in self._plugin_rules.items():
            for item in rules:
                handler = item["handler"]
                rule_name = item["name"]
                try:
                    result = handler(self, user_id, text)
                    matched = await result if asyncio.iscoroutine(result) else bool(result)
                    if matched:
                        print(
                            f"[plugin] rule matched: plugin={plugin_name}, rule={rule_name}, user_id={user_id}"
                        )
                        return True
                except Exception as exc:
                    print(
                        f"[plugin] rule error: plugin={plugin_name}, rule={rule_name}, err={exc}"
                    )
        return False

    async def _reply(self, user_id: int, message: str) -> None:
        print(f"[msg] reply: user_id={user_id}, message={message}")
        await self._napcat_http.send_private_msg(user_id=user_id, message=message)

    async def on_private_text(
        self,
        user_id: int | str,
        text: str,
        group_id: int | str | None = None,
    ) -> None:
        target_user_id: int
        if isinstance(user_id, int):
            target_user_id = user_id
        else:
            target_user_id = int(user_id)

        print(f"[msg] on_private_text: user_id={target_user_id}, text={text}")
        if await self._run_plugin_rules(user_id=target_user_id, text=text):
            return

        await self._reply(target_user_id, text)

    async def run_plugin_schedulers(self) -> None:
        print("[scheduler] plugin schedulers booting")
        self._scheduler_running = True
        tasks: list[asyncio.Task[Any]] = []
        for plugin_name, schedulers in self._plugin_schedulers.items():
            for item in schedulers:
                handler = item["handler"]
                scheduler_name = item["name"]
                tasks.append(
                    asyncio.create_task(
                        self._run_plugin_scheduler(
                            plugin_name=plugin_name,
                            scheduler_name=scheduler_name,
                            handler=handler,
                        )
                    )
                )

        if not tasks:
            print("[scheduler] no plugin scheduler registered")
            while True:
                await asyncio.sleep(3600)

        await asyncio.gather(*tasks)