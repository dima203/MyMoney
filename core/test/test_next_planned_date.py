from datetime import date

from core.recurrence import next_planned_date

TODAY = date(2026, 10, 30)


class TestNextPlannedDate:
    def test_daily(self):
        assert next_planned_date(date(2026, 10, 30), "daily", TODAY) == date(2026, 10, 31)

    def test_weekly(self):
        assert next_planned_date(date(2026, 10, 25), "weekly", TODAY) == date(2026, 11, 1)

    def test_monthly_interval(self):
        assert next_planned_date(date(2026, 10, 15), "monthly every 2", TODAY) == date(2026, 12, 15)

    def test_monthly_catch_up_overdue(self):
        assert next_planned_date(date(2026, 6, 1), "monthly", TODAY) == date(2026, 11, 1)

    def test_yearly(self):
        assert next_planned_date(date(2026, 10, 1), "yearly", TODAY) == date(2027, 10, 1)

    def test_until_exhausted(self):
        assert next_planned_date(date(2026, 10, 1), "daily until 2026-10-05", TODAY) is None

    def test_until_still_active(self):
        assert next_planned_date(date(2026, 10, 29), "daily until 2026-11-05", TODAY) == date(2026, 10, 31)

    def test_invalid_rule(self):
        assert next_planned_date(date(2026, 10, 1), "FREQ=MONTHLY", TODAY) is None
        assert next_planned_date(date(2026, 10, 1), "", TODAY) is None
