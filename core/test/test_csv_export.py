"""Тесты CSV-экспорта MyMoney (слайс 3.3a)."""

from __future__ import annotations

import csv
import datetime
from io import StringIO

from core.csv_export import (
    ACCOUNT_HEADER,
    PLANNED_NO,
    PLANNED_YES,
    TRANSACTION_HEADER,
    accounts_csv,
    csv_filename,
    transactions_csv,
)

ACCOUNTS = [
    {"id": 1, "name": "Наличные", "resource": "BYN", "current_balance_qty": 430.5, "group": "", "account_type": "main"},
    {"id": 2, "name": "Крипта", "resource": "USDT", "resource_count": 12, "group": "investments"},
]
TRANSACTIONS = [
    {
        "date": "2026-10-05T10:00:00",
        "category": "Еда",
        "description": "Обед, кафе",
        "entries": [{"account": 1, "amount": -12.345}],
    },
    {
        "date": "2026-11-01",
        "category": "Подписки",
        "description": "",
        "is_planned": True,
        "entries": [{"account": 2, "amount": -5}, {"account": 1, "amount": 5}],
    },
]


def parse(text: str) -> list[list[str]]:
    return list(csv.reader(StringIO(text)))


class TestTransactionsCsv:
    def test_header_and_rows(self) -> None:
        rows = parse(transactions_csv(TRANSACTIONS, ACCOUNTS))

        assert tuple(rows[0]) == TRANSACTION_HEADER
        assert len(rows) == 4  # header + 1 entry + 2 entries

    def test_maps_account_fields_and_amount(self) -> None:
        rows = parse(transactions_csv(TRANSACTIONS, ACCOUNTS))

        assert rows[1] == ["2026-10-05", "Еда", "Обед, кафе", "Наличные", "-12.35", "BYN", PLANNED_NO]

    def test_planned_flag(self) -> None:
        rows = parse(transactions_csv(TRANSACTIONS, ACCOUNTS))

        assert [row[6] for row in rows[2:]] == [PLANNED_YES, PLANNED_YES]

    def test_description_with_separators_survives_round_trip(self) -> None:
        tx = [
            {
                "date": "2026-10-05",
                "category": "Разное",
                "description": 'Кафе "У дома",\n2 этаж',
                "entries": [{"account": 1, "amount": 1}],
            }
        ]

        rows = parse(transactions_csv(tx, ACCOUNTS))

        assert rows[1][2] == 'Кафе "У дома",\n2 этаж'

    def test_unknown_account_leaves_blank_fields(self) -> None:
        tx = [{"date": "2026-10-05", "category": "", "description": "", "entries": [{"account": 99, "amount": 7}]}]

        rows = parse(transactions_csv(tx, ACCOUNTS))

        assert rows[1] == ["2026-10-05", "", "", "", "7.00", "", PLANNED_NO]

    def test_garbage_entries_and_rows_skipped(self) -> None:
        tx = [
            "oops",
            {"date": "2026-10-05", "entries": ["bad", {"account": 1, "amount": None}]},
        ]

        rows = parse(transactions_csv(tx, ACCOUNTS))

        assert len(rows) == 2
        assert rows[1][4] == "0.00"

    def test_empty_input_has_header_only(self) -> None:
        assert parse(transactions_csv([], [])) == [list(TRANSACTION_HEADER)]


class TestAccountsCsv:
    def test_header_and_rows(self) -> None:
        rows = parse(accounts_csv(ACCOUNTS))

        assert tuple(rows[0]) == ACCOUNT_HEADER
        assert rows[1] == ["Наличные", "BYN", "430.50", "", "main"]

    def test_resource_count_fallback_and_default_type(self) -> None:
        rows = parse(accounts_csv(ACCOUNTS))

        assert rows[2] == ["Крипта", "USDT", "12.00", "investments", "main"]

    def test_garbage_skipped(self) -> None:
        rows = parse(accounts_csv([None, "oops"]))

        assert rows == [list(ACCOUNT_HEADER)]


class TestFilename:
    def test_filename(self) -> None:
        assert csv_filename("transactions", datetime.date(2026, 10, 23)) == "mymoney-transactions-2026-10-23.csv"
        assert csv_filename("accounts", datetime.date(2026, 1, 2)) == "mymoney-accounts-2026-01-02.csv"
