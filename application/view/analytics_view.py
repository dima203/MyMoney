"""Экран «Аналитика» MyMoney: расходы по месяцам и категориям (слайс 3.2a).

Конверты, цели и шаблоны бюджетов переехали в отдельный раздел «Бюджеты»
(B-13): здесь остаются только графики расходов, итоги и PDF-отчёт.
"""

from __future__ import annotations

import asyncio
import math

import flet as ft
import flet_charts as ftc
from application.components import BaseView
from application.components.file_save import save_bytes_file, show_toast
from application.components.formatting import UNKNOWN_CURRENCY, format_money
from application.components.navigation_items import NAVIGATION_ITEMS
from application.view.data_loading import DataLoadingMixin
from core.analytics import (
    DEFAULT_PERIOD,
    PERIOD_MONTHS,
    PERIODS,
    ExpenseSummary,
    MonthTotal,
    build_summary,
)
from core.pdf_report import monthly_report_pdf, pdf_filename

from MySpaceShared.components.elevated_card import ElevatedCard
from MySpaceShared.components.empty_state import EmptyState
from MySpaceShared.components.hero_value import HeroValue
from MySpaceShared.components.section_header import SectionHeader
from MySpaceShared.core.charts import axis_label_width, chart_palette, nice_ticks
from MySpaceShared.core.formatting import format_percent

ANALYTICS_INDEX = 3
CHART_HEIGHT = 220
CHART_TICKS = 4
MIN_TICK_GAP = 44
BAR_WIDTH = 22
BAR_RADIUS = 4
CATEGORY_BAR_HEIGHT = 6
CATEGORY_BAR_RADIUS = 3
GRID_OPACITY = 0.25
TRACK_OPACITY = 0.15
NO_EXPENSES_TITLE = "Нет расходов за период"
NO_EXPENSES_SUBTITLE = "Добавьте транзакции — здесь появятся графики и разбивка по категориям"
PDF_TOOLTIP = "PDF-отчёт за месяц"


def period_caption(months: int) -> str:
    if months == 1:
        return "за месяц"
    if months == 12:
        return "за год"
    return f"за {months} мес."


def axis_label(value: float, step: float = 1.0) -> str:
    """Подпись деления оси: целое с пробелом между тысячами, дробное — по шагу."""
    decimals = 0 if step >= 1 else min(6, max(0, -math.floor(math.log10(step))))
    return f"{value:,.{decimals}f}".replace(",", " ")


def chart_ticks(max_amount: float) -> list[float]:
    """Круглые деления оси Y с учётом высоты графика (подписи не наезжают)."""
    target = max(1, min(CHART_TICKS, int(CHART_HEIGHT // MIN_TICK_GAP)))
    return nice_ticks(max_amount, target=target)


def _event_period(event) -> str | None:
    """Ключ периода из события SegmentedButton (Flet отдаёт str или список)."""
    data = getattr(event, "data", None)
    if isinstance(data, str):
        payload = [data]
    elif isinstance(data, (list, tuple)):
        payload = data
    else:
        return None
    return next((item for item in payload if isinstance(item, str) and item in PERIOD_MONTHS), None)


def _bar_rod(point: MonthTotal, currency: str) -> ftc.BarChartRod:
    return ftc.BarChartRod(
        to_y=point.amount,
        width=BAR_WIDTH,
        color=ft.Colors.PRIMARY,
        border_radius=BAR_RADIUS,
        tooltip=format_money(point.amount, currency),
    )


def _value_axis(ticks: list[float], labels: list[str]) -> ftc.ChartAxis:
    """Левая ось: подпись на каждом круглом делении, ширина — по самой длинной."""
    return ftc.ChartAxis(
        labels=[
            ftc.ChartAxisLabel(
                value=value,
                label=ft.Text(
                    text,
                    size=10,
                    no_wrap=True,
                    color=ft.Colors.ON_SURFACE_VARIANT,
                ),
            )
            for value, text in zip(ticks, labels, strict=True)
        ],
        label_size=axis_label_width(labels),
        show_labels=True,
        title_size=0,
    )


class AnalyticsView(DataLoadingMixin, BaseView):
    """График расходов по месяцам + разбивка по категориям (данные из локального кэша/сети)."""

    def __init__(self, route: str, api_client, transaction_view=None, account_view=None, connection_banner=None):
        self._period = DEFAULT_PERIOD
        self._summary: ExpenseSummary | None = None
        self._init_data_loading(
            api_client,
            transaction_view=transaction_view,
            account_view=account_view,
            connection_banner=connection_banner,
        )
        self._period_selector = ft.SegmentedButton(
            segments=[ft.Segment(value=key, label=ft.Text(label)) for key, label, _months in PERIODS],
            selected=[self._period],
            show_selected_icon=False,
            on_change=self._on_period_changed,
        )

        super().__init__(
            content=self._content,
            title="Аналитика",
            route=route,
            selected_index=ANALYTICS_INDEX,
            navigation_items=NAVIGATION_ITEMS,
        )

    # ------------------------------------------------------------------ рендер

    def _on_period_changed(self, e) -> None:
        period = _event_period(e)
        if period is None or period == self._period:
            return
        self._period = period
        # Flet 1.0.3 не возвращает selected из клиента в Python:
        # без ручной синхронизации подсветка остаётся на старом сегменте.
        self._period_selector.selected = [period]
        self._rebuild()

    def _rebuild(self) -> None:
        summary = build_summary(
            self._rows,
            self._accounts,
            today=self._today(),
            months=PERIOD_MONTHS[self._period],
            base_currency=self._base_currency,
        )
        self._summary = summary
        self._body.controls = [
            self._period_row(),
            self._total_card(summary),
            self._composition_hint(summary),
            *self._details(summary),
        ]
        self.update()

    def _composition_hint(self, summary: ExpenseSummary) -> ft.Text:
        """Пояснение состава аналитики (2.36): что входит в расчёт, а что нет."""
        currency = summary.currency or "валюте счетов"
        return ft.Text(
            (
                f"В расчёт входят расходы в {currency} {period_caption(summary.period_months)}; "
                "переводы, плановые операции и технические записи OKX не учитываются."
            ),
            size=12,
            color=ft.Colors.ON_SURFACE_VARIANT,
        )

    def _period_row(self) -> ft.Row:
        """Селектор периода и кнопка PDF; Row нужен, чтобы контролы не растянулись на всю ширину."""
        return ft.Row(
            controls=[
                self._period_selector,
                ft.Container(expand=True),
                ft.IconButton(
                    ft.Icons.PICTURE_AS_PDF_OUTLINED,
                    tooltip=PDF_TOOLTIP,
                    on_click=self._export_pdf,
                ),
            ],
            vertical_alignment=ft.CrossAxisAlignment.CENTER,
        )

    async def _export_pdf(self, _event=None) -> None:
        """Сохранить PDF-отчёт за текущий месяц (итог, среднее, категории)."""
        try:
            today = self._today()
            content = await asyncio.to_thread(
                monthly_report_pdf,
                self._rows,
                self._accounts,
                today=today,
                base_currency=self._base_currency,
            )
            target = await save_bytes_file(self.page, file_name=pdf_filename(today), content=content)
        except (OSError, RuntimeError, ValueError) as exc:
            self._show_error(f"Ошибка PDF: {exc}")
            return
        if target:
            show_toast(self.page, f"Сохранено: {target}")

    def _total_card(self, summary: ExpenseSummary) -> ft.Control:
        return ElevatedCard(
            content=ft.Column(
                controls=[
                    HeroValue(
                        format_money(summary.total, summary.currency),
                        label=f"Расходы {period_caption(summary.period_months)}",
                        value_size=34,
                    ),
                    ft.Text(
                        f"В среднем {format_money(summary.average_per_month, summary.currency)} в месяц",
                        size=12,
                        color=ft.Colors.ON_SURFACE_VARIANT,
                    ),
                ],
                spacing=4,
            )
        )

    def _details(self, summary: ExpenseSummary) -> list[ft.Control]:
        if summary.total <= 0:
            return [EmptyState(icon=ft.Icons.INSIGHTS, title=NO_EXPENSES_TITLE, subtitle=NO_EXPENSES_SUBTITLE)]
        return [self._chart_card(summary), SectionHeader("По категориям"), self._category_list(summary)]

    def _chart_card(self, summary: ExpenseSummary) -> ft.Control:
        max_amount = max((point.amount for point in summary.months), default=0.0)
        ticks = chart_ticks(max_amount)
        step = ticks[1] - ticks[0]
        labels = [axis_label(value, step) for value in ticks]
        groups = [
            ftc.BarChartGroup(x=index, rods=[_bar_rod(point, summary.currency)])
            for index, point in enumerate(summary.months)
        ]
        month_labels = [
            ftc.ChartAxisLabel(value=index, label=ft.Text(point.label)) for index, point in enumerate(summary.months)
        ]
        chart = ftc.BarChart(
            groups=groups,
            height=CHART_HEIGHT,
            interactive=True,
            min_y=0,
            max_y=ticks[-1],
            group_alignment=ft.MainAxisAlignment.SPACE_EVENLY,
            horizontal_grid_lines=ftc.ChartGridLines(
                interval=step,
                color=ft.Colors.with_opacity(GRID_OPACITY, ft.Colors.ON_SURFACE),
                width=1,
            ),
            left_axis=_value_axis(ticks, labels),
            bottom_axis=ftc.ChartAxis(
                labels=month_labels,
                label_size=28,
                title_size=0,
            ),
            top_axis=ftc.ChartAxis(show_labels=False, title_size=0),
            right_axis=ftc.ChartAxis(show_labels=False, title_size=0),
        )
        return ElevatedCard(
            content=ft.Column(
                controls=[
                    ft.Text(
                        f"Расходы по месяцам, {summary.currency or UNKNOWN_CURRENCY}",
                        size=13,
                        weight=ft.FontWeight.W_600,
                    ),
                    chart,
                ],
                spacing=8,
            )
        )

    def _category_list(self, summary: ExpenseSummary) -> ft.Control:
        categories = [category for category in summary.categories if category.amount > 0]
        controls: list[ft.Control] = []
        for color, category in zip(chart_palette(len(categories)), categories, strict=True):
            share = category.amount / summary.total if summary.total else 0.0
            controls.append(self._category_row(category.category, category.amount, share, color, summary.currency))
        return ft.Column(controls=controls, spacing=12)

    @staticmethod
    def _category_row(name: str, amount: float, share: float, color: str, currency: str) -> ft.Control:
        return ft.Column(
            controls=[
                ft.Row(
                    controls=[
                        ft.Container(width=8, height=8, border_radius=4, bgcolor=color),
                        ft.Text(
                            name,
                            size=13,
                            expand=True,
                            no_wrap=True,
                            overflow=ft.TextOverflow.ELLIPSIS,
                        ),
                        ft.Text(
                            format_percent(share * 100),
                            size=12,
                            no_wrap=True,
                            color=ft.Colors.ON_SURFACE_VARIANT,
                        ),
                        ft.Text(format_money(amount, currency), size=13, no_wrap=True),
                    ],
                    spacing=8,
                    vertical_alignment=ft.CrossAxisAlignment.CENTER,
                ),
                ft.ProgressBar(
                    value=min(max(share, 0.0), 1.0),
                    color=color,
                    bgcolor=ft.Colors.with_opacity(TRACK_OPACITY, color),
                    height=CATEGORY_BAR_HEIGHT,
                    border_radius=CATEGORY_BAR_RADIUS,
                ),
            ],
            spacing=4,
        )


__all__ = ["AnalyticsView", "format_money", "period_caption"]
