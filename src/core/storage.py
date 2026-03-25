from __future__ import annotations

import sqlite3
import time
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path

from core.time_utils import CN_TZ


@dataclass(frozen=True)
class Note:
    id: int
    user_id: str
    content: str
    created_at: float


@dataclass(frozen=True)
class Reminder:
    id: int
    user_id: str
    content: str
    remind_at: float
    status: str
    created_at: float


class SQLiteStore:
    def __init__(self, database_url: str) -> None:
        self._db_path = self._parse_sqlite_path(database_url)
        Path(self._db_path).parent.mkdir(parents=True, exist_ok=True)
        self._conn = sqlite3.connect(self._db_path)
        self._conn.row_factory = sqlite3.Row
        print(f"[db] connected: {self._db_path}")
        self._init_tables()

    @staticmethod
    def _parse_sqlite_path(database_url: str) -> str:
        if database_url.startswith("sqlite:///"):
            return database_url[len("sqlite:///") :]
        if database_url == "":
            return "weijian.db"
        return database_url

    def _init_tables(self) -> None:
        cur = self._conn.cursor()
        cur.execute(
            """
            CREATE TABLE IF NOT EXISTS notes (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id TEXT NOT NULL,
                content TEXT NOT NULL,
                created_at REAL NOT NULL
            )
            """
        )
        cur.execute(
            """
            CREATE TABLE IF NOT EXISTS reminders (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id TEXT NOT NULL,
                content TEXT NOT NULL,
                remind_at REAL NOT NULL,
                status TEXT NOT NULL,
                created_at REAL NOT NULL
            )
            """
        )
        self._conn.commit()
        print("[db] tables ensured: notes, reminders")

    @staticmethod
    def _to_ts(value: float | int | str) -> float:
        if isinstance(value, (float, int)):
            return float(value)
        raw = str(value)
        try:
            return float(raw)
        except ValueError:
            dt = datetime.strptime(raw, "%Y-%m-%d %H:%M:%S").replace(tzinfo=CN_TZ)
            return dt.timestamp()

    def add_note(self, user_id: int | str, content: str) -> int:
        created_at = time.time()
        cur = self._conn.cursor()
        cur.execute(
            "INSERT INTO notes(user_id, content, created_at) VALUES(?, ?, ?)",
            (str(user_id), content, created_at),
        )
        self._conn.commit()
        note_id = int(cur.lastrowid)
        print(f"[db] note inserted: id={note_id}, user_id={user_id}")
        return note_id

    def recent_notes(self, user_id: int | str, limit: int = 10) -> list[Note]:
        cur = self._conn.cursor()
        cur.execute(
            """
            SELECT id, user_id, content, created_at
            FROM notes
            WHERE user_id = ?
            ORDER BY id DESC
            LIMIT ?
            """,
            (str(user_id), limit),
        )
        rows = cur.fetchall()
        notes = [
            Note(
                id=int(row["id"]),
                user_id=str(row["user_id"]),
                content=str(row["content"]),
                created_at=self._to_ts(row["created_at"]),
            )
            for row in rows
        ]
        print(f"[db] recent notes fetched: user_id={user_id}, count={len(notes)}")
        return notes

    def list_notes(self, limit: int = 100) -> list[Note]:
        cur = self._conn.cursor()
        cur.execute(
            """
            SELECT id, user_id, content, created_at
            FROM notes
            ORDER BY id DESC
            LIMIT ?
            """,
            (limit,),
        )
        rows = cur.fetchall()
        notes = [
            Note(
                id=int(row["id"]),
                user_id=str(row["user_id"]),
                content=str(row["content"]),
                created_at=self._to_ts(row["created_at"]),
            )
            for row in rows
        ]
        print(f"[db] notes listed: count={len(notes)}")
        return notes

    def add_reminder(self, user_id: int | str, content: str, remind_at: float) -> int:
        created_at = time.time()
        cur = self._conn.cursor()
        cur.execute(
            """
            INSERT INTO reminders(user_id, content, remind_at, status, created_at)
            VALUES(?, ?, ?, 'pending', ?)
            """,
            (str(user_id), content, remind_at, created_at),
        )
        self._conn.commit()
        reminder_id = int(cur.lastrowid)
        print(
            f"[db] reminder inserted: id={reminder_id}, user_id={user_id}, remind_at={remind_at}"
        )
        return reminder_id

    def due_reminders(self, now_ts: float) -> list[Reminder]:
        cur = self._conn.cursor()
        cur.execute(
            """
            SELECT id, user_id, content, remind_at, status, created_at
            FROM reminders
            WHERE status = 'pending' AND CAST(remind_at AS REAL) <= ?
            ORDER BY id ASC
            """,
            (now_ts,),
        )
        rows = cur.fetchall()
        reminders = [
            Reminder(
                id=int(row["id"]),
                user_id=str(row["user_id"]),
                content=str(row["content"]),
                remind_at=self._to_ts(row["remind_at"]),
                status=str(row["status"]),
                created_at=self._to_ts(row["created_at"]),
            )
            for row in rows
        ]
        if reminders:
            print(f"[db] due reminders fetched: count={len(reminders)}")
        return reminders

    def list_pending_reminders(self, user_id: int | str, limit: int = 10) -> list[Reminder]:
        cur = self._conn.cursor()
        cur.execute(
            """
            SELECT id, user_id, content, remind_at, status, created_at
            FROM reminders
            WHERE user_id = ? AND status = 'pending'
            ORDER BY remind_at ASC, id ASC
            LIMIT ?
            """,
            (str(user_id), limit),
        )
        rows = cur.fetchall()
        reminders = [
            Reminder(
                id=int(row["id"]),
                user_id=str(row["user_id"]),
                content=str(row["content"]),
                remind_at=self._to_ts(row["remind_at"]),
                status=str(row["status"]),
                created_at=self._to_ts(row["created_at"]),
            )
            for row in rows
        ]
        print(f"[db] pending reminders fetched: user_id={user_id}, count={len(reminders)}")
        return reminders

    def list_today_pending_reminders(self, user_id: int | str, limit: int = 10) -> list[Reminder]:
        now_cn = datetime.now(CN_TZ)
        start_cn = now_cn.replace(hour=0, minute=0, second=0, microsecond=0)
        end_cn = start_cn.replace(hour=23, minute=59, second=59, microsecond=999999)
        start_ts = start_cn.timestamp()
        end_ts = end_cn.timestamp()

        cur = self._conn.cursor()
        cur.execute(
            """
            SELECT id, user_id, content, remind_at, status, created_at
            FROM reminders
            WHERE user_id = ?
              AND status = 'pending'
              AND CAST(remind_at AS REAL) >= ?
              AND CAST(remind_at AS REAL) <= ?
            ORDER BY remind_at ASC, id ASC
            LIMIT ?
            """,
            (str(user_id), start_ts, end_ts, limit),
        )
        rows = cur.fetchall()
        reminders = [
            Reminder(
                id=int(row["id"]),
                user_id=str(row["user_id"]),
                content=str(row["content"]),
                remind_at=self._to_ts(row["remind_at"]),
                status=str(row["status"]),
                created_at=self._to_ts(row["created_at"]),
            )
            for row in rows
        ]
        print(f"[db] today pending reminders fetched: user_id={user_id}, count={len(reminders)}")
        return reminders

    def cancel_reminder(self, reminder_id: int, user_id: int | str) -> bool:
        cur = self._conn.cursor()
        cur.execute(
            """
            UPDATE reminders
            SET status = 'cancelled'
            WHERE id = ? AND user_id = ? AND status = 'pending'
            """,
            (reminder_id, str(user_id)),
        )
        self._conn.commit()
        ok = cur.rowcount > 0
        print(
            f"[db] reminder cancel: id={reminder_id}, user_id={user_id}, success={'yes' if ok else 'no'}"
        )
        return ok

    def mark_reminder_done(self, reminder_id: int) -> None:
        cur = self._conn.cursor()
        cur.execute("UPDATE reminders SET status = 'done' WHERE id = ?", (reminder_id,))
        self._conn.commit()
        print(f"[db] reminder done: id={reminder_id}")

    def list_reminders(self, status: str | None = None, limit: int = 100) -> list[Reminder]:
        cur = self._conn.cursor()
        if status:
            cur.execute(
                """
                SELECT id, user_id, content, remind_at, status, created_at
                FROM reminders
                WHERE status = ?
                ORDER BY id DESC
                LIMIT ?
                """,
                (status, limit),
            )
        else:
            cur.execute(
                """
                SELECT id, user_id, content, remind_at, status, created_at
                FROM reminders
                ORDER BY id DESC
                LIMIT ?
                """,
                (limit,),
            )

        rows = cur.fetchall()
        reminders = [
            Reminder(
                id=int(row["id"]),
                user_id=str(row["user_id"]),
                content=str(row["content"]),
                remind_at=self._to_ts(row["remind_at"]),
                status=str(row["status"]),
                created_at=self._to_ts(row["created_at"]),
            )
            for row in rows
        ]
        print(f"[db] reminders listed: status={status or 'all'}, count={len(reminders)}")
        return reminders

    def cancel_reminder_by_id(self, reminder_id: int) -> bool:
        cur = self._conn.cursor()
        cur.execute(
            """
            UPDATE reminders
            SET status = 'cancelled'
            WHERE id = ? AND status = 'pending'
            """,
            (reminder_id,),
        )
        self._conn.commit()
        ok = cur.rowcount > 0
        print(f"[db] reminder cancel admin: id={reminder_id}, success={'yes' if ok else 'no'}")
        return ok

    def clear_done_reminders(self, user_id: int | str) -> int:
        cur = self._conn.cursor()
        cur.execute(
            "DELETE FROM reminders WHERE user_id = ? AND status = 'done'",
            (str(user_id),),
        )
        self._conn.commit()
        count = cur.rowcount if cur.rowcount is not None else 0
        print(f"[db] done reminders cleared: user_id={user_id}, count={count}")
        return int(count)

    def clear_done_reminders_global(self) -> int:
        cur = self._conn.cursor()
        cur.execute("DELETE FROM reminders WHERE status = 'done'")
        self._conn.commit()
        count = cur.rowcount if cur.rowcount is not None else 0
        print(f"[db] done reminders cleared globally: count={count}")
        return int(count)
