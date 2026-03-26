from __future__ import annotations

import sys
from pathlib import Path
from typing import TextIO


class _TeeStream:
    def __init__(self, original: TextIO, log_file: TextIO) -> None:
        self._original = original
        self._log_file = log_file

    def write(self, data: str) -> int:
        written = self._original.write(data)
        self._log_file.write(data)
        self._log_file.flush()
        return written

    def flush(self) -> None:
        self._original.flush()
        self._log_file.flush()

    def isatty(self) -> bool:
        try:
            return bool(self._original.isatty())
        except Exception:
            return False

    def fileno(self) -> int:
        return self._original.fileno()

    @property
    def encoding(self) -> str | None:
        return getattr(self._original, "encoding", None)

    def __getattr__(self, name: str):
        return getattr(self._original, name)


def setup_runtime_logging(log_path: Path) -> None:
    log_path.parent.mkdir(parents=True, exist_ok=True)
    log_file = log_path.open("a", encoding="utf-8")
    sys.stdout = _TeeStream(sys.stdout, log_file)  # type: ignore[assignment]
    sys.stderr = _TeeStream(sys.stderr, log_file)  # type: ignore[assignment]
