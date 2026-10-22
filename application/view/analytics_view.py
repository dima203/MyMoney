"""Экран «Аналитика» MyMoney: расходы по месяцам и категориям (слайс 3.2a)."""

from __future__ import annotations

import asyncio
import datetime

import flet as ft
import flet_charts as ftc
from application.api import ApiError, BackendUnreachableError
from application.components import BaseView
from application.components.navigation_items import NAVIGATION_ITEMS
from core.analytics import (
    DEFAULT_PERIOD,
    PERIOD_MONTHS,
    PERIODS,
    ExpenseSummary,
    MonthTotal,
    build_summary,
)

from MySpaceShared.components.connection_status import ConnectionBanner
from MySpaceShared.components.elevated_card import ElevatedCard
from MySpaceShared.components.empty_state import EmptyState
from MySpaceShared.components.hero_value import HeroValue
from MySpaceShared.components.loading_state import LoadingState
from MySpaceShared.components.section_header import SectionHeader

ANALYTICS_INDEX = 3
CHART_HEIGHT = 220
CHART_HEADROOM = 1.2
CHART_GRID_LINES = 4
BAR_WIDTH = 22
BAR_RADIUS = 4
UNKNOWN_CURRENCY = "—"
NO_EXPENSES_TITLE = "Нет расходов за период"
NO_EXPENSES_SUBTITLE = "Добавьте транзакции — здесь появятся графики и разбивка по категориям"


def format_money(amount: float, currency: str) -> str:
    """Сумма с разделителем тысяч: «1 234.50 BYN»."""
    return f"{amount:,.2f} {currency or UNKNOWN_CURRENCY}".replace(",", " ").strip()


def period_caption(months: int) -> str:
    if months == 1:
        return "за месяц"
    if months == 12:
        return "за год"
    return f"за {months} мес."


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


class AnalyticsView(BaseView):
    """График расходов по месяцам + разбивка по категориям (данные из локального кэша/сети)."""

    def __init__(self, route: str, api_client, transaction_view=None, account_view=None, connection_banner=None):
        self.api_client = api_client
        self._transaction_view = transaction_view
        self._account_view = account_view
        self._connection_banner = connection_banner or ConnectionBanner()
        self._disposed = False
        self._rows: list[dict] = []
        self._accounts: list[dict] = []
        self._base_currency = ""
        self._period = DEFAULT_PERIOD
        self._summary: ExpenseSummary | None = None

        self._error_text = ft.Text("", size=13, color=ft.Colors.ERROR, visible=False)
        self._loading = LoadingState()
        self._loading.visible = True
        self._body = ft.Column(spacing=16, horizontal_alignment=ft.CrossAxisAlignment.STRETCH)
        self._period_selector = ft.SegmentedButton(
            segments=[ft.Segment(value=key, label=ft.Text(label)) for key, label, _months in PERIODS],
            selected=[self._period],
            show_selected_icon=False,
            on_change=self._on_period_changed,
        )
        self._content = ft.Column(
            controls=[self._connection_banner, self._error_text, self._loading, self._body],
            spacing=12,
            expand=True,
            scroll=ft.ScrollMode.AUTO,
        )

        super().__init__(
            content=self._content,
            title="Аналитика",
            route=route,
            selected_index=ANALYTICS_INDEX,
            navigation_items=NAVIGATION_ITEMS,
        )

    def did_mount(self):
        super().did_mount()
        self._load_task = asyncio.create_task(self._load_data())

    def dispose(self):
        self._disposed = True

    async def _load_data(self) -> None:
        try:
            self._error_text.visible = False
            self._loading.visible = True
            self.update()

            if self._transaction_view and self._account_view:
                rows = await asyncio.to_thread(self._transaction_view.get_all)
                accounts = await asyncio.to_thread(self._account_view.get_all)
            else:
                rows, accounts = await asyncio.gather(
                    asyncio.to_thread(self.api_client.list_transactions),
                    asyncio.to_thread(self.api_client.list_accounts),
                )
                rows = rows if isinstance(rows, list) else rows.get("results", [])
            if self._disposed:
                return

            self._rows = [row for row in rows if isinstance(row, dict)]
            self._accounts = [account for account in (accounts or []) if isinstance(account, dict)]
            self._base_currency = await self._fetch_base_currency()
            self._loading.visible = False
            self._sync_banner()
            self._rebuild()
        except BackendUnreachableError:
            self._fail("Сервер недоступен")
        except ApiError as exc:
            self._fail(f"Ошибка загрузки: {exc}")

    async def _fetch_base_currency(self) -> str:
        try:
            profile = await asyncio.to_thread(self.api_client.me)
        except Exception:
            return ""
        if isinstance(profile, dict):
            currency = profile.get("base_currency")
            return currency.strip() if isinstance(currency, str) else ""
        return ""

    def _fail(self, message: str) -> None:
        if self._disposed:
            return
        self._loading.visible = False
        self._error_text.value = message
        self._error_text.visible = True
        self.update()

    def _sync_banner(self) -> None:
        if self._transaction_view is not None and not self._transaction_view.is_online:
            self._connection_banner.show()
        else:
            self._connection_banner.hide()

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
            # Body тянется STRETCH: селектор заворачиваем в Row, иначе он растянется на всю ширину.
            ft.Row([self._period_selector]),
            self._total_card(summary),
            *self._details(summary),
        ]
        self.update()

    def _today(self) -> datetime.date:
        return datetime.date.today()

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
            max_y=max_amount * CHART_HEADROOM if max_amount else 1,
            group_alignment=ft.MainAxisAlignment.SPACE_AROUND,
            horizontal_grid_lines=ftc.ChartGridLines(
                interval=max(max_amount / CHART_GRID_LINES, 1), color=ft.Colors.OUTLINE_VARIANT
            ),
            left_axis=ftc.ChartAxis(label_size=48, title_size=0, show_labels=True),
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
        controls: list[ft.Control] = []
        for category in summary.categories:
            share = category.amount / summary.total if summary.total else 0.0
            controls.append(
                ft.Column(
                    controls=[
                        ft.Row(
                            controls=[
                                ft.Text(category.category, size=13, expand=True),
                                ft.Text(format_money(category.amount, summary.currency), size=13),
                            ],
                            spacing=8,
                        ),
                        ft.ProgressBar(value=min(max(share, 0.0), 1.0), color=ft.Colors.PRIMARY, height=6),
                    ],
                    spacing=4,
                )
            )
        return ft.Column(controls=controls, spacing=12)


__all__ = ["AnalyticsView", "format_money", "period_caption"]
