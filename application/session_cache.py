"""Кэш последних успешных ответов в памяти сессии (2.184).

Ключ — эндпоинт (или логическая витрина) + параметры; на диск ничего не
пишется. Витрины читают снимок при открытии вкладки (мгновенный рендер) и
обновляют его в фоне; любая запись сбрасывает затронутые ключи.
"""

from __future__ import annotations

import threading
from typing import Any

# Ключи витрин: префиксы для точечной инвалидации.
ACCOUNTS = "accounts"
TRANSACTIONS = "transactions"
PROFILE = "profile"
BUDGETS = "budgets"
ANALYTICS = "analytics"


def endpoint_key(endpoint: str, params: dict[str, Any] | None = None) -> str:
    """Ключ ``эндпоинт`` + отсортированные параметры; без параметров — сам эндпоинт."""
    if not params:
        return endpoint
    pairs = "&".join(f"{key}={params[key]}" for key in sorted(params))
    return f"{endpoint}?{pairs}"


class SessionCache:
    """Потокобезопасный кэш в памяти процесса (живёт до выхода из аккаунта)."""

    def __init__(self) -> None:
        self._data: dict[str, Any] = {}
        self._lock = threading.Lock()

    def get(self, key: str) -> Any:
        with self._lock:
            return self._data.get(key)

    def set(self, key: str, value: Any) -> None:
        with self._lock:
            self._data[key] = value

    def has(self, key: str) -> bool:
        with self._lock:
            return key in self._data

    def invalidate(self, *prefixes: str) -> int:
        """Сбросить ключи, начинающиеся с любого префикса; вернуть их число."""
        if not prefixes:
            return 0
        with self._lock:
            stale = [key for key in self._data if key.startswith(tuple(prefixes))]
            for key in stale:
                del self._data[key]
            return len(stale)

    def clear(self) -> None:
        with self._lock:
            self._data.clear()

    def keys(self) -> list[str]:
        with self._lock:
            return list(self._data)


CACHE = SessionCache()


def invalidate_data(*prefixes: str) -> None:
    """Инвалидация витрин после записи (по умолчанию — все списки)."""
    CACHE.invalidate(*(prefixes or (ACCOUNTS, TRANSACTIONS, PROFILE, BUDGETS, ANALYTICS)))


__all__ = [
    "ACCOUNTS",
    "ANALYTICS",
    "BUDGETS",
    "CACHE",
    "PROFILE",
    "TRANSACTIONS",
    "SessionCache",
    "endpoint_key",
    "invalidate_data",
]
