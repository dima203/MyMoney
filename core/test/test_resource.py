import pytest

from core import Resource


class TestResourceCreation:
    def test_create_with_string_pk(self):
        resource = Resource("USD", "Доллар")
        assert resource.pk == "USD"
        assert resource.name == "Доллар"

    def test_create_with_int_pk(self):
        resource = Resource(1, "BYN")
        assert resource.pk == 1
        assert resource.name == "BYN"

    def test_create_with_zero_pk(self):
        resource = Resource(0, "RUB")
        assert resource.pk == 0

    def test_create_with_empty_name(self):
        resource = Resource("USD", "")
        assert resource.name == ""


class TestResourceEquality:
    def test_equal_by_pk(self):
        r1 = Resource(1, "BYN")
        r2 = Resource(1, "Другое")
        assert r1 == r2

    def test_not_equal_different_pk(self):
        r1 = Resource(1, "BYN")
        r2 = Resource(2, "BYN")
        assert r1 != r2

    def test_equal_same_object(self):
        r = Resource(1, "USD")
        assert r == r


class TestResourceJson:
    def test_to_json(self):
        resource = Resource(1, "USD")
        json_data = resource.to_json()
        assert json_data["pk"] == 1
        assert json_data["name"] == "USD"
        assert "last_update" in json_data

    def test_to_json_preserves_pk_type(self):
        resource = Resource("BYN", "Белорусский рубль")
        json_data = resource.to_json()
        assert json_data["pk"] == "BYN"
