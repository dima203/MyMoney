"""PDF-отчёт MyMoney по месяцу (слайс 3.3c).

Слой без Flet: принимает «сырые» строки операций/счетов, отдаёт байты PDF.
Кириллица требует Unicode-шрифта: берём системный (Windows Arial, Linux/Pi
DejaVu); если шрифта нет — откат на Helvetica с ASCII-заменами, чтобы файл
всё равно создавался.
"""

from __future__ import annotations

from datetime import date
from pathlib import Path
from typing import NamedTuple

from fpdf import FPDF

from core.analytics import MONTH_LABELS, CategoryTotal, ExpenseSummary, build_summary

DEFAULT_FONT_PATHS: tuple[str, ...] = (
    "C:/Windows/Fonts/arial.ttf",
    "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf",
    "/Library/Fonts/Arial.ttf",
)
DEFAULT_FONT_FAMILY = "Report"
FALLBACK_FONT_FAMILY = "Helvetica"
TITLE_TEMPLATE = "MyMoney · отчёт за {month} {year}"
TOTAL_LABEL = "Расходы"
AVERAGE_LABEL = "В среднем за месяц"
CATEGORIES_LABEL = "По категориям"
NO_EXPENSES = "Нет расходов за период"
FOOTER = "MyMoney"
PAGE_MARGIN = 15


class _ReportFont(NamedTuple):
    """Шрифт отчёта: семейство и признак поддержки кириллицы."""

    family: str
    unicode_ok: bool

    def render(self, value: str) -> str:
        """Без Unicode-шрифта базовые PDF-шрифты не умеют кириллицу — заменяем на '?'."""
        return value if self.unicode_ok else value.encode("ascii", "replace").decode("ascii")


def monthly_report_pdf(
    rows,
    accounts,
    *,
    today: date,
    base_currency: str = "",
    font_paths=None,
) -> bytes:
    """PDF-отчёт за месяц: итог, среднее и расходы по категориям."""
    summary = build_summary(rows, accounts, today=today, months=1, base_currency=base_currency)
    pdf = _new_pdf()
    font = _register_font(pdf, DEFAULT_FONT_PATHS if font_paths is None else font_paths)
    _draw_header(pdf, font, today)
    _draw_summary(pdf, font, summary)
    _draw_categories(pdf, font, summary)
    _draw_footer(pdf, font)
    return bytes(pdf.output())


def pdf_filename(today: date) -> str:
    """Имя файла: `mymoney-report-2026-10.pdf`."""
    return f"mymoney-report-{today.year:04d}-{today.month:02d}.pdf"


def _new_pdf() -> FPDF:
    pdf = FPDF(format="A4")
    pdf.set_auto_page_break(auto=True, margin=PAGE_MARGIN)
    pdf.add_page()
    return pdf


def _register_font(pdf: FPDF, font_paths) -> _ReportFont:
    """Первый доступный Unicode-шрифт из кандидатов, иначе базовый Helvetica."""
    for path in font_paths or ():
        if Path(path).is_file() and _try_add_font(pdf, path):
            return _ReportFont(DEFAULT_FONT_FAMILY, unicode_ok=True)
    return _ReportFont(FALLBACK_FONT_FAMILY, unicode_ok=False)


def _try_add_font(pdf: FPDF, path: str) -> bool:
    """Зарегистрировать шрифт; битый или неподдерживаемый файл не срывает экспорт."""
    try:
        pdf.add_font(DEFAULT_FONT_FAMILY, fname=path)
    except Exception:
        return False
    return True


def _draw_header(pdf: FPDF, font: _ReportFont, today: date) -> None:
    pdf.set_font(font.family, size=16)
    title = TITLE_TEMPLATE.format(month=MONTH_LABELS[today.month - 1], year=today.year)
    pdf.cell(text=font.render(title), new_x="LMARGIN", new_y="NEXT")


def _draw_summary(pdf: FPDF, font: _ReportFont, summary: ExpenseSummary) -> None:
    pdf.set_font(font.family, size=12)
    totals = ((TOTAL_LABEL, summary.total), (AVERAGE_LABEL, summary.average_per_month))
    for label, amount in totals:
        pdf.cell(
            text=font.render(f"{label}: {_money(amount, summary.currency)}"),
            new_x="LMARGIN",
            new_y="NEXT",
        )
    pdf.ln(4)


def _draw_categories(pdf: FPDF, font: _ReportFont, summary: ExpenseSummary) -> None:
    if not summary.categories:
        pdf.multi_cell(0, 8, font.render(NO_EXPENSES), new_x="LMARGIN", new_y="NEXT")
        return
    pdf.set_font(font.family, size=13)
    pdf.cell(text=font.render(CATEGORIES_LABEL), new_x="LMARGIN", new_y="NEXT")
    pdf.set_font(font.family, size=11)
    for category in summary.categories:
        pdf.multi_cell(0, 7, font.render(_category_line(category, summary)), new_x="LMARGIN", new_y="NEXT")


def _draw_footer(pdf: FPDF, font: _ReportFont) -> None:
    pdf.ln(6)
    pdf.set_font(font.family, size=9)
    pdf.cell(text=font.render(FOOTER))


def _category_line(category: CategoryTotal, summary: ExpenseSummary) -> str:
    share = category.amount / summary.total if summary.total else 0.0
    return f"{category.category} — {_money(category.amount, summary.currency)} ({share:.0%})"


def _money(amount: float, currency: str) -> str:
    return f"{amount:,.2f} {currency}".replace(",", " ").strip()


__all__ = ["DEFAULT_FONT_PATHS", "monthly_report_pdf", "pdf_filename"]
