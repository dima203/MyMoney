"""Цели накоплений MyMoney: прогресс и пополнения (слайс 3.2c).

Слой без Flet и API: принимает строки целей из `/api/v1/goals/` — отдаёт
иммутабельные `GoalProgress`. Прогресс хранится на сервере явно
(`saved_amount`): пополнение — это PATCH с новой суммой.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import date

from core.analytics import as_float

MIN_TARGET = 0.0
MIN_SAVED = 0.0
MIN_CONTRIBUTION = 0.0
DATE_FORMAT = "ГГГГ-ММ-ДД"


@dataclass(frozen=True)
class GoalProgress:
    """Цель накоплений и её прогресс."""

    goal_id: int | None
    name: str
    target_amount: float
    saved_amount: float
    currency: str
    deadline: date | None = None

    @property
    def remaining(self) -> float:
        return round(max(self.target_amount - self.saved_amount, 0.0), 2)

    @property
    def is_reached(self) -> bool:
        return self.target_amount > 0 and self.saved_amount >= self.target_amount

    @property
    def share(self) -> float:
        """Доля накопленного 0..1 (для ProgressBar)."""
        if self.target_amount <= 0:
            return 0.0
        return min(max(self.saved_amount / self.target_amount, 0.0), 1.0)

    def days_left(self, today: date) -> int | None:
        """Дней до срока; None — срока нет."""
        if self.deadline is None:
            return None
        return (self.deadline - today).days

    def is_overdue(self, today: date) -> bool:
        days = self.days_left(today)
        return days is not None and days < 0 and not self.is_reached


def parse_amount(value, what: str) -> float:
    """Число из поля ввода (запятая, пробелы-разделители); иначе ValueError."""
    if value is None or (isinstance(value, str) and not value.strip()):
        raise ValueError(f"Укажите {what}")
    try:
        return float(str(value).replace(",", ".").replace(" ", ""))
    except (TypeError, ValueError):
        raise ValueError(f"{what[0].upper()}{what[1:]} должно быть числом") from None


def parse_deadline(value) -> date | None:
    """Необязательный срок «ГГГГ-ММ-ДД»; пусто → None."""
    raw = "" if value is None else str(value).strip()
    if not raw:
        return None
    try:
        return date.fromisoformat(raw)
    except ValueError:
        raise ValueError(f"Срок в формате {DATE_FORMAT}") from None


def goal_payload(
    name,
    target,
    saved=0,
    currency_id: int | None = None,
    deadline=None,
) -> dict:
    """Тело POST/PATCH цели: имя, положительная цель, накоплено ≥ 0, валюта, срок."""
    goal_name = str(name or "").strip()
    if not goal_name:
        raise ValueError("Укажите название цели")
    target_amount = parse_amount(target, "цель")
    if target_amount <= MIN_TARGET:
        raise ValueError("Цель должна быть больше нуля")
    saved_amount = 0.0 if saved in (None, "") else parse_amount(saved, "накоплено")
    if saved_amount < MIN_SAVED:
        raise ValueError("Накоплено не может быть отрицательным")
    parsed_deadline = parse_deadline(deadline)
    return {
        "name": goal_name,
        "target_amount": f"{target_amount:.4f}",
        "saved_amount": f"{saved_amount:.4f}",
        "currency": currency_id,
        "deadline": parsed_deadline.isoformat() if parsed_deadline else None,
    }


def contribution_payload(saved, amount) -> dict:
    """Тело PATCH пополнения: новый `saved_amount` = накоплено + сумма."""
    delta = parse_amount(amount, "сумму пополнения")
    if delta <= MIN_CONTRIBUTION:
        raise ValueError("Сумма пополнения должна быть больше нуля")
    return {"saved_amount": f"{as_float(saved) + delta:.4f}"}


def _deadline(value) -> date | None:
    if not value:
        return None
    try:
        return date.fromisoformat(str(value)[:10])
    except ValueError:
        return None


def goal_progress(goals, *, base_currency: str = "") -> list[GoalProgress]:
    """Прогресс целей: суммы с сервера, валюта — тикер или базовая."""
    progress: list[GoalProgress] = []
    for goal in goals or []:
        if not isinstance(goal, dict):
            continue
        name = str(goal.get("name") or "").strip()
        if not name:
            continue
        goal_id = goal.get("id", goal.get("pk"))
        progress.append(
            GoalProgress(
                goal_id=goal_id if isinstance(goal_id, int) else None,
                name=name,
                target_amount=as_float(goal.get("target_amount")),
                saved_amount=as_float(goal.get("saved_amount")),
                currency=str(goal.get("currency_ticker") or base_currency or "").strip(),
                deadline=_deadline(goal.get("deadline")),
            )
        )
    return progress


__all__ = [
    "DATE_FORMAT",
    "GoalProgress",
    "contribution_payload",
    "goal_payload",
    "goal_progress",
    "parse_amount",
    "parse_deadline",
]
