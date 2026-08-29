import datetime

import pytest

from core.recurrence import Frequency, RecurrenceRule


class TestRecurrenceRuleCreation:
    def test_create_daily(self):
        rule = RecurrenceRule(Frequency.DAILY)
        assert rule.frequency == Frequency.DAILY
        assert rule.interval == 1
        assert rule.until is None

    def test_create_weekly_with_interval(self):
        rule = RecurrenceRule(Frequency.WEEKLY, interval=2)
        assert rule.frequency == Frequency.WEEKLY
        assert rule.interval == 2

    def test_create_monthly_with_until(self):
        until = datetime.date(2026, 12, 31)
        rule = RecurrenceRule(Frequency.MONTHLY, until=until)
        assert rule.until == until

    def test_create_yearly(self):
        rule = RecurrenceRule(Frequency.YEARLY, interval=3)
        assert rule.interval == 3

    def test_interval_zero_raises(self):
        with pytest.raises(ValueError, match="Interval must be >= 1"):
            RecurrenceRule(Frequency.DAILY, interval=0)

    def test_interval_negative_raises(self):
        with pytest.raises(ValueError, match="Interval must be >= 1"):
            RecurrenceRule(Frequency.MONTHLY, interval=-1)


class TestRecurrenceRuleParse:
    def test_parse_empty_string(self):
        assert RecurrenceRule.parse("") is None

    def test_parse_none_like(self):
        assert RecurrenceRule.parse("  ") is None

    def test_parse_daily(self):
        rule = RecurrenceRule.parse("daily")
        assert rule is not None
        assert rule.frequency == Frequency.DAILY
        assert rule.interval == 1

    def test_parse_weekly(self):
        rule = RecurrenceRule.parse("weekly")
        assert rule.frequency == Frequency.WEEKLY

    def test_parse_monthly(self):
        rule = RecurrenceRule.parse("monthly")
        assert rule.frequency == Frequency.MONTHLY

    def test_parse_yearly(self):
        rule = RecurrenceRule.parse("yearly")
        assert rule.frequency == Frequency.YEARLY

    def test_parse_with_interval(self):
        rule = RecurrenceRule.parse("daily every 3")
        assert rule.interval == 3

    def test_parse_with_until(self):
        rule = RecurrenceRule.parse("monthly until 2026-12-31")
        assert rule.until == datetime.date(2026, 12, 31)

    def test_parse_with_interval_and_until(self):
        rule = RecurrenceRule.parse("weekly every 2 until 2026-06-01")
        assert rule.frequency == Frequency.WEEKLY
        assert rule.interval == 2
        assert rule.until == datetime.date(2026, 6, 1)

    def test_parse_unknown_frequency(self):
        assert RecurrenceRule.parse("annually") is None

    def test_parse_invalid_until_date(self):
        rule = RecurrenceRule.parse("monthly until not-a-date")
        assert rule is not None
        assert rule.until is None

    def test_parse_invalid_interval(self):
        rule = RecurrenceRule.parse("daily every abc")
        assert rule is not None
        assert rule.interval == 1

    def test_parse_case_insensitive(self):
        rule = RecurrenceRule.parse("DAILY")
        assert rule.frequency == Frequency.DAILY


class TestRecurrenceRuleNextDate:
    def test_next_date_daily(self):
        rule = RecurrenceRule(Frequency.DAILY)
        from_date = datetime.date(2026, 1, 1)
        assert rule.next_date(from_date) == datetime.date(2026, 1, 2)

    def test_next_date_daily_interval(self):
        rule = RecurrenceRule(Frequency.DAILY, interval=3)
        from_date = datetime.date(2026, 1, 1)
        assert rule.next_date(from_date) == datetime.date(2026, 1, 4)

    def test_next_date_weekly(self):
        rule = RecurrenceRule(Frequency.WEEKLY)
        from_date = datetime.date(2026, 1, 1)
        assert rule.next_date(from_date) == datetime.date(2026, 1, 8)

    def test_next_date_monthly(self):
        rule = RecurrenceRule(Frequency.MONTHLY)
        from_date = datetime.date(2026, 1, 15)
        assert rule.next_date(from_date) == datetime.date(2026, 2, 15)

    def test_next_date_monthly_end_of_month(self):
        rule = RecurrenceRule(Frequency.MONTHLY)
        from_date = datetime.date(2026, 1, 31)
        result = rule.next_date(from_date)
        assert result.month == 2
        assert result.day == 28

    def test_next_date_yearly(self):
        rule = RecurrenceRule(Frequency.YEARLY)
        from_date = datetime.date(2026, 6, 15)
        assert rule.next_date(from_date) == datetime.date(2027, 6, 15)

    def test_next_date_yearly_leap_day(self):
        rule = RecurrenceRule(Frequency.YEARLY)
        from_date = datetime.date(2024, 2, 29)
        assert rule.next_date(from_date) == datetime.date(2025, 2, 28)


class TestRecurrenceRuleGenerateDates:
    def test_generate_daily_3(self):
        rule = RecurrenceRule(Frequency.DAILY)
        dates = rule.generate_dates(datetime.date(2026, 1, 1), count=3)
        assert dates == [datetime.date(2026, 1, 2), datetime.date(2026, 1, 3), datetime.date(2026, 1, 4)]

    def test_generate_weekly_2(self):
        rule = RecurrenceRule(Frequency.WEEKLY)
        dates = rule.generate_dates(datetime.date(2026, 1, 1), count=2)
        assert dates == [datetime.date(2026, 1, 8), datetime.date(2026, 1, 15)]

    def test_generate_monthly_with_until(self):
        rule = RecurrenceRule(Frequency.MONTHLY, until=datetime.date(2026, 3, 31))
        dates = rule.generate_dates(datetime.date(2026, 1, 1), count=10)
        assert dates == [datetime.date(2026, 2, 1), datetime.date(2026, 3, 1)]

    def test_generate_empty_when_until_before_start(self):
        rule = RecurrenceRule(Frequency.MONTHLY, until=datetime.date(2025, 1, 1))
        dates = rule.generate_dates(datetime.date(2026, 1, 1), count=5)
        assert dates == []

    def test_generate_count_zero(self):
        rule = RecurrenceRule(Frequency.DAILY)
        dates = rule.generate_dates(datetime.date(2026, 1, 1), count=0)
        assert dates == []


class TestRecurrenceRuleString:
    def test_to_string_daily(self):
        rule = RecurrenceRule(Frequency.DAILY)
        assert rule.to_string() == "daily"

    def test_to_string_weekly_interval(self):
        rule = RecurrenceRule(Frequency.WEEKLY, interval=2)
        assert rule.to_string() == "weekly every 2"

    def test_to_string_monthly_until(self):
        rule = RecurrenceRule(Frequency.MONTHLY, until=datetime.date(2026, 12, 31))
        assert rule.to_string() == "monthly until 2026-12-31"

    def test_to_string_full(self):
        rule = RecurrenceRule(Frequency.YEARLY, interval=3, until=datetime.date(2030, 1, 1))
        assert rule.to_string() == "yearly every 3 until 2030-01-01"

    def test_str(self):
        rule = RecurrenceRule(Frequency.DAILY)
        assert str(rule) == "daily"

    def test_repr(self):
        rule = RecurrenceRule(Frequency.DAILY)
        assert repr(rule) == "RecurrenceRule('daily')"
