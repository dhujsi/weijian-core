from __future__ import annotations

import asyncio
import re
import time
from collections.abc import Awaitable, Callable
from datetime import datetime, timedelta
from typing import Any

from connectors.napcat.http_client import NapCatHttpClient
from core.storage import SQLiteStore
from core.time_utils import CN_TZ, fmt_ts


RuleHandler = Callable[["MessageService", int, str], bool | Awaitable[bool]]


class MessageService:
    def __init__(self, napcat_http: NapCatHttpClient, store: SQLiteStore) -> None:
        self._napcat_http = napcat_http
        self._store = store
        self._plugin_rules: dict[str, list[dict[str, Any]]] = {}
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

    def scheduler_status(self) -> dict[str, str]:
        return {
            "running": "yes" if self._scheduler_running else "no",
            "last_error": self._scheduler_last_error or "",
        }

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

    @staticmethod
    def _parse_simple_remind_time(text: str) -> tuple[float, str] | None:
        now_ts = time.time()
        now_cn = datetime.now(CN_TZ)

        relative_patterns: list[tuple[str, str]] = [
            (r"^(\d+)分钟后提醒我(.+)$", "minutes"),
            (r"^(\d+)小时后提醒我(.+)$", "hours"),
            (r"^(\d+)天后提醒我(.+)$", "days"),
        ]
        for pattern, unit in relative_patterns:
            m = re.match(pattern, text.strip())
            if m is None:
                continue
            x = int(m.group(1))
            content = m.group(2).strip()
            if x <= 0 or content == "":
                return None
            if unit == "minutes":
                return now_ts + x * 60, content
            if unit == "hours":
                return now_ts + x * 3600, content
            return now_ts + x * 86400, content

        marker = "提醒我"
        idx = text.find(marker)
        if idx == -1:
            return None

        prefix = text[:idx].strip()
        content = text[idx + len(marker) :].strip()
        if not content:
            return None

        if prefix == "":
            remind_at = now_ts + 60
            return remind_at, content

        if prefix == "今天":
            remind_at_dt = now_cn.replace(hour=20, minute=0, second=0, microsecond=0)
            remind_at = remind_at_dt.timestamp()
            if remind_at <= now_ts:
                remind_at = now_ts + 60
            return remind_at, content

        if prefix == "明天":
            base = now_cn + timedelta(days=1)
            remind_at = base.replace(hour=9, minute=0, second=0, microsecond=0)
            return remind_at.timestamp(), content

        if prefix.endswith("点"):
            hour_text = prefix[:-1].strip()
            if hour_text.isdigit():
                hour = int(hour_text)
                if 0 <= hour <= 23:
                    remind_at_dt = now_cn.replace(hour=hour, minute=0, second=0, microsecond=0)
                    remind_at = remind_at_dt.timestamp()
                    if remind_at <= now_ts:
                        remind_at = (remind_at_dt + timedelta(days=1)).timestamp()
                    return remind_at, content

        return None

    async def _reply(self, user_id: int, message: str) -> None:
        print(f"[msg] reply: user_id={user_id}, message={message}")
        await self._napcat_http.send_private_msg(user_id=user_id, message=message)

    async def _handle_note(self, user_id: int, text: str) -> bool:
        if not text.startswith("记一下"):
            return False
        content = text[len("记一下") :].strip()
        if not content:
            await self._reply(user_id, "要记的内容不能为空")
            return True
        self._store.add_note(user_id=user_id, content=content)
        await self._reply(user_id, "记下了")
        return True

    async def _handle_query_notes(self, user_id: int, text: str) -> bool:
        if text.strip() != "我最近记了什么":
            return False

        notes = self._store.recent_notes(user_id=user_id, limit=10)
        if not notes:
            await self._reply(user_id, "你最近还没有笔记")
            return True

        lines = ["你最近的笔记："]
        for i, note in enumerate(notes, start=1):
            lines.append(f"{i}. {note.content} ({fmt_ts(note.created_at)})")
        await self._reply(user_id, "\n".join(lines))
        return True

    async def _handle_reminder(self, user_id: int, text: str) -> bool:
        parsed = self._parse_simple_remind_time(text)
        if parsed is None:
            return False

        remind_at_ts, content = parsed
        print(
            f"[rule] reminder matched: user_id={user_id}, remind_at={fmt_ts(remind_at_ts)}, content={content}"
        )
        self._store.add_reminder(user_id=user_id, content=content, remind_at=remind_at_ts)
        await self._reply(user_id, f"已设置提醒：{fmt_ts(remind_at_ts)}")
        return True

    async def _handle_query_reminders(self, user_id: int, text: str) -> bool:
        if text.strip() != "我有哪些提醒":
            return False

        print(f"[rule] query reminders matched: user_id={user_id}")
        reminders = self._store.list_pending_reminders(user_id=user_id, limit=10)
        if not reminders:
            await self._reply(user_id, "你当前没有提醒")
            return True

        lines = ["你的提醒："]
        for item in reminders:
            lines.append(f"{item.id} | {fmt_ts(item.remind_at)} | {item.content}")
        await self._reply(user_id, "\n".join(lines))
        return True

    async def _handle_query_today_reminders(self, user_id: int, text: str) -> bool:
        if text.strip() != "我今天有什么提醒":
            return False

        print(f"[rule] query today reminders matched: user_id={user_id}")
        reminders = self._store.list_today_pending_reminders(user_id=user_id, limit=10)
        if not reminders:
            await self._reply(user_id, "你今天没有提醒")
            return True

        lines = ["你今天的提醒："]
        for item in reminders:
            lines.append(f"{item.id} | {fmt_ts(item.remind_at)} | {item.content}")
        await self._reply(user_id, "\n".join(lines))
        return True

    async def _handle_cancel_reminder(self, user_id: int, text: str) -> bool:
        m = re.match(r"^取消提醒\s+(\d+)$", text.strip())
        if m is None:
            return False

        reminder_id = int(m.group(1))
        print(f"[rule] cancel reminder matched: user_id={user_id}, id={reminder_id}")
        ok = self._store.cancel_reminder(reminder_id=reminder_id, user_id=user_id)
        if ok:
            await self._reply(user_id, "已取消提醒")
        else:
            await self._reply(user_id, "提醒不存在或不可取消")
        return True

    async def _handle_clear_done_reminders(self, user_id: int, text: str) -> bool:
        if text.strip() != "清空已完成提醒":
            return False

        print(f"[rule] clear done reminders matched: user_id={user_id}")
        count = self._store.clear_done_reminders(user_id=user_id)
        await self._reply(user_id, f"已清空{count}条")
        return True

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

        if await self._handle_note(user_id=target_user_id, text=text):
            return
        if await self._handle_clear_done_reminders(user_id=target_user_id, text=text):
            return
        if await self._handle_cancel_reminder(user_id=target_user_id, text=text):
            return
        if await self._handle_reminder(user_id=target_user_id, text=text):
            return
        if await self._handle_query_today_reminders(user_id=target_user_id, text=text):
            return
        if await self._handle_query_reminders(user_id=target_user_id, text=text):
            return
        if await self._handle_query_notes(user_id=target_user_id, text=text):
            return
        if await self._run_plugin_rules(user_id=target_user_id, text=text):
            return

        await self._reply(target_user_id, text)

    async def run_reminder_scheduler(self) -> None:
        print("[scheduler] reminder scheduler started (interval=10s)")
        self._scheduler_running = True
        while True:
            try:
                due = self._store.due_reminders(time.time())
                for item in due:
                    msg = f"[提醒#{item.id}] {item.content}"
                    print(
                        f"[scheduler] trigger reminder: id={item.id}, user_id={item.user_id}, remind_at={fmt_ts(item.remind_at)}"
                    )
                    if not str(item.user_id).isdigit():
                        print(
                            f"[scheduler] skip invalid user_id: id={item.id}, user_id={item.user_id}"
                        )
                        self._store.mark_reminder_done(item.id)
                        continue
                    await self._napcat_http.send_private_msg(
                        user_id=int(item.user_id),
                        message=msg,
                    )
                    self._store.mark_reminder_done(item.id)
            except Exception as exc:
                self._scheduler_last_error = str(exc)
                print(f"[scheduler] loop error: {exc}")

            await asyncio.sleep(10)