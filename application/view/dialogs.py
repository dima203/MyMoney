DIALOG_MAX_WIDTH = 560
DIALOG_WIDTH_RATIO = 0.9
DIALOG_MIN_WIDTH = 280
DIALOG_INSET = 80


def _try_get(source, name):
    try:
        return getattr(source, name, None)
    except RuntimeError:
        return None


def _width_of(source) -> float:
    if source is None:
        return 0.0
    width = _try_get(source, "width")
    if not width:
        width = _try_get(_try_get(source, "window"), "width")
    try:
        return float(width or 0)
    except (TypeError, ValueError):
        return 0.0


def _available_width(source) -> float:
    width = _width_of(source)
    if width <= 0:
        width = _width_of(_try_get(source, "page"))
    return width


def dialog_width(source, max_width: int = DIALOG_MAX_WIDTH) -> int:
    """Ширина диалога: min(max_width, 0.9 × окно, окно − inset); без окна — max_width."""
    available = _available_width(source)
    if available <= 0:
        return max_width
    fitted = min(max_width, available - DIALOG_INSET, available * DIALOG_WIDTH_RATIO)
    return int(max(DIALOG_MIN_WIDTH, fitted))


def full_width(*fields) -> list:
    """Поля формы на всю ширину (для ResponsiveRow)."""
    for field in fields:
        field.col = 12
    return list(fields)


def half_width(*fields) -> list:
    """Поля формы в две колонки: внутри диалога (≤560) sm-брейкпоинт не срабатывает."""
    for field in fields:
        field.col = 6
    return list(fields)


__all__ = ["DIALOG_MAX_WIDTH", "DIALOG_WIDTH_RATIO", "dialog_width", "full_width", "half_width"]
