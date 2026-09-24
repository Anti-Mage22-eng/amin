"""Проверка слоя данных: чтение файла, отчёт о проверке, производные поля."""

from __future__ import annotations

import pytest

from data_loader import DataError, load_cars
from paths import DEMO_CSV


@pytest.fixture(scope="module")
def demo():
    if not DEMO_CSV.exists():
        pytest.skip("Демо-файл не создан: запустите scripts/make_demo_data.py")
    return load_cars(DEMO_CSV)


def test_demo_file_is_read(demo):
    assert len(demo.df) > 80
    assert demo.report["rows_read"] > len(demo.df)  # часть строк отсеялась при проверке


def test_dirty_rows_are_cleaned(demo):
    report = demo.report
    assert report["dropped_bad_values"] >= 3, "строки без цены/пробега должны отбраковываться"
    assert report["duplicates_removed"] >= 2, "дубликаты должны удаляться"
    assert report["anomalies_removed"] >= 1, "нулевая цена должна отбраковываться"


def test_all_required_columns_detected(demo):
    for canon in ("brand", "model", "price", "mileage", "year", "fuel", "transmission", "body"):
        assert canon in demo.column_map


def test_values_are_numeric_and_sane(demo):
    df = demo.df
    assert df["price"].notna().all()
    assert (df["price"] > 0).all()
    assert (df["mileage"] >= 0).all()
    assert df["year"].dropna().between(1950, 2026).all()
    assert df["price"].between(200_000, 10_000_000).all()


def test_derived_columns(demo):
    df = demo.df
    for column in ("car_id", "brand_key", "age", "mileage_per_year"):
        assert column in df.columns
    assert df["car_id"].is_unique
    assert df["mileage_per_year"].notna().all()
    # пробег в год — неотрицательный и разумный
    assert (df["mileage_per_year"] >= 0).all()
    assert (df["mileage_per_year"] < 200_000).all()


def test_report_has_analysis_sections(demo):
    report = demo.report
    assert report["brands"] > 5
    assert report["price"]["median"] > 0
    assert report["mileage"]["mean"] > 0
    assert report["year"]["min"] and report["year"]["max"]
    assert report["brands_top"]
    assert report["columns_found"]["Марка"] == "Марка"


def test_missing_file_raises_readable_error():
    with pytest.raises(DataError) as exc:
        load_cars("нет-такого-файла.csv")
    assert "не найден" in str(exc.value).lower()


def test_unsupported_format_raises(tmp_path):
    bad = tmp_path / "data.parquet"
    bad.write_text("не таблица", encoding="utf-8")
    with pytest.raises(DataError):
        load_cars(bad)


def test_file_without_required_columns_raises(tmp_path):
    bad = tmp_path / "cars.csv"
    bad.write_text("Столбец1;Столбец2\n1;2\n", encoding="utf-8")
    with pytest.raises(DataError) as exc:
        load_cars(bad)
    assert "обязательные колонки" in str(exc.value).lower()
