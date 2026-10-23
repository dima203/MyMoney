"""Импорт CSV-выписок MyMoney: разбор, маппинг колонок и тела операций (слайс 3.3b).

Слой без Flet и API: принимает текст выписки, отдаёт `Statement`,
предполагаемый маппинг колонок и payload-ы для `TransactionView.add`.
Дата и сумма — обязательные колонки, описание и категория — нет.
"""

from __future__ import annotations

import csv
from dataclasses import dataclass
from datetime import datetime
from io import StringIO

FIELDS: tuple[str, ...] = ("date", "amount", "description", "category")
FIELD_LABELS: dict[str, str] = {
    "date": "Дата",
    "amount": "Сумма",
    "description": "Описание",
    "category": "Категория",
}
SYNONYMS: dict[str, tuple[str, ...]] = {
    "date": ("дата", "date", "день", "дата операции"),
    "amount": ("сумма", "amount", "сумма операции", "оборот"),
    "description": ("описание", "назначение", "description", "комментарий"),
    "category": ("категория", "category", "раздел"),
}
DATE_FORMATS: tuple[str, ...] = ("%Y-%m-%d", "%d.%m.%Y", "%d/%m/%Y", "%Y/%m/%d", "%d.%m.%y")
DELIMITERS: tuple[str, ...] = (",", ";", "\t")
BOM = "\ufeff"
EMPTY_CELL = ""


@dataclass(frozen=True)
class Statement:
    """Разобранная выписка: заголовки и строки без заголовка."""

    headers: tuple[str, ...]
    rows: tuple[tuple[str, ...], ...]


@dataclass(frozen=True)
class _Columns:
    """Индексы колонок выписки под поля операции; описание и категория необязательны."""

    date: int
    amount: int
    description: int | None = None
    category: int | None = None


def parse_csv(text: str) -> Statement:
    """Разобрать CSV: BOM, автоматический выбор разделителя (`,` `;` tab)."""
    body = str(text or "").lstrip(BOM)
    if not body.strip():
        return Statement((), ())
    reader = csv.reader(StringIO(body), delimiter=detect_delimiter(body))
    rows = [[cell.strip() for cell in row] for row in reader if any(cell.strip() for cell in row)]
    if not rows:
        return Statement((), ())
    return Statement(tuple(rows[0]), tuple(tuple(row) for row in rows[1:]))


def detect_delimiter(text: str) -> str:
    """Разделитель по первой непустой строке: самый частый из `,` `;` tab."""
    first = next((line for line in str(text or "").splitlines() if line.strip()), "")
    counts = {delimiter: first.count(delimiter) for delimiter in DELIMITERS}
    delimiter = max(counts, key=counts.get)
    return delimiter if counts[delimiter] else ","


def guess_mapping(headers) -> dict[str, str | None]:
    """Предположить колонки по синонимам заголовков (RU/EN, без учёта регистра)."""
    normalized = [(header, _normalize(header)) for header in headers or ()]
    mapping: dict[str, str | None] = {}
    for field in FIELDS:
        mapping[field] = next(
            (header for header, text in normalized if any(synonym in text for synonym in SYNONYMS[field])),
            None,
        )
    return mapping


def build_transactions(statement: Statement, mapping: dict, account_id: int) -> tuple[list[dict], list[str]]:
    """Payload-ы операций и текст ошибок по строкам выписки."""
    columns = _resolve_columns(statement, mapping)
    payloads: list[dict] = []
    errors: list[str] = []
    for number, row in enumerate(statement.rows, start=2):
        date_value = parse_date(_cell(row, columns.date))
        amount = parse_amount(_cell(row, columns.amount))
        problem = _row_problem(date_value, amount)
        if problem:
            errors.append(f"Строка {number}: {problem}")
            continue
        payloads.append(_payload(row, columns, account_id, date_value, amount))
    return payloads, errors


def parse_date(value) -> str | None:
    """ISO-дата из строки выписки; None — формат не распознан."""
    text = str(value or "").strip()
    if not text:
        return None
    if len(text) >= 10 and text[4:5] == "-" and text[7:8] == "-":
        text = text[:10]
    for fmt in DATE_FORMATS:
        parsed = _parse_datetime(text, fmt)
        if parsed is not None:
            return parsed.date().isoformat()
    return None


def parse_amount(value) -> float | None:
    """Сумма из строки выписки: пробелы-разделители, запятая, скобки = минус."""
    text = str(value or "").strip().replace("\u00a0", "").replace(" ", "")
    negative = text.startswith("(") and text.endswith(")")
    if negative:
        text = text[1:-1]
    if not text:
        return None
    try:
        amount = float(text.replace(",", "."))
    except ValueError:
        return None
    return -amount if negative else amount


def _parse_datetime(text: str, fmt: str) -> datetime | None:
    """Дата по одному формату; None — строка ему не соответствует."""
    try:
        return datetime.strptime(text, fmt)  # ruff: ignore[call-datetime-strptime-without-zone]
    except ValueError:
        return None


def _resolve_columns(statement: Statement, mapping: dict) -> _Columns:
    """Сопоставить поля операции колонкам выписки; дата и сумма обязательны."""
    date_index = _column_index(statement, mapping.get("date"))
    amount_index = _column_index(statement, mapping.get("amount"))
    if date_index is None or amount_index is None:
        raise ValueError("Выберите колонки даты и суммы")
    return _Columns(
        date=date_index,
        amount=amount_index,
        description=_column_index(statement, mapping.get("description")),
        category=_column_index(statement, mapping.get("category")),
    )


def _row_problem(date_value: str | None, amount: float | None) -> str | None:
    """Почему строку нельзя импортировать; None — строка корректна."""
    if date_value is None:
        return "неверная дата"
    if amount is None:
        return "неверная сумма"
    return "нулевая сумма" if amount == 0 else None


def _payload(row, columns: _Columns, account_id: int, date_value: str, amount: float) -> dict:
    """Тело операции для `TransactionView.add` из строки выписки."""
    return {
        "date": date_value,
        "description": _cell(row, columns.description),
        "category": _cell(row, columns.category),
        "is_planned": False,
        "entries": [{"account": account_id, "amount": amount, "quantity": amount, "unit_price": 1}],
    }


def _column_index(statement: Statement, header: str | None) -> int | None:
    if not header:
        return None
    try:
        return statement.headers.index(header)
    except ValueError:
        return None


def _cell(row, index: int | None) -> str:
    if index is None or index >= len(row):
        return EMPTY_CELL
    return row[index]


def _normalize(header) -> str:
    return str(header or "").strip().casefold()


__all__ = [
    "FIELDS",
    "FIELD_LABELS",
    "Statement",
    "build_transactions",
    "detect_delimiter",
    "guess_mapping",
    "parse_amount",
    "parse_csv",
    "parse_date",
]
