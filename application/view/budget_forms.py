"""Общая обвязка форм MyMoney: диалог с валидацией, сохранением и удалением.

Используется экраном «Бюджеты»: поля + строка ошибки, кнопка блокируется на время
запроса, ошибки сервера остаются в диалоге.
"""

from __future__ import annotations

import asyncio

import flet as ft
from application.api import ApiError, BackendUnreachableError
from application.view.dialogs import DIALOG_MAX_WIDTH, dialog_width

from MySpaceShared.components.confirm_dialog import ConfirmDialog

DIALOG_WIDTH = DIALOG_MAX_WIDTH


def hint(text: str, *, size: int = 13) -> ft.Text:
    """Приглушённая подпись секции."""
    return ft.Text(text, size=size, color=ft.Colors.ON_SURFACE_VARIANT)


def form_error() -> ft.Text:
    """Скрытая строка ошибки валидации в диалоге формы."""
    return ft.Text("", size=12, color=ft.Colors.ERROR, visible=False)


class FormDialogMixin:
    """Диалог формы и подтверждение удаления для вьюх MyMoney.

    Рассчитывает на ``self.page`` и ``self._show_error`` у вьюхи-наследника.
    """

    def _dialog_error(self, error_text: ft.Text, message: str) -> None:
        error_text.value = message
        error_text.visible = True
        self.page.update()

    def _save_handler(self, *, save_button, error_text: ft.Text, save_text: str, busy_text: str, build_payload, save):
        """Обработчик кнопки сохранения: валидация → busy → запрос, ошибки остаются в диалоге."""

        async def on_click(_event) -> None:
            try:
                payload = build_payload()
            except ValueError as exc:
                self._dialog_error(error_text, str(exc))
                return

            save_button.disabled = True
            save_button.content = busy_text
            self.page.update()
            try:
                await save(payload)
            except (ApiError, BackendUnreachableError) as exc:
                save_button.disabled = False
                save_button.content = save_text
                self._dialog_error(error_text, str(exc))

        return on_click

    def _form_dialog(
        self,
        *,
        title: str,
        fields: list[ft.Control],
        save_text: str,
        busy_text: str,
        build_payload,
        save,
    ) -> ft.AlertDialog:
        """Диалог формы: поля и ошибка, «Отмена»/save с общей обвязкой сохранения.

        `build_payload` проверяет ввод и отдаёт тело запроса (ValueError → ошибка в диалоге),
        `save` отправляет его на сервер, закрывает диалог и перечитывает секцию.
        """
        error_text = form_error()

        save_button = ft.Button(save_text)
        save_button.on_click = self._save_handler(
            save_button=save_button,
            error_text=error_text,
            save_text=save_text,
            busy_text=busy_text,
            build_payload=build_payload,
            save=save,
        )
        return ft.AlertDialog(
            title=ft.Text(title),
            content=ft.Container(
                content=ft.ResponsiveRow(
                    controls=[*fields, error_text],
                    spacing=12,
                    run_spacing=12,
                    columns=12,
                    width=dialog_width(self),
                ),
            ),
            actions=[
                ft.TextButton("Отмена", on_click=lambda _: self.page.pop_dialog()),
                save_button,
            ],
            actions_alignment=ft.MainAxisAlignment.END,
        )

    def _confirm_delete(self, *, title: str, message: str, remove, reload) -> None:
        """Подтверждение удаления: `remove` — вызов сервера, `reload` — перечитывание секции."""

        async def delete(_event) -> None:
            try:
                await asyncio.to_thread(remove)
            except (ApiError, BackendUnreachableError) as exc:
                self.page.pop_dialog()
                self._show_error(f"Ошибка удаления: {exc}")
                return
            self.page.pop_dialog()
            await reload()

        ConfirmDialog(
            title=title,
            message=message,
            on_confirm=lambda event: asyncio.create_task(delete(event)),
        ).show(self.page)


__all__ = ["DIALOG_WIDTH", "FormDialogMixin", "form_error", "hint"]
