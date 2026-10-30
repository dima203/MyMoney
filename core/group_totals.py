from __future__ import annotations

from dataclasses import dataclass, field
from decimal import Decimal, InvalidOperation

from MySpaceShared.core import IGNORED_CURRENCIES

QUOTE_CURRENCY = "USDT"
_USDT_SUFFIX = "-USDT"
_UNKNOWN_SYMBOL = "—"


def _to_decimal(value) -> Decimal | None:
    try:
        return Decimal(str(value))
    except (InvalidOperation, ValueError):
        return None


def price_symbol_for_resource(resource: dict | None) -> str:
    if not isinstance(resource, dict):
        return ""
    unit = str(resource.get("unit") or "").strip()
    if unit:
        return unit.upper()
    ticker = str(resource.get("ticker") or "").strip().upper().removesuffix(_USDT_SUFFIX)
    if ticker:
        return ticker
    name = str(resource.get("name") or "").strip()
    return name.upper()


def build_price_map(rows) -> dict[str, Decimal]:
    prices: dict[str, Decimal] = {}
    if not isinstance(rows, list):
        return prices
    for row in rows:
        if not isinstance(row, dict):
            continue
        symbol = str(row.get("symbol") or "").strip().upper()
        price = _to_decimal(row.get("price"))
        if not symbol or price is None or price <= 0:
            continue
        prices[symbol] = price
    return prices


def build_rate_map(price_rows, fx_rows=None) -> dict[str, Decimal]:
    """Единая карта «символ → стоимость в USD/USDT»: крипта из PriceCache, фиат из FX.

    Оба источника приводятся к одному якорю (USDT ≈ USD), поэтому ``rate_to_base``
    работает одинаково для крипты, фиата и их комбинаций.
    """
    values = build_price_map(price_rows)
    if isinstance(fx_rows, list):
        for row in fx_rows:
            if not isinstance(row, dict):
                continue
            symbol = str(row.get("quote") or row.get("symbol") or "").strip().upper()
            rate = _to_decimal(row.get("rate") if row.get("rate") is not None else row.get("price"))
            if symbol and rate is not None and rate > 0:
                values[symbol] = rate
    values.setdefault(QUOTE_CURRENCY, Decimal(1))
    values.setdefault("USD", Decimal(1))
    return values


def rate_to_base(symbol: str, base_currency: str, prices: dict[str, Decimal]) -> Decimal | None:
    if not symbol or not base_currency:
        return None
    if symbol == base_currency:
        return Decimal(1)
    src = prices.get(symbol)
    dst = prices.get(base_currency)
    if src is None or dst is None:
        return None
    return src / dst


@dataclass(frozen=True)
class GroupBaseTotal:
    total: Decimal
    converted: int
    missing_symbols: tuple[str, ...] = field(default_factory=tuple)

    @property
    def has_missing(self) -> bool:
        return bool(self.missing_symbols)

    @property
    def is_fully_missing(self) -> bool:
        return self.converted == 0 and bool(self.missing_symbols)


def group_total_in_base(
    accounts: list[dict],
    resource_map: dict[int, dict],
    base_currency: str,
    prices: dict[str, Decimal],
) -> GroupBaseTotal:
    base = (base_currency or "").strip().upper()
    total = Decimal(0)
    converted = 0
    missing: set[str] = set()
    for acc in accounts:
        if not isinstance(acc, dict):
            continue
        resource = resource_map.get(acc.get("resource_definition"))
        symbol = price_symbol_for_resource(resource)
        if symbol in IGNORED_CURRENCIES:
            # 7.5: делистнутые тикеры (MAX) не участвуют в конверсии
            continue
        qty = _to_decimal(acc.get("current_balance_qty", 0))
        if qty is None:
            qty = Decimal(0)
        rate = rate_to_base(symbol, base, prices)
        if rate is None:
            missing.add(symbol or _UNKNOWN_SYMBOL)
            continue
        total += qty * rate
        converted += 1
    return GroupBaseTotal(total=total, converted=converted, missing_symbols=tuple(sorted(missing)))


def format_amount(value: Decimal) -> str:
    """Сумма в формате экосистемы: пробел как разделитель тысяч."""
    return f"{value:,.2f}".replace(",", " ")


def format_group_total(result: GroupBaseTotal, base_currency: str) -> str:
    base = (base_currency or "").strip().upper()
    if result.is_fully_missing:
        return "Итого: курс недоступен"
    text = f"Итого: {format_amount(result.total)} {base}".rstrip()
    if result.has_missing:
        text += f" (курс недоступен: {', '.join(result.missing_symbols)})"
    return text


__all__ = [
    "QUOTE_CURRENCY",
    "GroupBaseTotal",
    "build_price_map",
    "build_rate_map",
    "format_amount",
    "format_group_total",
    "group_total_in_base",
    "price_symbol_for_resource",
    "rate_to_base",
]
