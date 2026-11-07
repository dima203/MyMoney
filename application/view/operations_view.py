"""Экран «Операции»: фактические операции и план в одном месте (2.48b)."""

from __future__ import annotations

import asyncio
import datetime

import flet as ft
from application.api import ApiError, BackendUnreachableError, RestClientError
from application.apps_launcher import open_cross_plan
from application.components.cross_app_budget_card import CrossAppBudgetCard
from application.components.file_save import show_toast
from application.display import FAB_CLEARANCE, is_read_only_transaction
from application.fx_rates import FxRateStore, load_fx_rows, resolve_profile_base
from application.planned_actions import execute_planned
from application.session_cache import invalidate_data
from application.view.dialogs import dialog_width
from application.view.planned_sections import build_plan_card, load_cross_app_budgets
from application.view.transactions_view import TransactionsView
from core.okx_categories import apply_category, is_service_category, unlabeled_operations
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
TRANSFER_BADGE_HINT = "Похоже на перевод"
TRANSFER_BADGE_MANUAL = "Перевод?"
TRANSFER_LINK_LABEL = "Связать с операцией"
TRANSFER_MANUAL_LABEL = "Это перевод"
TRANSFER_EMPTY_HINT = "Совпадений нет — операция останется внешним поступлением/выводом."
TRANSFER_WINDOW_DAYS = 7


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
        self._transfer_suggestions: dict[int, dict] = {}
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
        self._okx_checks: list[ft.Checkbox] = []
        self._okx_rows: list[dict] = []
        self._okx_category = ft.Dropdown(
            label="Категория",
            options=[],
            border=ft.OutlineInputBorder(border_radius=8),
            on_select=lambda _event: self._sync_okx_apply_state(),
        )
        self._okx_select_all = ft.Checkbox(
            label="Выбрать все",
            value=False,
            on_change=self._on_okx_select_all,
        )
        self._okx_apply = ft.Button(
            "Применить",
            disabled=True,
            on_click=lambda _event: asyncio.create_task(self._apply_okx_categories()),
        )
        self._okx_categories_button = ft.IconButton(
            ft.Icons.SELL_OUTLINED,
            tooltip="Категории OKX",
            on_click=self._show_okx_categories_dialog,
        )
        self._filter_bar.controls.insert(1, self._okx_categories_button)

    # ------------------------------------------------ категории OKX (2.57b)

    def _show_okx_categories_dialog(self, _event=None) -> None:
        """Диалог массовой разметки: неразмеченные OKX-операции за период."""
        if not self._online():
            show_toast(self.page, "Нужен сервер")
            return
        period = str(getattr(self._filter_period, "value", None) or "all")
        self._okx_rows = unlabeled_operations(self._transactions, period=period)
        if not self._okx_rows:
            show_toast(self.page, "Все OKX-операции размечены")
            return

        self._okx_category.value = None
        self._okx_category.options = [
            ft.dropdown.Option(name) for name in self._active_category_names() if name and not is_service_category(name)
        ]
        self._okx_select_all.value = False
        self._okx_checks = [self._make_okx_check(row) for row in self._okx_rows]
        self._okx_apply.disabled = True
        self._okx_list = ft.Column(
            self._okx_checks,
            spacing=2,
            tight=True,
            scroll=ft.ScrollMode.AUTO,
            height=280,
        )
        body = ft.Column(
            [
                ft.Text(
                    f"Неразмечено: {len(self._okx_rows)}",
                    size=12,
                    color=ft.Colors.ON_SURFACE_VARIANT,
                ),
                self._okx_select_all,
                self._okx_list,
                self._okx_category,
            ],
            spacing=8,
            tight=True,
        )
        dialog = ft.AlertDialog(
            title=ft.Text("Категории OKX"),
            content=ft.Container(content=body, width=dialog_width(self)),
            actions=[
                ft.TextButton("Отмена", on_click=lambda _: self.page.pop_dialog()),
                self._okx_apply,
            ],
            actions_alignment=ft.MainAxisAlignment.END,
        )
        self.page.show_dialog(dialog)

    @staticmethod
    def _okx_row_label(tx: dict) -> str:
        """Строка выбора: дата, описание операции (или категория) и сумма."""
        title = str(tx.get("description") or tx.get("category") or "Операция").strip()
        if len(title) > 40:
            title = f"{title[:39]}…"
        entries = tx.get("entries") or []
        total = sum(float(entry.get("amount", 0)) for entry in entries if isinstance(entry, dict))
        return f"{str(tx.get('date') or '')[:10]} · {title} · {total:+.2f}"

    def _on_okx_select_all(self, event) -> None:
        value = bool(getattr(event.control, "value", False))
        for check in self._okx_checks:
            check.value = value
            try:
                check.update()
            except RuntimeError:
                pass
        self._sync_okx_apply_state()

    def _sync_okx_apply_state(self) -> None:
        """Кнопка «Применить» активна только при выборе строк и категории."""
        selected = any(check.value for check in self._okx_checks)
        self._okx_apply.disabled = not (selected and bool(self._okx_category.value))
        try:
            self._okx_apply.update()
        except RuntimeError:
            pass

    def _selected_okx_rows(self) -> list[dict]:
        return [row for row, check in zip(self._okx_rows, self._okx_checks, strict=False) if check.value]

    async def _apply_okx_categories(self) -> None:
        rows = self._selected_okx_rows()
        category = str(self._okx_category.value or "").strip()
        if not rows or not category:
            self._sync_okx_apply_state()
            return
        await self._apply_selected_categories(rows, category)

    async def _apply_selected_categories(self, rows: list[dict], category: str) -> None:
        """PATCH категории по выбранным операциям; частичный сбой — счётчики и повтор."""
        updated, failed = await asyncio.to_thread(
            apply_category,
            rows,
            category,
            self.api_client.update_transaction,
        )
        if failed:
            self._category_error(f"Обновлено {updated}, не удалось {len(failed)}: {failed[0]['error']}")
        else:
            self.page.pop_dialog()
            self._show_toast(f"Обновлено {updated} операций")
        await self._load_data()
        if failed:
            self._keep_failed_rows([item["id"] for item in failed])

    def _keep_failed_rows(self, failed_ids: list[int]) -> None:
        """Оставить в диалоге только неудачные строки, чтобы повтор не дублировал успешные."""
        failed = set(failed_ids)
        self._okx_rows = [row for row in self._okx_rows if row.get("id") in failed]
        self._okx_checks = [self._make_okx_check(row, value=True) for row in self._okx_rows]
        if getattr(self, "_okx_list", None) is not None:
            self._okx_list.controls = list(self._okx_checks)
            try:
                self._okx_list.update()
            except RuntimeError:
                pass
        self._sync_okx_apply_state()

    def _make_okx_check(self, row: dict, *, value: bool = False) -> ft.Checkbox:
        return ft.Checkbox(
            value=value,
            label=self._okx_row_label(row),
            on_change=lambda _event: self._sync_okx_apply_state(),
        )

    def _show_toast(self, text: str) -> None:
        show_toast(self.page, text)

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
        self._transfer_suggestions = await self._load_transfer_suggestions()
        self._budgets, self._budget_hint = await load_cross_app_budgets(self.api_client, self._transaction_view)
        self._base_currency, self._prices, self._fx_rows = await asyncio.to_thread(self._fetch_fx)

    def _online(self) -> bool:
        """Доступен ли сервер (офлайн-слой знает лучше, чем прямой клиент)."""
        return bool(getattr(self._transaction_view, "is_online", True))

    async def _load_transfer_suggestions(self) -> dict[int, dict]:
        """Несвязанные OKX-вводы/выводы с кандидатами (2.160b); офлайн — пусто."""
        if not self._online():
            return {}
        try:
            payload = await asyncio.to_thread(self.api_client.list_okx_transfer_suggestions)
        except (RestClientError, AttributeError, TypeError):
            return {}
        if not isinstance(payload, dict):
            return {}
        return {
            item["okx_transaction"]: item
            for item in payload.get("items") or []
            if isinstance(item, dict) and isinstance(item.get("okx_transaction"), int)
        }

    def _transfer_card_options(self, tx: dict) -> dict:
        """Бейдж и действие «связать» у несвязанного OKX-ввода/вывода."""
        suggestion = self._transfer_suggestions.get(tx.get("id"))
        if suggestion is None or tx.get("kind") == "transfer":
            return {}
        candidates = suggestion.get("candidates") or []
        return {
            "badge": TRANSFER_BADGE_HINT if candidates else TRANSFER_BADGE_MANUAL,
            "on_link_transfer": lambda t=tx, s=suggestion: self._show_transfer_dialog(t, s),
            "link_label": TRANSFER_LINK_LABEL if candidates else TRANSFER_MANUAL_LABEL,
        }

    @staticmethod
    def _tx_day(tx: dict) -> datetime.date | None:
        try:
            return datetime.date.fromisoformat(str(tx.get("date") or "")[:10])
        except ValueError:
            return None

    def _manual_operations(self, okx: dict) -> list[dict]:
        """Ручной выбор операции за ±7 дней, если сервер не нашёл кандидатов."""
        target = self._tx_day(okx)
        if target is None:
            return []
        rows: list[dict] = []
        for tx in self._transactions:
            if tx.get("id") == okx.get("id") or tx.get("is_planned"):
                continue
            if tx.get("source") == "okx":
                continue
            if tx.get("kind") in ("snapshot", "opening", "transfer"):
                continue
            day = self._tx_day(tx)
            if day is None or abs((day - target).days) > TRANSFER_WINDOW_DAYS:
                continue
            rows.append(tx)
        rows.sort(key=lambda item: item.get("date", ""), reverse=True)
        return rows

    def _operation_label(self, tx: dict) -> str:
        entries = tx.get("entries") or []
        total = sum(float(entry.get("amount", 0)) for entry in entries)
        title = tx.get("category") or tx.get("description") or "Операция"
        return f"{str(tx.get('date') or '')[:10]} · {title} · {total:+.2f}"

    def _show_transfer_dialog(self, tx: dict, suggestion: dict | None = None) -> None:
        """Подтверждение пары OKX ↔ карта: кандидаты или ручной выбор за ±7 дней."""
        if not self._online():
            show_toast(self.page, "Нужен сервер")
            return
        suggestion = suggestion or {}
        candidates = suggestion.get("candidates") or []
        if candidates:
            options = [
                ft.Radio(
                    value=str(candidate["id"]),
                    label=(
                        f"{candidate.get('account_name', '')} · {str(candidate.get('date', ''))[:10]} · "
                        f"{candidate.get('amount', '')} ({candidate.get('diff_percent', '')} %)"
                    ),
                )
                for candidate in candidates
            ]
        else:
            options = [
                ft.Radio(value=str(item["id"]), label=self._operation_label(item))
                for item in self._manual_operations(tx)
            ]
        radio = ft.RadioGroup(content=ft.Column(options, spacing=4), value=options[0].value if options else None)
        controls: list[ft.Control] = [
            ft.Text(tx.get("description") or "OKX", size=14, weight=ft.FontWeight.W_600),
            ft.Text("Выберите операцию на счёте вне OKX:", size=12, color=ft.Colors.ON_SURFACE_VARIANT),
            radio,
        ]
        if not candidates:
            controls.append(ft.Text(TRANSFER_EMPTY_HINT, size=12, color=ft.Colors.ON_SURFACE_VARIANT))

        async def confirm(_event) -> None:
            if not radio.value:
                return
            try:
                await asyncio.to_thread(self.api_client.link_okx_transfer, tx["id"], int(radio.value))
            except (ApiError, BackendUnreachableError, RestClientError) as exc:
                self._show_error(f"Не удалось связать: {exc}")
                return
            self.page.pop_dialog()
            invalidate_data()
            await self._load_data()

        dialog = ft.AlertDialog(
            title=ft.Text("Связать перевод"),
            content=ft.Container(content=ft.Column(controls, spacing=8, tight=True), width=dialog_width(self)),
            actions=[
                ft.TextButton("Отмена", on_click=lambda _: self.page.pop_dialog()),
                ft.Button(
                    "Связать",
                    disabled=not options,
                    on_click=lambda e: asyncio.create_task(confirm(e)),
                ),
            ],
            actions_alignment=ft.MainAxisAlignment.END,
        )
        self.page.show_dialog(dialog)

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
