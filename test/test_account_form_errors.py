"""Ошибки сервера в форме счёта MyMoney (2.41): читаемый текст и подсветка полей."""

from __future__ import annotations

import flet as ft
from application.api import ApiError, BackendUnreachableError
from application.view.accounts_view import FIELD_LABELS, apply_api_error, field_error, set_field_error


def _fields() -> dict[str, ft.Control]:
    return {
        "name": ft.TextField(label="Название"),
        "resource_definition": ft.Dropdown(label="Валюта/Ресурс"),
        "group": ft.TextField(label="Группа"),
        "account_type": ft.Dropdown(label="Тип счёта"),
    }


def _error() -> ft.Text:
    return ft.Text("", size=12, color=ft.Colors.ERROR, visible=False)


class TestFieldErrors:
    def test_errors_are_laid_out_on_fields(self) -> None:
        fields = _fields()
        error_text = _error()
        exc = ApiError(
            400,
            detail={
                "resource_definition": ["account with this user, resource definition and account type already exists."],
                "account_type": ["Неверный тип"],
            },
        )

        apply_api_error(error_text, exc, fields)

        assert "already exists" in field_error(fields["resource_definition"])
        assert field_error(fields["account_type"]) == "Неверный тип"
        assert field_error(fields["name"]) is None
        assert error_text.visible is True
        assert "Тип счёта: Неверный тип" in error_text.value
        assert "Валюта/ресурс:" in error_text.value

    def test_field_errors_use_visible_error_property(self) -> None:
        """В Flet 1.0.3 подпись ошибки — `error`, а не несуществующий `error_text`."""
        fields = _fields()
        exc = ApiError(400, detail={"name": ["Обязательное поле"]})

        apply_api_error(_error(), exc, fields)

        assert field_error(fields["name"]) == "Обязательное поле"
        assert hasattr(type(fields["name"]), "error")
        assert not hasattr(type(fields["name"]), "error_text")

    def test_field_labels_cover_form_fields(self) -> None:
        assert set(FIELD_LABELS) >= {"name", "resource_definition", "group", "account_type"}

    def test_field_error_can_be_cleared_for_dropdown(self) -> None:
        """Сброс ошибки работает и у Dropdown: у него только `error_text`, `error` нет."""
        dropdown = ft.Dropdown(label="Тип счёта")

        set_field_error(dropdown, "Неверный тип")
        assert field_error(dropdown) == "Неверный тип"

        set_field_error(dropdown, None)
        assert field_error(dropdown) is None


class TestGeneralErrors:
    def test_detail_only_message_is_shown(self) -> None:
        fields = _fields()
        error_text = _error()
        exc = ApiError(400, detail={"detail": "Недостаточно прав"})

        apply_api_error(error_text, exc, fields)

        assert error_text.value == "Недостаточно прав"
        assert error_text.visible is True
        assert all(field_error(field) is None for field in fields.values())

    def test_unmapped_field_keeps_summary(self) -> None:
        fields = _fields()
        error_text = _error()
        exc = ApiError(400, detail={"unknown_field": ["Что-то не так"]})

        apply_api_error(error_text, exc, fields)

        assert "unknown_field" in error_text.value
        assert all(field_error(field) is None for field in fields.values())

    def test_backend_unreachable_is_shown_as_is(self) -> None:
        fields = _fields()
        error_text = _error()

        apply_api_error(error_text, BackendUnreachableError("Сервер недоступен"), fields)

        assert error_text.value == "Сервер недоступен"
        assert error_text.visible is True
