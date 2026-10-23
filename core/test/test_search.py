"""Тесты глобального поиска MyMoney: находки и ранжирование (слайс 1.6)."""

from __future__ import annotations

import pytest

from core.search import (
    ACCOUNT_ROUTE,
    KIND_ACCOUNT,
    KIND_PLANNED,
    KIND_TRANSACTION,
    PLANNED_ROUTE,
    TRANSACTION_ROUTE,
    search_hits,
)

ACCOUNTS = [
    {"id": 1, "name": "Наличные", "resource": "BYN"},
    {"id": 2, "name": "Крипта", "resource": "USDT"},
    {"id": 3, "name": ""},
    "oops",
]
TRANSACTIONS = [
    {"id": 1, "date": "2026-10-05T10:00:00", "category": "Еда", "description": "Обед в кафе"},
    {"id": 2, "date": "2026-10-06T10:00:00", "category": "Транспорт", "description": ""},
    {"id": 3, "date": "2026-11-01T10:00:00", "category": "Подписки", "description": "Netflix", "is_planned": True},
]


def hits(query: str, *, limit: int = 10):
    return search_hits(query, TRANSACTIONS, ACCOUNTS, limit=limit)


class TestAccounts:
    def test_matches_name_case_insensitive(self) -> None:
        result = hits("нал")

        assert [hit.kind for hit in result] == [KIND_ACCOUNT]
        assert result[0].title == "Наличные"
        assert result[0].subtitle == "Счёт · BYN"
        assert result[0].route == ACCOUNT_ROUTE

    def test_matches_ticker(self) -> None:
        result = hits("usdt")

        assert [(hit.title, hit.subtitle) for hit in result] == [("Крипта", "Счёт · USDT")]

    def test_account_without_ticker(self) -> None:
        result = search_hits("крипта", [], [{"name": "Крипта"}])

        assert result[0].subtitle == "Счёт"


class TestTransactions:
    def test_matches_description(self) -> None:
        result = hits("обед")

        assert [(hit.kind, hit.title) for hit in result] == [(KIND_TRANSACTION, "Обед в кафе")]
        assert result[0].subtitle == "Транзакция · Еда · 2026-10-05"
        assert result[0].route == TRANSACTION_ROUTE

    def test_matches_category(self) -> None:
        result = hits("транспорт")

        assert [hit.kind for hit in result] == [KIND_TRANSACTION]
        assert result[0].title == "Транспорт"

    def test_planned_hit_goes_to_planned(self) -> None:
        result = hits("netflix")

        assert [(hit.kind, hit.route) for hit in result] == [(KIND_PLANNED, PLANNED_ROUTE)]
        assert result[0].subtitle == "План · Подписки · 2026-11-01"

    def test_empty_description_falls_back_to_category(self) -> None:
        result = search_hits("транспорт", [{"category": "Транспорт", "date": "2026-10-06"}], [])

        assert result[0].title == "Транспорт"

    def test_row_without_text_is_skipped(self) -> None:
        result = search_hits("x", [{"category": "", "description": ""}], [])

        assert result == []


class TestRanking:
    def test_prefix_matches_go_first(self) -> None:
        transactions = [
            {"category": "Кафе", "description": "Обед"},
            {"category": "Обед", "description": ""},
        ]

        result = search_hits("обед", transactions, [])

        assert [hit.title for hit in result] == ["Обед", "Обед"]

    def test_accounts_before_transactions_for_same_prefix(self) -> None:
        result = search_hits("ед", [{"category": "Еда"}], [{"name": "Еда дома", "resource": "BYN"}])

        assert [hit.kind for hit in result] == [KIND_ACCOUNT, KIND_TRANSACTION]

    def test_limit_is_applied(self) -> None:
        result = hits("а", limit=2)

        assert len(result) == 2

    @pytest.mark.parametrize("query", ["", "   ", None])
    def test_blank_query_returns_nothing(self, query) -> None:
        assert hits(query) == []

    def test_zero_limit_returns_nothing(self) -> None:
        assert hits("еда", limit=0) == []

    def test_no_matches(self) -> None:
        assert hits("нет-такого") == []

    def test_garbage_rows_skipped(self) -> None:
        result = search_hits("x", ["oops", None, {"description": None, "category": None}], ["oops"])

        assert result == []
