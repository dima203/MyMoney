"""Автоподстановка категории по описанию операции (2.53)."""

from __future__ import annotations

from collections import Counter


def normalize_description(value) -> str:
    """Описание без лишних пробелов и с единым регистром."""
    return " ".join(str(value or "").casefold().split())


def suggest_category(description, transactions, allowed: list[str] | None = None) -> str:
    """Самая частая категория прошлых операций с тем же описанием.

    ``allowed`` — активный словарь: если задан, подставляются только его
    названия (в каноническом написании), архивные и удалённые не предлагаются.
    Пустое описание или отсутствие истории дают пустую строку.
    """
    key = normalize_description(description)
    if not key:
        return ""
    allowed_map = {str(name).strip().casefold(): str(name).strip() for name in allowed or [] if str(name).strip()}
    counts: Counter[str] = Counter()
    spellings: dict[str, str] = {}
    for tx in transactions or []:
        if not isinstance(tx, dict) or tx.get("is_planned"):
            continue
        if normalize_description(tx.get("description")) != key:
            continue
        category = str(tx.get("category") or "").strip()
        if not category:
            continue
        folded = category.casefold()
        if allowed is not None and folded not in allowed_map:
            continue
        spellings.setdefault(folded, category)
        counts[folded] += 1
    if not counts:
        return ""
    best = counts.most_common(1)[0][0]
    return allowed_map.get(best) or spellings[best]


__all__ = ["normalize_description", "suggest_category"]
