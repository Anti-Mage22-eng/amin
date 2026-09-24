"""Скилл «Соответствие» — жёсткий фильтр по обязательным требованиям клиента.

Этот агент ничего не оценивает, он отсекает: если машина не проходит по бюджету,
пробегу, году, марке, топливу, КПП или кузову — она не попадает в рейтинг.
Причина отказа формулируется так, чтобы её можно было показать клиенту.
"""

from __future__ import annotations

from normalize import brand_key

DESCRIPTION = (
    "Жёсткий отбор: проверяет бюджет, пробег, год, марку, топливо, КПП и кузов. "
    "Не подходящие варианты отсекаются с понятной причиной отказа."
)

FORMULA = "проходит / не проходит (без баллов); причина отказа возвращается текстом"


def _brand_matches(car_brand: str, wanted: list[str]) -> bool:
    car_key = brand_key(car_brand)
    return any(car_key == brand_key(w) or brand_key(w) in str(car_brand).lower() for w in wanted)


def is_eligible(car: dict, ctx: dict) -> tuple[bool, str]:
    """Возвращает (подходит?, причина отказа)."""
    request = ctx.get("request", {})

    budget = request.get("budget_max")
    if budget and float(car.get("price") or 0) > float(budget):
        return False, "Цена выше бюджета"

    mileage_limit = request.get("mileage_max")
    if mileage_limit and float(car.get("mileage") or 0) > float(mileage_limit):
        return False, "Пробег выше лимита"

    year_min = request.get("year_min")
    year_max = request.get("year_max")
    year = car.get("year")
    if year_min:
        if year is None:
            return False, "Год выпуска не указан"
        if int(year) < int(year_min):
            return False, "Год выпуска ниже требуемого"
    if year_max:
        if year is None:
            return False, "Год выпуска не указан"
        if int(year) > int(year_max):
            return False, "Год выпуска выше требуемого"

    brands = request.get("brands") or []
    if brands and not _brand_matches(str(car.get("brand") or ""), brands):
        return False, "Другая марка"

    for field, title in (("fuel", "топливо"), ("transmission", "КПП"), ("body", "кузов")):
        wanted = request.get(field)
        if wanted and str(car.get(field) or "") != str(wanted):
            return False, f"Не подходит {title}"

    return True, ""
