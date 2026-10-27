"""Экран «Бюджеты» MyMoney: конверты месяца, цели накоплений и шаблоны (B-13).

Раньше эти секции жили внизу «Аналитики» и терялись среди графиков; теперь это
отдельный раздел навигации, а аналитика остаётся про расходы по месяцам.
"""

from __future__ import annotations

import asyncio
import datetime

import flet as ft
from application.api import ApiError, BackendUnreachableError
from application.components import BaseView
from application.components.envelope_card import EnvelopeCard
from application.components.file_save import show_toast
from application.components.goal_card import GoalCard
from application.components.navigation_items import NAVIGATION_ITEMS
from application.view.budget_forms import DIALOG_WIDTH, FormDialogMixin, dict_rows, form_error, hint
from core.budget_templates import template_infos, template_items, template_payload
from core.envelopes import EnvelopeProgress, envelope_payload, envelope_progress
from core.goals import (
    DATE_FORMAT,
    GoalProgress,
    contribution_payload,
    goal_payload,
    goal_progress,
)

from MySpaceShared.components.connection_status import ConnectionBanner
from MySpaceShared.components.loading_state import LoadingState
from MySpaceShared.components.section_header import SectionHeader

BUDGETS_INDEX = 3
TITLE = "Бюджеты"
ENVELOPES_TITLE = "Конверты месяца"
ENVELOPES_KEY = "envelopes"
ENVELOPES_EMPTY = "Лимиты не заданы — добавьте конверт, чтобы следить за тратами по категории"
ENVELOPES_OFFLINE = "Конверты недоступны без подключения к серверу"
ENVELOPES_SUBTITLE = "Лимит расходов на текущий месяц по категории"
TEMPLATES_BUTTON = "Шаблоны"
TEMPLATES_TITLE = "Шаблоны бюджетов"
TEMPLATES_SAVE = "Сохранить из текущих"
TEMPLATES_APPLY = "Применить"
TEMPLATES_NAME = "Название шаблона"
TEMPLATES_PUBLIC = "Публичный шаблон"
TEMPLATES_MINE = "Мои шаблоны"
TEMPLATES_PUBLIC_SECTION = "Публичные шаблоны"
TEMPLATES_EMPTY = "Шаблонов нет — сохраните текущие конверты"
TEMPLATES_SAVED = "Шаблон сохранён"
TEMPLATES_DELETE = "Удалить шаблон"
GOALS_TITLE = "Цели накоплений"
GOALS_KEY = "goals"
GOALS_EMPTY = "Целей нет — добавьте цель, чтобы следить за накоплениями"
GOALS_OFFLINE = "Цели недоступны без подключения к серверу"
GOALS_SUBTITLE = "Накопления к целевой сумме; пополнения добавляются вручную"
SECTION_ADD = "Добавить"
SAVE_BUSY = "Сохранение..."
TEMPLATES_DIALOG_HEIGHT = 420
TEMPLATE_FAILED = object()


def limit_text(value) -> str:
    """Сумма для поля ввода: «500» вместо «500.0000»."""
    if value is None or (isinstance(value, str) and not value.strip()):
        return ""
    try:
        amount = float(value)
    except (TypeError, ValueError):
        return ""
    return f"{amount:.2f}".rstrip("0").rstrip(".")


def _goal_row(goal: GoalProgress) -> dict:
    """Строка цели для диалогов, если исходная запись недоступна."""
    return {
        "name": goal.name,
        "target_amount": goal.target_amount,
        "saved_amount": goal.saved_amount,
        "currency_ticker": goal.currency,
        "deadline": goal.deadline.isoformat() if goal.deadline else None,
    }


class BudgetsView(FormDialogMixin, BaseView):
    """Конверты месяца, цели накоплений и шаблоны бюджетов."""

    def __init__(self, route: str, api_client, transaction_view=None, account_view=None, connection_banner=None):
        self.api_client = api_client
        self._transaction_view = transaction_view
        self._account_view = account_view
        self._connection_banner = connection_banner or ConnectionBanner()
        self._disposed = False
        self._rows: list[dict] = []
        self._accounts: list[dict] = []
        self._base_currency = ""
        self._envelopes: list[dict] = []
        self._envelopes_offline = False
        self._goals: list[dict] = []
        self._goals_offline = False

        self._error_text = ft.Text("", size=13, color=ft.Colors.ERROR, visible=False)
        self._loading = LoadingState()
        self._loading.visible = True
        self._body = ft.Column(spacing=16, horizontal_alignment=ft.CrossAxisAlignment.STRETCH)
        self._content = ft.Column(
            controls=[self._connection_banner, self._error_text, self._loading, self._body],
            spacing=12,
            expand=True,
            scroll=ft.ScrollMode.AUTO,
        )

        super().__init__(
            content=self._content,
            title=TITLE,
            route=route,
            selected_index=BUDGETS_INDEX,
            navigation_items=NAVIGATION_ITEMS,
        )

    def did_mount(self):
        super().did_mount()
        self._load_task = asyncio.create_task(self._load_data())

    def dispose(self):
        self._disposed = True

    # ------------------------------------------------------------- загрузка

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

            self._rows = dict_rows(rows)
            self._accounts = dict_rows(accounts)
            self._base_currency = await self._fetch_base_currency()
            await self._load_envelopes()
            await self._load_goals()
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
        """Конверты online-only: их сбой не должен ломать остальные секции."""
        rows = await self._load_online(self.api_client.list_envelopes)
        self._envelopes = rows or []
        self._envelopes_offline = rows is None

    async def _load_goals(self) -> None:
        """Цели online-only: их сбой не должен ломать остальные секции."""
        rows = await self._load_online(self.api_client.list_goals)
        self._goals = rows or []
        self._goals_offline = rows is None

    async def _load_online(self, loader) -> list[dict] | None:
        """Строки online-only секции; None — офлайн или сервер недоступен."""
        if self._offline:
            return None
        try:
            payload = await asyncio.to_thread(loader)
        except (ApiError, BackendUnreachableError):
            return None
        return dict_rows(payload)

    async def _reload_envelopes(self) -> None:
        await self._load_envelopes()
        self._rebuild()

    async def _reload_goals(self) -> None:
        await self._load_goals()
        self._rebuild()

    def _fail(self, message: str) -> None:
        if self._disposed:
            return
        self._loading.visible = False
        self._show_error(message)

    def _show_error(self, message: str) -> None:
        self._error_text.value = message
        self._error_text.visible = True
        self.update()

    @property
    def _offline(self) -> bool:
        return self._transaction_view is not None and not self._transaction_view.is_online

    def _sync_banner(self) -> None:
        if self._offline:
            self._connection_banner.show()
        else:
            self._connection_banner.hide()

    def _today(self) -> datetime.date:
        return datetime.date.today()

    # --------------------------------------------------------------- рендер

    def _rebuild(self) -> None:
        self._body.controls = [*self._envelopes_section(), *self._goals_section()]
        self.update()

    def _section_header(
        self,
        title: str,
        key: str,
        trailing: ft.Control | None = None,
    ) -> SectionHeader:
        """Заголовок секции; `key` нужен для прокрутки к секции."""
        header = SectionHeader(title, trailing=trailing)
        header.key = key
        return header

    def _currency_options(self) -> dict[str, int | None]:
        """Тикер валюты → id ресурса (для FK конверта/цели); базовая может быть без id."""
        options: dict[str, int | None] = {}
        for account in self._accounts:
            ticker = account.get("resource")
            resource_id = account.get("resource_definition")
            if isinstance(ticker, str) and ticker.strip():
                options.setdefault(ticker.strip(), resource_id if isinstance(resource_id, int) else None)
        if self._base_currency:
            options.setdefault(self._base_currency, None)
        return options

    def _currency_dropdown(self, selected: str, currency_map: dict[str, int | None]) -> ft.Dropdown:
        options = [ft.DropdownOption(key=ticker, text=ticker) for ticker in sorted(currency_map)]
        if selected and selected not in currency_map:
            options.append(ft.DropdownOption(key=selected, text=selected))
        return ft.Dropdown(label="Валюта", value=selected or None, options=options, width=DIALOG_WIDTH)

    # -------------------------------------------------------------- конверты

    def _envelopes_section(self) -> list[ft.Control]:
        if self._envelopes_offline:
            return [self._section_header(ENVELOPES_TITLE, ENVELOPES_KEY), hint(ENVELOPES_OFFLINE)]

        progress = envelope_progress(
            self._envelopes,
            self._rows,
            self._accounts,
            today=self._today(),
            base_currency=self._base_currency,
        )
        add_button = ft.TextButton(SECTION_ADD, icon=ft.Icons.ADD, on_click=self._open_envelope_editor)
        templates_button = ft.TextButton(
            TEMPLATES_BUTTON,
            icon=ft.Icons.BOOKMARKS_OUTLINED,
            on_click=self._open_templates,
        )
        header = self._section_header(
            ENVELOPES_TITLE,
            ENVELOPES_KEY,
            ft.Row(controls=[templates_button, add_button], spacing=4),
        )
        if not progress:
            return [header, hint(ENVELOPES_EMPTY)]
        cards = self._envelope_cards(progress)
        return [header, hint(ENVELOPES_SUBTITLE, size=12), ft.Column(cards, spacing=12)]

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

    def _envelope_dialog(self, envelope: dict) -> ft.AlertDialog:
        currency_map = self._currency_options()
        selected_currency = str(envelope.get("currency_ticker") or self._base_currency or "")
        envelope_id = envelope.get("id")

        category_field = ft.TextField(label="Категория", value=str(envelope.get("category") or ""), autofocus=True)
        limit_field = ft.TextField(
            label="Лимит на месяц",
            value=limit_text(envelope.get("limit_amount")),
            keyboard_type=ft.KeyboardType.NUMBER,
        )
        currency_dropdown = self._currency_dropdown(selected_currency, currency_map)

        def build_payload() -> dict:
            return envelope_payload(
                category_field.value,
                limit_field.value,
                currency_map.get(currency_dropdown.value or ""),
            )

        async def save(payload: dict) -> None:
            if envelope_id:
                await asyncio.to_thread(self.api_client.update_envelope, envelope_id, payload)
            else:
                await asyncio.to_thread(self.api_client.create_envelope, payload)
            self.page.pop_dialog()
            await self._reload_envelopes()

        return self._form_dialog(
            title="Изменить конверт" if envelope_id else "Новый конверт",
            fields=[category_field, limit_field, currency_dropdown],
            save_text="Сохранить",
            busy_text=SAVE_BUSY,
            build_payload=build_payload,
            save=save,
        )

    def _open_envelope_editor(self, envelope: dict | None = None) -> None:
        self.page.show_dialog(self._envelope_dialog(envelope if isinstance(envelope, dict) else {}))

    def _confirm_delete_envelope(self, envelope: dict) -> None:
        category = str(envelope.get("category") or "")
        self._confirm_delete(
            title="Удалить конверт?",
            message=f"Конверт «{category}» будет удалён.",
            remove=lambda: self.api_client.delete_envelope(envelope.get("id")),
            reload=self._reload_envelopes,
        )

    # -------------------------------------------------------------- шаблоны

    async def _open_templates(self, _event=None) -> None:
        """Загрузить свои и публичные шаблоны и открыть диалог."""
        try:
            mine, public = await asyncio.gather(
                asyncio.to_thread(self.api_client.list_budget_templates, scope="mine"),
                asyncio.to_thread(self.api_client.list_budget_templates, scope="public"),
            )
        except (ApiError, BackendUnreachableError) as exc:
            self._show_error(f"Ошибка шаблонов: {exc}")
            return
        self.page.show_dialog(self._templates_dialog(dict_rows(mine), dict_rows(public)))

    def _templates_dialog(self, mine, public) -> ft.AlertDialog:
        name_field = ft.TextField(label=TEMPLATES_NAME, value="")
        public_switch = ft.Switch(label=TEMPLATES_PUBLIC, value=False)
        error_text = form_error()
        save_button = ft.Button(TEMPLATES_SAVE)
        save_button.on_click = self._save_handler(
            save_button=save_button,
            error_text=error_text,
            save_text=TEMPLATES_SAVE,
            busy_text=SAVE_BUSY,
            build_payload=lambda: template_payload(
                name_field.value,
                template_items(self._envelopes),
                is_public=bool(public_switch.value),
            ),
            save=self._create_template,
        )

        controls: list[ft.Control] = [
            name_field,
            public_switch,
            error_text,
            ft.Row([save_button]),
            ft.Divider(height=1),
            *self._template_lists(mine, public),
        ]
        return ft.AlertDialog(
            title=ft.Text(TEMPLATES_TITLE),
            content=ft.Container(
                content=ft.Column(
                    controls=controls,
                    spacing=8,
                    width=DIALOG_WIDTH,
                    scroll=ft.ScrollMode.AUTO,
                    horizontal_alignment=ft.CrossAxisAlignment.STRETCH,
                ),
                height=TEMPLATES_DIALOG_HEIGHT,
            ),
            actions=[
                ft.TextButton("Закрыть", on_click=lambda _event: self.page.pop_dialog()),
            ],
            actions_alignment=ft.MainAxisAlignment.END,
        )

    async def _create_template(self, payload: dict) -> None:
        """Сохранить шаблон из текущих конвертов, закрыть диалог и подтвердить тостом."""
        await asyncio.to_thread(self.api_client.create_budget_template, payload)
        self.page.pop_dialog()
        show_toast(self.page, TEMPLATES_SAVED)

    def _template_lists(self, mine, public) -> list[ft.Control]:
        """Разделы «Мои»/«Публичные»; если шаблонов нет — подсказка пустого состояния."""
        mine_infos = template_infos(mine)
        public_infos = template_infos(public)
        if not mine_infos and not public_infos:
            return [hint(TEMPLATES_EMPTY, size=12)]
        return [
            *self._template_section(TEMPLATES_MINE, mine_infos, own=True),
            *self._template_section(TEMPLATES_PUBLIC_SECTION, public_infos, own=False),
        ]

    def _template_section(self, title: str, infos, *, own: bool) -> list[ft.Control]:
        """Подпись раздела и плитки его шаблонов (пустой раздел не показывается)."""
        if not infos:
            return []
        return [hint(title, size=12), *(self._template_tile(info, own=own) for info in infos)]

    def _template_tile(self, info, *, own: bool) -> ft.Control:
        """Строка шаблона: имя с подзаголовком и действия справа."""
        title = ft.Column(
            controls=[
                ft.Text(info.name, size=14),
                ft.Text(info.subtitle, size=12, color=ft.Colors.ON_SURFACE_VARIANT),
            ],
            spacing=2,
            expand=True,
        )
        return ft.Container(
            content=ft.Row(
                controls=[title, ft.Row(controls=self._template_actions(info, own=own), spacing=0)],
                vertical_alignment=ft.CrossAxisAlignment.CENTER,
            ),
            padding=ft.Padding.symmetric(horizontal=4, vertical=2),
        )

    def _template_actions(self, info, *, own: bool) -> list[ft.Control]:
        """«Применить» у любого шаблона, удаление — только у своего."""
        template_id = info.template_id
        actions: list[ft.Control] = [
            ft.TextButton(
                TEMPLATES_APPLY,
                on_click=lambda _event: asyncio.create_task(self._apply_template(template_id)),
            )
        ]
        if own and template_id is not None:
            actions.append(
                ft.IconButton(
                    ft.Icons.DELETE_OUTLINE,
                    tooltip=TEMPLATES_DELETE,
                    icon_size=18,
                    on_click=lambda _event: asyncio.create_task(self._delete_template(template_id)),
                )
            )
        return actions

    async def _template_request(self, template_id: int | None, label: str, call):
        """Запрос к API шаблона в потоке; `TEMPLATE_FAILED` — нечего делать или ошибка показана."""
        if template_id is None:
            return TEMPLATE_FAILED
        try:
            return await asyncio.to_thread(call, template_id)
        except (ApiError, BackendUnreachableError) as exc:
            self._show_error(f"Ошибка {label}: {exc}")
            return TEMPLATE_FAILED

    async def _apply_template(self, template_id: int | None) -> None:
        result = await self._template_request(template_id, "применения", self.api_client.apply_budget_template)
        if result is TEMPLATE_FAILED:
            return
        self.page.pop_dialog()
        counts = result if isinstance(result, dict) else {}
        created, skipped = counts.get("created", 0), counts.get("skipped", 0)
        show_toast(self.page, f"Создано конвертов: {created}, пропущено: {skipped}")
        await self._reload_envelopes()

    async def _delete_template(self, template_id: int | None) -> None:
        removed = await self._template_request(template_id, "удаления шаблона", self.api_client.delete_budget_template)
        if removed is TEMPLATE_FAILED:
            return
        self.page.pop_dialog()
        await self._open_templates()

    # ------------------------------------------------------------------ цели

    def _goals_section(self) -> list[ft.Control]:
        if self._goals_offline:
            return [self._section_header(GOALS_TITLE, GOALS_KEY), hint(GOALS_OFFLINE)]

        progress = goal_progress(self._goals, base_currency=self._base_currency)
        add_button = ft.TextButton(SECTION_ADD, icon=ft.Icons.ADD, on_click=self._open_goal_editor)
        header = self._section_header(GOALS_TITLE, GOALS_KEY, add_button)
        if not progress:
            return [header, hint(GOALS_EMPTY)]
        cards = self._goal_cards(progress)
        return [header, hint(GOALS_SUBTITLE, size=12), ft.Column(cards, spacing=12)]

    def _goal_cards(self, progress: list[GoalProgress]) -> list[ft.Control]:
        raw_by_id = {row.get("id"): row for row in self._goals}
        return [self._goal_card(item, raw_by_id.get(item.goal_id)) for item in progress]

    def _goal_card(self, item: GoalProgress, raw: dict | None) -> GoalCard:
        goal = raw or _goal_row(item)
        return GoalCard(
            item,
            today=self._today(),
            on_contribute=lambda _event, goal=goal: self._open_contribution_dialog(goal),
            on_edit=lambda _event, goal=goal: self._open_goal_editor(goal),
            on_delete=lambda _event, goal=goal: self._confirm_delete_goal(goal),
        )

    def _goal_dialog(self, goal: dict) -> ft.AlertDialog:
        currency_map = self._currency_options()
        selected_currency = str(goal.get("currency_ticker") or self._base_currency or "")
        goal_id = goal.get("id")

        name_field = ft.TextField(label="Название", value=str(goal.get("name") or ""), autofocus=True)
        target_field = ft.TextField(
            label="Цель",
            value=limit_text(goal.get("target_amount")),
            keyboard_type=ft.KeyboardType.NUMBER,
        )
        saved_field = ft.TextField(
            label="Уже накоплено",
            value=limit_text(goal.get("saved_amount")),
            keyboard_type=ft.KeyboardType.NUMBER,
        )
        deadline_field = ft.TextField(
            label=f"Срок ({DATE_FORMAT})",
            value=str(goal.get("deadline") or ""),
        )
        currency_dropdown = self._currency_dropdown(selected_currency, currency_map)

        def build_payload() -> dict:
            return goal_payload(
                name_field.value,
                target_field.value,
                saved_field.value,
                currency_map.get(currency_dropdown.value or ""),
                deadline_field.value,
            )

        async def save(payload: dict) -> None:
            if goal_id:
                await asyncio.to_thread(self.api_client.update_goal, goal_id, payload)
            else:
                await asyncio.to_thread(self.api_client.create_goal, payload)
            self.page.pop_dialog()
            await self._reload_goals()

        return self._form_dialog(
            title="Изменить цель" if goal_id else "Новая цель",
            fields=[name_field, target_field, saved_field, deadline_field, currency_dropdown],
            save_text="Сохранить",
            busy_text=SAVE_BUSY,
            build_payload=build_payload,
            save=save,
        )

    def _contribution_dialog(self, goal: dict) -> ft.AlertDialog:
        amount_field = ft.TextField(
            label="Сумма пополнения",
            keyboard_type=ft.KeyboardType.NUMBER,
            autofocus=True,
        )

        def build_payload() -> dict:
            return contribution_payload(goal.get("saved_amount"), amount_field.value)

        async def save(payload: dict) -> None:
            await asyncio.to_thread(self.api_client.update_goal, goal.get("id"), payload)
            self.page.pop_dialog()
            await self._reload_goals()

        return self._form_dialog(
            title=f"Пополнить «{goal.get('name') or ''}»",
            fields=[amount_field],
            save_text="Пополнить",
            busy_text="Пополнение...",
            build_payload=build_payload,
            save=save,
        )

    def _open_goal_editor(self, goal: dict | None = None) -> None:
        self.page.show_dialog(self._goal_dialog(goal if isinstance(goal, dict) else {}))

    def _open_contribution_dialog(self, goal: dict) -> None:
        self.page.show_dialog(self._contribution_dialog(goal))

    def _confirm_delete_goal(self, goal: dict) -> None:
        name = str(goal.get("name") or "")
        self._confirm_delete(
            title="Удалить цель?",
            message=f"Цель «{name}» будет удалена.",
            remove=lambda: self.api_client.delete_goal(goal.get("id")),
            reload=self._reload_goals,
        )


__all__ = ["BUDGETS_INDEX", "BudgetsView", "limit_text"]
