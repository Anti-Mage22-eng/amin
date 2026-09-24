"""Проверка аналитики дашборда: KPI и данные для всех диаграмм считаются pandas."""

from __future__ import annotations

import pytest

from dashboard import (
    avg_price_by_year,
    brand_shares,
    category_shares,
    dataset_kpis,
    price_by_brand,
    price_mileage_points,
    selection_kpis,
    top_models_by_score,
)
from data_loader import load_cars
from orchestrator import ClientRequest, Selector
from paths import DEMO_CSV


@pytest.fixture(scope="module")
def df():
    if not DEMO_CSV.exists():
        pytest.skip("Демо-файл не создан: запустите scripts/make_demo_data.py")
    return load_cars(DEMO_CSV).df


@pytest.fixture(scope="module")
def result(df):
    return Selector().select(df, ClientRequest(budget_max=2_000_000, mileage_max=150_000, top_n=10))


def test_dataset_kpis(df):
    kpis = dataset_kpis(df)
    assert len(kpis) == 4
    assert all(kpi["label"] and kpi["value"] for kpi in kpis)
    assert kpis[0]["value"].replace(" ", "").isdigit()


def test_price_by_brand_is_limited_and_sorted(df):
    rows = price_by_brand(df, top_n=8)
    assert 0 < len(rows) <= 8
    assert [row["avg_price"] for row in rows] == sorted((row["avg_price"] for row in rows), reverse=True)
    assert all(row["avg_price"] > 0 and row["count"] > 0 for row in rows)


def test_brand_shares_cover_whole_dataset(df):
    shares = brand_shares(df, top_n=6)
    assert len(shares) <= 7  # топ-6 + «Прочие»
    assert sum(item["count"] for item in shares) == len(df)


def test_category_shares(df):
    shares = category_shares(df, "fuel")
    assert sum(item["count"] for item in shares) == len(df)
    assert any(item["label"] == "Бензин" for item in shares)


def test_price_mileage_points(df):
    points = price_mileage_points(df, limit=50)
    assert 0 < len(points) <= 50
    assert all(point["price"] > 0 and point["mileage"] >= 0 for point in points)
    assert all(point["label"] for point in points)


def test_avg_price_by_year(df):
    rows = avg_price_by_year(df, min_year=2010)
    assert rows
    assert [row["year"] for row in rows] == sorted(row["year"] for row in rows)
    assert all(row["avg_price"] > 0 for row in rows)


def test_selection_kpis_and_top_models(result):
    kpis = selection_kpis(result)
    assert len(kpis) == 4
    assert kpis[0]["value"] == str(result.eligible)
    top = top_models_by_score(result.recommendations, top_n=5)
    assert 0 < len(top) <= 5
    assert [row["avg_score"] for row in top] == sorted((row["avg_score"] for row in top), reverse=True)


def test_empty_input_is_safe():
    import pandas as pd

    empty = pd.DataFrame(columns=["brand", "model", "price", "mileage", "year", "fuel"])
    assert dataset_kpis(empty) == []
    assert price_by_brand(empty) == []
    assert brand_shares(empty) == []
    assert price_mileage_points(empty) == []
    assert selection_kpis(None) == []
