"""Редактор повторения плановой операции (2.48b)."""

from __future__ import annotations

import flet as ft
from core.recurrence import Frequency, RecurrenceRule

FREQUENCY_OPTIONS = [
    ft.dropdown.Option(key="daily", text="Ежедневно"),
    ft.dropdown.Option(key="weekly", text="Еженедельно"),
    ft.dropdown.Option(key="monthly", text="Ежемесячно"),
    ft.dropdown.Option(key="yearly", text="Ежегодно"),
]

DEFAULT_FREQUENCY = Frequency.MONTHLY


def recurrence_rule_text(frequency: str | None, interval) -> str:
    """Строка правила из значений полей; неверные частота и интервал сводятся к дефолту."""
    try:
        freq = Frequency(frequency or DEFAULT_FREQUENCY.value)
    except ValueError:
        freq = DEFAULT_FREQUENCY
    try:
        step = max(int(interval or 1), 1)
    except (TypeError, ValueError):
        step = 1
    return RecurrenceRule(freq, step).to_string()


class RecurrenceEditor(ft.Column):
    """Переключатель «Повторяющаяся» с частотой и интервалом; ``value`` — строка правила."""

    def __init__(self, rule_str: str = "") -> None:
        self.switch = ft.Switch(label="Повторяющаяся", value=False, on_change=self._on_toggle)
        self.frequency = ft.Dropdown(
            label="Частота",
            options=FREQUENCY_OPTIONS,
            value=DEFAULT_FREQUENCY.value,
            border=ft.OutlineInputBorder(border_radius=8),
            col=6,
        )
        self.interval = ft.TextField(
            label="Интервал",
            value="1",
            keyboard_type=ft.KeyboardType.NUMBER,
            border=ft.OutlineInputBorder(border_radius=8),
            col=6,
        )
        self._row = ft.ResponsiveRow(
            controls=[self.frequency, self.interval],
            spacing=12,
            run_spacing=12,
            columns=12,
            visible=False,
        )
        super().__init__(controls=[self.switch, self._row], spacing=8)
        self.set_rule(rule_str)

    def _on_toggle(self, event) -> None:
        self._row.visible = bool(event.control.value)
        self.update()

    def set_rule(self, rule_str: str) -> None:
        rule = RecurrenceRule.parse(rule_str or "")
        if rule is None:
            return
        self.switch.value = True
        self._row.visible = True
        self.frequency.value = rule.frequency.value
        self.interval.value = str(rule.interval)

    @property
    def value(self) -> str:
        """Правило повторения или пустая строка, если повтор выключен."""
        if not self.switch.value:
            return ""
        return recurrence_rule_text(self.frequency.value, self.interval.value)


__all__ = ["DEFAULT_FREQUENCY", "FREQUENCY_OPTIONS", "RecurrenceEditor", "recurrence_rule_text"]
