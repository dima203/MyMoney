from pathlib import Path

from MySpaceShared.api.token_store import SharedTokenStore, TokenData


class TokenStore:
    """Обёртка над общим TokenStore с совместимым API для приложения."""

    def __init__(self, path: Path | str | None = None):
        if path is not None:
            self._store = SharedTokenStore(app_name="mymoney", path=path)
        else:
            self._store = SharedTokenStore(app_name="mymoney")

    @property
    def path(self) -> Path:
        return self._store.path

    def load(self) -> TokenData:
        return self._store.load()

    def save(self, token: TokenData) -> None:
        self._store.save(token)

    def clear(self) -> None:
        self._store.clear()


__all__ = ["TokenData", "TokenStore"]
