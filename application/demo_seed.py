"""Сидинг демо-данных MyMoney в пустой аккаунт через существующие REST-представления."""

from __future__ import annotations

import datetime
import os
from dataclasses import dataclass, field

from database.views import TransactionView

DATA_DIR = os.path.join(os.path.dirname(os.path.dirname(__file__)), "data")

DEMO_RESOURCES: list[dict[str, str]] = [
    {
        "ticker": "USD",
        "name": "Доллар США",
        "unit": "USD",
        "category": "currency",
        "resource_type": "currency",
    },
    {
        "ticker": "EUR",
        "name": "Евро",
        "unit": "EUR",
        "category": "currency",
        "resource_type": "currency",
    },
    {
        "ticker": "BTC",
        "name": "Биткоин",
        "unit": "BTC",
        "category": "crypto",
        "resource_type": "asset",
    },
]

DEMO_ACCOUNTS: list[dict[str, str]] = [
    {"key": "cash_usd", "resource": "USD", "name": "Наличные", "group": "Наличные", "account_type": "main"},
    {"key": "card_eur", "resource": "EUR", "name": "Карта", "group": "Карты", "account_type": "main"},
    {"key": "crypto", "resource": "BTC", "name": "Крипто-счёт", "group": "Крипто", "account_type": "main"},
    {"key": "savings_usd", "resource": "USD", "name": "Сбережения", "group": "Сбережения", "account_type": "earn"},
]


def build_demo_transactions(today: datetime.date | None = None) -> list[dict]:
    """Описания демо-операций: счёт задан ключом из DEMO_ACCOUNTS, даты — относительно today."""
    base = today or datetime.date.today()

    def tx(
        account: str,
        amount: float,
        description: str,
        category: str,
        day_offset: int,
        *,
        is_planned: bool = False,
        recurrence_rule: str = "",
        pair: tuple[str, float] | None = None,
    ) -> dict:
        day = base + datetime.timedelta(days=day_offset)
        item: dict = {
            "account": account,
            "amount": amount,
            "description": description,
            "category": category,
            "date": f"{day.isoformat()}T12:00:00",
            "is_planned": is_planned,
            "recurrence_rule": recurrence_rule,
        }
        if pair is not None:
            item["pair"] = pair
        return item

    return [
        tx("cash_usd", 2500.0, "Зарплата", "Зарплата", -30),
        tx("cash_usd", -850.0, "Аренда квартиры", "Жильё", -29),
        tx("card_eur", 450.0, "Фриланс-проект", "Подработка", -28),
        tx("cash_usd", -126.4, "Супермаркет", "Еда", -27),
        tx("cash_usd", -300.0, "Перевод в сбережения", "Другое", -25, pair=("savings_usd", 300.0)),
        tx("card_eur", -38.5, "Кофе и обед", "Еда", -24),
        tx("cash_usd", -54.0, "Проездной", "Транспорт", -21),
        tx("cash_usd", -320.0, "Кроссовки", "Другое", -19),
        tx("cash_usd", -300.0, "Покупка BTC", "Другое", -17, pair=("crypto", 0.0045)),
        tx("cash_usd", -45.9, "Аптека", "Здоровье", -14),
        tx("card_eur", -72.0, "Ужин с друзьями", "Развлечения", -10),
        tx("cash_usd", -19.9, "Кино", "Развлечения", -6),
        tx("cash_usd", -45.0, "Интернет", "Жильё", 1, is_planned=True, recurrence_rule="FREQ=MONTHLY"),
        tx("card_eur", -12.99, "Стриминг", "Развлечения", 3, is_planned=True, recurrence_rule="FREQ=MONTHLY"),
        tx("cash_usd", -35.0, "Спортзал", "Здоровье", 5, is_planned=True, recurrence_rule="FREQ=MONTHLY"),
    ]


@dataclass
class SeedResult:
    """Итог заполнения: статус, счётчики созданных записей и ошибки."""

    status: str
    created: dict[str, int] = field(default_factory=dict)
    errors: list[str] = field(default_factory=list)

    @property
    def message(self) -> str:
        if self.status == "created":
            accounts = self.created.get("accounts", 0)
            transactions = self.created.get("transactions", 0)
            return f"Примеры добавлены: счетов — {accounts}, операций — {transactions}"
        if self.status == "skipped":
            return "Данные уже есть — заполнение не выполнялось"
        if self.status == "offline":
            return "Заполнение примерами требует подключения к серверу"
        detail = self.errors[0] if self.errors else "неизвестная ошибка"
        prefix = "Заполнение прервано" if self.status == "partial" else "Ошибка заполнения"
        return f"{prefix}: {detail}"


class DemoSeeder:
    """Заполняет пустой аккаунт демо-счетами и операциями через offline-представления."""

    def __init__(
        self, resource_view, account_view, transaction_view=None, api_client=None, data_dir: str | None = None
    ) -> None:
        self._resource_view = resource_view
        self._account_view = account_view
        if transaction_view is not None:
            self._transaction_view = transaction_view
        else:
            self._transaction_view = TransactionView(api_client, data_dir or DATA_DIR)

    def seed(self) -> SeedResult:
        resources = self._resource_view.get_all()
        self._account_view.get_all()
        if not (self._resource_view.is_online and self._account_view.is_online):
            return SeedResult(status="offline")

        resource_ids: dict[str, int] = {}
        for item in resources:
            ticker = str(item.get("ticker", "")).upper()
            if ticker and ticker not in resource_ids and item.get("id") is not None:
                resource_ids[ticker] = item["id"]

        created = {"resources": 0, "accounts": 0, "transactions": 0}
        errors: list[str] = []
        failure: str | None = None

        if self._account_view.get_all():
            return SeedResult(status="skipped")

        for spec in DEMO_RESOURCES:
            ticker = spec["ticker"].upper()
            if ticker in resource_ids:
                continue
            pk = self._resource_view.add(dict(spec))
            if pk is None or pk < 0:
                failure = f"ресурс «{spec['name']}»"
                break
            resource_ids[ticker] = pk
            created["resources"] += 1

        account_ids: dict[str, int] = {}
        if failure is None:
            for spec in DEMO_ACCOUNTS:
                resource_id = resource_ids.get(spec["resource"].upper())
                if resource_id is None:
                    failure = f"счёт «{spec['name']}» (нет ресурса {spec['resource']})"
                    break
                payload = {
                    "name": spec["name"],
                    "resource_definition": resource_id,
                    "group": spec["group"],
                    "account_type": spec["account_type"],
                }
                pk = self._account_view.add(payload)
                if pk is None or pk < 0:
                    failure = f"счёт «{spec['name']}»"
                    break
                account_ids[spec["key"]] = pk
                created["accounts"] += 1

        if failure is None:
            for spec in build_demo_transactions():
                account_id = account_ids.get(spec["account"])
                if account_id is None:
                    failure = f"операция «{spec['description']}» (неизвестный счёт)"
                    break
                entries: list[dict] = [
                    {
                        "account": account_id,
                        "quantity": spec["amount"],
                        "amount": spec["amount"],
                        "unit_price": 1,
                    }
                ]
                pair = spec.get("pair")
                if pair is not None:
                    pair_id = account_ids.get(pair[0])
                    if pair_id is None:
                        failure = f"операция «{spec['description']}» (неизвестный счёт)"
                        break
                    entries.append(
                        {
                            "account": pair_id,
                            "quantity": pair[1],
                            "amount": pair[1],
                            "unit_price": 1,
                        }
                    )
                payload = {
                    "date": spec["date"],
                    "description": spec["description"],
                    "category": spec["category"],
                    "entries": entries,
                    "is_planned": spec["is_planned"],
                    "recurrence_rule": spec["recurrence_rule"],
                }
                pk = self._transaction_view.add(payload)
                if pk is None or pk < 0:
                    failure = f"операция «{spec['description']}»"
                    break
                created["transactions"] += 1

        if failure is not None:
            errors.append(f"не удалось создать {failure}")
            status = "partial" if any(created.values()) else "error"
            return SeedResult(status=status, created=created, errors=errors)
        return SeedResult(status="created", created=created)


__all__ = ["DEMO_ACCOUNTS", "DEMO_RESOURCES", "DemoSeeder", "SeedResult", "build_demo_transactions"]
