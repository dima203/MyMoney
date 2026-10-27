"""Тесты экрана «Аналитика» MyMoney (слайс 3.2a; 2.23 — только расходы)."""

from __future__ import annotations

import asyncio
import datetime
from types import SimpleNamespace
from unittest.mock import MagicMock

import flet as ft
import flet_charts as ftc
from application.api import BackendUnreachableError
from application.view.analytics_view import (
    PDF_TOOLTIP,
    AnalyticsView,
    format_money,
    period_caption,
)

TODAY = datetime.date(2026, 10, 22)
ACCOUNTS = [{"id": 1, "resource": "BYN"}, {"id": 2, "resource": "USD"}]


def _walk(control) -> list:
    found = [control]
    for child in getattr(control, "controls", None) or []:
        found.extend(_walk(child))
    content = getattr(control, "content", None)
    if content is not None and not isinstance(content, str):
        found.extend(_walk(content))
    return found


def _texts(control) -> list[str]:
    return [str(item.value) for item in _walk(control) if isinstance(item, ft.Text)]


def _entry(account: int, amount: float) -> dict:
    return {"account": account, "amount": amount, "quantity": amount, "unit_price": 1}


def _rows() -> list[dict]:
    return [
        {"date": "2026-10-05T10:00:00", "category": "Еда", "entries": [_entry(1, -100)]},
        {"date": "2026-10-12T10:00:00", "category": "Еда", "entries": [_entry(1, -50)]},
        {"date": "2026-08-01T10:00:00", "category": "Жильё", "entries": [_entry(1, -500)]},
        {"date": "2026-09-20T10:00:00", "category": "Транспорт", "entries": [_entry(1, -30)]},
    ]


def _api(me=None) -> MagicMock:
    api = MagicMock()
    api.me.return_value = {"base_currency": "BYN"} if me is None else me
    return api


def _ready(view: AnalyticsView) -> AnalyticsView:
    """Фиксирует «сегодня» и отвязывает update от живой Flet-страницы."""
    view._today = lambda: TODAY
    view.update = MagicMock()
    return view


def _view(rows=None, accounts=None, is_online=True, me=None) -> AnalyticsView:
    api = _api(me)
    transaction_view = MagicMock()
    transaction_view.is_online = is_online
    transaction_view.get_all.return_value = _rows() if rows is None else rows
    account_view = MagicMock()
    account_view.get_all.return_value = ACCOUNTS if accounts is None else accounts
    return _ready(
        AnalyticsView(
            route="/analytics",
            api_client=api,
            transaction_view=transaction_view,
            account_view=account_view,
        )
    )


class TestAnalyticsViewLoad:
    def test_starts_in_loading_state(self) -> None:
        view = _view()

        assert view._loading.visible is True
        assert view._body.controls == []
        assert view.selected_index == 4
        assert view.route == "/analytics"

    def test_load_totals_average_and_categories(self) -> None:
        view = _view()

        asyncio.run(view._load_data())

        assert view._loading.visible is False
        texts = _texts(view._content)
        assert "680.00 BYN" in texts
        assert "Расходы за 3 мес." in texts
        assert "В среднем 226.67 BYN в месяц" in texts
        assert "Жильё" in texts
        assert "Еда" in texts
        assert "Транспорт" in texts

    def test_budget_sections_moved_to_budgets_view(self) -> None:
        """2.23: конверты/цели больше не дублируются в аналитике."""
        view = _view()

        asyncio.run(view._load_data())

        texts = _texts(view._content)
        assert "Конверты месяца" not in texts
        assert "Цели накоплений" not in texts
        view.api_client.list_envelopes.assert_not_called()
        view.api_client.list_goals.assert_not_called()

    def test_chart_has_month_groups(self) -> None:
        view = _view()

        asyncio.run(view._load_data())

        charts = [item for item in _walk(view._body) if isinstance(item, ftc.BarChart)]
        assert len(charts) == 1
        groups = charts[0].groups
        assert len(groups) == 3
        assert [group.rods[0].to_y for group in groups] == [500.0, 30.0, 150.0]
        assert groups[2].rods[0].tooltip == "150.00 BYN"
        labels = [label.label.value for label in charts[0].bottom_axis.labels]
        assert labels == ["авг", "сен", "окт"]

    def test_period_change_rebuilds_summary(self) -> None:
        view = _view()
        asyncio.run(view._load_data())

        view._on_period_changed(SimpleNamespace(data="12m"))

        assert view._period == "12m"
        assert view._summary.period_months == 12
        assert view._summary.total == 680.0
        assert "Расходы за год" in _texts(view._content)

    def test_period_change_syncs_selected_segment(self) -> None:
        """Flet 1.0.3 не возвращает selected из клиента — вью ставит его сама."""
        view = _view()
        asyncio.run(view._load_data())
        assert view._period_selector.selected == ["3m"]

        view._on_period_changed(SimpleNamespace(data="12m"))

        assert view._period_selector.selected == ["12m"]

    def test_body_stretches_cards_but_selector_stays_compact(self) -> None:
        view = _view()
        asyncio.run(view._load_data())

        assert view._body.horizontal_alignment == ft.CrossAxisAlignment.STRETCH
        first = view._body.controls[0]
        assert isinstance(first, ft.Row)
        assert first.controls[0] is view._period_selector
        assert isinstance(first.controls[-1], ft.IconButton)
        assert first.controls[-1].tooltip == PDF_TOOLTIP

    def test_period_change_accepts_list_payload(self) -> None:
        view = _view()
        asyncio.run(view._load_data())

        view._on_period_changed(SimpleNamespace(data=["1m"]))

        assert view._period == "1m"
        assert view._summary.total == 150.0

    def test_unknown_period_is_ignored(self) -> None:
        view = _view()
        asyncio.run(view._load_data())

        view._on_period_changed(SimpleNamespace(data="7d"))
        view._on_period_changed(SimpleNamespace(data=None))

        assert view._period == "3m"

    def test_empty_rows_render_empty_state(self) -> None:
        view = _view(rows=[])

        asyncio.run(view._load_data())

        texts = _texts(view._content)
        assert "Нет расходов за период" in texts
        assert "0.00 BYN" in texts

    def test_offline_banner_visible(self) -> None:
        view = _view(is_online=False)

        asyncio.run(view._load_data())

        assert view._connection_banner.visible is True

    def test_backend_unreachable_sets_error(self) -> None:
        view = _view()
        view._transaction_view.get_all.side_effect = BackendUnreachableError("down")

        asyncio.run(view._load_data())

        assert view._error_text.visible is True
        assert "Сервер недоступен" in view._error_text.value
        assert view._loading.visible is False

    def test_api_fallback_accepts_paginated_payload(self) -> None:
        api = _api()
        api.list_transactions.return_value = {"results": _rows()}
        api.list_accounts.return_value = ACCOUNTS
        view = _ready(AnalyticsView(route="/analytics", api_client=api))

        asyncio.run(view._load_data())

        assert view._summary.total == 680.0
        assert view._connection_banner.visible is False


class TestFormatting:
    def test_format_money_thousands(self) -> None:
        assert format_money(1234.5, "BYN") == "1 234.50 BYN"

    def test_format_money_unknown_currency(self) -> None:
        assert format_money(10, "") == "10.00 —"

    def test_period_caption(self) -> None:
        assert period_caption(1) == "за месяц"
        assert period_caption(3) == "за 3 мес."
        assert period_caption(12) == "за год"


class TestPdfExport:
    def _ready(
        self,
        monkeypatch,
        *,
        result="C:/exports/report.pdf",
        error=None,
    ) -> tuple[AnalyticsView, dict, MagicMock]:
        view = _view()
        asyncio.run(view._load_data())
        monkeypatch.setattr(type(view), "page", property(lambda self: MagicMock()))
        state: dict = {}

        async def fake_save(page, *, file_name, content, dialog_title="Сохранить PDF"):
            state["file_name"] = file_name
            state["content"] = content
            if error is not None:
                raise error
            return result

        monkeypatch.setattr("application.view.analytics_view.save_bytes_file", fake_save)
        toast = MagicMock()
        monkeypatch.setattr("application.view.analytics_view.show_toast", toast)
        return view, state, toast

    def test_export_writes_pdf(self, monkeypatch) -> None:
        view, state, toast = self._ready(monkeypatch)

        asyncio.run(view._export_pdf())

        assert state["file_name"] == "mymoney-report-2026-10.pdf"
        assert state["content"].startswith(b"%PDF")
        toast.assert_called_once()
        assert "Сохранено" in toast.call_args.args[1]

    def test_cancelled_dialog_has_no_toast(self, monkeypatch) -> None:
        view, _state, toast = self._ready(monkeypatch, result=None)

        asyncio.run(view._export_pdf())

        toast.assert_not_called()

    def test_write_error_is_reported(self, monkeypatch) -> None:
        view, _state, _toast = self._ready(monkeypatch, error=OSError("disk full"))

        asyncio.run(view._export_pdf())

        assert view._error_text.visible is True
        assert "disk full" in view._error_text.value
