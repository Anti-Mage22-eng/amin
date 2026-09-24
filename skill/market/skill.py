"""Скилл «Рынок» — сравнение цены с медианой цен аналогичных автомобилей.

Аналоги ищутся по принципу «от частного к общему»: сначала та же марка и модель,
если таких машин в базе достаточно; затем просто та же марка; и только в крайнем
случае — вся база. Чем дешевле машина относительно аналогов, тем выше оценка.
"""

from __future__ import annotations

DESCRIPTION = (
    "Сравнивает цену с медианой цен аналогичных автомобилей (модель → марка → вся база) "
    "и находит недооценённые предложения."
)

FORMULA = "≤ 80 % медианы → 100; 80–130 % → линейно 100→10; ≥ 130 % → 10"

MIN_SOURCE_SIZE = 4


def _money(value: float) -> str:
    return f"{value:,.0f}".replace(",", " ") + " ₽"


def evaluate(car: dict, ctx: dict) -> tuple[float, list[str]]:
    market = ctx.get("market") or {}
    median = market.get("median_price")
    source = market.get("source", "")
    price = float(car.get("price") or 0)

    if not median or median <= 0:
        return 70.0, ["Недостаточно аналогов в базе для сравнения цены"]

    ratio = price / float(median)
    delta = (1.0 - ratio) * 100.0

    if ratio <= 0.8:
        score = 100.0
    elif ratio >= 1.3:
        score = 10.0
    else:
        score = 100.0 - 90.0 * (ratio - 0.8) / 0.5

    if abs(delta) <= 3:
        reason = f"Цена на уровне рынка ({_money(float(median))}, выборка: {source}) — торг не поможет"
    else:
        direction = "ниже" if delta > 0 else "выше"
        reason = (
            f"Цена на {abs(delta):.0f} % {direction} медианы аналогов "
            f"({_money(float(median))}, выборка: {source})"
        )

    return round(score, 1), [reason]
