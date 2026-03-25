from __future__ import annotations

from datetime import datetime
from zoneinfo import ZoneInfo


CN_TZ = ZoneInfo("Asia/Shanghai")


def fmt_ts(ts: float) -> str:
    return datetime.fromtimestamp(ts, CN_TZ).strftime("%Y-%m-%d %H:%M:%S")
