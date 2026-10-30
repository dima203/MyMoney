import os
import tempfile
from pathlib import Path

os.environ.setdefault(
    "MYSPACE_FX_RATES_PATH",
    str(Path(tempfile.gettempdir()) / "myspace-tests" / "fx_rates.json"),
)
