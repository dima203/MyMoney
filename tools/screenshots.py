"""Agent-friendly screenshots — см. `python tools/screenshots.py --list`.

Опции: --screen NAME, --dialog NAME, --all-screens, --all-dialogs, --width N,
--height N, --theme dark|light|system, --out DIR, --prefix P, --settle S,
--timeout S, --dump-tree, --isolate-dir DIR, --no-isolate, --json, --list,
--keep-open. Коды выхода: 0 ok, 2 аргументы, 3 нужен вход, 4 ошибка прогона.
"""

import sys
from pathlib import Path

TOOLS = Path(__file__).resolve().parent
ROOT = TOOLS.parent
for path in (str(ROOT), str(TOOLS)):
    if path not in sys.path:
        sys.path.insert(0, path)

from MySpaceShared.tools.shots import run  # ruff: ignore[module-import-not-at-top-of-file]

if __name__ == "__main__":
    sys.exit(run("shots_manifest"))
