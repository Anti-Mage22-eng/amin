"""Проверка нормализации: грязные значения из файлов должны разбираться однозначно."""

from __future__ import annotations

import pandas as pd
import pytest

from normalize import (
    COLUMN_ALIASES,
    brand_key,
    detect_columns,
    normalize_body,
    normalize_fuel,
    normalize_transmission,
    normalize_year,
    parse_number,
)


@pytest.mark.parametrize(
    ("raw", "expected"),
    [
        ("1 350 000 ₽", 1_350_000),
        ("1\u00a0350\u00a0000", 1_350_000),
        ("1 200 000 руб.", 1_200_000),
        ("890000", 890_000),
        (890_000, 890_000),
        ("132 тыс. км", 132_000),
        ("132 000 км", 132_000),
        ("1,6", 1.6),
        ("2,0", 2.0),
        ("1.6", 1.6),
        ("1.350", 1350),
        ("1.234,56", 1234.56),
        ("—", None),
        ("", None),
        ("н/д", None),
        ("по договорённости", None),
        ("0", 0.0),
    ],
)
def test_parse_number(raw, expected):
    assert parse_number(raw) == expected


@pytest.mark.parametrize(
    ("raw", "expected"),
    [("2019", 2019), ("2019 г.", 2019), ("2019 год", 2019), ("19", 2019), ("95", 1995), ("", None), (None, None)],
)
def test_normalize_year(raw, expected):
    assert normalize_year(raw) == expected


def test_normalize_categories():
    assert normalize_fuel("бензин") == "Бензин"
    assert normalize_fuel("ДТ") == "Дизель"
    assert normalize_fuel("hybrid") == "Гибрид"
    assert normalize_transmission("автомат") == "АКПП"
    assert normalize_transmission("вариатор") == "Вариатор"
    assert normalize_transmission("DSG") == "Робот"
    assert normalize_transmission("механика") == "МКПП"
    assert normalize_body("кроссовер") == "Кроссовер"
    assert normalize_body("седан") == "Седан"


def test_brand_key_merges_synonyms():
    assert brand_key("ЛАДА (ВАЗ)") == "lada"
    assert brand_key("Lada") == "lada"
    assert brand_key("Хендай") == "hyundai"
    assert brand_key("BMW") == "bmw"


def test_detect_columns_maps_russian_headers():
    """Колонки распознаются даже с «Цена, руб» и без единого совпадения регистра."""
    df = pd.DataFrame(
        columns=["Марка", "Модель", "Цена, руб", "Пробег, км", "Год выпуска",
                 "Топливо", "КПП", "Кузов", "Объём двигателя"]
    )
    mapping = detect_columns(df)
    assert mapping["brand"] == "Марка"
    assert mapping["price"] == "Цена, руб"
    assert mapping["mileage"] == "Пробег, км"
    assert mapping["year"] == "Год выпуска"
    assert mapping["transmission"] == "КПП"
    # регрессия: «Объём двигателя» не должен перехватываться полем «топливо»
    assert mapping["engine_volume"] == "Объём двигателя"
    assert mapping["fuel"] == "Топливо"


def test_detect_columns_english_headers():
    df = pd.DataFrame(columns=["Make", "Model", "Price", "Mileage", "Year", "Fuel", "Transmission"])
    mapping = detect_columns(df)
    assert set(COLUMN_ALIASES) & set(mapping) >= {"brand", "price", "mileage", "year"}
    assert mapping["brand"] == "Make"
    assert mapping["price"] == "Price"
