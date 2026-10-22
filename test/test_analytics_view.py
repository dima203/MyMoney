"""Тесты экрана «Аналитика» MyMoney (слайс 3.2a)."""

from __future__ import annotations

import asyncio
import datetime
from types import SimpleNamespace
from unittest.mock import MagicMock

import flet as ft
import flet_charts as ftc
from application.api import BackendUnreachableError
from application.view.analytics_view import (
    ENVELOPES_EMPTY,
    ENVELOPES_OFFLINE,
    AnalyticsView,
    format_money,
    limit_text,
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
    api.list_envelopes.return_value = []
    return api


def _ready(view: AnalyticsView) -> AnalyticsView:
    """Фиксирует «сегодня» и отвязывает update от живой Flet-страницы."""
    view._today = lambda: TODAY
    view.update = MagicMock()
    return view


def _view(rows=None, accounts=None, is_online=True, me=None, envelopes=None) -> AnalyticsView:
    api = _api(me)
    if envelopes is not None:
        api.list_envelopes.return_value = envelopes
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


def _envelope(**overrides) -> dict:
    row = {"id": 1, "category": "Еда", "limit_amount": "100.0000", "currency_ticker": "BYN", "currency": None}
    row.update(overrides)
    return row


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
        assert first.controls == [view._period_selector]

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

    def test_limit_text_strips_trailing_zeros(self) -> None:
        assert limit_text("500.0000") == "500"
        assert limit_text("650.50") == "650.5"
        assert limit_text(0) == "0"
        assert limit_text(None) == ""
        assert limit_text("oops") == ""


class TestEnvelopesSection:
    def test_renders_progress_and_overspending(self) -> None:
        view = _view(envelopes=[_envelope()])

        asyncio.run(view._load_data())

        texts = _texts(view._content)
        assert "Конверты месяца" in texts
        assert "150.00 BYN из 100.00 BYN" in texts
        assert "Превышение на 50.00 BYN" in texts
        bars = [item for item in _walk(view._body) if isinstance(item, ft.ProgressBar)]
        assert any(bar.color == ft.Colors.ERROR and bar.value == 1.0 for bar in bars)

    def test_renders_envelope_within_limit(self) -> None:
        view = _view(envelopes=[_envelope(limit_amount="300")])

        asyncio.run(view._load_data())

        texts = _texts(view._content)
        assert "150.00 BYN из 300.00 BYN" in texts
        assert not [text for text in texts if text.startswith("Превышение")]
        bars = [item for item in _walk(view._body) if isinstance(item, ft.ProgressBar)]
        assert any(bar.color == ft.Colors.PRIMARY and bar.value == 0.5 for bar in bars)

    def test_empty_state_has_add_button(self) -> None:
        view = _view()

        asyncio.run(view._load_data())

        texts = _texts(view._content)
        assert ENVELOPES_EMPTY in texts
        buttons = [item for item in _walk(view._body) if isinstance(item, ft.TextButton)]
        assert any(button.content == "Добавить" for button in buttons)

    def test_offline_shows_hint_without_request(self) -> None:
        view = _view(is_online=False)

        asyncio.run(view._load_data())

        assert ENVELOPES_OFFLINE in _texts(view._content)
        view.api_client.list_envelopes.assert_not_called()

    def test_backend_error_keeps_charts_alive(self) -> None:
        view = _view()
        view.api_client.list_envelopes.side_effect = BackendUnreachableError("down")

        asyncio.run(view._load_data())

        texts = _texts(view._content)
        assert ENVELOPES_OFFLINE in texts
        assert "680.00 BYN" in texts
        assert view._error_text.visible is False

    def test_currency_options_map_resource_ids(self) -> None:
        accounts = [
            {"id": 1, "resource": "BYN", "resource_definition": 11},
            {"id": 2, "resource": "USD", "resource_definition": 12},
            {"id": 3, "resource": "BYN", "resource_definition": 11},
            {"id": 4, "resource": "EUR"},
        ]
        view = _view(accounts=accounts)

        asyncio.run(view._load_data())

        assert view._currency_options() == {"BYN": 11, "USD": 12, "EUR": None}

    def test_paginated_envelopes_payload(self) -> None:
        view = _view(envelopes={"results": [_envelope()]})

        asyncio.run(view._load_data())

        assert "150.00 BYN из 100.00 BYN" in _texts(view._content)


class TestEnvelopeDialog:
    def test_edit_dialog_prefilled_and_stretched(self) -> None:
        view = _view()
        view._envelopes = [_envelope(limit_amount="300.0000")]

        dialog = view._envelope_dialog(view._envelopes[0])

        assert dialog.title.value == "Изменить конверт"
        fields = dialog.content.content.controls
        assert [field.value for field in fields[:3]] == ["Еда", "300", "BYN"]
        assert dialog.content.content.horizontal_alignment == ft.CrossAxisAlignment.STRETCH
        assert fields[0].autofocus is True

    def test_new_dialog_defaults(self) -> None:
        view = _view()
        asyncio.run(view._load_data())

        dialog = view._envelope_dialog({})

        assert dialog.title.value == "Новый конверт"
        fields = dialog.content.content.controls
        assert fields[0].value == ""
        assert fields[1].value == ""
        assert fields[2].value == "BYN"
        assert [field.text for field in fields[2].options] == ["BYN", "USD"]
        assert dialog.actions[1].content == "Сохранить"
