"""Вывод полей формы редактирования транзакции из её проводок (двойная запись).

Карточка показывает итог `sum(amount)` с знаком «+» при `>= 0` — форма должна
загружать те же значения: сумма = |итог|, тип = по знаку итога, перевод = две
уравновешенные проводки по разным счетам.
"""

from dataclasses import dataclass

from application.display import format_amount_input

TYPE_EXPENSE = "expense"
TYPE_INCOME = "income"
TYPE_TRANSFER = "transfer"

BALANCE_TOLERANCE = 1e-9


@dataclass(frozen=True)
class TransactionFormState:
    amount_text: str
    tx_type: str
    account_id: str
    to_account_id: str | None = None


def entries_total(entries: list[dict]) -> float:
    """Итог по проводкам — ровно то, что суммирует карточка (`_build_card`)."""
    return sum(float(entry.get("amount", 0)) for entry in entries)


def is_transfer(entries: list[dict]) -> bool:
    """Перевод: две проводки по разным счетам с противоположными суммами (сумма ≈ 0).

    Совпадает с семантикой создания: перевод всегда `{from: -amount, to: +amount}`.
    Смешанные обмены (сумма ≠ 0) переводом не считаются.
    """
    if len(entries) != 2:
        return False
    first, second = entries
    if first.get("account") == second.get("account"):
        return False
    first_amount = float(first.get("amount", 0))
    second_amount = float(second.get("amount", 0))
    if first_amount == second_amount:
        return False
    return abs(first_amount + second_amount) <= BALANCE_TOLERANCE


def form_state(entries: list[dict], *, allow_transfer: bool = True) -> TransactionFormState:
    """Состояние формы из проводок: сумма как на карточке, тип по знаку итога, счёт первой проводки."""
    total = entries_total(entries)
    if allow_transfer and is_transfer(entries):
        amounts = [float(entry.get("amount", 0)) for entry in entries]
        from_index = 0 if amounts[0] <= amounts[1] else 1
        to_index = 1 - from_index
        return TransactionFormState(
            amount_text=format_amount_input(amounts[from_index]),
            tx_type=TYPE_TRANSFER,
            account_id=str(entries[from_index].get("account", "")),
            to_account_id=str(entries[to_index].get("account", "")),
        )
    return TransactionFormState(
        amount_text=format_amount_input(total),
        tx_type=TYPE_INCOME if total >= 0 else TYPE_EXPENSE,
        account_id=str(entries[0].get("account", "")) if entries else "",
    )


__all__ = [
    "BALANCE_TOLERANCE",
    "TYPE_EXPENSE",
    "TYPE_INCOME",
    "TYPE_TRANSFER",
    "TransactionFormState",
    "entries_total",
    "form_state",
    "is_transfer",
]
