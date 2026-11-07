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
from application.session_cache import CACHE
from application.view.stale_cache import build_stale_banner, payload_changed

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
        self._stale_banner = build_stale_banner(self._retry_load)
        self._body = ft.Column(spacing=16, horizontal_alignment=ft.CrossAxisAlignment.STRETCH)
        self._content = ft.Column(
            controls=[self._connection_banner, self._error_text, self._stale_banner, self._loading, self._body],
            spacing=12,
            expand=True,
            scroll=ft.ScrollMode.AUTO,
        )

    def did_mount(self):
        super().did_mount()
        self._load_task = asyncio.create_task(self._load_data())

    def dispose(self):
        self._disposed = True

    def _cache_key(self) -> str:
        """Ключ витрины: наследник задаёт свой (``budgets``/``analytics``)."""
        return "data"

    def _section_snapshot(self) -> dict:
        """Снимок секций наследника (по умолчанию секций нет)."""
        return {}

    def _restore_sections(self, snapshot: dict) -> None:
        """Восстановить секции наследника из снимка."""

    def _data_snapshot(self) -> dict:
        return {
            "rows": self._rows,
            "accounts": self._accounts,
            "base_currency": self._base_currency,
            "sections": self._section_snapshot(),
        }

    def _paint_cached(self, snapshot: dict) -> None:
        self._rows = list(snapshot.get("rows") or [])
        self._accounts = list(snapshot.get("accounts") or [])
        self._base_currency = str(snapshot.get("base_currency") or "")
        self._restore_sections(snapshot.get("sections") or {})
        self._loading.visible = False
        self._stale_banner.visible = False
        self._rebuild()

    def _retry_load(self) -> None:
        CACHE.invalidate(self._cache_key())
        self._load_task = asyncio.create_task(self._load_data())

    async def _load_data(self) -> None:
        cached = CACHE.get(self._cache_key())
        if cached:
            self._paint_cached(cached)
            self.update()
        else:
            self._error_text.visible = False
            self._loading.visible = True
            self.update()
        try:
            self._error_text.visible = False
            self._stale_banner.visible = False

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
            snapshot = self._data_snapshot()
            CACHE.set(self._cache_key(), snapshot)
            if not cached or payload_changed(cached, snapshot):
                self._rebuild()
            self.update()
        except BackendUnreachableError:
            self._fail("Сервер недоступен", cached)
        except ApiError as exc:
            self._fail(f"Ошибка загрузки: {exc}", cached)

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

    def _fail(self, message: str, cached=None) -> None:
        if self._disposed:
            return
        self._loading.visible = False
        if cached:
            self._stale_banner.visible = True
            self._rebuild()
            self.update()
            return
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
