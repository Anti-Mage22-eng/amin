"""Скилл «Надёжность» — экспертная оценка марки.

Базовая шкала составлена по сводной статистике отказов, стоимости запчастей и
отзывов сервисов (учебная экспертная таблица, 0–100). Марка без оценки получает
нейтральные 70 баллов, чтобы агент не «выключался» на редких брендах.
"""

from __future__ import annotations

from normalize import brand_key

DESCRIPTION = (
    "Оценка конструктивной надёжности и стоимости обслуживания по марке: "
    "экспертная шкала 0–100 плюс поправка на возраст автомобиля."
)

FORMULA = "score = шкала марки (55–95) − поправка за возраст старше 15 лет"

DEFAULT_SCORE = 70.0

BRAND_SCORES: dict[str, float] = {
    "lexus": 95, "toyota": 92, "honda": 90, "mazda": 88, "subaru": 84,
    "kia": 83, "hyundai": 82, "suzuki": 80, "skoda": 80, "genesis": 80,
    "nissan": 78, "mitsubishi": 78, "volkswagen": 76, "exeed": 76,
    "volvo": 75, "belgee": 74, "haval": 74, "renault": 74, "seat": 74,
    "geely": 73, "chery": 72, "opel": 72, "ford": 72, "datsun": 72,
    "jetour": 72, "peugeot": 71, "lada": 70, "chevrolet": 70,
    "citroen": 70, "infiniti": 70, "porsche": 70, "omoda": 70,
    "mercedes": 68, "audi": 66, "gaz": 66, "bmw": 65, "daewoo": 64,
    "moskvich": 64, "jeep": 64, "uaz": 62, "landrover": 62, "mini": 62,
    "lifan": 60, "smart": 60,
}

OLD_CAR_AGE = 15
OLD_CAR_PENALTY = 8.0


def evaluate(car: dict, ctx: dict) -> tuple[float, list[str]]:
    brand = str(car.get("brand") or "")
    key = brand_key(brand)
    score = BRAND_SCORES.get(key)
    reasons: list[str] = []

    if score is None:
        score = DEFAULT_SCORE
        reasons.append(f"{brand or 'Марка не указана'}: нет экспертной оценки — принят средний уровень 70/100")
    else:
        reasons.append(f"{brand}: надёжность {score:.0f}/100 (экспертная шкала марок)")

    age = car.get("age")
    if age is not None and age > OLD_CAR_AGE:
        score = max(0.0, score - OLD_CAR_PENALTY)
        reasons.append(f"Возраст {int(age)} лет — поправка −{OLD_CAR_PENALTY:.0f} балла за износ и коррозию")

    return round(score, 1), reasons
