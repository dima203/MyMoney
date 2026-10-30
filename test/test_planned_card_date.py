"""Дата в карточке плана — русский компактный формат (2.72)."""

import datetime

import flet as ft
from application.components.planned_transaction_card import PlannedTransactionCard


def _texts(control) -> list[str]:
    found: list[str] = []
    if isinstance(control, ft.Text) and isinstance(control.value, str):
        found.append(control.value)
    for child in getattr(control, "controls", None) or []:
        found.extend(_texts(child))
    content = getattr(control, "content", None)
    if content is not None and not isinstance(content, str):
        found.extend(_texts(content))
    return found


def test_plan_card_uses_russian_date_instead_of_latin_month():
    planned = datetime.date.today() + datetime.timedelta(days=10)

    card = PlannedTransactionCard(
        description="Аренда",
        amount=-100.0,
        account_name="Карта",
        planned_date=planned,
    )

    texts = _texts(card)
    assert planned.strftime("%d.%m") in texts
    assert planned.strftime("%d %b") not in texts
