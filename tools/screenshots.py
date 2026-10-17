"""Boot the real MyMoney app and save one PNG per tab for UI acceptance.

Usage (from the MyMoney root):

    set PYTHONPATH=%CD% && .venv\\Scripts\\python.exe tools\\screenshots.py [tab1 tab2 ...]

No arguments captures every tab. PNGs land in tools/screenshots/NN-<tab>.png.
If the app opens the login screen, 00-login.png is saved, a warning is printed
and the script exits (log in in the app, then rerun). A crash on one tab does
not lose the PNGs already captured; a summary table is printed at the end.
"""

import asyncio
import sys
import time
from pathlib import Path

import flet as ft
from application.app import MyMoneyApp

TABS: list[tuple[str, str]] = [
    ("accounts", "/accounts"),
    ("transactions", "/transactions"),
    ("planned", "/planned"),
    ("settings", "/settings"),
]
OUT_DIR = Path(__file__).resolve().parent / "screenshots"
BOOT_TIMEOUT = 20.0
BOOT_SETTLE = 2.5
NAV_SETTLE = 1.5
GLOBAL_TIMEOUT = 60.0

RESULTS: list[tuple[str, str, int]] = []
FAILURES: list[str] = []


async def wait_ready(page: ft.Page, deadline: float) -> None:
    last: tuple[str, int] | None = None
    stable_since: float | None = None
    while time.monotonic() < deadline:
        snapshot = (page.route, len(page.views))
        if page.views and snapshot == last:
            if stable_since is None:
                stable_since = time.monotonic()
            elif time.monotonic() - stable_since >= 0.5:
                return
        else:
            stable_since = None
        last = snapshot
        await asyncio.sleep(0.1)


async def capture_tab(page: ft.Page, name: str, route: str, index: int, deadline: float) -> None:
    page.navigate(route)
    await asyncio.sleep(min(NAV_SETTLE, max(deadline - time.monotonic(), 0.5)))
    data = await page.take_screenshot()
    path = OUT_DIR / f"{index:02d}-{name}.png"
    path.write_bytes(data)
    RESULTS.append((name, str(path), len(data)))
    print(f"{name} -> {path} ({len(data)} bytes, route={page.route})")


async def save_login_shot(page: ft.Page) -> None:
    print("WARNING: app landed on /login - log in in the app window and rerun this script")
    print("WARNING: залогиньтесь в приложении и перезапустите этот скрипт")
    try:
        data = await page.take_screenshot()
        path = OUT_DIR / "00-login.png"
        path.write_bytes(data)
        RESULTS.append(("login", str(path), len(data)))
        print(f"login -> {path} ({len(data)} bytes)")
    except Exception as exc:
        FAILURES.append(f"login capture failed: {exc}")


def print_summary() -> None:
    print("-" * 60)
    for name, path, size in RESULTS:
        print(f"{name:<20} {path} ({size} bytes)")
    print(f"saved: {len(RESULTS)}, failed: {len(FAILURES)}")
    for failure in FAILURES:
        print(f"  FAIL {failure}")


async def main(page: ft.Page) -> None:
    page.enable_screenshots = True
    requested = sys.argv[1:]
    selected = [pair for pair in TABS if not requested or pair[0] in requested]
    deadline = time.monotonic() + GLOBAL_TIMEOUT

    app = MyMoneyApp()
    try:
        await asyncio.wait_for(app.main(page), BOOT_TIMEOUT)
    except TimeoutError:
        print(f"WARNING: app boot exceeded {BOOT_TIMEOUT}s - capturing current state anyway")
        FAILURES.append(f"boot exceeded {int(BOOT_TIMEOUT)}s")

    await wait_ready(page, min(deadline, time.monotonic() + BOOT_TIMEOUT))
    remaining = deadline - time.monotonic()
    if remaining > 0:
        await asyncio.sleep(min(BOOT_SETTLE, remaining))

    if page.route == "/login":
        await save_login_shot(page)
        print_summary()
        await page.window.close()
        return

    for index, (name, route) in enumerate(selected, start=1):
        if time.monotonic() > deadline - 1.0:
            FAILURES.append(f"{name}: global {int(GLOBAL_TIMEOUT)}s timeout reached")
            continue
        try:
            await capture_tab(page, name, route, index, deadline)
        except Exception as exc:
            FAILURES.append(f"{name}: {exc}")
            print(f"{name}: FAILED ({exc})")

    print_summary()
    await page.window.close()


if __name__ == "__main__":
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    known = [name for name, _ in TABS]
    unknown = [tab for tab in sys.argv[1:] if tab not in known]
    if unknown:
        print(f"unknown tabs: {', '.join(unknown)}")
        print(f"available tabs: {', '.join(known)}")
        sys.exit(2)
    ft.run(main)
    sys.exit(1 if FAILURES else 0)
