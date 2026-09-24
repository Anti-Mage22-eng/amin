"""Статистика и данные для диаграмм — только pandas, без привязки к интерфейсу.

Здесь нет ни одного импорта Flet: модуль легко тестировать и переиспользовать
(например, для отчёта в консоли).
"""

from __future__ import annotations

import pandas as pd

from normalize import COLUMN_TITLES


def _fmt_money(value: float | None) -> str:
    if value is None:
        return "—"
    return f"{value:,.0f} ₽".replace(",", " ")


def _fmt_km(value: float | None) -> str:
    if value is None:
        return "—"
    return f"{value:,.0f} км".replace(",", " ")


def format_car_price(value: float | None) -> str:
    return _fmt_money(value)


def format_mileage(value: float | None) -> str:
    return _fmt_km(value)


def dataset_kpis(df: pd.DataFrame) -> list[dict]:
    """KPI-карточки по всему файлу."""
    if df.empty:
        return []
    return [
        {"label": "Автомобилей в базе", "value": f"{len(df):,}".replace(",", " "), "hint": "после проверки данных"},
        {"label": "Средняя цена", "value": _fmt_money(df["price"].mean()), "hint": f"медиана {_fmt_money(df['price'].median())}"},
        {"label": "Средний пробег", "value": _fmt_km(df["mileage"].mean()), "hint": f"медиана {_fmt_km(df['mileage'].median())}"},
        {"label": "Марок", "value": str(df["brand"].nunique()), "hint": f"моделей: {df['model'].replace('', pd.NA).nunique() or '—'}"},
    ]


def price_by_brand(df: pd.DataFrame, top_n: int = 8) -> list[dict]:
    """Средняя цена и количество машин по маркам (для столбчатой диаграммы)."""
    if df.empty:
        return []
    grouped = (
        df.groupby("brand", dropna=True)
        .agg(avg_price=("price", "mean"), count=("price", "size"))
        .sort_values("avg_price", ascending=False)
        .head(top_n)
    )
    return [
        {"brand": str(brand), "avg_price": float(row["avg_price"]), "count": int(row["count"])}
        for brand, row in grouped.iterrows()
    ]


def brand_shares(df: pd.DataFrame, top_n: int = 6) -> list[dict]:
    """Доли марок в базе (для круговой диаграммы)."""
    if df.empty:
        return []
    counts = df["brand"].value_counts()
    head = counts.head(top_n)
    rest = int(counts.iloc[top_n:].sum())
    shares = [{"brand": str(brand), "count": int(count)} for brand, count in head.items()]
    if rest:
        shares.append({"brand": "Прочие", "count": rest})
    return shares


def category_shares(df: pd.DataFrame, column: str, top_n: int = 6) -> list[dict]:
    """Доли категорий (топливо, КПП, кузов) — для круговой диаграммы."""
    if df.empty or column not in df.columns:
        return []
    counts = df[column].astype(str).replace("", "Не указано").value_counts()
    head = counts.head(top_n)
    rest = int(counts.iloc[top_n:].sum())
    shares = [{"label": str(k), "count": int(v)} for k, v in head.items()]
    if rest:
        shares.append({"label": "Прочие", "count": rest})
    return shares


def price_mileage_points(df: pd.DataFrame, limit: int = 400) -> list[dict]:
    """Точки «пробег → цена» (для диаграммы рассеяния)."""
    if df.empty:
        return []
    sample = df.sort_values("price", ascending=False).head(limit)
    return [
        {"mileage": float(row.mileage), "price": float(row.price), "label": f"{row.brand} {row.model}".strip()}
        for row in sample.itertuples()
    ]


def avg_price_by_year(df: pd.DataFrame, min_year: int = 2010) -> list[dict]:
    """Средняя цена по годам выпуска (для линейного графика)."""
    if df.empty or df["year"].isna().all():
        return []
    data = df.dropna(subset=["year"])
    data = data[data["year"] >= min_year]
    if data.empty:
        return []
    grouped = data.groupby(data["year"].astype(int)).agg(avg_price=("price", "mean"), count=("price", "size"))
    return [
        {"year": int(year), "avg_price": float(row["avg_price"]), "count": int(row["count"])}
        for year, row in grouped.iterrows()
    ]


def top_models_by_score(recommendations: list, top_n: int = 5) -> list[dict]:
    """Топ подобранных моделей по итоговой оценке агентов."""
    if not recommendations:
        return []
    grouped: dict[str, list[float]] = {}
    for rec in recommendations:
        name = f"{rec.car.get('brand', '')} {rec.car.get('model', '')}".strip()
        grouped.setdefault(name, []).append(rec.total)
    rows = [
        {"model": name, "avg_score": sum(scores) / len(scores), "count": len(scores)}
        for name, scores in grouped.items()
    ]
    rows.sort(key=lambda r: r["avg_score"], reverse=True)
    return rows[:top_n]


def selection_kpis(result) -> list[dict]:
    """KPI по результату подбора."""
    if result is None:
        return []
    best = result.recommendations[0] if result.recommendations else None
    return [
        {"label": "Прошли фильтр", "value": str(result.eligible), "hint": f"из {result.considered} в базе"},
        {"label": "Отклонено", "value": str(result.rejected), "hint": "не подошли по обязательным параметрам"},
        {"label": "Лучшая оценка", "value": f"{best.total:.0f}/100" if best else "—", "hint": best.car["brand"] if best else "нет вариантов"},
        {"label": "Медиана цены отбора", "value": _fmt_money(result.median_price), "hint": "по прошедшим фильтр"},
    ]


def column_titles() -> dict[str, str]:
    return dict(COLUMN_TITLES)
