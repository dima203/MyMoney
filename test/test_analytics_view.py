"""Тесты экрана «Аналитика» MyMoney (слайс 3.2a; 2.23 — только расходы)."""

from __future__ import annotations

import asyncio
import datetime
from types import SimpleNamespace
from unittest.mock import MagicMock

import flet as ft
import flet_charts as ftc
import pytest
from application.api import BackendUnreachableError
from application.view.analytics_view import (
    BAR_WIDTH,
    PDF_TOOLTIP,
    AnalyticsView,
    axis_label,
    chart_ticks,
    format_money,
    period_caption,
)
from core.analytics import CategoryTotal, ExpenseSummary

from MySpaceShared.core.charts import chart_palette

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


def _charts(control) -> list[ftc.BarChart]:
    return [item for item in _walk(control) if isinstance(item, ftc.BarChart)]


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
        assert view.selected_index == 3
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


class TestChartAxis:
    def test_ticks_are_round_and_cover_max(self) -> None:
        assert chart_ticks(500) == [0.0, 200.0, 400.0, 600.0]
        assert chart_ticks(680) == [0.0, 200.0, 400.0, 600.0, 800.0]
        assert chart_ticks(21.3) == [0.0, 10.0, 20.0, 30.0]

    @pytest.mark.parametrize("max_amount", [0, 1, 7, 21.3, 150, 500, 680, 12345])
    def test_tick_labels_have_no_duplicates(self, max_amount: float) -> None:
        ticks = chart_ticks(max_amount)
        step = ticks[1] - ticks[0]
        labels = [axis_label(value, step) for value in ticks]

        assert len(set(labels)) == len(labels)

    def test_axis_label_groups_thousands(self) -> None:
        assert axis_label(12345) == "12 345"
        assert axis_label(0.0) == "0"

    def test_chart_uses_last_tick_as_max_y(self) -> None:
        view = _view()
        asyncio.run(view._load_data())

        chart = _charts(view._body)[0]

        assert chart.min_y == 0
        assert chart.max_y == 600.0
        assert chart.horizontal_grid_lines.interval == 200.0
        assert [label.label.value for label in chart.left_axis.labels] == ["0", "200", "400", "600"]
        assert chart.left_axis.label_size == 36.0

    def test_single_month_keeps_fixed_rod_width(self) -> None:
        view = _view()
        view._period = "1m"
        asyncio.run(view._load_data())

        chart = _charts(view._body)[0]

        assert len(chart.groups) == 1
        assert chart.groups[0].rods[0].width == BAR_WIDTH
        assert chart.max_y == 150.0


class TestCategoryList:
    @staticmethod
    def _summary(*categories: CategoryTotal) -> ExpenseSummary:
        total = sum(category.amount for category in categories if category.amount > 0)
        return ExpenseSummary("BYN", 1, total, (), tuple(categories))

    def test_bars_use_distinct_palette_colors(self) -> None:
        view = _view()
        asyncio.run(view._load_data())

        bars = [item for item in _walk(view._body) if isinstance(item, ft.ProgressBar)]
        colors = [bar.color for bar in bars]

        assert len(colors) == 3
        assert len(set(colors)) == 3
        assert colors == chart_palette(3)
        assert all(bar.height == 6 and bar.border_radius == 3 for bar in bars)

    def test_category_shows_share_percent(self) -> None:
        view = _view()
        asyncio.run(view._load_data())

        texts = _texts(view._content)

        assert "73.53%" in texts
        assert "22.06%" in texts
        assert "4.41%" in texts

    def test_zero_share_category_hidden(self) -> None:
        view = _view()
        summary = self._summary(CategoryTotal("Еда", 100.0), CategoryTotal("Пусто", 0.0))

        control = view._category_list(summary)
        texts = _texts(control)

        assert "Еда" in texts
        assert "Пусто" not in texts
        assert "100.00%" in texts
        assert len([item for item in _walk(control) if isinstance(item, ft.ProgressBar)]) == 1

    def test_negative_category_hidden(self) -> None:
        view = _view()
        summary = self._summary(CategoryTotal("Еда", 100.0), CategoryTotal("Возврат", -20.0))

        texts = _texts(view._category_list(summary))

        assert "Еда" in texts
        assert "Возврат" not in texts


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


class TestCompositionHint:
    def test_hint_lists_inclusions_and_exclusions(self) -> None:
        view = _view()
        summary = ExpenseSummary("BYN", 3, 100.0, (), ())

        text = view._composition_hint(summary).value

        assert "BYN" in text
        assert "за 3 мес." in text
        assert "переводы" in text
        assert "OKX" in text

    def test_hint_falls_back_to_account_currencies(self) -> None:
        view = _view()
        summary = ExpenseSummary("", 1, 0.0, (), ())

        assert "валюте счетов" in view._composition_hint(summary).value
