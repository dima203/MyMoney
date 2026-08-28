from core import Resource


class TestResourceCreation:
    def test_create_with_string_pk(self):
        resource = Resource("USD", "Dollar")
        assert resource.pk == "USD"
        assert resource.name == "Dollar"

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

    def test_create_with_optional_fields(self):
        resource = Resource(
            1, "Bitcoin", ticker="BTC", unit="BTC", category="crypto", resource_type="asset", icon="btc"
        )
        assert resource.ticker == "BTC"
        assert resource.unit == "BTC"
        assert resource.category == "crypto"
        assert resource.resource_type == "asset"
        assert resource.icon == "btc"


class TestResourceEquality:
    def test_equal_by_pk(self):
        r1 = Resource(1, "BYN")
        r2 = Resource(1, "Other")
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
        assert json_data["id"] == 1
        assert json_data["name"] == "USD"
        assert json_data["ticker"] == ""
        assert json_data["unit"] == ""
        assert json_data["category"] == ""
        assert json_data["resource_type"] == "custom"
        assert json_data["icon"] == ""

    def test_to_json_with_fields(self):
        resource = Resource(
            2, "Ethereum", ticker="ETH", unit="ETH", category="crypto", resource_type="asset", icon="eth"
        )
        json_data = resource.to_json()
        assert json_data["id"] == 2
        assert json_data["ticker"] == "ETH"
        assert json_data["resource_type"] == "asset"

    def test_to_json_preserves_pk_type(self):
        resource = Resource("BYN", "Belarusian Ruble")
        json_data = resource.to_json()
        assert json_data["id"] == "BYN"
