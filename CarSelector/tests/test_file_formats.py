"""Проверка чтения реальных «капризных» форматов файлов.

Здесь воспроизводим то, что чаще всего приходит от пользователей: Excel из 1С,
CSV в кодировке Windows-1251 и CSV с запятой-разделителем, где внутри поля
встречаются пробелы и подписи «руб.».
"""

from __future__ import annotations

import pandas as pd
import pytest

from data_loader import load_cars
from paths import DEMO_CSV

SIMPLE_CSV = (
    "Марка,Модель,Цена,Пробег,Год,Топливо,КПП,Кузов\n"
    "Kia,Rio,\"1 350 000 руб.\",\"45 000 км\",2019,бензин,автомат,седан\n"
    "Hyundai,Solaris,980000,72000,2018,Бензин,МКПП,седан\n"
    "Toyota,Camry,2400000,110000,2017,бензин,автомат,седан\n"
)


@pytest.fixture(scope="module")
def raw_demo() -> pd.DataFrame:
    if not DEMO_CSV.exists():
        pytest.skip("Демо-файл не создан: запустите scripts/make_demo_data.py")
    return pd.read_csv(DEMO_CSV, sep=";", dtype=str, keep_default_na=False, encoding="utf-8-sig")


def test_excel_round_trip(tmp_path, raw_demo):
    """Excel выгружается из 1С и читается обратно без потерь."""
    path = tmp_path / "cars.xlsx"
    raw_demo.to_excel(path, index=False)
    result = load_cars(path)
    assert result.report["rows_valid"] > 80
    assert result.column_map["brand"] == "Марка"
    assert result.df["price"].between(200_000, 10_000_000).all()


def test_windows_1251_csv(tmp_path, raw_demo):
    """CSV в cp1251 (типичная выгрузка Excel) — без символа ₽, которого нет в кодировке."""
    path = tmp_path / "cars_cp1251.csv"
    prepared = raw_demo.copy()
    for column in prepared.columns:  # в cp1251 символа ₽ нет — заменяем на «руб.»
        prepared[column] = prepared[column].astype(str).str.replace("₽", "руб.", regex=False)
    prepared.to_csv(path, sep=";", index=False, encoding="cp1251")
    result = load_cars(path)
    assert result.report["rows_valid"] > 80
    assert result.df["brand"].notna().all()


def test_semicolon_and_comma_separated_csv(tmp_path):
    r"""CSV с запятой-разделителем, где в одном поле есть запятая внутри кавычек."""
    path = tmp_path / "simple.csv"
    path.write_text(SIMPLE_CSV, encoding="utf-8")
    result = load_cars(path)
    assert result.report["rows_valid"] == 3
    assert list(result.df["price"]) == [1_350_000, 980_000, 2_400_000]
    assert set(result.df["fuel"]) == {"Бензин"}
    assert result.df.loc[0, "transmission"] == "АКПП"


def test_cyrillic_and_latin_headers_are_equal(tmp_path):
    """Русские и английские заголовки дают одинаковый результат."""
    ru = tmp_path / "ru.csv"
    en = tmp_path / "en.csv"
    ru.write_text("Марка;Цена;Пробег\nLada;900000;60000\n", encoding="utf-8")
    en.write_text("make;price;mileage\nLada;900000;60000\n", encoding="utf-8")
    ru_result = load_cars(ru)
    en_result = load_cars(en)
    assert ru_result.df["price"].iloc[0] == en_result.df["price"].iloc[0]
    assert ru_result.df["brand"].iloc[0] == en_result.df["brand"].iloc[0]


def test_extra_unknown_columns_do_not_break_loading(tmp_path):
    path = tmp_path / "extra.csv"
    path.write_text(
        "Марка;Цена;Пробег;Комментарий менеджера;Дата постановки\n"
        "Kia;1200000;80000;хорошая машина;01.02.2026\n",
        encoding="utf-8",
    )
    result = load_cars(path)
    assert result.report["rows_valid"] == 1
    assert result.df["price"].iloc[0] == 1_200_000
