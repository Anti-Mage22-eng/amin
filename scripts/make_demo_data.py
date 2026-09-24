"""Генератор демо-данных: создаёт data/cars.csv с «грязными» значениями.

Специально воспроизводит реальные проблемы файлов из Excel и 1С: цена строкой
(«1 350 000 ₽»), пробег в «тыс. км», год с пометкой «г.», пустые строки, дубликаты
и мусор вроде «по договорённости». Так проверяем, что слой проверки данных
действительно работает, а не только на идеальной таблице.

Запуск:  .venv\\Scripts\\python.exe scripts\\make_demo_data.py
"""

from __future__ import annotations

import csv
import random
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "data" / "cars.csv"

random.seed(42)

# (марка, модель, кузов, год_от, год_до, цена_от, цена_до)
CATALOG = [
    ("Toyota", "Camry", "Седан", 2011, 2024, 1_150_000, 3_450_000),
    ("Toyota", "Corolla", "Седан", 2012, 2021, 850_000, 2_050_000),
    ("Toyota", "RAV4", "Кроссовер", 2013, 2024, 1_450_000, 3_600_000),
    ("Kia", "Rio", "Седан", 2012, 2022, 520_000, 1_620_000),
    ("Kia", "Sportage", "Кроссовер", 2013, 2023, 1_150_000, 3_200_000),
    ("Kia", "K5", "Седан", 2016, 2023, 1_300_000, 2_750_000),
    ("Hyundai", "Solaris", "Седан", 2012, 2022, 560_000, 1_750_000),
    ("Hyundai", "Creta", "Кроссовер", 2016, 2024, 950_000, 2_350_000),
    ("Hyundai", "Tucson", "Кроссовер", 2014, 2023, 1_300_000, 3_100_000),
    ("Lada", "Vesta", "Седан", 2016, 2024, 560_000, 1_750_000),
    ("Lada", "Granta", "Седан", 2013, 2024, 380_000, 1_150_000),
    ("Lada", "Niva Legend", "Внедорожник", 2010, 2023, 350_000, 1_050_000),
    ("Volkswagen", "Polo", "Седан", 2012, 2021, 620_000, 1_750_000),
    ("Volkswagen", "Tiguan", "Кроссовер", 2012, 2022, 1_250_000, 3_500_000),
    ("Skoda", "Octavia", "Седан", 2012, 2022, 750_000, 2_450_000),
    ("Skoda", "Karoq", "Кроссовер", 2018, 2022, 1_250_000, 2_700_000),
    ("Nissan", "Qashqai", "Кроссовер", 2012, 2022, 950_000, 2_400_000),
    ("Mazda", "CX-5", "Кроссовер", 2013, 2023, 1_350_000, 3_300_000),
    ("Mazda", "6", "Седан", 2011, 2021, 820_000, 2_250_000),
    ("BMW", "3 series", "Седан", 2011, 2021, 950_000, 3_600_000),
    ("Mercedes", "E-class", "Седан", 2011, 2021, 1_150_000, 3_800_000),
    ("Audi", "A4", "Седан", 2011, 2021, 950_000, 3_200_000),
    ("Renault", "Logan", "Седан", 2012, 2022, 420_000, 1_150_000),
    ("Renault", "Duster", "Кроссовер", 2012, 2022, 720_000, 1_950_000),
    ("Haval", "Jolion", "Кроссовер", 2020, 2024, 1_350_000, 2_250_000),
    ("Chery", "Tiggo 4", "Кроссовер", 2019, 2024, 1_250_000, 2_150_000),
    ("Geely", "Coolray", "Кроссовер", 2019, 2024, 1_350_000, 2_250_000),
    ("Mitsubishi", "Outlander", "Кроссовер", 2012, 2021, 1_050_000, 2_800_000),
]

HEADER = ["Марка", "Модель", "Цена, руб", "Пробег, км", "Год выпуска", "Топливо", "КПП", "Кузов", "Объём двигателя"]
CURRENT_YEAR = 2026


def _price_text(value: int) -> str:
    variant = random.random()
    grouped = f"{value:,}".replace(",", " ")
    if variant < 0.45:
        return f"{grouped} ₽"
    if variant < 0.75:
        return str(value)
    if variant < 0.9:
        return f"{grouped} руб."
    return grouped


def _mileage_text(value: int) -> str:
    variant = random.random()
    if variant < 0.4:
        return f"{value:,}".replace(",", " ") + " км"
    if variant < 0.75:
        return str(value)
    return f"{round(value / 1000)} тыс. км"


def _year_text(value: int) -> str:
    variant = random.random()
    if variant < 0.7:
        return str(value)
    if variant < 0.9:
        return f"{value} г."
    return str(value)[2:]


def make_rows(count: int = 90) -> list[list]:
    rows: list[list] = []
    while len(rows) < count:
        brand, model, body, year_from, year_to, price_from, price_to = random.choice(CATALOG)
        year = random.randint(year_from, min(year_to, CURRENT_YEAR))
        age = max(1, CURRENT_YEAR - year)
        mileage = min(260_000, int(age * random.uniform(7_000, 24_000) / 1000) * 1000)

        year_factor = (year - year_from) / max(1, year_to - year_from)
        wear_factor = min(1.0, mileage / 260_000)
        base = price_from + (price_to - price_from) * (0.6 * year_factor + 0.4 * (1 - wear_factor))
        price = int(base * random.uniform(0.9, 1.12) / 10_000) * 10_000

        fuel = random.choices(
            ["Бензин", "Дизель", "Гибрид", "Электро"], weights=[84, 8, 5, 3]
        )[0]
        if fuel == "Электро":
            engine = "—"
        else:
            engine = f"{random.choice(['1.2', '1.4', '1.6', '1.8', '2.0', '2.5'])}"
            if random.random() < 0.4:
                engine = engine.replace(".", ",")

        transmission = random.choices(
            ["АКПП", "МКПП", "Вариатор", "Робот", "автомат"], weights=[35, 25, 20, 10, 10]
        )[0]

        rows.append([
            brand, model, _price_text(price), _mileage_text(mileage), _year_text(year),
            fuel, transmission, body, engine,
        ])
    return rows


def add_problem_rows(rows: list[list]) -> list[list]:
    """Добавляет строки-проблемы: пустые значения, мусор, дубликаты."""
    dirty = list(rows)
    dirty.append(["Ford", "Focus", "по договорённости", "145 000 км", "2014", "Бензин", "АКПП", "Седан", "1.6"])
    dirty.append(["Nissan", "Almera", "", "180 000 км", "2013", "Бензин", "МКПП", "Седан", "1.6"])
    dirty.append(["Hyundai", "Elantra", "1 250 000 ₽", "", "2018 г.", "Бензин", "АКПП", "Седан", "1.8"])
    dirty.append(["", "", "", "", "", "", "", "", ""])
    dirty.append(["Kia", "Optima", "0", "210 000", "2012", "Бензин", "АКПП", "Седан", "2.0"])
    dirty.append(list(rows[0]))   # дубликат
    dirty.append(list(rows[1]))   # дубликат
    dirty.append(["Lada", "Vesta", "1 320 000 ₽", "54 000 км", "2021", "бензин", "вариатор", "седан", "1.8"])
    return dirty


def main() -> None:
    OUT.parent.mkdir(parents=True, exist_ok=True)
    rows = add_problem_rows(make_rows())
    with OUT.open("w", newline="", encoding="utf-8-sig") as handle:
        writer = csv.writer(handle, delimiter=";")
        writer.writerow(HEADER)
        writer.writerows(rows)
    print(f"Готово: {OUT} — строк данных: {len(rows)}")


if __name__ == "__main__":
    main()
