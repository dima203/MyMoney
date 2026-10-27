"""Общая загрузка витрин MyMoney: транзакции, счета, базовая валюта и офлайн-баннер.

Миксин используют экраны «Бюджеты» и «Аналитика»: данные берутся из dual-database
вьюх (или REST, если вьюх нет), ошибки показываются строкой над телом, а свои
секции наследник догружает в `_load_sections` и рисует в `_rebuild`.
"""

from __future__ import annotations

import asyncio
import datetime

import flet as ft
from application.api import ApiError, BackendUnreachableError

from MySpaceShared.components.connection_status import ConnectionBanner
from MySpaceShared.components.loading_state import LoadingState


def dict_rows(payload) -> list[dict]:
    """Строки ответа API (список или `{results: [...]}`), только dict-элементы."""
    if isinstance(payload, list):
        items = payload
    elif isinstance(payload, dict):
        items = payload.get("results", [])
    else:
        items = []
    return [item for item in items or [] if isinstance(item, dict)]


class DataLoadingMixin:
    """Загрузка витрины и офлайн-состояние для вьюх MyMoney.

    Рассчитывает на `BaseView` в MRO (`did_mount`/`update`); наследник
    переопределяет `_load_sections` (догрузка своих секций) и `_rebuild` (рендер).
    """

    def _init_data_loading(self, api_client, *, transaction_view=None, account_view=None, connection_banner=None):
        self.api_client = api_client
        self._transaction_view = transaction_view
        self._account_view = account_view
        self._connection_banner = connection_banner or ConnectionBanner()
        self._disposed = False
        self._rows: list[dict] = []
        self._accounts: list[dict] = []
        self._base_currency = ""

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
            if self._disposed:
                return

            self._rows = dict_rows(rows)
            self._accounts = dict_rows(accounts)
            self._base_currency = await self._fetch_base_currency()
            await self._load_sections()
            self._loading.visible = False
            self._sync_banner()
            self._rebuild()
        except BackendUnreachableError:
            self._fail("Сервер недоступен")
        except ApiError as exc:
            self._fail(f"Ошибка загрузки: {exc}")

    async def _load_sections(self) -> None:
        """Секции сверх общих данных (по умолчанию их нет)."""

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
        self._show_error(message)

    def _show_error(self, message: str) -> None:
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

    def _today(self) -> datetime.date:
        return datetime.date.today()


__all__ = ["DataLoadingMixin", "dict_rows"]
