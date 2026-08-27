import datetime

from core import Account, Money, Resource, PlannedTransaction


class TestPlannedTransactionCreation:
    def setup_method(self):
        self.byn = Resource(0, "BYN")
        self.account = Account(0, "Test", self.byn, 100)

    def test_create(self):
        pt = PlannedTransaction(self.account, Money(50, self.byn), datetime.datetime(2025, 1, 1), "monthly")
        assert pt.storage == self.account
        assert pt.value == Money(50, self.byn)
        assert pt.planned_time == datetime.datetime(2025, 1, 1)
        assert pt.repeatability == "monthly"

    def test_create_with_none_repeatability(self):
        pt = PlannedTransaction(self.account, Money(10, self.byn), datetime.datetime.now(), None)
        assert pt.repeatability is None


class TestPlannedTransactionJson:
    def setup_method(self):
        self.byn = Resource(0, "BYN")
        self.account = Account(0, "Test", self.byn, 100)

    def test_to_json(self):
        planned_time = datetime.datetime(2025, 6, 15, 10, 30)
        pt = PlannedTransaction(self.account, Money(75.5, self.byn), planned_time, "weekly")
        json_data = pt.to_json()

        assert json_data["storage_id"] == 0
        assert json_data["resource_count"] == 75.5
        assert json_data["resource_type"] == 0
        assert json_data["planned_time"] == planned_time.isoformat()
        assert json_data["repeatability"] == "weekly"
        assert "last_update" in json_data

    def test_to_json_with_different_currency(self):
        usd = Resource(1, "USD")
        account = Account(1, "USD Account", usd, 500)
        pt = PlannedTransaction(account, Money(200, usd), datetime.datetime(2025, 3, 1), "yearly")
        json_data = pt.to_json()
        assert json_data["resource_type"] == 1
        assert json_data["resource_count"] == 200
