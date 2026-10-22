"""Экран «Аналитика» MyMoney: расходы по месяцам и категориям (слайс 3.2a)."""

from __future__ import annotations

import asyncio
import datetime

import flet as ft
import flet_charts as ftc
from application.api import ApiError, BackendUnreachableError
from application.components import BaseView
from application.components.envelope_card import EnvelopeCard
from application.components.formatting import UNKNOWN_CURRENCY, format_money
from application.components.navigation_items import NAVIGATION_ITEMS
from core.analytics import (
    DEFAULT_PERIOD,
    PERIOD_MONTHS,
    PERIODS,
    ExpenseSummary,
    MonthTotal,
    build_summary,
)
from core.envelopes import EnvelopeProgress, envelope_payload, envelope_progress

from MySpaceShared.components.confirm_dialog import ConfirmDialog
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
NO_EXPENSES_TITLE = "Нет расходов за период"
NO_EXPENSES_SUBTITLE = "Добавьте транзакции — здесь появятся графики и разбивка по категориям"
ENVELOPES_TITLE = "Конверты месяца"
ENVELOPES_KEY = "envelopes"
ENVELOPES_EMPTY = "Лимиты не заданы — добавьте конверт, чтобы следить за тратами по категории"
ENVELOPES_OFFLINE = "Конверты недоступны без подключения к серверу"
ENVELOPES_ADD = "Добавить"
ENVELOPES_SUBTITLE = "Лимит расходов на текущий месяц по категории"
DIALOG_WIDTH = 350


def period_caption(months: int) -> str:
    if months == 1:
        return "за месяц"
    if months == 12:
        return "за год"
    return f"за {months} мес."


def limit_text(value) -> str:
    """Лимит для поля ввода: «500» вместо «500.0000»."""
    if value is None or (isinstance(value, str) and not value.strip()):
        return ""
    try:
        amount = float(value)
    except (TypeError, ValueError):
        return ""
    return f"{amount:.2f}".rstrip("0").rstrip(".")


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


def _dict_rows(payload) -> list[dict]:
    """Строки ответа API (список или `{results: [...]}`), только dict-элементы."""
    if isinstance(payload, list):
        items = payload
    elif isinstance(payload, dict):
        items = payload.get("results", [])
    else:
        items = []
    return [item for item in items or [] if isinstance(item, dict)]


def _hint(text: str, *, size: int = 13) -> ft.Text:
    """Приглушённая подпись секции."""
    return ft.Text(text, size=size, color=ft.Colors.ON_SURFACE_VARIANT)


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
        self._envelopes: list[dict] = []
        self._envelopes_offline = False

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

            self._rows = _dict_rows(rows)
            self._accounts = _dict_rows(accounts)
            self._base_currency = await self._fetch_base_currency()
            await self._load_envelopes()
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

    async def _load_envelopes(self) -> None:
        """Конверты online-only: их сбой не должен ломать графики расходов."""
        if self._offline:
            self._mark_envelopes_offline()
            return
        try:
            payload = await asyncio.to_thread(self.api_client.list_envelopes)
        except (ApiError, BackendUnreachableError):
            self._mark_envelopes_offline()
            return
        self._envelopes_offline = False
        self._envelopes = _dict_rows(payload)

    def _mark_envelopes_offline(self) -> None:
        self._envelopes = []
        self._envelopes_offline = True

    async def _reload_envelopes(self) -> None:
        await self._load_envelopes()
        self._rebuild()

    def _fail(self, message: str) -> None:
        if self._disposed:
            return
        self._loading.visible = False
        self._error_text.value = message
        self._error_text.visible = True
        self.update()

    @property
    def _offline(self) -> bool:
        """Локальный режим: dual-database view знает о недоступности сервера."""
        return self._transaction_view is not None and not self._transaction_view.is_online

    def _sync_banner(self) -> None:
        if self._offline:
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
            *self._envelopes_section(),
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

    # --------------------------------------------------------------- конверты

    def _currency_options(self) -> dict[str, int | None]:
        """Тикер валюты → id ресурса (для FK конверта); базовая может быть без id."""
        options: dict[str, int | None] = {}
        for account in self._accounts:
            ticker = account.get("resource")
            resource_id = account.get("resource_definition")
            if isinstance(ticker, str) and ticker.strip():
                options.setdefault(ticker.strip(), resource_id if isinstance(resource_id, int) else None)
        if self._base_currency:
            options.setdefault(self._base_currency, None)
        return options

    def _envelopes_section(self) -> list[ft.Control]:
        if self._envelopes_offline:
            return [self._envelopes_header(), _hint(ENVELOPES_OFFLINE)]

        progress = envelope_progress(
            self._envelopes,
            self._rows,
            self._accounts,
            today=self._today(),
            base_currency=self._base_currency,
        )
        add_button = ft.TextButton(ENVELOPES_ADD, icon=ft.Icons.ADD, on_click=self._open_envelope_editor)
        header = self._envelopes_header(add_button)
        if not progress:
            return [header, _hint(ENVELOPES_EMPTY)]
        cards = self._envelope_cards(progress)
        return [header, _hint(ENVELOPES_SUBTITLE, size=12), ft.Column(cards, spacing=12)]

    def _envelopes_header(self, trailing: ft.Control | None = None) -> SectionHeader:
        """Заголовок секции; `key` нужен для прокрутки к конвертам."""
        header = SectionHeader(ENVELOPES_TITLE, trailing=trailing)
        header.key = ENVELOPES_KEY
        return header

    def _envelope_cards(self, progress: list[EnvelopeProgress]) -> list[ft.Control]:
        raw_by_id = {row.get("id"): row for row in self._envelopes}
        return [self._envelope_card(item, raw_by_id.get(item.envelope_id)) for item in progress]

    def _envelope_card(self, item: EnvelopeProgress, raw: dict | None) -> EnvelopeCard:
        envelope = raw or {"category": item.category, "limit_amount": item.limit_amount}
        return EnvelopeCard(
            item,
            on_edit=lambda _event, envelope=envelope: self._open_envelope_editor(envelope),
            on_delete=lambda _event, envelope=envelope: self._confirm_delete_envelope(envelope),
        )

    def _currency_dropdown(self, selected: str, currency_map: dict[str, int | None]) -> ft.Dropdown:
        options = [ft.DropdownOption(key=ticker, text=ticker) for ticker in sorted(currency_map)]
        if selected and selected not in currency_map:
            options.append(ft.DropdownOption(key=selected, text=selected))
        return ft.Dropdown(label="Валюта", value=selected or None, options=options, width=DIALOG_WIDTH)

    def _dialog_error(self, error_text: ft.Text, message: str) -> None:
        error_text.value = message
        error_text.visible = True
        self.page.update()

    def _envelope_dialog(self, envelope: dict) -> ft.AlertDialog:
        currency_map = self._currency_options()
        selected_currency = str(envelope.get("currency_ticker") or self._base_currency or "")

        category_field = ft.TextField(label="Категория", value=str(envelope.get("category") or ""), autofocus=True)
        limit_field = ft.TextField(
            label="Лимит на месяц",
            value=limit_text(envelope.get("limit_amount")),
            keyboard_type=ft.KeyboardType.NUMBER,
        )
        currency_dropdown = self._currency_dropdown(selected_currency, currency_map)
        error_text = ft.Text("", size=12, color=ft.Colors.ERROR, visible=False)

        async def on_submit(_event) -> None:
            try:
                payload = envelope_payload(
                    category_field.value,
                    limit_field.value,
                    currency_map.get(currency_dropdown.value or ""),
                )
            except ValueError as exc:
                self._dialog_error(error_text, str(exc))
                return

            save_button.disabled = True
            save_button.text = "Сохранение..."
            self.page.update()
            try:
                envelope_id = envelope.get("id")
                if envelope_id:
                    await asyncio.to_thread(self.api_client.update_envelope, envelope_id, payload)
                else:
                    await asyncio.to_thread(self.api_client.create_envelope, payload)
                self.page.pop_dialog()
                await self._reload_envelopes()
            except (ApiError, BackendUnreachableError) as exc:
                save_button.disabled = False
                save_button.text = "Сохранить"
                self._dialog_error(error_text, str(exc))

        save_button = ft.Button("Сохранить", on_click=on_submit)
        return ft.AlertDialog(
            title=ft.Text("Изменить конверт" if envelope.get("id") else "Новый конверт"),
            content=ft.Container(
                content=ft.Column(
                    controls=[category_field, limit_field, currency_dropdown, error_text],
                    spacing=12,
                    width=DIALOG_WIDTH,
                    horizontal_alignment=ft.CrossAxisAlignment.STRETCH,
                ),
            ),
            actions=[
                ft.TextButton("Отмена", on_click=lambda _: self.page.pop_dialog()),
                save_button,
            ],
            actions_alignment=ft.MainAxisAlignment.END,
        )

    def _open_envelope_editor(self, envelope: dict | None = None) -> None:
        self.page.show_dialog(self._envelope_dialog(envelope if isinstance(envelope, dict) else {}))

    def _confirm_delete_envelope(self, envelope: dict) -> None:
        async def delete(_event) -> None:
            try:
                await asyncio.to_thread(self.api_client.delete_envelope, envelope.get("id"))
            except (ApiError, BackendUnreachableError) as exc:
                self.page.pop_dialog()
                self._error_text.value = f"Ошибка удаления: {exc}"
                self._error_text.visible = True
                self.update()
                return
            self.page.pop_dialog()
            await self._reload_envelopes()

        category = str(envelope.get("category") or "")
        ConfirmDialog(
            title="Удалить конверт?",
            message=f"Конверт «{category}» будет удалён.",
            on_confirm=lambda event: asyncio.create_task(delete(event)),
        ).show(self.page)


__all__ = ["AnalyticsView", "format_money", "period_caption"]
