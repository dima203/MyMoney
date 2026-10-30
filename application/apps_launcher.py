"""Запуск клиентов экосистемы из MyMoney: кросс-планы 2.51."""

from __future__ import annotations

import subprocess  # ruff: ignore[suspicious-subprocess-import] - запуск клиента по реестру MySpaceShared
import sys

from MySpaceShared.core.apps import APP_BY_KEY, launch_command

SOURCE_APPS = {"task": "list", "calendar": "calendar"}


def app_key_for_source(source) -> str | None:
    """Ключ приложения-источника кросс-плана (task → MyList, calendar → MyCalendar)."""
    return SOURCE_APPS.get(str(source or ""))


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


__all__ = ["app_key_for_source", "launch_source_app"]
