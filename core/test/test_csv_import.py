"""Тесты импорта CSV-выписок MyMoney (слайс 3.3b)."""

from __future__ import annotations

import pytest

from core.csv_import import (
    Statement,
    build_transactions,
    detect_delimiter,
    guess_mapping,
    parse_amount,
    parse_csv,
    parse_date,
)

STATEMENT = parse_csv(
    "Дата;Сумма;Назначение;Категория\n"
    "05.10.2026;-12,50;Обед в кафе;Еда\n"
    "06.10.2026;1000;Зарплата;\n"
    "07.10.2026;abc;Битая сумма;Еда\n"
)
MAPPING = {
    "date": "Дата",
    "amount": "Сумма",
    "description": "Назначение",
    "category": "Категория",
}
DATE_AMOUNT_MAPPING = {"date": "date", "amount": "amount"}


class TestParseCsv:
    def test_semicolon_and_bom(self) -> None:
        statement = parse_csv("\ufeffДата;Сумма\n05.10.2026;-10\n")

        assert statement.headers == ("Дата", "Сумма")
        assert statement.rows == (("05.10.2026", "-10"),)

    def test_comma_delimiter(self) -> None:
        statement = parse_csv("date,amount\n2026-10-05,-10\n")

        assert statement.headers == ("date", "amount")
        assert statement.rows == (("2026-10-05", "-10"),)

    def test_tab_delimiter(self) -> None:
        statement = parse_csv("date\tamount\n2026-10-05\t-10\n")

        assert statement.headers == ("date", "amount")

    def test_quoted_cells(self) -> None:
        statement = parse_csv('date,amount,description\n2026-10-05,-10,"Кафе, 2 этаж"\n')

        assert statement.rows[0][2] == "Кафе, 2 этаж"

    def test_crlf_and_blank_lines(self) -> None:
        statement = parse_csv("date,amount\r\n2026-10-05,-10\r\n\r\n")

        assert statement.rows == (("2026-10-05", "-10"),)

    def test_empty_text(self) -> None:
        assert parse_csv("") == Statement((), ())
        assert parse_csv("   \n\n") == Statement((), ())

    def test_detect_delimiter_defaults_to_comma(self) -> None:
        assert detect_delimiter("одна колонка") == ","
        assert detect_delimiter("a;b;c") == ";"


class TestGuessMapping:
    def test_russian_headers(self) -> None:
        mapping = guess_mapping(("Дата операции", "Сумма операции", "Назначение", "Категория"))

        assert mapping == {
            "date": "Дата операции",
            "amount": "Сумма операции",
            "description": "Назначение",
            "category": "Категория",
        }

    def test_english_headers_case_insensitive(self) -> None:
        mapping = guess_mapping(("DATE", "Amount", "Description"))

        assert mapping == {"date": "DATE", "amount": "Amount", "description": "Description", "category": None}

    def test_unknown_headers(self) -> None:
        assert guess_mapping(("a", "b")) == {
            "date": None,
            "amount": None,
            "description": None,
            "category": None,
        }


class TestParsing:
    @pytest.mark.parametrize(
        ("raw", "expected"),
        [
            ("-12,50", -12.5),
            ("1 234,56", 1234.56),
            ("(100)", -100.0),
            ("1 000", 1000.0),
            ("abc", None),
            ("", None),
            (None, None),
        ],
    )
    def test_parse_amount(self, raw, expected) -> None:
        assert parse_amount(raw) == expected

    @pytest.mark.parametrize(
        ("raw", "expected"),
        [
            ("2026-10-05", "2026-10-05"),
            ("05.10.2026", "2026-10-05"),
            ("05/10/2026", "2026-10-05"),
            ("2026-10-05T10:00:00", "2026-10-05"),
            ("32.13.2026", None),
            ("", None),
        ],
    )
    def test_parse_date(self, raw, expected) -> None:
        assert parse_date(raw) == expected


class TestBuildTransactions:
    def test_builds_payloads(self) -> None:
        payloads, errors = build_transactions(STATEMENT, MAPPING, account_id=7)

        assert len(payloads) == 2
        assert payloads[0] == {
            "date": "2026-10-05",
            "description": "Обед в кафе",
            "category": "Еда",
            "is_planned": False,
            "entries": [{"account": 7, "amount": -12.5, "quantity": -12.5, "unit_price": 1}],
        }
        assert payloads[1]["category"] == ""
        assert errors == ["Строка 4: неверная сумма"]

    def test_missing_required_mapping_raises(self) -> None:
        with pytest.raises(ValueError, match="даты и суммы"):
            build_transactions(STATEMENT, {"date": "Дата"}, account_id=1)

    def test_optional_columns_absent(self) -> None:
        statement = parse_csv("date,amount\n2026-10-05,-10\n")

        payloads, errors = build_transactions(statement, DATE_AMOUNT_MAPPING, account_id=1)

        assert payloads[0]["description"] == ""
        assert payloads[0]["category"] == ""
        assert errors == []

    def test_zero_amount_is_an_error(self) -> None:
        statement = parse_csv("date,amount\n2026-10-05,0\n")

        payloads, errors = build_transactions(statement, DATE_AMOUNT_MAPPING, account_id=1)

        assert payloads == []
        assert errors == ["Строка 2: нулевая сумма"]

    def test_bad_date_is_an_error(self) -> None:
        statement = parse_csv("date,amount\nзавтра,10\n")

        payloads, errors = build_transactions(statement, DATE_AMOUNT_MAPPING, account_id=1)

        assert payloads == []
        assert errors == ["Строка 2: неверная дата"]

    def test_mapping_to_unknown_header_raises(self) -> None:
        with pytest.raises(ValueError):
            build_transactions(STATEMENT, {"date": "Нет", "amount": "Сумма"}, account_id=1)
