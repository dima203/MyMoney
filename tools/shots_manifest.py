"""Экраны и диалоги для агентского раннера скриншотов."""

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from application.app import MyMoneyApp  # ruff: ignore[module-import-not-at-top-of-file]

from MySpaceShared.tools.shots import AppSpec, Dialog, Screen  # ruff: ignore[module-import-not-at-top-of-file]


def _open_categories_dialog(view) -> None:
    """Открыть менеджер словаря категорий поверх формы операции (2.53)."""
    view._open_transaction_dialog()
    picker = getattr(view, "_category_picker", None)
    if picker is not None:
        picker._get_page = lambda: view.page
        picker._show_manager_dialog(None)


def _open_plan_dialog(view) -> None:
    """Открыть диалог плана на объединённом экране (2.48b)."""
    view.set_mode("planned")
    view._open_transaction_dialog(planned=True)


APP = AppSpec(
    key="MyMoney",
    title="MyMoney",
    boot=lambda page: MyMoneyApp().main(page),
    screens=(
        Screen("accounts", "/accounts"),
        Screen("operations", "/operations"),
        Screen("planned", "/planned"),
        Screen("budgets", "/budgets"),
        Screen("analytics", "/analytics"),
        Screen("settings", "/settings"),
    ),
    dialogs=(
        Dialog("account", "/accounts", lambda view: view._open_account_dialog(), "Сохранить"),
        Dialog("plan", "/operations", _open_plan_dialog, "Сохранить"),
        Dialog(
            "transaction",
            "/operations",
            lambda view: view._open_transaction_dialog(),
            "Сохранить",
        ),
        Dialog("categories", "/operations", _open_categories_dialog, "Закрыть"),
        Dialog("goal", "/budgets", lambda view: view._open_goal_editor(), "Сохранить"),
        Dialog("envelope", "/budgets", lambda view: view._open_envelope_editor(), "Сохранить"),
    ),
)
