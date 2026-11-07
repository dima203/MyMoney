import os
import tempfile
from pathlib import Path

import pytest

os.environ.setdefault(
    "MYSPACE_FX_RATES_PATH",
    str(Path(tempfile.gettempdir()) / "myspace-tests" / "fx_rates.json"),
)


@pytest.fixture(autouse=True)
def _fresh_session_cache():
    """2.184: кэш сессии — глобальный, тесты не должны видеть чужие снимки."""
    from application.session_cache import CACHE

    CACHE.clear()
    yield
    CACHE.clear()
