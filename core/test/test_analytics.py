"""Тесты домена аналитики расходов MyMoney (слайс 3.2a)."""

from __future__ import annotations

import datetime

import pytest

from core.analytics import (
    DEFAULT_PERIOD,
    PERIOD_MONTHS,
    UNCATEGORIZED,
    ExpenseRecord,
    ExpenseSummary,
    account_currencies,
    build_summary,
    expense_records,
    expense_total,
    is_snapshot_row,
    month_sequence,
    parse_day,
    period_start,
    preferred_currency,
)

TODAY = datetime.date(2026, 10, 22)
ACCOUNTS = [
    {"id": 1, "resource": "BYN"},
    {"id": 2, "resource": "USD"},
    {"pk": 3, "resource_definition": "BYN"},
]


def tx(day, category, entries, **extra) -> dict:
    row = {"date": day, "category": category, "entries": entries}
    row.update(extra)
    return row


def entry(account: int, amount: float) -> dict:
    return {"account": account, "amount": amount, "quantity": amount, "unit_price": 1}


def rows_sample() -> list[dict]:
    return [
        tx("2026-10-05T10:00:00", "Еда", [entry(1, -100)]),
        tx("2026-10-12T18:30:00", "Еда", [entry(1, -50)]),
        tx("2026-09-20T09:00:00", "Транспорт", [entry(3, -30)]),
        tx("2026-08-01T09:00:00", "Жильё", [entry(1, -500)]),
        tx("2026-07-01T09:00:00", "Жильё", [entry(1, -700)]),
        tx("2026-10-10T09:00:00", "Зарплата", [entry(1, 1000)]),
        tx("2026-10-11T09:00:00", "Перевод", [entry(1, -200), entry(2, 200)]),
        tx("2026-10-13T09:00:00", "Планы", [entry(1, -40)], is_planned=True),
        tx("2026-10-14T09:00:00", "Доллары", [entry(2, -10)]),
    ]


def records_sample() -> list[ExpenseRecord]:
    return expense_records(rows_sample(), account_currencies(ACCOUNTS))


def summary_for(
    rows=None,
    *,
    months: int = 3,
    base_currency: str = "BYN",
    currency: str | None = None,
) -> ExpenseSummary:
    return build_summary(
        rows_sample() if rows is None else rows,
        ACCOUNTS,
        today=TODAY,
        months=months,
        base_currency=base_currency,
        currency=currency,
    )


class TestParseDay:
    def test_iso_datetime(self) -> None:
        assert parse_day("2026-10-05T10:00:00") == datetime.date(2026, 10, 5)

    def test_iso_datetime_with_timezone(self) -> None:
        assert parse_day("2026-10-05T10:00:00+03:00") == datetime.date(2026, 10, 5)

    def test_iso_date(self) -> None:
        assert parse_day("2026-10-05") == datetime.date(2026, 10, 5)

    def test_datetime_and_date_objects(self) -> None:
        assert parse_day(datetime.datetime(2026, 10, 5, 23, 59)) == datetime.date(2026, 10, 5)
        assert parse_day(datetime.date(2026, 10, 5)) == datetime.date(2026, 10, 5)

    def test_garbage_and_empty(self) -> None:
        assert parse_day(None) is None
        assert parse_day("") is None
        assert parse_day("05.10.2026") is None
        assert parse_day(42) is None


class TestExpenseTotal:
    def test_expense_is_positive_module(self) -> None:
        assert expense_total([entry(1, -100), entry(2, -50)]) == 150

    def test_income_is_zero(self) -> None:
        assert expense_total([entry(1, 1000)]) == 0

    def test_transfer_is_zero(self) -> None:
        assert expense_total([entry(1, -200), entry(2, 200)]) == 0

    def test_empty_and_garbage(self) -> None:
        assert expense_total([]) == 0
        assert expense_total(None) == 0
        assert expense_total([{"amount": "oops"}, {"amount": None}]) == 0


class TestAccountCurrencies:
    def test_id_and_pk_fallback(self) -> None:
        assert account_currencies(ACCOUNTS) == {1: "BYN", 2: "USD", 3: "BYN"}

    def test_skips_incomplete_rows(self) -> None:
        accounts = [{"id": 1}, {"resource": "USD"}, {"id": "x", "resource": "USD"}, "oops", {"id": 5, "resource": "  "}]
        assert account_currencies(accounts) == {}


class TestExpenseRecords:
    def test_expenses_only_without_planned_and_transfers(self) -> None:
        records = records_sample()

        assert [(r.category, r.amount) for r in records] == [
            ("Еда", 100.0),
            ("Еда", 50.0),
            ("Транспорт", 30.0),
            ("Жильё", 500.0),
            ("Жильё", 700.0),
            ("Доллары", 10.0),
        ]

    def test_category_fallback_and_unknown_account(self) -> None:
        rows = [tx("2026-10-05", "", [entry(99, -5)]), tx("2026-10-05", None, [entry(1, -7)])]

        records = expense_records(rows, {1: "BYN"})

        assert [(r.category, r.currency, r.amount) for r in records] == [
            (UNCATEGORIZED, "", 5.0),
            (UNCATEGORIZED, "BYN", 7.0),
        ]


class TestSnapshots:
    """2.12: технические снимки OKX не считаются расходами."""

    @pytest.mark.parametrize(
        "extra",
        [
            pytest.param({"read_only": True}, id="server-flag"),
            pytest.param({"description": "okx: snapshot 2026-10-05 07:00"}, id="okx-prefix"),
            pytest.param({"description": "import: snapshot 2026-08-02 12:00"}, id="import-prefix"),
            pytest.param({"read_only": None, "description": "okx: snapshot "}, id="null-flag-falls-back"),
        ],
    )
    def test_snapshot_is_not_an_expense(self, extra: dict) -> None:
        rows = [tx("2026-10-05", "OKX", [entry(1, -15)], **extra)]

        assert expense_records(rows, {1: "BYN"}) == []

    def test_server_flag_false_wins_over_prefix(self) -> None:
        row = tx("2026-10-05", "OKX", [entry(1, -15)], description="okx: snapshot ", read_only=False)

        assert is_snapshot_row(row) is False
        assert [(r.category, r.amount) for r in expense_records([row], {1: "BYN"})] == [("OKX", 15.0)]

    def test_regular_row_is_not_snapshot(self) -> None:
        assert is_snapshot_row(tx("2026-10-05", "Еда", [entry(1, -5)])) is False

    def test_snapshot_does_not_create_okx_category_in_summary(self) -> None:
        rows = [
            tx("2026-10-05", "Еда", [entry(1, -100)]),
            tx("2026-10-06", "OKX", [entry(1, -500)], description="okx: snapshot 2026-10-06 07:00"),
        ]

        summary = summary_for(rows)

        assert [c.category for c in summary.categories] == ["Еда"]
        assert summary.total == 100.0


class TestPreferredCurrency:
    def test_base_currency_wins_when_present(self) -> None:
        records = records_sample()

        assert preferred_currency(records, "BYN") == "BYN"

    def test_falls_back_to_largest_volume(self) -> None:
        records = records_sample()

        assert preferred_currency(records, "EUR") == "BYN"

    def test_empty_records_returns_base(self) -> None:
        assert preferred_currency([], "BYN") == "BYN"


class TestPeriodBoundaries:
    def test_period_start(self) -> None:
        assert period_start(TODAY, 1) == datetime.date(2026, 10, 1)
        assert period_start(TODAY, 3) == datetime.date(2026, 8, 1)
        assert period_start(TODAY, 12) == datetime.date(2025, 11, 1)

    def test_period_start_clamps_zero_months(self) -> None:
        assert period_start(TODAY, 0) == datetime.date(2026, 10, 1)

    def test_month_sequence(self) -> None:
        assert month_sequence(TODAY, 3) == [(2026, 8), (2026, 9), (2026, 10)]
        assert len(month_sequence(TODAY, 12)) == 12
        assert month_sequence(TODAY, 12)[0] == (2025, 11)


class TestBuildSummary:
    def test_totals_months_and_categories(self) -> None:
        summary = summary_for()

        assert summary.currency == "BYN"
        assert summary.period_months == 3
        assert summary.total == 680.0
        assert [p.amount for p in summary.months] == [500.0, 30.0, 150.0]
        assert [(c.category, c.amount) for c in summary.categories] == [
            ("Жильё", 500.0),
            ("Еда", 150.0),
            ("Транспорт", 30.0),
        ]
        assert summary.average_per_month == 680.0 / 3
        assert summary.top_category.category == "Жильё"

    def test_month_labels(self) -> None:
        summary = summary_for()

        assert [p.label for p in summary.months] == ["авг", "сен", "окт"]

    def test_explicit_currency_overrides_base(self) -> None:
        summary = summary_for(currency="USD")

        assert summary.currency == "USD"
        assert summary.total == 10.0

    def test_months_limit_cuts_old_rows(self) -> None:
        summary = summary_for(months=1)

        assert summary.total == 150.0
        assert [p.amount for p in summary.months] == [150.0]

    def test_future_rows_ignored(self) -> None:
        rows = [tx("2026-12-01", "Еда", [entry(1, -99)])]

        summary = summary_for(rows)

        assert summary.total == 0
        assert summary.categories == ()

    def test_empty_rows(self) -> None:
        summary = summary_for([])

        assert summary.currency == "BYN"
        assert summary.total == 0
        assert summary.categories == ()
        assert summary.average_per_month == 0
        assert summary.top_category is None

    def test_default_period_constant(self) -> None:
        assert PERIOD_MONTHS[DEFAULT_PERIOD] == 3
