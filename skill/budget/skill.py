"""Скилл «Бюджет» — насколько комфортно цена укладывается в бюджет клиента.

Логика: чем больше остаток бюджета после покупки, тем выше оценка. Слишком
дешёвая машина (менее 35 % бюджета) оценку не повышает, а ограничивается — это
повод проверить состояние и историю, а не повод радоваться.
"""

from __future__ import annotations

DESCRIPTION = (
    "Считает запас бюджета клиента: чем дешевле машина относительно бюджета, "
    "тем выше оценка. Подозрительно дешёвые варианты ограничиваются сверху."
)

FORMULA = "score = 100 × min(1, запас / 45 %); при цене < 35 % бюджета score ≤ 82"


def _money(value: float) -> str:
    """1 350 000 ₽ — пробел как разделитель тысяч, не запятая."""
    return f"{value:,.0f}".replace(",", " ") + " ₽"


def evaluate(car: dict, ctx: dict) -> tuple[float, list[str]]:
    """Возвращает (оценка 0–100, список обоснований)."""
    request = ctx.get("request", {})
    budget = float(request.get("budget_max") or 0)
    price = float(car.get("price") or 0)

    if budget <= 0:
        return 60.0, ["Бюджет не задан — оценка нейтральная"]

    ratio = price / budget
    if ratio >= 1:
        return 0.0, [f"Цена {_money(price)} выходит за бюджет {_money(budget)}"]

    saving = 1.0 - ratio
    score = 100.0 * min(1.0, saving / 0.45)
    reasons = [f"Запас бюджета: {_money(budget - price)} ({saving * 100:.0f} % от бюджета)"]
    if ratio < 0.35:
        score = min(score, 82.0)
        reasons.append("Цена ниже 35 % бюджета — проверьте состояние и юридическую чистоту")
    return round(score, 1), reasons
