from application.display import account_currency


class AmountCurrencyMixin:
    """Суффикс суммового поля следует за выбранным счётом (форма операции/плана)."""

    def _sync_amount_currency(self, field, account_id) -> None:
        field.set_currency(account_currency(self._accounts, account_id))
        try:
            field.update()
        except RuntimeError:
            pass


__all__ = ["AmountCurrencyMixin"]
