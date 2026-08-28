"""Хранение JWT-токенов на клиенте."""

import json
import os
import tempfile
from dataclasses import dataclass
from pathlib import Path

DEFAULT_TOKEN_DIR = Path.home() / ".mymoney"
DEFAULT_TOKEN_FILE = DEFAULT_TOKEN_DIR / "tokens.json"


@dataclass
class TokenData:
    access: str = ""
    refresh: str = ""
    username: str = ""

    @property
    def is_authenticated(self) -> bool:
        return bool(self.access)


class TokenStore:
    def __init__(self, path: Path | str | None = None):
        self.path = Path(path) if path is not None else DEFAULT_TOKEN_FILE

    def load(self) -> TokenData:
        if not self.path.exists():
            return TokenData()
        try:
            data = json.loads(self.path.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError, UnicodeDecodeError):
            return TokenData()
        return TokenData(
            access=data.get("access", ""),
            refresh=data.get("refresh", ""),
            username=data.get("username", ""),
        )

    def save(self, token: TokenData) -> None:
        self.path.parent.mkdir(parents=True, exist_ok=True)
        payload = {
            "access": token.access,
            "refresh": token.refresh,
            "username": token.username,
        }
        fd, tmp_name = tempfile.mkstemp(dir=str(self.path.parent), suffix=".tmp")
        try:
            with os.fdopen(fd, "w", encoding="utf-8") as fh:
                json.dump(payload, fh, ensure_ascii=False, indent=2)
            os.replace(tmp_name, self.path)
        finally:
            if os.path.exists(tmp_name):
                os.unlink(tmp_name)

    def clear(self) -> None:
        if self.path.exists():
            try:
                self.path.unlink()
            except OSError:
                pass


__all__ = ["TokenData", "TokenStore"]
