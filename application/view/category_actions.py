"""Общие действия со словарём категорий для экранов MyMoney (2.53)."""

from __future__ import annotations

import asyncio

from application.api import ApiError, RestClientError
from application.components.category_picker import CategoryPicker


class CategoryActionsMixin:
    """Загрузка словаря и CRUD для ``CategoryPicker``.

    Наследник предоставляет ``api_client``, ``_error_text`` (строка ошибки экрана)
    и ``_category_rows`` (список загруженного словаря).
    """

    async def _load_categories(self) -> None:
        self._category_rows = []
        try:
            rows = await asyncio.to_thread(self.api_client.list_categories)
        except (RestClientError, AttributeError):
            rows = []
        self._category_rows = [row for row in rows if isinstance(row, dict)] if isinstance(rows, list) else []

    def _active_category_names(self) -> list[str]:
        return [str(row.get("name") or "") for row in getattr(self, "_category_rows", []) if not row.get("is_archived")]

    def _picker_categories(self, current: str = "") -> list[str] | None:
        """Активные категории; ``None`` — словарь недоступен (встроенный список).

        Текущее значение операции сохраняется в списке, даже если его ещё нет
        в словаре (старые записи до бэкфилла/ручные строки).
        """
        names = self._active_category_names()
        if not names:
            return [] if getattr(self, "_category_rows", []) else None
        if current and current.casefold() not in {name.casefold() for name in names}:
            return [current, *names]
        return names

    def _build_category_picker(self, value: str = "") -> CategoryPicker:
        """Пикер с серверным словарём, callback-ами CRUD и текущим значением операции."""
        return CategoryPicker(
            value=value,
            categories=self._picker_categories(value),
            rows=getattr(self, "_category_rows", []) or None,
            on_create=self._create_category,
            on_rename=self._rename_category,
            on_archive=self._archive_category,
        )

    def _category_id(self, name: str) -> int | None:
        folded = str(name or "").strip().casefold()
        for row in getattr(self, "_category_rows", []):
            if str(row.get("name") or "").strip().casefold() == folded:
                return row.get("id")
        return None

    async def _create_category(self, name: str) -> str | None:
        try:
            row = await asyncio.to_thread(self.api_client.create_category, {"name": name})
        except (ApiError, RestClientError) as exc:
            self._category_error(f"Не удалось создать категорию: {exc}")
            return None
        await self._load_categories()
        return str(row.get("name") or name) if isinstance(row, dict) else name

    async def _patch_category(self, name: str, payload: dict, failure: str) -> dict | None:
        """PATCH категории по названию: поиск id, ошибки и перезагрузка словаря."""
        category_id = self._category_id(name)
        if category_id is None:
            self._category_error(f"Категория «{name}» не найдена в словаре")
            return None
        try:
            row = await asyncio.to_thread(self.api_client.update_category, category_id, payload)
        except (ApiError, RestClientError) as exc:
            self._category_error(f"{failure}: {exc}")
            return None
        await self._load_categories()
        return row if isinstance(row, dict) else {"name": name, **payload}

    async def _rename_category(self, old: str, new: str) -> str | None:
        row = await self._patch_category(old, {"name": new}, "Не удалось переименовать категорию")
        return str(row.get("name") or new) if row else None

    async def _archive_category(self, name: str, archived: bool):
        return await self._patch_category(name, {"is_archived": archived}, "Не удалось обновить категорию")

    def _category_error(self, message: str) -> None:
        self._error_text.value = message
        self._error_text.visible = True
        self.update()


__all__ = ["CategoryActionsMixin"]
