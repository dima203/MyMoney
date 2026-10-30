"""Кросс-переходы из планов MyMoney в MyList/MyCalendar (2.51)."""

from pathlib import Path
from unittest.mock import patch

from application.apps_launcher import app_key_for_source, launch_source_app, open_cross_plan, source_app_title
from application.components.cross_app_budget_card import CrossAppBudgetCard

TASK_ITEM = {"source_app": "task", "title": "Сдать отчёт", "date": "2026-11-03", "amount": None, "currency": ""}
LAUNCH_COMMAND = (["python", "main.py"], Path("C:/repo/MyList"))


class TestAppKey:
    def test_task_opens_list(self):
        assert app_key_for_source("task") == "list"

    def test_calendar_opens_calendar(self):
        assert app_key_for_source("calendar") == "calendar"

    def test_unknown_source(self):
        assert app_key_for_source("money") is None
        assert app_key_for_source(None) is None

    def test_source_title_uses_registry(self):
        assert source_app_title("task") == "MyList"
        assert source_app_title("calendar") == "MyCalendar"


class TestLaunch:
    def test_launches_process_in_app_directory(self):
        with (
            patch("application.apps_launcher.launch_command", return_value=LAUNCH_COMMAND),
            patch("application.apps_launcher.subprocess.Popen") as popen,
        ):
            assert launch_source_app("task") is True

        popen.assert_called_once_with(LAUNCH_COMMAND[0], cwd=str(LAUNCH_COMMAND[1]))

    def test_missing_app_returns_false(self):
        with patch("application.apps_launcher.launch_command", return_value=None):
            assert launch_source_app("calendar") is False

    def test_os_error_returns_false(self):
        with (
            patch("application.apps_launcher.launch_command", return_value=LAUNCH_COMMAND),
            patch("application.apps_launcher.subprocess.Popen", side_effect=OSError("boom")),
        ):
            assert launch_source_app("task") is False

    def test_unknown_source_does_not_launch(self):
        with patch("application.apps_launcher.launch_command") as command:
            assert launch_source_app("crypto") is False

        command.assert_not_called()


class TestOpenCrossPlan:
    def test_success_shows_toast(self):
        errors: list[str] = []
        page = object()
        with (
            patch("application.apps_launcher.launch_source_app", return_value=True),
            patch("application.components.file_save.show_toast") as toast,
        ):
            open_cross_plan(page, TASK_ITEM, errors.append)

        toast.assert_called_once_with(page, "Открываю MyList")
        assert errors == []

    def test_failure_reports_error(self):
        errors: list[str] = []
        with patch("application.apps_launcher.launch_source_app", return_value=False):
            open_cross_plan(object(), TASK_ITEM, errors.append)

        assert errors == ["MyList не найден рядом с MyMoney"]


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
