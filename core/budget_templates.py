"""Шаблоны бюджетов MyMoney: конверты → шаблон, шаблон → применение (3.5b-2).

Слой без Flet и API: принимает строки конвертов из `/api/v1/envelopes/` и
шаблонов из `/api/v1/budget-templates/`, отдаёт payload-ы и `TemplateInfo`.
"""

from __future__ import annotations

from dataclasses import dataclass

from core.analytics import as_float

MAX_ITEMS = 100
PUBLIC_MARK = "публичный"
PRIVATE_MARK = "приватный"


@dataclass(frozen=True)
class TemplateInfo:
    """Шаблон бюджета для списка в диалоге."""

    template_id: int | None
    name: str
    items: int
    is_public: bool
    currency: str

    @property
    def subtitle(self) -> str:
        visibility = PUBLIC_MARK if self.is_public else PRIVATE_MARK
        parts = [f"{self.items} категорий", visibility]
        if self.currency:
            parts.append(self.currency)
        return " · ".join(parts)


def template_items(envelopes) -> list[dict]:
    """Конверты → items шаблона (категория и положительный лимит)."""
    items: list[dict] = []
    for row in envelopes or []:
        if not isinstance(row, dict):
            continue
        category = str(row.get("category") or "").strip()
        limit = as_float(row.get("limit_amount"))
        if not category or limit <= 0:
            continue
        items.append({"category": category, "limit_amount": f"{limit:.4f}"})
    return items


def template_payload(name, items, currency_id: int | None = None, is_public: bool = False) -> dict:
    """Тело POST шаблона: имя, непустой список items, валюта, публичность."""
    template_name = str(name or "").strip()
    if not template_name:
        raise ValueError("Укажите название шаблона")
    if not items:
        raise ValueError("Нет конвертов для шаблона")
    if len(items) > MAX_ITEMS:
        raise ValueError(f"Слишком много конвертов (максимум {MAX_ITEMS})")
    return {
        "name": template_name,
        "items": list(items),
        "currency": currency_id,
        "is_public": bool(is_public),
    }


def template_infos(rows) -> list[TemplateInfo]:
    """Строки API → TemplateInfo (мусор пропускается)."""
    infos: list[TemplateInfo] = []
    for row in rows or []:
        if not isinstance(row, dict):
            continue
        name = str(row.get("name") or "").strip()
        if not name:
            continue
        items = row.get("items") if isinstance(row.get("items"), list) else []
        template_id = row.get("id")
        infos.append(
            TemplateInfo(
                template_id=template_id if isinstance(template_id, int) else None,
                name=name,
                items=len(items),
                is_public=bool(row.get("is_public")),
                currency=str(row.get("currency_ticker") or "").strip(),
            )
        )
    return infos


__all__ = [
    "MAX_ITEMS",
    "TemplateInfo",
    "template_infos",
    "template_items",
    "template_payload",
]
