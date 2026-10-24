"""Тесты шаблонов бюджетов MyMoney: payload и инфо (слайс 3.5b-2)."""

from __future__ import annotations

import pytest

from core.budget_templates import (
    MAX_ITEMS,
    TemplateInfo,
    template_infos,
    template_items,
    template_payload,
)


class TestTemplateItems:
    def test_maps_envelopes(self) -> None:
        envelopes = [
            {"category": "Еда", "limit_amount": "500.0000"},
            {"category": "  Транспорт  ", "limit_amount": "120.5"},
        ]

        assert template_items(envelopes) == [
            {"category": "Еда", "limit_amount": "500.0000"},
            {"category": "Транспорт", "limit_amount": "120.5000"},
        ]

    def test_garbage_is_skipped(self) -> None:
        envelopes = [
            "oops",
            {"category": "", "limit_amount": "10"},
            {"category": "Еда", "limit_amount": "0"},
            {"category": "Еда", "limit_amount": "abc"},
            {"category": "Кафе", "limit_amount": "10"},
        ]

        assert template_items(envelopes) == [{"category": "Кафе", "limit_amount": "10.0000"}]

    def test_empty(self) -> None:
        assert template_items([]) == []
        assert template_items(None) == []


class TestTemplatePayload:
    def test_valid(self) -> None:
        items = [{"category": "Еда", "limit_amount": "10.0000"}]

        assert template_payload("  Базовый ", items, 11, True) == {
            "name": "Базовый",
            "items": items,
            "currency": 11,
            "is_public": True,
        }

    @pytest.mark.parametrize("name", ["", "   ", None])
    def test_blank_name_rejected(self, name) -> None:
        with pytest.raises(ValueError, match="название"):
            template_payload(name, [{"category": "Еда", "limit_amount": "1"}])

    def test_empty_items_rejected(self) -> None:
        with pytest.raises(ValueError, match="Нет конвертов"):
            template_payload("Базовый", [])

    def test_too_many_items_rejected(self) -> None:
        items = [{"category": f"К{i}", "limit_amount": "1"} for i in range(MAX_ITEMS + 1)]

        with pytest.raises(ValueError, match="Слишком много"):
            template_payload("Базовый", items)

    def test_currency_optional(self) -> None:
        payload = template_payload("Базовый", [{"category": "Еда", "limit_amount": "1"}])

        assert payload["currency"] is None
        assert payload["is_public"] is False


class TestTemplateInfos:
    def test_maps_rows(self) -> None:
        rows = [
            {"id": 1, "name": "Мой", "items": [{"category": "Еда"}], "is_public": False, "currency_ticker": "BYN"},
            {"id": 2, "name": "Публичный", "items": [], "is_public": True},
        ]

        infos = template_infos(rows)

        assert [info.name for info in infos] == ["Мой", "Публичный"]
        assert infos[0].template_id == 1
        assert infos[0].items == 1
        assert infos[0].currency == "BYN"
        assert infos[0].is_public is False
        assert infos[1].subtitle == "0 категорий · публичный"

    def test_garbage_skipped(self) -> None:
        assert template_infos([None, "oops", {"name": " "}, {"id": "x", "name": "Без id"}])[0].template_id is None

    def test_subtitle(self) -> None:
        info = TemplateInfo(1, "Мой", 2, False, "BYN")

        assert info.subtitle == "2 категорий · приватный · BYN"
