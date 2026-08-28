import json
from pathlib import Path

_TOKEN_FILE = Path.cwd() / ".auth_token.json"


def save_tokens(access: str, refresh: str) -> None:
    _TOKEN_FILE.write_text(json.dumps({"access": access, "refresh": refresh}))


def load_tokens() -> dict | None:
    if not _TOKEN_FILE.exists():
        return None
    try:
        return json.loads(_TOKEN_FILE.read_text())
    except (json.JSONDecodeError, KeyError):
        return None


def clear_tokens() -> None:
    if _TOKEN_FILE.exists():
        _TOKEN_FILE.unlink()
