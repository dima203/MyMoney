"""CSV-экспорт MyMoney: операции и счета (слайс 3.3a).

Слой без Flet: принимает «сырые» строки (`TransactionView.get_all()`,
`AccountView.get_all()`), отдаёт CSV-текст. Файл пишется вызывающим кодом
в UTF-8 с BOM, чтобы Excel открывал кириллицу без ручной настройки.
"""

from __future__ import annotations

import csv
from datetime import date
from io import StringIO

TRANSACTION_HEADER = ("date", "category", "description", "account", "amount", "currency", "planned")
ACCOUNT_HEADER = ("name", "currency", "balance", "group", "type")
PLANNED_YES = "yes"
PLANNED_NO = "no"
DEFAULT_ACCOUNT_TYPE = "main"
LINE_TERMINATOR = "\n"
FILE_PREFIX = "mymoney"


def transactions_csv(transactions, accounts) -> str:
    """Одна строка CSV на проводку: дата, категория, описание, счёт, сумма, валюта, план."""
    return _write_csv(TRANSACTION_HEADER, _transaction_rows(transactions, _account_map(accounts)))


def accounts_csv(accounts) -> str:
    """Одна строка CSV на счёт: название, валюта, баланс, группа, тип."""
    return _write_csv(ACCOUNT_HEADER, (_account_row(account) for account in _dict_rows(accounts)))


def csv_filename(kind: str, today: date) -> str:
    """Имя файла: `mymoney-transactions-2026-10-23.csv`."""
    return f"{FILE_PREFIX}-{kind}-{today.isoformat()}.csv"


def _write_csv(header, rows) -> str:
    buffer = StringIO()
    writer = csv.writer(buffer, lineterminator=LINE_TERMINATOR)
    writer.writerow(header)
    writer.writerows(rows)
    return buffer.getvalue()


def _transaction_rows(transactions, account_map: dict):
    for transaction in _dict_rows(transactions):
        base = [
            _text(transaction.get("date"))[:10],
            _text(transaction.get("category")),
            _text(transaction.get("description")),
        ]
        planned = PLANNED_YES if transaction.get("is_planned") else PLANNED_NO
        for entry in transaction.get("entries") or []:
            if not isinstance(entry, dict):
                continue
            account = account_map.get(entry.get("account"), {})
            yield [
                *base,
                _text(account.get("name")),
                _amount(entry.get("amount")),
                _text(account.get("resource")),
                planned,
            ]


def _account_row(account: dict) -> list[str]:
    return [
        _text(account.get("name")),
        _text(account.get("resource")),
        _amount(account.get("current_balance_qty", account.get("resource_count"))),
        _text(account.get("group")),
        _text(account.get("account_type")) or DEFAULT_ACCOUNT_TYPE,
    ]


def _account_map(accounts) -> dict:
    """id счёта → строка счёта; строки без id не участвуют в маппинге."""
    return {row.get("id"): row for row in _dict_rows(accounts) if row.get("id") is not None}


def _dict_rows(value):
    """Только словарные строки: мусор из источников не должен ломать экспорт."""
    return (row for row in value or [] if isinstance(row, dict))


def _amount(value) -> str:
    try:
        return f"{float(value):.2f}"
    except (TypeError, ValueError):
        return "0.00"


def _text(value) -> str:
    return value.strip() if isinstance(value, str) else ""


__all__ = [
    "ACCOUNT_HEADER",
    "PLANNED_NO",
    "PLANNED_YES",
    "TRANSACTION_HEADER",
    "accounts_csv",
    "csv_filename",
    "transactions_csv",
]
