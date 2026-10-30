"""Экраны и диалоги для агентского раннера скриншотов."""

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from application.app import MyMoneyApp  # ruff: ignore[module-import-not-at-top-of-file]

from MySpaceShared.tools.shots import AppSpec, Dialog, Screen  # ruff: ignore[module-import-not-at-top-of-file]

APP = AppSpec(
    key="MyMoney",
    title="MyMoney",
    boot=lambda page: MyMoneyApp().main(page),
    screens=(
        Screen("accounts", "/accounts"),
        Screen("transactions", "/transactions"),
        Screen("planned", "/planned"),
        Screen("budgets", "/budgets"),
        Screen("analytics", "/analytics"),
        Screen("settings", "/settings"),
    ),
    dialogs=(
        Dialog("account", "/accounts", lambda view: view._open_account_dialog(), "Сохранить"),
        Dialog("plan", "/planned", lambda view: view._open_transaction_dialog(), "Сохранить"),
        Dialog("transaction", "/transactions", lambda view: view._open_transaction_dialog(), "Сохранить"),
        Dialog("goal", "/budgets", lambda view: view._open_goal_editor(), "Сохранить"),
        Dialog("envelope", "/budgets", lambda view: view._open_envelope_editor(), "Сохранить"),
    ),
)
