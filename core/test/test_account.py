from unittest.mock import MagicMock

from core import Account, Money, Resource


class TestAccountCreation:
    def setup_class(self) -> None:
        self.BYN = Resource(0, "BYN")

    def test_get_currency(self) -> None:
        account = Account(0, "BYN", self.BYN)
        assert account.get_balance() == Money(0, self.BYN)

    def test_create_with_initial_value(self):
        account = Account(1, "Savings", self.BYN, 500)
        assert account.get_balance() == Money(500, self.BYN)

    def test_create_with_string_pk(self):
        account = Account("acc_1", "Card", self.BYN, 100)
        assert account.pk == "acc_1"
        assert account.get_balance() == Money(100, self.BYN)

    def test_to_json(self) -> None:
        test_account = Account(0, "test1", self.BYN)
        json = test_account.to_json()
        json.pop("last_update")
        assert json == {"pk": 0, "name": "test1", "resource_count": 0, "resource_type": self.BYN.pk}

    def test_to_json_with_value(self):
        account = Account(1, "Card", self.BYN, 250)
        json = account.to_json()
        json.pop("last_update")
        assert json == {"pk": 1, "name": "Card", "resource_count": 250, "resource_type": 0}


class TestAccountEquality:
    def setup_class(self) -> None:
        self.BYN = Resource(0, "BYN")

    def test_equal_accounts(self):
        a1 = Account(0, "A", self.BYN, 100)
        a2 = Account(1, "B", self.BYN, 100)
        assert a1 == a2

    def test_not_equal_accounts(self):
        a1 = Account(0, "A", self.BYN, 100)
        a2 = Account(1, "B", self.BYN, 200)
        assert a1 != a2


class TestAccountSubscribe:
    def setup_method(self) -> None:
        self.BYN = Resource(0, "BYN")
        self.account = Account(0, "Test", self.BYN, 100)

    def test_subscribe_receives_notification(self):
        callback = MagicMock()
        self.account.subscribe(callback)
        self.account.name = "New Name"
        callback.assert_called_once()

    def test_unsubscribe_stops_notifications(self):
        callback = MagicMock()
        self.account.subscribe(callback)
        self.account.unsubscribe(callback)
        self.account.name = "New Name"
        callback.assert_not_called()

    def test_multiple_subscribers(self):
        cb1 = MagicMock()
        cb2 = MagicMock()
        self.account.subscribe(cb1)
        self.account.subscribe(cb2)
        self.account.name = "Changed"
        cb1.assert_called_once()
        cb2.assert_called_once()

    def test_subscribe_callback_receives_pk_and_json(self):
        callback = MagicMock()
        self.account.subscribe(callback)
        self.account.name = "Updated"
        args = callback.call_args[0]
        assert args[0] == 0
        assert "name" in args[1]
        assert args[1]["name"] == "Updated"


class TestAccountsetattr:
    def setup_method(self) -> None:
        self.BYN = Resource(0, "BYN")

    def test_setattr_triggers_observer(self):
        account = Account(0, "Test", self.BYN, 100)
        callback = MagicMock()
        account.subscribe(callback)
        account.value = Money(200, self.BYN)
        callback.assert_called()

    def test_initial_setattr_no_observer_call(self):
        callback = MagicMock()
        account = Account(0, "Test", self.BYN, 100)
        account.subscribe(callback)
        callback.assert_not_called()
