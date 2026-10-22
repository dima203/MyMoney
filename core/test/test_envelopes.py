"""Тесты бюджетов-конвертов MyMoney: прогресс лимитов и тело запроса (3.2b)."""

from __future__ import annotations

import datetime

import pytest

from core.envelopes import EnvelopeProgress, envelope_payload, envelope_progress

TODAY = datetime.date(2026, 10, 22)
ACCOUNTS = [
    {"id": 1, "resource": "BYN", "resource_definition": 11},
    {"id": 2, "resource": "USD", "resource_definition": 12},
]


def entry(account: int, amount: float) -> dict:
    return {"account": account, "amount": amount, "quantity": amount, "unit_price": 1}


def tx(day: str, category: str, entries: list[dict], **extra) -> dict:
    row = {"date": day, "category": category, "entries": entries}
    row.update(extra)
    return row


def rows_sample() -> list[dict]:
    return [
        tx("2026-10-05", "Еда", [entry(1, -100)]),
        tx("2026-10-12", "еда", [entry(1, -50)]),
        tx("2026-09-30", "Еда", [entry(1, -999)]),
        tx("2026-10-06", "Еда", [entry(2, -10)]),
        tx("2026-10-07", "Еда", [entry(1, -40)], is_planned=True),
        tx("2026-10-08", "Еда", [entry(1, 500)]),
        tx("2026-10-09", "Перевод", [entry(1, -70), entry(2, 70)]),
        tx("2026-10-10", "Транспорт", [entry(1, -30)]),
    ]


def envelope(**overrides) -> dict:
    row = {"id": 1, "category": "Еда", "limit_amount": "200.0000", "currency_ticker": "BYN", "currency": 11}
    row.update(overrides)
    return row


def progress_for(envelopes, base_currency: str = "BYN") -> list[EnvelopeProgress]:
    return envelope_progress(envelopes, rows_sample(), ACCOUNTS, today=TODAY, base_currency=base_currency)


class TestEnvelopeProgress:
    def test_month_spent_is_case_insensitive(self) -> None:
        item = progress_for([envelope()])[0]

        assert item.category == "Еда"
        assert item.limit_amount == 200.0
        assert item.currency == "BYN"
        assert item.spent == 150.0
        assert item.remaining == 50.0
        assert item.share == 0.75
        assert item.is_over is False
        assert item.overspent == 0.0

    def test_over_limit(self) -> None:
        item = progress_for([envelope(category="Транспорт", limit_amount="20")])[0]

        assert item.spent == 30.0
        assert item.is_over is True
        assert item.overspent == 10.0
        assert item.share == 1.0
        assert item.remaining == -10.0

    def test_currency_from_ticker_or_base(self) -> None:
        items = progress_for(
            [
                envelope(category="Еда", currency_ticker=None, currency=None),
                envelope(id=2, category="Еда", currency_ticker="USD", currency=12),
            ],
            base_currency="USD",
        )

        assert (items[0].currency, items[0].spent) == ("USD", 10.0)
        assert (items[1].currency, items[1].spent) == ("USD", 10.0)

    def test_empty_currency_means_base_currency(self) -> None:
        item = progress_for([envelope(currency_ticker=None, currency=None)], base_currency="BYN")[0]

        assert item.currency == "BYN"
        assert item.spent == 150.0

    def test_unknown_currency_without_base_has_no_spent(self) -> None:
        item = progress_for([envelope(currency_ticker=None, currency=None)], base_currency="")[0]

        assert item.currency == ""
        assert item.spent == 0.0

    def test_previous_month_and_income_are_ignored(self) -> None:
        items = progress_for([envelope(category="Еда", limit_amount="1000")])

        assert items[0].spent == 150.0

    def test_garbage_rows_skipped(self) -> None:
        items = progress_for([envelope(category=" "), "oops", envelope(id=None, category="Транспорт")])

        assert [item.category for item in items] == ["Транспорт"]
        assert items[0].envelope_id is None

    def test_no_envelopes(self) -> None:
        assert progress_for([]) == []

    def test_zero_limit_share_is_zero(self) -> None:
        item = EnvelopeProgress(None, "Еда", 0.0, "BYN", 10.0)

        assert item.share == 0.0
        assert item.is_over is True


class TestEnvelopePayload:
    def test_valid_payload(self) -> None:
        assert envelope_payload("  Еда ", "500", 11) == {
            "category": "Еда",
            "limit_amount": "500.0000",
            "currency": 11,
        }

    def test_comma_and_spaces_in_limit(self) -> None:
        assert envelope_payload("Еда", "1 234,50")["limit_amount"] == "1234.5000"

    def test_currency_is_optional(self) -> None:
        assert envelope_payload("Еда", 100)["currency"] is None

    @pytest.mark.parametrize("category", ["", "   ", None])
    def test_blank_category_rejected(self, category) -> None:
        with pytest.raises(ValueError, match="категорию"):
            envelope_payload(category, "100")

    @pytest.mark.parametrize("limit", ["", "abc", None, 0, -5])
    def test_bad_limit_rejected(self, limit) -> None:
        with pytest.raises(ValueError):
            envelope_payload("Еда", limit)
