"""Тесты демо-данных MyMoney: DemoSeeder, OnboardingState и пустого экрана AccountsView."""

import asyncio
import datetime
import json
from unittest.mock import MagicMock

import flet as ft
from application.demo_seed import DEMO_ACCOUNTS, DEMO_RESOURCES, DemoSeeder, SeedResult, build_demo_transactions
from application.view.accounts_view import AccountsView, build_empty_state
from core.onboarding import OnboardingState


def _texts(control) -> list[str]:
    found: list[str] = []
    if isinstance(control, ft.Text) and control.value is not None:
        found.append(str(control.value))
    content = getattr(control, "content", None)
    if isinstance(content, str):
        found.append(content)
    elif content is not None:
        found.extend(_texts(content))
    for child in getattr(control, "controls", None) or []:
        found.extend(_texts(child))
    return found


def _make_view(
    tmp_path,
    *,
    resources=None,
    accounts=None,
    online=True,
    seeder_factory=None,
    seen=False,
):
    onboarding = OnboardingState(path=tmp_path / "onboarding.json")
    if seen:
        onboarding.mark_welcome_seen()
    resource_view = MagicMock()
    resource_view.is_online = online
    resource_view.get_all.side_effect = lambda: list(resources or [])
    account_view = MagicMock()
    account_view.is_online = online
    account_view.get_all.side_effect = lambda: list(accounts or [])
    view = AccountsView(
        route="/accounts",
        api_client=MagicMock(),
        resource_view=resource_view,
        account_view=account_view,
        onboarding=onboarding,
        seeder_factory=seeder_factory,
    )
    view.update = MagicMock()
    return view, resource_view, account_view, onboarding


class _StubSeeder:
    def __init__(self, result: SeedResult | None = None, error: Exception | None = None):
        self.result = result
        self.error = error
        self.calls = 0

    def seed(self) -> SeedResult:
        self.calls += 1
        if self.error is not None:
            raise self.error
        return self.result


class TestBuildDemoTransactions:
    def test_manifest_size_and_planned(self) -> None:
        items = build_demo_transactions(datetime.date(2026, 10, 13))
        assert len(items) == 15
        planned = [i for i in items if i["is_planned"]]
        assert len(planned) == 3
        assert all(i["recurrence_rule"] == "FREQ=MONTHLY" for i in planned)
        assert all(not i["is_planned"] for i in items if i["recurrence_rule"] == "")

    def test_dates_relative_to_today(self) -> None:
        items = build_demo_transactions(datetime.date(2026, 10, 13))
        salary = next(i for i in items if i["description"] == "Зарплата")
        assert salary["date"] == "2026-09-13T12:00:00"
        assert all("T12:00:00" in i["date"] for i in items)

    def test_required_keys_present(self) -> None:
        items = build_demo_transactions(datetime.date(2026, 10, 13))
        for item in items:
            assert {"account", "amount", "description", "category", "date"} <= item.keys()

    def test_default_today(self) -> None:
        items = build_demo_transactions()
        assert len(items) == 15


class TestDemoSeederCreated:
    def _seeder(self) -> tuple[DemoSeeder, MagicMock, MagicMock, MagicMock]:
        resource_view = MagicMock()
        resource_view.is_online = True
        resource_view.get_all.side_effect = lambda: []
        resource_view.add.side_effect = [1, 2, 3]
        account_view = MagicMock()
        account_view.is_online = True
        account_view.get_all.side_effect = lambda: []
        account_view.add.side_effect = [1, 2, 3, 4]
        transaction_view = MagicMock()
        transaction_view.add.side_effect = list(range(1, 16))
        seeder = DemoSeeder(resource_view, account_view, transaction_view=transaction_view)
        return seeder, resource_view, account_view, transaction_view

    def test_full_seed_counts(self) -> None:
        seeder, _, _, _ = self._seeder()
        result = seeder.seed()
        assert result.status == "created"
        assert result.created == {"resources": 3, "accounts": 4, "transactions": 15}
        assert len(DEMO_RESOURCES) == 3
        assert len(DEMO_ACCOUNTS) == 4
        assert "счетов — 4" in result.message

    def test_account_payloads_map_resources(self) -> None:
        seeder, _, account_view, _ = self._seeder()
        seeder.seed()
        payloads = [c.args[0] for c in account_view.add.call_args_list]
        assert payloads[0] == {
            "name": "Наличные",
            "resource_definition": 1,
            "group": "Наличные",
            "account_type": "main",
        }
        assert payloads[3]["resource_definition"] == 1
        assert payloads[2]["resource_definition"] == 3

    def test_transaction_entries_and_pairs(self) -> None:
        seeder, _, _, transaction_view = self._seeder()
        seeder.seed()
        by_desc = {c.args[0]["description"]: c.args[0] for c in transaction_view.add.call_args_list}
        btc = by_desc["Покупка BTC"]
        assert btc["entries"][0] == {"account": 1, "quantity": -300.0, "amount": -300.0, "unit_price": 1}
        assert btc["entries"][1]["account"] == 3
        assert btc["entries"][1]["quantity"] == 0.0045
        transfer = by_desc["Перевод в сбережения"]
        assert transfer["entries"][1]["account"] == 4
        assert transfer["entries"][1]["amount"] == 300.0
        assert not by_desc["Зарплата"]["is_planned"]

    def test_transaction_none_result_aborts(self) -> None:
        seeder, _, _, transaction_view = self._seeder()
        transaction_view.add.side_effect = [None]
        result = seeder.seed()
        assert result.status == "partial"
        assert result.created["transactions"] == 0
        assert result.created["accounts"] == 4
        assert transaction_view.add.call_count == 1
        assert "операция" in result.errors[0]


class TestDemoSeederSkipsAndOffline:
    def test_skips_when_accounts_exist(self) -> None:
        resource_view = MagicMock()
        resource_view.is_online = True
        resource_view.get_all.side_effect = lambda: []
        account_view = MagicMock()
        account_view.is_online = True
        account_view.get_all.side_effect = lambda: [{"id": 9, "name": "Existing"}]
        seeder = DemoSeeder(resource_view, account_view, transaction_view=MagicMock())
        result = seeder.seed()
        assert result.status == "skipped"
        resource_view.add.assert_not_called()
        account_view.add.assert_not_called()

    def test_reuses_existing_resources(self) -> None:
        resource_view = MagicMock()
        resource_view.is_online = True
        resource_view.get_all.side_effect = lambda: [{"id": 7, "ticker": "USD"}]
        resource_view.add.side_effect = [2, 3]
        account_view = MagicMock()
        account_view.is_online = True
        account_view.get_all.side_effect = lambda: []
        account_view.add.side_effect = [1, 2, 3, 4]
        transaction_view = MagicMock()
        transaction_view.add.side_effect = list(range(1, 16))
        seeder = DemoSeeder(resource_view, account_view, transaction_view=transaction_view)
        result = seeder.seed()
        assert result.status == "created"
        assert resource_view.add.call_count == 2
        first_account = account_view.add.call_args_list[0].args[0]
        assert first_account["resource_definition"] == 7
        assert transaction_view.add.call_count == 15

    def test_offline_makes_no_writes(self) -> None:
        resource_view = MagicMock()
        resource_view.is_online = False
        account_view = MagicMock()
        seeder = DemoSeeder(resource_view, account_view, transaction_view=MagicMock())
        result = seeder.seed()
        assert result.status == "offline"
        assert "требует подключения" in result.message
        resource_view.add.assert_not_called()
        account_view.add.assert_not_called()


class TestDemoSeederFailures:
    def test_account_failure_aborts_with_partial(self) -> None:
        resource_view = MagicMock()
        resource_view.is_online = True
        resource_view.get_all.side_effect = lambda: []
        resource_view.add.side_effect = [1, 2, 3]
        account_view = MagicMock()
        account_view.is_online = True
        account_view.get_all.side_effect = lambda: []
        account_view.add.side_effect = [1, -1]
        transaction_view = MagicMock()
        seeder = DemoSeeder(resource_view, account_view, transaction_view=transaction_view)
        result = seeder.seed()
        assert result.status == "partial"
        assert result.created["accounts"] == 1
        transaction_view.add.assert_not_called()
        assert result.errors
        assert "счёт" in result.errors[0]
        assert result.message.startswith("Заполнение прервано")

    def test_first_resource_failure_is_error(self) -> None:
        resource_view = MagicMock()
        resource_view.is_online = True
        resource_view.get_all.side_effect = lambda: []
        resource_view.add.side_effect = [None]
        account_view = MagicMock()
        account_view.is_online = True
        account_view.get_all.side_effect = lambda: []
        seeder = DemoSeeder(resource_view, account_view, transaction_view=MagicMock())
        result = seeder.seed()
        assert result.status == "error"
        assert result.created == {"resources": 0, "accounts": 0, "transactions": 0}
        assert result.message.startswith("Ошибка заполнения")
        account_view.add.assert_not_called()

    def test_transaction_failure_is_partial(self) -> None:
        resource_view = MagicMock()
        resource_view.is_online = True
        resource_view.get_all.side_effect = lambda: []
        resource_view.add.side_effect = [1, 2, 3]
        account_view = MagicMock()
        account_view.is_online = True
        account_view.get_all.side_effect = lambda: []
        account_view.add.side_effect = [1, 2, 3, 4]
        transaction_view = MagicMock()
        transaction_view.add.side_effect = [1, -1]
        seeder = DemoSeeder(resource_view, account_view, transaction_view=transaction_view)
        result = seeder.seed()
        assert result.status == "partial"
        assert result.created["accounts"] == 4
        assert result.created["transactions"] == 1
        assert "операция" in result.errors[0]


class TestOnboardingState:
    def test_unseen_by_default(self, tmp_path) -> None:
        state = OnboardingState(path=tmp_path / "onboarding.json")
        assert state.welcome_seen is False

    def test_mark_seen_persists(self, tmp_path) -> None:
        path = tmp_path / "onboarding.json"
        OnboardingState(path=path).mark_welcome_seen()
        assert OnboardingState(path=path).welcome_seen is True
        payload = json.loads(path.read_text(encoding="utf-8"))
        assert payload == {"welcome_seen": True}

    def test_corrupt_file_returns_false(self, tmp_path) -> None:
        path = tmp_path / "onboarding.json"
        path.write_text("не json", encoding="utf-8")
        assert OnboardingState(path=path).welcome_seen is False

    def test_non_dict_payload_returns_false(self, tmp_path) -> None:
        path = tmp_path / "onboarding.json"
        path.write_text("[1, 2]", encoding="utf-8")
        assert OnboardingState(path=path).welcome_seen is False

    def test_mark_creates_missing_dirs(self, tmp_path) -> None:
        path = tmp_path / "nested" / "deeper" / "onboarding.json"
        state = OnboardingState(path=path)
        state.mark_welcome_seen()
        assert state.welcome_seen is True

    def test_real_default_path_bypassed(self) -> None:
        state = OnboardingState()
        assert ".mymoney" in str(state._path)


class TestBuildEmptyState:
    def test_welcome_variant(self) -> None:
        control = build_empty_state(True, lambda e: None, lambda e: None)
        texts = _texts(control)
        assert "Добро пожаловать в MyMoney!" in texts
        assert "Заполнить примерами" in texts
        assert "Начать с нуля" in texts

    def test_plain_variant(self) -> None:
        control = build_empty_state(False, lambda e: None, lambda e: None)
        texts = _texts(control)
        assert "Нет счетов" in texts
        assert "Заполнить примерами" in texts
        assert "Добро пожаловать" not in " ".join(texts)


class TestAccountsViewEmptyState:
    def test_welcome_shown_when_flag_unset(self, tmp_path) -> None:
        view, _, _, _ = _make_view(tmp_path)
        asyncio.run(view._load_data())
        texts = _texts(view._accounts_column)
        assert "Добро пожаловать в MyMoney!" in texts
        assert "Заполнить примерами" in texts

    def test_welcome_hidden_after_flag_set(self, tmp_path) -> None:
        view, _, _, _ = _make_view(tmp_path, seen=True)
        asyncio.run(view._load_data())
        texts = _texts(view._accounts_column)
        assert "Нет счетов" in texts
        assert "Добро пожаловать в MyMoney!" not in texts
        assert "Заполнить примерами" in texts

    def test_seed_ui_hidden_when_accounts_exist(self, tmp_path) -> None:
        resources = [{"id": 1, "name": "USD", "ticker": "USD", "resource_type": "currency"}]
        accounts = [
            {
                "id": 10,
                "name": "Наличные",
                "resource_definition": 1,
                "group": "Наличные",
                "account_type": "main",
                "current_balance_qty": 100,
            }
        ]
        view, _, _, _ = _make_view(tmp_path, resources=resources, accounts=accounts)
        asyncio.run(view._load_data())
        texts = " ".join(_texts(view._accounts_column))
        assert "Заполнить примерами" not in texts
        assert "Добро пожаловать" not in texts
        assert "Наличные" in texts


class TestAccountsViewSeedFlow:
    def test_success_marks_seen_and_refreshes(self, tmp_path) -> None:
        stub = _StubSeeder(result=SeedResult(status="created", created={"accounts": 4, "transactions": 15}))
        view, resource_view, _, onboarding = _make_view(tmp_path, seeder_factory=lambda: stub)
        asyncio.run(view._load_data())
        asyncio.run(view._on_seed_demo())
        assert stub.calls == 1
        assert onboarding.welcome_seen is True
        assert view._seed_status.visible is False
        assert resource_view.get_all.call_count >= 2

    def test_offline_shows_error_message(self, tmp_path) -> None:
        stub = _StubSeeder(result=SeedResult(status="offline"))
        view, _, _, onboarding = _make_view(tmp_path, seeder_factory=lambda: stub)
        asyncio.run(view._load_data())
        asyncio.run(view._on_seed_demo())
        assert view._seed_status.visible is True
        assert "требует подключения" in view._seed_status.value
        assert view._seed_status.color == ft.Colors.ERROR
        assert onboarding.welcome_seen is False

    def test_skipped_shows_info_message(self, tmp_path) -> None:
        stub = _StubSeeder(result=SeedResult(status="skipped"))
        view, _, _, _ = _make_view(tmp_path, seeder_factory=lambda: stub)
        asyncio.run(view._load_data())
        asyncio.run(view._on_seed_demo())
        assert view._seed_status.visible is True
        assert "уже есть" in view._seed_status.value
        assert view._seed_status.color == ft.Colors.ON_SURFACE_VARIANT

    def test_double_click_guard(self, tmp_path) -> None:
        stub = _StubSeeder(result=SeedResult(status="created"))
        view, _, _, _ = _make_view(tmp_path, seeder_factory=lambda: stub)
        view._seeding = True
        asyncio.run(view._on_seed_demo())
        assert stub.calls == 0

    def test_exception_is_caught(self, tmp_path) -> None:
        stub = _StubSeeder(error=RuntimeError("disk full"))
        view, _, _, _ = _make_view(tmp_path, seeder_factory=lambda: stub)
        asyncio.run(view._load_data())
        asyncio.run(view._on_seed_demo())
        assert view._seed_status.visible is True
        assert "Ошибка заполнения" in view._seed_status.value
        assert "disk full" in view._seed_status.value

    def test_start_fresh_marks_seen(self, tmp_path) -> None:
        view, _, _, onboarding = _make_view(tmp_path)
        asyncio.run(view._load_data())
        view._on_start_fresh(None)
        assert onboarding.welcome_seen is True
        texts = _texts(view._accounts_column)
        assert "Добро пожаловать в MyMoney!" not in texts

    def test_status_cleared_on_reload(self, tmp_path) -> None:
        stub = _StubSeeder(result=SeedResult(status="offline"))
        view, _, _, _ = _make_view(tmp_path, seeder_factory=lambda: stub)
        asyncio.run(view._load_data())
        asyncio.run(view._on_seed_demo())
        assert view._seed_status.visible is True
        asyncio.run(view._load_data())
        assert view._seed_status.visible is False
