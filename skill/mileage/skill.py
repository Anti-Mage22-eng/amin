"""Скилл «Пробег и износ» — оценивает пробег сам по себе и интенсивность езды.

Два независимых сигнала:
  1) запас до лимита клиента (пробег 132 000 при лимите 150 000 — почти на пределе);
  2) пробег в год — средняя интенсивность эксплуатации (норма до ~15 000 км/год).
Итог — взвешенная смесь, где интенсивность весит больше: именно она отличает
«честные 90 000 за 3 года» от «скрученных 90 000 за 12 лет».
"""

from __future__ import annotations

DESCRIPTION = (
    "Оценивает пробег двумя способами: запас до лимита клиента и пробег в год "
    "(интенсивность эксплуатации). Выявляет «скрученный» пробег."
)

FORMULA = "score = 0,4 × запас до лимита + 0,6 × интенсивность (норма ≤ 15 000 км/год)"

NORM_KM_PER_YEAR = 15_000
HIGH_KM_PER_YEAR = 35_000
LOW_KM_PER_YEAR = 12_000


def _num(value: float) -> str:
    """1 350 000 — пробел как разделитель тысяч."""
    return f"{value:,.0f}".replace(",", " ")


def _intensity_score(mileage_per_year: float | None) -> tuple[float, str]:
    if mileage_per_year is None:
        return 70.0, "Интенсивность эксплуатации неизвестна (нет года выпуска)"
    if mileage_per_year <= LOW_KM_PER_YEAR:
        return 100.0, f"≈{_num(mileage_per_year)} км/год — ниже нормы, щадящая эксплуатация"
    if mileage_per_year >= HIGH_KM_PER_YEAR:
        return 20.0, f"≈{_num(mileage_per_year)} км/год — очень высокая нагрузка"
    score = 100.0 - 80.0 * (mileage_per_year - LOW_KM_PER_YEAR) / (HIGH_KM_PER_YEAR - LOW_KM_PER_YEAR)
    return score, f"≈{_num(mileage_per_year)} км/год — умеренная эксплуатация"


def evaluate(car: dict, ctx: dict) -> tuple[float, list[str]]:
    request = ctx.get("request", {})
    limit = request.get("mileage_max")
    mileage = float(car.get("mileage") or 0)
    reasons: list[str] = []

    if limit:
        used = min(1.0, mileage / float(limit))
        score_limit = 100.0 - 35.0 * used
        reasons.append(f"Пробег {_num(mileage)} км — {used * 100:.0f} % от лимита {_num(float(limit))} км")
    else:
        score_limit = 80.0
        reasons.append(f"Пробег {_num(mileage)} км (лимит не задан)")

    score_rate, rate_reason = _intensity_score(car.get("mileage_per_year"))
    reasons.append(rate_reason)

    score = 0.4 * score_limit + 0.6 * score_rate
    return round(score, 1), reasons
