import math

import pytest

from core import Money, Resource


class TestMoneyCreation:
    def setup_class(self):
        self.usd = Resource("USD", "USD")

    def test_create(self):
        m = Money(10, self.usd)
        assert m.value == 10
        assert m.currency == self.usd

    def test_create_zero(self):
        m = Money(0, self.usd)
        assert m.value == 0

    def test_create_negative(self):
        m = Money(-5, self.usd)
        assert m.value == -5


class TestMoneyCopy:
    def setup_class(self):
        self.usd = Resource("USD", "USD")

    def test_copy_creates_new_instance(self):
        original = Money(50, self.usd)
        copied = original.copy()
        assert copied == original
        assert copied is not original

    def test_copy_independent(self):
        original = Money(50, self.usd)
        copied = original.copy()
        original.value = 100
        assert copied.value == 50


class TestMoneyEquality:
    def setup_class(self):
        self.usd = Resource("USD", "USD")
        self.eur = Resource("EUR", "EUR")

    def test_currency_equal(self):
        assert Money(5, self.usd) == Money(5, self.usd)

    def test_not_equal_different_value(self):
        assert Money(5, self.usd) != Money(10, self.usd)

    def test_not_equal_different_currency(self):
        assert Money(5, self.usd) != Money(5, self.eur)

    def test_equal_to_int(self):
        assert Money(5, self.usd) == 5

    def test_equal_to_float(self):
        assert Money(5.0, self.usd) == 5.0

    def test_not_equal_to_int(self):
        assert Money(5, self.usd) != 10


class TestMoneyComparison:
    def setup_class(self):
        self.usd = Resource("USD", "USD")
        self.eur = Resource("EUR", "EUR")

    def test_currency_little(self):
        assert Money(3, self.usd) < Money(5, self.usd)

    def test_currency_little_int(self):
        assert Money(3, self.usd) < 5

    def test_currency_little_float(self):
        assert Money(3, self.usd) < 5.0

    def test_currency_not_little(self):
        assert not (Money(5, self.usd) < Money(3, self.usd))

    def test_different_currency_raises(self):
        with pytest.raises(TypeError):
            _ = Money(3, self.usd) < Money(5, self.eur)

    def test_gt(self):
        assert Money(10, self.usd) > Money(5, self.usd)

    def test_gt_int(self):
        assert Money(10, self.usd) > 5

    def test_gt_different_currency_raises(self):
        with pytest.raises(TypeError):
            _ = Money(10, self.usd) > Money(5, self.eur)


class TestMoneyArithmetic:
    def setup_class(self):
        self.usd = Resource("USD", "USD")
        self.eur = Resource("EUR", "EUR")

    def test_currency_sum(self):
        result = Money(5, self.usd) + Money(7, self.usd)
        assert result == Money(12, self.usd)

    def test_currency_sub(self):
        result = Money(13, self.usd) - Money(7, self.usd)
        assert result == Money(6, self.usd)

    def test_currency_multiply(self):
        result = Money(5, self.usd) * 2
        assert result == Money(10, self.usd)

    def test_currency_float_multiply(self):
        result = Money(1.5, self.usd) * 2
        assert result == Money(3, self.usd)

    def test_sum_different_currency_raises(self):
        with pytest.raises(TypeError):
            Money(5, self.usd) + Money(7, self.eur)

    def test_sub_different_currency_raises(self):
        with pytest.raises(TypeError):
            Money(5, self.usd) - Money(7, self.eur)

    def test_mul_money_raises(self):
        with pytest.raises(TypeError):
            Money(3, self.usd) * Money(5, self.eur)

    def test_sum_int(self):
        result = Money(5, self.usd) + 10
        assert result == Money(15, self.usd)

    def test_sum_float(self):
        result = Money(5, self.usd) + 2.5
        assert result == Money(7.5, self.usd)

    def test_sub_int(self):
        result = Money(10, self.usd) - 3
        assert result == Money(7, self.usd)

    def test_sub_float(self):
        result = Money(10, self.usd) - 1.5
        assert result == Money(8.5, self.usd)


class TestMoneyNegation:
    def setup_class(self):
        self.usd = Resource("USD", "USD")

    def test_neg(self):
        assert -Money(5, self.usd) == Money(-5, self.usd)

    def test_neg_negative(self):
        assert -Money(-5, self.usd) == Money(5, self.usd)


class TestMoneyAbs:
    def setup_class(self):
        self.usd = Resource("USD", "USD")

    def test_abs_positive(self):
        assert abs(Money(5, self.usd)) == Money(5, self.usd)

    def test_abs_negative(self):
        assert abs(Money(-5, self.usd)) == Money(5, self.usd)

    def test_abs_zero(self):
        assert abs(Money(0, self.usd)) == Money(0, self.usd)


class TestMoneyRepresentation:
    def setup_class(self):
        self.usd = Resource("USD", "USD")
        self.eur = Resource("EUR", "EUR")
        self.rub = Resource("RUB", "RUB")
        self.byn = Resource("BYN", "BYN")

    def test_repr(self):
        assert repr(Money(5, self.usd)) == "Money(5, Dollar)"

    def test_str(self):
        assert str(Money(5, self.usd)) == "5 $"

    def test_repr_eur(self):
        assert repr(Money(10, self.eur)) == "Money(10, Euro)"

    def test_str_eur(self):
        assert str(Money(10, self.eur)) == "10 \u20ac"

    def test_repr_rub(self):
        assert repr(Money(100, self.rub)) == "Money(100, Ruble)"

    def test_str_rub(self):
        assert str(Money(100, self.rub)) == "100 \u20bd"


class TestMoneyEdgeCases:
    def setup_class(self):
        self.usd = Resource("USD", "USD")

    def test_very_large_number(self):
        m = Money(1e308, self.usd)
        assert m.value == 1e308

    def test_very_small_number(self):
        m = Money(1e-308, self.usd)
        assert m.value == 1e-308

    def test_nan(self):
        m = Money(float("nan"), self.usd)
        assert math.isnan(m.value)

    def test_infinity(self):
        m = Money(float("inf"), self.usd)
        assert m.value == float("inf")
