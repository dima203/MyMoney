"""Автоподстановка категории по описанию операции (2.53)."""

from core.category_suggest import normalize_description, suggest_category


def _tx(description, category, planned=False) -> dict:
    return {"description": description, "category": category, "is_planned": planned}


class TestNormalize:
    def test_case_and_spaces(self):
        assert normalize_description("  Кофе   с собой ") == "кофе с собой"

    def test_none_is_empty(self):
        assert normalize_description(None) == ""


class TestSuggest:
    def test_matches_description_case_insensitively(self):
        rows = [_tx("Кофе с собой", "Еда")]

        assert suggest_category("кофе   С СОБОЙ", rows) == "Еда"

    def test_most_frequent_wins(self):
        rows = [_tx("Такси", "Транспорт"), _tx("такси", "Еда"), _tx("Такси", "Транспорт")]

        assert suggest_category("Такси", rows) == "Транспорт"

    def test_empty_description_returns_empty(self):
        assert suggest_category("  ", [_tx("Такси", "Транспорт")]) == ""

    def test_no_history_returns_empty(self):
        assert suggest_category("Аптека", [_tx("Такси", "Транспорт")]) == ""

    def test_planned_rows_ignored(self):
        rows = [_tx("Аренда", "Жильё", planned=True)]

        assert suggest_category("Аренда", rows) == ""

    def test_empty_category_rows_ignored(self):
        rows = [_tx("Аптека", "")]

        assert suggest_category("Аптека", rows) == ""

    def test_allowed_dictionary_filters_archived(self):
        rows = [_tx("Аптека", "Здоровье"), _tx("Аптека", "Старая")]

        assert suggest_category("Аптека", rows, allowed=["Здоровье"]) == "Здоровье"

    def test_allowed_dictionary_returns_canonical_spelling(self):
        rows = [_tx("Аптека", "здоровье")]

        assert suggest_category("Аптека", rows, allowed=["Здоровье"]) == "Здоровье"

    def test_unknown_category_not_suggested_when_dictionary_set(self):
        rows = [_tx("Аптека", "Свободная строка")]

        assert suggest_category("Аптека", rows, allowed=["Еда"]) == ""

    def test_junk_rows_ignored(self):
        rows = [None, "junk", {"description": "Аптека"}, _tx("Аптека", "Здоровье")]

        assert suggest_category("Аптека", rows) == "Здоровье"
