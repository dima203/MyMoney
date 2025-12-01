from core import Account, Money, Resource


class TestAccount:
    def setup_class(self) -> None:
        self.BYN = Resource(0, "BYN")

    def test_get_currency(self) -> None:
        account = Account(0, "BYN", self.BYN)
        assert account.get_balance() == Money(0, self.BYN)

    def test_to_json(self) -> None:
        test_account = Account(0, "test1", self.BYN)
        json = test_account.to_json()
        json.pop("last_update")
        assert json == {"pk": 0, "name": "test1", "resource_count": 0, "resource_type": self.BYN.pk}

    # TODO: add sum of few accounts
