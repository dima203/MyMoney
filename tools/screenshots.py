"""Boot the real MyMoney app and save PNGs for UI acceptance.

Usage (from the MyMoney root):

    set PYTHONPATH=%CD% && .venv\\Scripts\\python.exe tools\\screenshots.py [tab1 tab2 ...]
    .venv\\Scripts\\python.exe tools\\screenshots.py --dialogs [--width 500]

No arguments captures every tab. `--dialogs` opens the main dialog of each
screen (account, plan, transaction, goal, envelope) and saves one PNG each;
`--width N` sets the window width before boot (for adaptive-layout checks).
PNGs land in tools/screenshots/NN-<name>.png. If the app opens the login
screen, 00-login.png is saved, a warning is printed and the script exits
(log in in the app, then rerun).
"""

import asyncio
import sys
import time
from pathlib import Path

import flet as ft
from application.app import MyMoneyApp

from MySpaceShared.tools.screenshots import (
    capture_png,
    click_dialog_action,
    close_dialog,
    open_dialog,
    wait_for_route,
    wait_ready,
)

TABS: list[tuple[str, str]] = [
    ("accounts", "/accounts"),
    ("transactions", "/transactions"),
    ("planned", "/planned"),
    ("budgets", "/budgets"),
    ("settings", "/settings"),
]

DIALOGS: list[tuple[str, str, str]] = [
    ("dialog-account", "/accounts", "_open_account_dialog"),
    ("dialog-plan", "/planned", "_open_transaction_dialog"),
    ("dialog-transaction", "/transactions", "_open_transaction_dialog"),
    ("dialog-goal", "/budgets", "_open_goal_editor"),
    ("dialog-envelope", "/budgets", "_open_envelope_editor"),
]

DIALOG_SETTLE = 1.0
DIALOG_CLOSE_SETTLE = 0.5
OUT_DIR = Path(__file__).resolve().parent / "screenshots"
BOOT_TIMEOUT = 20.0
BOOT_SETTLE = 2.5
NAV_SETTLE = 1.5
NAV_TIMEOUT = 10.0
GLOBAL_TIMEOUT = 60.0
DIALOG_GLOBAL_TIMEOUT = 75.0

RESULTS: list[tuple[str, str, int]] = []
FAILURES: list[str] = []


async def capture_tab(page: ft.Page, name: str, route: str, index: int, deadline: float) -> None:
    page.navigate(route)
    await wait_for_route(page, route, min(deadline, time.monotonic() + NAV_TIMEOUT))
    await asyncio.sleep(min(NAV_SETTLE, max(deadline - time.monotonic(), 0.5)))
    data = await page.take_screenshot()
    path = OUT_DIR / f"{index:02d}-{name}.png"
    path.write_bytes(data)
    RESULTS.append((name, str(path), len(data)))
    print(f"{name} -> {path} ({len(data)} bytes, route={page.route})")


async def capture_dialog(page: ft.Page, name: str, route: str, opener: str, index: int, deadline: float) -> None:
    page.navigate(route)
    await wait_for_route(page, route, min(deadline, time.monotonic() + NAV_TIMEOUT))
    await asyncio.sleep(min(NAV_SETTLE, max(deadline - time.monotonic(), 0.5)))
    await open_dialog(page, opener)
    path, size = await capture_png(page, OUT_DIR, name, index)
    RESULTS.append((name, path, size))
    print(f"{name} -> {path} ({size} bytes, route={page.route})")
    await close_dialog(page)


async def capture_dialog_error(page: ft.Page, index: int, deadline: float) -> None:
    """Пустая форма счёта: «Сохранить» → подсветка поля «Название»."""
    page.navigate("/accounts")
    await wait_for_route(page, "/accounts", min(deadline, time.monotonic() + NAV_TIMEOUT))
    await asyncio.sleep(min(NAV_SETTLE, max(deadline - time.monotonic(), 0.5)))
    await open_dialog(page, "_open_account_dialog")
    await click_dialog_action(page, "Сохранить")
    path, size = await capture_png(page, OUT_DIR, "dialog-account-error", index)
    RESULTS.append(("dialog-account-error", path, size))
    print(f"dialog-account-error -> {path} ({size} bytes)")
    await close_dialog(page)


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


def _parse_args(argv: list[str]) -> tuple[list[str], bool, int | None]:
    args = list(argv)
    width = None
    if "--width" in args:
        index = args.index("--width")
        if index + 1 < len(args):
            try:
                width = int(args[index + 1])
            except ValueError:
                width = None
            del args[index : index + 2]
        else:
            del args[index]
    dialogs = "--dialogs" in args
    tabs = [item for item in args if not item.startswith("-")]
    return tabs, dialogs, width


async def main(page: ft.Page) -> None:
    page.enable_screenshots = True
    requested, dialogs_mode, width = _parse_args(sys.argv[1:])
    if width:
        page.window.width = width
    selected = [pair for pair in TABS if not requested or pair[0] in requested]
    deadline = time.monotonic() + GLOBAL_TIMEOUT
    if dialogs_mode:
        deadline = time.monotonic() + DIALOG_GLOBAL_TIMEOUT

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
    if width:
        page.window.width = width
        page.update()
        await asyncio.sleep(0.8)

    if page.route == "/login":
        await save_login_shot(page)
        print_summary()
        await page.window.close()
        return

    if dialogs_mode:
        for index, (name, route, opener) in enumerate(DIALOGS, start=1):
            if time.monotonic() > deadline - 1.0:
                FAILURES.append(f"{name}: global timeout reached")
                continue
            try:
                await capture_dialog(page, name, route, opener, index, deadline)
            except Exception as exc:
                FAILURES.append(f"{name}: {exc}")
                print(f"{name}: FAILED ({exc})")
        try:
            await capture_dialog_error(page, len(DIALOGS) + 1, deadline)
        except Exception as exc:
            FAILURES.append(f"dialog-account-error: {exc}")
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
    tabs, dialogs_mode, width = _parse_args(sys.argv[1:])
    known = [name for name, _ in TABS]
    unknown = [tab for tab in tabs if tab not in known]
    if unknown:
        print(f"unknown tabs: {', '.join(unknown)}")
        print(f"available tabs: {', '.join(known)}")
        sys.exit(2)
    ft.run(main)
    sys.exit(1 if FAILURES else 0)
