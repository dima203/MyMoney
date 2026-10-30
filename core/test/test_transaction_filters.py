from datetime import date, datetime

from core.transaction_filters import (
    filter_transactions,
    has_active_filters,
    in_period,
    transaction_type,
    tx_account_ids,
    tx_total,
)

TODAY = date(2026, 10, 30)


def _tx(date_str: str, amount: float, account: int = 1, category: str = "Еда", second: dict | None = None) -> dict:
    entries = [{"account": account, "amount": amount}]
    if second is not None:
        entries.append(second)
    return {"date": f"{date_str}T10:00:00", "entries": entries, "category": category}


class TestTxHelpers:
    def test_total_sums_entries(self):
        tx = _tx("2026-10-01", -50.0, second={"account": 2, "amount": 50.0})
        assert tx_total(tx) == 0.0

    def test_account_ids(self):
        tx = _tx("2026-10-01", -50.0, account=1, second={"account": 7, "amount": 50.0})
        assert tx_account_ids(tx) == {1, 7}

    def test_type_expense_income(self):
        assert transaction_type(_tx("2026-10-01", -10.0)) == "expense"
        assert transaction_type(_tx("2026-10-01", 10.0)) == "income"

    def test_type_transfer(self):
        tx = _tx("2026-10-01", -10.0, account=1, second={"account": 2, "amount": 10.0})
        assert transaction_type(tx) == "transfer"

    def test_date_parsing(self):
        assert in_period(date(2026, 10, 1), "month", TODAY) is True
        assert in_period(None, "month", TODAY) is False
        assert in_period(date(2026, 9, 30), "prev_month", TODAY) is True
        assert in_period(date(2026, 10, 30), "7d", TODAY) is True
        assert in_period(date(2026, 10, 1), "30d", TODAY) is True
        assert in_period(date(2026, 10, 30), "all", TODAY) is True


class TestFilterTransactions:
    def test_no_filters_keeps_everything(self):
        rows = [_tx("2026-10-01", -10.0), _tx("2026-09-01", 5.0)]
        assert filter_transactions(rows, today=TODAY) == rows

    def test_period_month(self):
        rows = [_tx("2026-10-01", -10.0), _tx("2026-09-01", 5.0)]
        result = filter_transactions(rows, period="month", today=TODAY)
        assert [tx["date"][:7] for tx in result] == ["2026-10"]

    def test_account(self):
        rows = [_tx("2026-10-01", -10.0, account=1), _tx("2026-10-02", -10.0, account=2)]
        result = filter_transactions(rows, account_id=2, today=TODAY)
        assert len(result) == 1
        assert tx_account_ids(result[0]) == {2}

    def test_type(self):
        rows = [
            _tx("2026-10-01", -10.0),
            _tx("2026-10-02", 20.0),
            _tx("2026-10-03", -5.0, second={"account": 2, "amount": 5.0}),
        ]
        assert len(filter_transactions(rows, tx_type="income", today=TODAY)) == 1
        assert len(filter_transactions(rows, tx_type="transfer", today=TODAY)) == 1
        assert len(filter_transactions(rows, tx_type="expense", today=TODAY)) == 1

    def test_category(self):
        rows = [_tx("2026-10-01", -10.0, category="Еда"), _tx("2026-10-02", -10.0, category="Транспорт")]
        result = filter_transactions(rows, category="Транспорт", today=TODAY)
        assert [tx["category"] for tx in result] == ["Транспорт"]

    def test_combined(self):
        rows = [
            _tx("2026-10-01", -10.0, account=1, category="Еда"),
            _tx("2026-10-02", -10.0, account=2, category="Еда"),
            _tx("2026-09-01", -10.0, account=2, category="Еда"),
        ]
        result = filter_transactions(rows, period="month", account_id="2", category="Еда", today=TODAY)
        assert len(result) == 1
        assert result[0]["date"].startswith("2026-10-02")

    def test_bad_account_value_ignored(self):
        rows = [_tx("2026-10-01", -10.0)]
        assert filter_transactions(rows, account_id="abc", today=TODAY) == rows

    def test_active_filters(self):
        assert has_active_filters() is False
        assert has_active_filters(period="month") is True
        assert has_active_filters(account_id=2) is True
        assert has_active_filters(tx_type="income") is True
        assert has_active_filters(category="Еда") is True


def test_filter_uses_today_default(monkeypatch):
    class FixedDate(datetime):
        @classmethod
        def now(cls, tz=None):
            return datetime(2026, 10, 30, 12, 0, 0)

    monkeypatch.setattr("core.transaction_filters.datetime", FixedDate)
    rows = [_tx("2026-10-30", -1.0), _tx("2026-08-01", -1.0)]
    assert len(filter_transactions(rows, period="month")) == 1


def test_prev_month_across_year_boundary():
    assert in_period(date(2026, 12, 31), "prev_month", date(2027, 1, 5)) is True
    assert in_period(date(2026, 11, 30), "prev_month", date(2027, 1, 5)) is False


def test_rolling_windows_exclude_edges():
    today = date(2026, 10, 30)
    assert in_period(date(2026, 10, 23), "7d", today) is False
    assert in_period(date(2026, 10, 24), "7d", today) is True
    assert in_period(date(2026, 9, 30), "30d", today) is False
    assert in_period(date(2026, 10, 1), "30d", today) is True


def test_bad_account_does_not_activate_filters():
    assert has_active_filters(account_id="abc") is False
