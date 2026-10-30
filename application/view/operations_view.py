"""Экран «Операции»: фактические операции и план в одном месте (2.48b)."""

from __future__ import annotations

import asyncio

import flet as ft
from application.api import RestClientError
from application.apps_launcher import open_cross_plan
from application.components.cross_app_budget_card import CrossAppBudgetCard
from application.display import FAB_CLEARANCE, is_read_only_transaction
from application.fx_rates import FxRateStore, load_fx_rows, resolve_profile_base
from application.planned_actions import execute_planned
from application.view.planned_sections import build_plan_card, load_cross_app_budgets
from application.view.transactions_view import TransactionsView
from core.operations_totals import format_period_totals, period_totals
from core.transaction_filters import ALL_CATEGORY, filter_transactions

from MySpaceShared.components.confirm_dialog import ConfirmDialog
from MySpaceShared.components.empty_state import EmptyState
from MySpaceShared.components.section_header import SectionHeader

MODE_ACTUAL = "actual"
MODE_PLANNED = "planned"
MODES = (MODE_ACTUAL, MODE_PLANNED)
NO_PLANS_TITLE = "Нет планов"
NO_PLANS_SUBTITLE = "Нажмите + чтобы добавить план"


class OperationsView(TransactionsView):
    """Транзакции и плановые операции с переключателем режима."""

    def __init__(
        self,
        route: str,
        api_client,
        transaction_view=None,
        account_view=None,
        connection_banner=None,
        initial_mode: str = MODE_ACTUAL,
        fx_store: FxRateStore | None = None,
    ):
        self._mode = initial_mode if initial_mode in MODES else MODE_ACTUAL
        self._budgets: list[dict] = []
        self._budget_hint = ""
        self._base_currency: str | None = None
        self._prices: list[dict] = []
        self._fx_rows: list[dict] = []
        self._fx_store = fx_store or FxRateStore()
        super().__init__(
            route=route,
            api_client=api_client,
            transaction_view=transaction_view,
            account_view=account_view,
            connection_banner=connection_banner,
        )

        self.title = "Операции"
        self.app_bar.title.value = "Операции"
        self._segments = ft.SegmentedButton(
            segments=[
                ft.Segment(value=MODE_ACTUAL, label=ft.Text("Операции")),
                ft.Segment(value=MODE_PLANNED, label=ft.Text("План")),
            ],
            selected=[self._mode],
            show_selected_icon=False,
            on_change=self._on_mode_change,
        )
        self._totals = ft.Text("", size=12, color=ft.Colors.ON_SURFACE_VARIANT)
        controls = self.content.controls
        controls.insert(3, self._segments)
        controls.insert(6, self._totals)

    # ------------------------------------------------------------------ режим

    def _on_mode_change(self, event) -> None:
        selected = list(getattr(event.control, "selected", []) or [])
        if selected and selected[0] in MODES:
            self._mode = selected[0]
        self._segments.selected = [self._mode]
        self._rebuild_list()

    def set_mode(self, mode: str) -> None:
        self._mode = mode if mode in MODES else MODE_ACTUAL
        if hasattr(self, "_segments"):
            self._segments.selected = [self._mode]
        self._rebuild_list()

    # ------------------------------------------------------------------- данные

    async def _load_sections(self) -> None:
        """Словарь категорий, кросс-планы и контекст курсов для итогов периода."""
        await super()._load_sections()
        self._budgets, self._budget_hint = await load_cross_app_budgets(self.api_client, self._transaction_view)
        self._base_currency, self._prices, self._fx_rows = await asyncio.to_thread(self._fetch_fx)

    def _fetch_fx(self) -> tuple[str | None, list, list]:
        """База профиля, цены крипты и фиатные курсы для итогов (сеть — вне event loop)."""
        base = resolve_profile_base(self.api_client, self._fx_store)
        if base is None:
            return None, [], []
        try:
            prices = self.api_client.get_prices() or []
        except RestClientError:
            prices = []
        return base, prices, load_fx_rows(self.api_client, self._fx_store)

    # ------------------------------------------------------------------ выборка

    def _get_filtered_transactions(self) -> list[dict]:
        wanted_planned = self._mode == MODE_PLANNED
        rows = [tx for tx in self._transactions if bool(tx.get("is_planned")) is wanted_planned]
        if not wanted_planned and not self._show_snapshots.value:
            rows = [tx for tx in rows if not is_read_only_transaction(tx)]
        rows = filter_transactions(
            rows,
            period=self._filter_period.value or "all",
            account_id=self._filter_account.value,
            tx_type=self._filter_type.value or "all",
            category=self._filter_category.value or ALL_CATEGORY,
        )
        rows.sort(key=lambda tx: tx.get("date", ""), reverse=not wanted_planned)
        return rows

    # ------------------------------------------------------------------ рендер

    def _rebuild_list(self):
        is_actual = self._mode == MODE_ACTUAL
        self._show_snapshots.visible = is_actual
        self._filter_bar.visible = is_actual
        self._update_totals()
        if self._mode == MODE_PLANNED:
            self._rebuild_plan_list()
            return
        super()._rebuild_list()

    def _update_totals(self) -> None:
        rows = self._get_filtered_transactions()
        if self._mode == MODE_PLANNED:
            self._totals.value = f"Планов: {len(rows)}"
        elif self._base_currency:
            totals = period_totals(rows, self._account_map, self._base_currency, self._prices, self._fx_rows)
            self._totals.value = format_period_totals(totals, self._base_currency)
        else:
            self._totals.value = ""

    def _rebuild_plan_list(self) -> None:
        self._tx_list.controls.clear()
        self._day_groups = []
        self._pinned_label.value = ""
        self._pinned_header.visible = False
        rows = self._get_filtered_transactions()
        has_content = False

        if self._budgets:
            self._tx_list.controls.append(SectionHeader("Из задач и событий"))
            self._tx_list.controls.extend(
                CrossAppBudgetCard(item, on_open=self._open_cross_plan) for item in self._budgets
            )
            has_content = True
        elif self._budget_hint:
            self._tx_list.controls.append(ft.Text(self._budget_hint, size=12, color=ft.Colors.ON_SURFACE_VARIANT))
            has_content = True

        if rows:
            self._tx_list.controls.append(SectionHeader("Плановые операции"))
            self._tx_list.controls.extend(self._build_plan_card(tx) for tx in rows)
            has_content = True

        if not has_content:
            self._tx_list.controls.append(
                EmptyState(icon=ft.Icons.EVENT_NOTE, title=NO_PLANS_TITLE, subtitle=NO_PLANS_SUBTITLE)
            )

        self._tx_list.controls.append(ft.Container(height=FAB_CLEARANCE))
        self.update()

    def _open_cross_plan(self, item: dict) -> None:
        """Открыть задачу в MyList или событие в MyCalendar (2.51)."""
        open_cross_plan(self.page, item, self._show_error)

    def _build_plan_card(self, tx: dict) -> ft.Control:
        return build_plan_card(
            tx,
            self._account_map,
            on_execute=lambda item: self.page.run_task(self._execute_plan, item),
            on_edit=lambda item: self._open_transaction_dialog(tx=item, planned=True),
            on_delete=self._confirm_delete_plan,
        )

    async def _execute_plan(self, tx: dict) -> None:
        try:
            await execute_planned(self._transaction_view, self.api_client, tx)
        except Exception as exc:
            self._show_error(f"Ошибка проведения: {exc}")
            return
        self._mode = MODE_ACTUAL
        self._segments.selected = [self._mode]
        await self._load_data()

    def _confirm_delete_plan(self, tx: dict) -> None:
        async def delete() -> None:
            try:
                await self._delete_transaction(tx)
                self.page.pop_dialog()
            except Exception as exc:
                self._show_error(f"Ошибка удаления: {exc}")
                return
            await self._load_data()

        ConfirmDialog(
            title="Удалить план?",
            message=f"«{tx.get('description') or 'Без описания'}» будет удалён.",
            on_confirm=lambda _event: asyncio.create_task(delete()),
        ).show(self.page)

    def _show_add_dialog(self, e):
        self._open_transaction_dialog(planned=self._mode == MODE_PLANNED)


__all__ = ["MODES", "MODE_ACTUAL", "MODE_PLANNED", "OperationsView"]
