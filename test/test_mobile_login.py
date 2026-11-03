"""2.164: мобильный вход возвращается в схему приложения MyMoney."""

import tomllib
from pathlib import Path
from unittest.mock import MagicMock

from application.screens import LoginView

APP_KEY = "money"


def _root() -> Path:
    return Path(__file__).resolve().parents[1]


def test_login_view_passes_app_key():
    view = LoginView(backend_url="http://testserver", on_success=MagicMock())

    assert view.app_key == APP_KEY


def test_deep_link_host_matches_app_key():
    config = tomllib.loads((_root() / "pyproject.toml").read_text(encoding="utf-8"))

    deep_linking = config["tool"]["flet"]["deep_linking"]
    assert deep_linking["scheme"] == "myspace"
    assert deep_linking["host"] == APP_KEY
