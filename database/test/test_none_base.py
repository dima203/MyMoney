from database import NoneBase


class TestNoneBase:
    def setup_method(self):
        self.db = NoneBase()

    def test_load_returns_empty(self):
        assert self.db.load() == []

    def test_add_returns_negative_one(self):
        result = self.db.add({"pk": 1, "name": "test"})
        assert result == -1

    def test_update_is_noop(self):
        self.db.update(1, {"pk": 1, "name": "test"})

    def test_delete_is_noop(self):
        self.db.delete(1)
