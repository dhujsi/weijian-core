from __future__ import annotations

import asyncio
import re
import time
from datetime import datetime, timedelta

from core.time_utils import CN_TZ, fmt_ts

__version__ = "0.1.0"


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


def register(registry) -> None:
    registry.register_frontend_page(
        title="笔记",
        route="/ui/ext/notes",
        view_type="template",
        source="web/notes.html",
        order=20,
    )
    registry.register_frontend_page(
        title="提醒",
        route="/ui/ext/reminders",
        view_type="template",
        source="web/reminders.html",
        order=21,
    )

    async def on_note(service, user_id: int, text: str) -> bool:
        if not text.startswith("记一下"):
            return False
        content = text[len("记一下") :].strip()
        if not content:
            await service._reply(user_id, "要记的内容不能为空")
            return True
        service._store.add_note(user_id=user_id, content=content)
        await service._reply(user_id, "记下了")
        return True

    async def on_query_notes(service, user_id: int, text: str) -> bool:
        if text.strip() != "我最近记了什么":
            return False

        notes = service._store.recent_notes(user_id=user_id, limit=10)
        if not notes:
            await service._reply(user_id, "你最近还没有笔记")
            return True

        lines = ["你最近的笔记："]
        for i, note in enumerate(notes, start=1):
            lines.append(f"{i}. {note.content} ({fmt_ts(note.created_at)})")
        await service._reply(user_id, "\n".join(lines))
        return True

    async def on_clear_done_reminders(service, user_id: int, text: str) -> bool:
        if text.strip() != "清空已完成提醒":
            return False

        count = service._store.clear_done_reminders(user_id=user_id)
        await service._reply(user_id, f"已清空{count}条")
        return True

    async def on_cancel_reminder(service, user_id: int, text: str) -> bool:
        m = re.match(r"^取消提醒\s+(\d+)$", text.strip())
        if m is None:
            return False

        reminder_id = int(m.group(1))
        ok = service._store.cancel_reminder(reminder_id=reminder_id, user_id=user_id)
        if ok:
            await service._reply(user_id, "已取消提醒")
        else:
            await service._reply(user_id, "提醒不存在或不可取消")
        return True

    async def on_create_reminder(service, user_id: int, text: str) -> bool:
        parsed = _parse_simple_remind_time(text)
        if parsed is None:
            return False

        remind_at_ts, content = parsed
        service._store.add_reminder(user_id=user_id, content=content, remind_at=remind_at_ts)
        await service._reply(user_id, f"已设置提醒：{fmt_ts(remind_at_ts)}")
        return True

    async def on_query_today_reminders(service, user_id: int, text: str) -> bool:
        if text.strip() != "我今天有什么提醒":
            return False

        reminders = service._store.list_today_pending_reminders(user_id=user_id, limit=10)
        if not reminders:
            await service._reply(user_id, "你今天没有提醒")
            return True

        lines = ["你今天的提醒："]
        for item in reminders:
            lines.append(f"{item.id} | {fmt_ts(item.remind_at)} | {item.content}")
        await service._reply(user_id, "\n".join(lines))
        return True

    async def on_query_reminders(service, user_id: int, text: str) -> bool:
        if text.strip() != "我有哪些提醒":
            return False

        reminders = service._store.list_pending_reminders(user_id=user_id, limit=10)
        if not reminders:
            await service._reply(user_id, "你当前没有提醒")
            return True

        lines = ["你的提醒："]
        for item in reminders:
            lines.append(f"{item.id} | {fmt_ts(item.remind_at)} | {item.content}")
        await service._reply(user_id, "\n".join(lines))
        return True

    async def reminder_scheduler(service) -> None:
        print("[scheduler] builtin_notes_reminders started (interval=10s)")
        while True:
            try:
                due = service._store.due_reminders(time.time())
                for item in due:
                    msg = f"[提醒#{item.id}] {item.content}"
                    print(
                        "[scheduler] trigger reminder: "
                        f"id={item.id}, user_id={item.user_id}, remind_at={fmt_ts(item.remind_at)}"
                    )
                    if not str(item.user_id).isdigit():
                        print(
                            f"[scheduler] skip invalid user_id: id={item.id}, user_id={item.user_id}"
                        )
                        service._store.mark_reminder_done(item.id)
                        continue
                    await service._napcat_http.send_private_msg(
                        user_id=int(item.user_id),
                        message=msg,
                    )
                    service._store.mark_reminder_done(item.id)
            except Exception as exc:
                print(f"[scheduler] builtin_notes_reminders loop error: {exc}")

            await asyncio.sleep(10)

    # 保持原有优先级：笔记 -> 提醒管理 -> 设置提醒 -> 提醒查询 -> 笔记查询
    registry.register_rule("builtin_note_add", on_note)
    registry.register_rule("builtin_reminder_clear_done", on_clear_done_reminders)
    registry.register_rule("builtin_reminder_cancel", on_cancel_reminder)
    registry.register_rule("builtin_reminder_add", on_create_reminder)
    registry.register_rule("builtin_reminder_query_today", on_query_today_reminders)
    registry.register_rule("builtin_reminder_query_all", on_query_reminders)
    registry.register_rule("builtin_note_query", on_query_notes)
    registry.register_scheduler("builtin_reminder_scheduler", reminder_scheduler)
