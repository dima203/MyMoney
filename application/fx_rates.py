"""Курсы фиатных валют: загрузка с офлайн-фолбэком на последний известный набор (2.50)."""

from __future__ import annotations

import json
import os
import tempfile
from pathlib import Path

from application.api import RestClientError

DEFAULT_FX_PATH = Path.home() / ".myspace" / "fx_rates.json"


def fx_store_path() -> Path:
    """Путь кэша курсов; MYSPACE_FX_RATES_PATH переопределяет его (тесты, отдельные профили)."""
    custom = os.getenv("MYSPACE_FX_RATES_PATH")
    return Path(custom) if custom else DEFAULT_FX_PATH


class FxRateStore:
    """Последние курсы и базовая валюта профиля: переживают перезапуск без сети."""

    def __init__(self, path: str | Path | None = None) -> None:
        self.path = Path(path) if path else fx_store_path()

    def _read(self) -> dict:
        try:
            raw = json.loads(self.path.read_text(encoding="utf-8"))
        except (OSError, ValueError, UnicodeDecodeError):
            return {}
        return raw if isinstance(raw, dict) else {}

    def load(self) -> list[dict]:
        rows = self._read().get("rates")
        return rows if isinstance(rows, list) else []

    def load_profile_base(self) -> str | None:
        base = self._read().get("profile_base")
        return base.strip().upper() if isinstance(base, str) and base.strip() else None

    def save(self, rows: list[dict], profile_base: str | None = None) -> None:
        payload = self._read()
        payload["base"] = "USD"
        payload["rates"] = rows
        if profile_base:
            payload["profile_base"] = profile_base.strip().upper()
        self._write(payload)

    def save_profile_base(self, base: str) -> None:
        """Запомнить базовую валюту профиля, не переписывая файл без изменений."""
        normalized = base.strip().upper()
        if self.load_profile_base() == normalized:
            return
        self.save(self.load(), profile_base=normalized)

    def _write(self, payload: dict) -> None:
        try:
            self.path.parent.mkdir(parents=True, exist_ok=True)
            fd, tmp_path = tempfile.mkstemp(dir=self.path.parent, suffix=".tmp")
        except OSError:
            return
        try:
            with os.fdopen(fd, "w", encoding="utf-8") as handle:
                json.dump(payload, handle, ensure_ascii=False)
            os.replace(tmp_path, self.path)
        except (OSError, TypeError, ValueError):
            try:
                os.unlink(tmp_path)
            except OSError:
                pass


def resolve_profile_base(api_client, store: FxRateStore) -> str | None:
    """Базовая валюта профиля; при сбое сети или пустом ответе — последняя известная из кэша."""
    try:
        profile = api_client.me()
    except RestClientError:
        profile = None
    base = profile.get("base_currency") if isinstance(profile, dict) else None
    base = base.strip().upper() if isinstance(base, str) and base.strip() else None
    if base is None:
        return store.load_profile_base()
    store.save_profile_base(base)
    return base


def load_fx_rows(api_client, store: FxRateStore | None = None) -> list[dict]:
    """Свежие USD-курсы с сервера; при сбое или пустом ответе — последний кэш."""
    store = store or FxRateStore()
    try:
        rows = api_client.get_fx_rates("USD")
    except (RestClientError, AttributeError):
        return store.load()
    if not isinstance(rows, list) or not rows:
        return store.load()
    store.save(rows)
    return rows


__all__ = ["DEFAULT_FX_PATH", "FxRateStore", "fx_store_path", "load_fx_rows", "resolve_profile_base"]
