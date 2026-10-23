"""Тесты PDF-отчёта MyMoney (слайс 3.3c)."""

from __future__ import annotations

import datetime

import pytest

from core.pdf_report import DEFAULT_FONT_FAMILY, FALLBACK_FONT_FAMILY, monthly_report_pdf, pdf_filename

TODAY = datetime.date(2026, 10, 23)
ACCOUNTS = [{"id": 1, "resource": "BYN"}]
ROWS = [
    {"date": "2026-10-05", "category": "Еда", "entries": [{"account": 1, "amount": -100, "quantity": -100}]},
    {"date": "2026-10-12", "category": "Еда", "entries": [{"account": 1, "amount": -50, "quantity": -50}]},
    {"date": "2026-10-15", "category": "Транспорт", "entries": [{"account": 1, "amount": -30, "quantity": -30}]},
    {"date": "2026-09-20", "category": "Жильё", "entries": [{"account": 1, "amount": -500, "quantity": -500}]},
]


class RecordingPdf:
    """Минимальный двойник FPDF: запоминает шрифты и тексты."""

    def __init__(self, *args, **kwargs):
        self.fonts: list[tuple] = []
        self.texts: list[str] = []
        self.pages = 0

    def set_auto_page_break(self, **kwargs) -> None:
        pass

    def add_page(self) -> None:
        self.pages += 1

    def add_font(self, family, fname=None, **kwargs) -> None:
        self.fonts.append((family, fname))

    def set_font(self, family, size=0, **kwargs) -> None:
        self.fonts.append((family, size))

    def cell(self, text: str = "", **kwargs) -> None:
        self.texts.append(text)

    def multi_cell(self, width, height, text: str = "", **kwargs) -> None:
        self.texts.append(text)

    def ln(self, height) -> None:
        pass

    def output(self) -> bytes:
        return b"%PDF-fake"


@pytest.fixture
def fake_font(tmp_path) -> str:
    font = tmp_path / "DejaVuSans.ttf"
    font.write_bytes(b"fake-font")
    return str(font)


def _report(monkeypatch, *, font_paths, rows=ROWS, accounts=ACCOUNTS) -> tuple[RecordingPdf, bytes]:
    recorder: list[RecordingPdf] = []

    def factory(*args, **kwargs):
        recorder.append(RecordingPdf(*args, **kwargs))
        return recorder[-1]

    monkeypatch.setattr("core.pdf_report.FPDF", factory)
    data = monthly_report_pdf(rows, accounts, today=TODAY, base_currency="BYN", font_paths=font_paths)
    return recorder[0], data


class TestContent:
    def test_title_totals_and_categories(self, monkeypatch, fake_font) -> None:
        pdf, _data = _report(monkeypatch, font_paths=[fake_font])

        assert pdf.pages == 1
        assert pdf.texts[0] == "MyMoney · отчёт за окт 2026"
        assert pdf.texts[1] == "Расходы: 180.00 BYN"
        assert pdf.texts[2] == "В среднем за месяц: 180.00 BYN"
        assert pdf.texts[3] == "По категориям"
        assert pdf.texts[4] == "Еда — 150.00 BYN (83%)"
        assert pdf.texts[5] == "Транспорт — 30.00 BYN (17%)"

    def test_month_boundaries_are_respected(self, monkeypatch, fake_font) -> None:
        pdf, _data = _report(monkeypatch, font_paths=[fake_font])

        assert not [text for text in pdf.texts if "Жильё" in text]

    def test_no_expenses(self, monkeypatch, fake_font) -> None:
        pdf, _data = _report(monkeypatch, font_paths=[fake_font], rows=[], accounts=[])

        assert "Нет расходов за период" in pdf.texts

    def test_fallback_font_replaces_cyrillic(self, monkeypatch) -> None:
        pdf, _data = _report(monkeypatch, font_paths=[])

        assert (FALLBACK_FONT_FAMILY, 16) in pdf.fonts
        assert pdf.texts[0].startswith("MyMoney")

    def test_unicode_font_is_registered(self, monkeypatch, fake_font) -> None:
        pdf, _data = _report(monkeypatch, font_paths=[fake_font])

        assert (DEFAULT_FONT_FAMILY, fake_font) in pdf.fonts
        assert "Еда" in " ".join(pdf.texts)

    def test_broken_font_falls_back_to_ascii(self, tmp_path) -> None:
        broken = tmp_path / "broken.ttf"
        broken.write_bytes(b"not-a-font")

        data = monthly_report_pdf(ROWS, ACCOUNTS, today=TODAY, base_currency="BYN", font_paths=[str(broken)])

        assert data.startswith(b"%PDF")


class TestOutput:
    def test_real_pdf_bytes(self) -> None:
        data = monthly_report_pdf(ROWS, ACCOUNTS, today=TODAY, base_currency="BYN")

        assert data.startswith(b"%PDF")
        assert data.rstrip().endswith(b"%%EOF")
        assert len(data) > 1000

    def test_filename(self) -> None:
        assert pdf_filename(TODAY) == "mymoney-report-2026-10.pdf"
