"""Тесты целей накоплений MyMoney: прогресс, тело запроса, пополнения (3.2c)."""

from __future__ import annotations

import datetime

import pytest

from core.goals import GoalProgress, contribution_payload, goal_payload, goal_progress, parse_amount, parse_deadline

TODAY = datetime.date(2026, 10, 23)


def goal(**overrides) -> dict:
    row = {
        "id": 1,
        "name": "Отпуск",
        "target_amount": "3000.0000",
        "saved_amount": "1200.0000",
        "currency_ticker": "BYN",
        "deadline": "2027-06-01",
    }
    row.update(overrides)
    return row


class TestGoalProgress:
    def test_remaining_and_share(self) -> None:
        item = GoalProgress(1, "Отпуск", 3000.0, 1200.0, "BYN", datetime.date(2027, 6, 1))

        assert item.remaining == 1800.0
        assert item.share == 0.4
        assert item.is_reached is False

    def test_reached_goal_has_no_remaining(self) -> None:
        item = GoalProgress(1, "Отпуск", 1000.0, 1500.0, "BYN")

        assert item.remaining == 0.0
        assert item.share == 1.0
        assert item.is_reached is True

    def test_zero_target_share_is_zero(self) -> None:
        item = GoalProgress(None, "Странная", 0.0, 100.0, "")

        assert item.share == 0.0
        assert item.is_reached is False

    def test_days_left_and_overdue(self) -> None:
        item = GoalProgress(1, "Отпуск", 3000.0, 100.0, "BYN", TODAY + datetime.timedelta(days=10))
        overdue = GoalProgress(2, "Срок", 3000.0, 100.0, "BYN", TODAY - datetime.timedelta(days=1))
        reached_overdue = GoalProgress(3, "Готово", 100.0, 100.0, "BYN", TODAY - datetime.timedelta(days=5))

        assert item.days_left(TODAY) == 10
        assert item.is_overdue(TODAY) is False
        assert overdue.days_left(TODAY) == -1
        assert overdue.is_overdue(TODAY) is True
        assert reached_overdue.is_overdue(TODAY) is False
        assert GoalProgress(4, "Без срока", 10.0, 0.0, "").days_left(TODAY) is None


class TestAmountParsing:
    def test_comma_and_spaces(self) -> None:
        assert parse_amount("1 234,50", "цель") == 1234.5

    @pytest.mark.parametrize("value", [None, "", "  ", "abc"])
    def test_bad_amount(self, value) -> None:
        with pytest.raises(ValueError):
            parse_amount(value, "цель")


class TestGoalPayload:
    def test_valid_payload(self) -> None:
        assert goal_payload("  Отпуск  ", "3 000", "1 200", 11, "2027-06-01") == {
            "name": "Отпуск",
            "target_amount": "3000.0000",
            "saved_amount": "1200.0000",
            "currency": 11,
            "deadline": "2027-06-01",
        }

    def test_saved_defaults_to_zero(self) -> None:
        assert goal_payload("Отпуск", "1000", None)["saved_amount"] == "0.0000"
        assert goal_payload("Отпуск", "1000", "")["saved_amount"] == "0.0000"

    def test_currency_and_deadline_optional(self) -> None:
        payload = goal_payload("Отпуск", "1000")

        assert payload["currency"] is None
        assert payload["deadline"] is None

    @pytest.mark.parametrize("name", ["", "   ", None])
    def test_blank_name_rejected(self, name) -> None:
        with pytest.raises(ValueError, match="название"):
            goal_payload(name, "100")

    @pytest.mark.parametrize("target", [None, "", "abc", 0, -10])
    def test_bad_target_rejected(self, target) -> None:
        with pytest.raises(ValueError):
            goal_payload("Отпуск", target)

    def test_negative_saved_rejected(self) -> None:
        with pytest.raises(ValueError, match="отрицательным"):
            goal_payload("Отпуск", "100", "-1")

    @pytest.mark.parametrize("value", ["2027-13-01", "01.06.2027", "завтра"])
    def test_bad_deadline_rejected(self, value) -> None:
        with pytest.raises(ValueError, match="формате"):
            parse_deadline(value)

    def test_blank_deadline_is_none(self) -> None:
        assert parse_deadline("") is None
        assert parse_deadline(None) is None


class TestContribution:
    def test_adds_to_saved(self) -> None:
        assert contribution_payload("1200.5000", "300") == {"saved_amount": "1500.5000"}

    def test_missing_saved_starts_from_zero(self) -> None:
        assert contribution_payload(None, 50) == {"saved_amount": "50.0000"}

    @pytest.mark.parametrize("amount", [None, "", "abc", 0, -5])
    def test_bad_amount_rejected(self, amount) -> None:
        with pytest.raises(ValueError):
            contribution_payload(100, amount)


class TestGoalProgressMapping:
    def test_maps_rows(self) -> None:
        items = goal_progress([goal()], base_currency="USD")

        assert len(items) == 1
        assert items[0].goal_id == 1
        assert items[0].name == "Отпуск"
        assert (items[0].target_amount, items[0].saved_amount) == (3000.0, 1200.0)
        assert items[0].currency == "BYN"
        assert items[0].deadline == datetime.date(2027, 6, 1)

    def test_empty_ticker_uses_base_currency(self) -> None:
        items = goal_progress([goal(currency_ticker=None)], base_currency="USD")

        assert items[0].currency == "USD"

    def test_unknown_currency_without_base(self) -> None:
        items = goal_progress([goal(currency_ticker=None)], base_currency="")

        assert items[0].currency == ""

    def test_garbage_rows_skipped(self) -> None:
        items = goal_progress([goal(name=" "), "oops", goal(id="x", name="Без id")])

        assert [item.name for item in items] == ["Без id"]
        assert items[0].goal_id is None

    def test_garbage_amounts_and_deadline(self) -> None:
        items = goal_progress([goal(target_amount="oops", saved_amount=None, deadline="2027-99-99")])

        assert (items[0].target_amount, items[0].saved_amount) == (0.0, 0.0)
        assert items[0].deadline is None

    def test_empty_list(self) -> None:
        assert goal_progress([]) == []
