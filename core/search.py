"""Глобальный поиск MyMoney: счета и транзакции для палитры Ctrl+K (слайс 1.6).

Слой без Flet и API: принимает «сырые» строки (`AccountView.get_all()`,
`TransactionView.get_all()`), отдаёт иммутабельные `SearchHit` с маршрутом
раздела, куда ведёт выбор.
"""

from __future__ import annotations

from collections.abc import Iterable
from dataclasses import dataclass

ACCOUNT_ROUTE = "/accounts"
TRANSACTION_ROUTE = "/transactions"
PLANNED_ROUTE = "/planned"
DEFAULT_LIMIT = 10
KIND_ACCOUNT = "account"
KIND_TRANSACTION = "transaction"
KIND_PLANNED = "planned"


@dataclass(frozen=True)
class SearchHit:
    """Одна находка палитры: что показать и куда перейти."""

    kind: str
    title: str
    subtitle: str
    route: str


def search_hits(query, transactions, accounts, *, limit: int = DEFAULT_LIMIT) -> list[SearchHit]:
    """Находки по подстроке без учёта регистра; сначала совпадения с начала названия."""
    needle = _text(query).casefold()
    if not needle or limit <= 0:
        return []

    hits = [*_account_hits(accounts, needle), *_transaction_hits(transactions, needle)]
    hits.sort(key=lambda hit: _prefix_rank(hit, needle))
    return hits[:limit]


def _prefix_rank(hit: SearchHit, needle: str) -> bool:
    """False — совпадение с начала названия; сортировка стабильна, поэтому прочий порядок сохраняется."""
    return not hit.title.casefold().startswith(needle)


def _account_hits(accounts, needle: str) -> list[SearchHit]:
    hits: list[SearchHit] = []
    for row in _rows(accounts):
        name = _text(row.get("name"))
        ticker = _text(row.get("resource"))
        if name and _matches(needle, name, ticker):
            hits.append(SearchHit(KIND_ACCOUNT, name, _account_subtitle(ticker), ACCOUNT_ROUTE))
    return hits


def _transaction_hits(rows, needle: str) -> list[SearchHit]:
    hits: list[SearchHit] = []
    for row in _rows(rows):
        description = _text(row.get("description"))
        category = _text(row.get("category"))
        title = description or category
        if not title or not _matches(needle, description, category):
            continue
        planned = bool(row.get("is_planned"))
        kind, route = (KIND_PLANNED, PLANNED_ROUTE) if planned else (KIND_TRANSACTION, TRANSACTION_ROUTE)
        subtitle = _transaction_subtitle(planned, category, _text(row.get("date"))[:10])
        hits.append(SearchHit(kind, title, subtitle, route))
    return hits


def _rows(rows) -> Iterable[dict]:
    """Только строки-словари: мусор (`None`, строки, числа) пропускается."""
    return (row for row in rows or [] if isinstance(row, dict))


def _matches(needle: str, *parts: str) -> bool:
    return needle in " ".join(parts).casefold()


def _account_subtitle(ticker: str) -> str:
    return f"Счёт · {ticker}" if ticker else "Счёт"


def _transaction_subtitle(planned: bool, category: str, day: str) -> str:
    parts = ["План" if planned else "Транзакция", category, day]
    return " · ".join(part for part in parts if part)


def _text(value) -> str:
    return value.strip() if isinstance(value, str) else ""


__all__ = [
    "ACCOUNT_ROUTE",
    "DEFAULT_LIMIT",
    "KIND_ACCOUNT",
    "KIND_PLANNED",
    "KIND_TRANSACTION",
    "PLANNED_ROUTE",
    "TRANSACTION_ROUTE",
    "SearchHit",
    "search_hits",
]
