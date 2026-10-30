"""Кросс-переходы из планов MyMoney в MyList/MyCalendar (2.51)."""

from pathlib import Path
from unittest.mock import patch

from application.apps_launcher import app_key_for_source, launch_source_app
from application.components.cross_app_budget_card import CrossAppBudgetCard

TASK_ITEM = {"source_app": "task", "title": "Сдать отчёт", "date": "2026-11-03", "amount": None, "currency": ""}


class TestAppKey:
    def test_task_opens_list(self):
        assert app_key_for_source("task") == "list"

    def test_calendar_opens_calendar(self):
        assert app_key_for_source("calendar") == "calendar"

    def test_unknown_source(self):
        assert app_key_for_source("money") is None
        assert app_key_for_source(None) is None


class TestLaunch:
    def test_launches_process_in_app_directory(self):
        directory = Path("C:/repo/MyList")
        with (
            patch("application.apps_launcher.launch_command", return_value=(["python", "main.py"], directory)),
            patch("application.apps_launcher.subprocess.Popen") as popen,
        ):
            assert launch_source_app("task") is True

        popen.assert_called_once_with(["python", "main.py"], cwd=str(directory))

    def test_missing_app_returns_false(self):
        with patch("application.apps_launcher.launch_command", return_value=None):
            assert launch_source_app("calendar") is False

    def test_os_error_returns_false(self):
        with (
            patch("application.apps_launcher.launch_command", return_value=(["python", "main.py"], Path("C:/repo"))),
            patch("application.apps_launcher.subprocess.Popen", side_effect=OSError("boom")),
        ):
            assert launch_source_app("task") is False

    def test_unknown_source_does_not_launch(self):
        with patch("application.apps_launcher.launch_command") as command:
            assert launch_source_app("crypto") is False

        command.assert_not_called()


class TestCardClick:
    def test_card_invokes_open_callback(self):
        calls = []
        card = CrossAppBudgetCard(TASK_ITEM, on_open=calls.append)

        card.on_click(None)

        assert calls == [TASK_ITEM]
        assert card.tooltip == "Открыть в другом приложении"

    def test_card_without_callback_stays_read_only(self):
        card = CrossAppBudgetCard(TASK_ITEM)

        assert card.on_click is None
        assert "только для чтения" in card.tooltip
