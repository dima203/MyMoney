from __future__ import annotations

import contextlib
import json
import os
import tempfile
from pathlib import Path


class OnboardingState:
    """Флаг первого запуска (приветственный экран) в файле настроек приложения."""

    def __init__(self, path: Path | None = None) -> None:
        self._path = path or Path.home() / ".mymoney" / "onboarding.json"

    @property
    def welcome_seen(self) -> bool:
        try:
            raw = json.loads(self._path.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError, UnicodeDecodeError):
            return False
        if not isinstance(raw, dict):
            return False
        return bool(raw.get("welcome_seen", False))

    def mark_welcome_seen(self) -> None:
        with contextlib.suppress(OSError):
            self._write({"welcome_seen": True})

    def _write(self, payload: dict) -> None:
        self._path.parent.mkdir(parents=True, exist_ok=True)
        fd, tmp_name = tempfile.mkstemp(dir=str(self._path.parent), suffix=".tmp")
        with os.fdopen(fd, "w", encoding="utf-8") as fh:
            json.dump(payload, fh, ensure_ascii=False)
        os.replace(tmp_name, self._path)


__all__ = ["OnboardingState"]
