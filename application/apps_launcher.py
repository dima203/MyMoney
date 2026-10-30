"""Запуск клиентов экосистемы из MyMoney: кросс-планы 2.51."""

from __future__ import annotations

import subprocess  # ruff: ignore[suspicious-subprocess-import] - запуск клиента по реестру MySpaceShared
import sys
from collections.abc import Callable

from MySpaceShared.core.apps import APP_BY_KEY, launch_command

SOURCE_APPS = {"task": "list", "calendar": "calendar"}
DEFAULT_SOURCE_KEY = "calendar"


def app_key_for_source(source) -> str | None:
    """Ключ приложения-источника кросс-плана (task → MyList, calendar → MyCalendar)."""
    return SOURCE_APPS.get(str(source or ""))


def source_app_title(source) -> str:
    """Название клиента-источника для сообщений UI (task → MyList, calendar → MyCalendar)."""
    return APP_BY_KEY[SOURCE_APPS.get(str(source or ""), DEFAULT_SOURCE_KEY)].title


def launch_source_app(source) -> bool:
    """Запустить клиент источника отдельным процессом; False — приложение не найдено."""
    key = app_key_for_source(source)
    if key is None:
        return False
    command = launch_command(APP_BY_KEY[key], python=sys.executable)
    if command is None:
        return False
    cmd, directory = command
    try:
        subprocess.Popen(cmd, cwd=str(directory))  # ruff: ignore[subprocess-without-shell-equals-true] - команда из реестра
    except OSError:
        return False
    return True


def open_cross_plan(page, item: dict, on_error: Callable[[str], None]) -> None:
    """Открыть источник кросс-плана: тост при успехе, ``on_error`` — если клиента нет рядом."""
    from application.components.file_save import show_toast

    source = item.get("source_app")
    title = source_app_title(source)
    if launch_source_app(source):
        show_toast(page, f"Открываю {title}")
        return
    on_error(f"{title} не найден рядом с MyMoney")


__all__ = ["app_key_for_source", "launch_source_app", "open_cross_plan", "source_app_title"]
