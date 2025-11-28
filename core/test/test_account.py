import datetime

from core import Account, Money, Transaction, Resource


class TestAccount:
    def test_get_currency(self) -> None:
        byn = Resource("", "BYN")
        account = Account("", "BYN", byn)
        assert account.get_balance() == Money(0, byn)

    def test_to_json(self) -> None:
        rub = Resource("RUB", "RUB")
        test_account = Account("test", "RUB", rub)
        now_time_stamp = datetime.datetime.now()
        transaction = Transaction(0, test_account, Money(100, rub), now_time_stamp)
        json = transaction.to_json()
        del json["last_update"]
        assert json == {"pk": 0, "resource_type": "RUB", "resource_count": 100, "storage_id": "test", "time_stamp": now_time_stamp.isoformat()}

    # TODO: add sum of few accounts
