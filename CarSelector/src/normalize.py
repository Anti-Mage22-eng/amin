"""Нормализация «грязных» данных из файла: числа, годы, топливо, КПП, кузов.

Файлы приходят из Excel и 1С, поэтому цена может быть «1 350 000 ₽», пробег —
«132 тыс. км», а коробка — «автомат» вместо «АКПП». Здесь всё приводится к одному
каноническому виду, и только потом попадает в анализ.
"""

from __future__ import annotations

import re
from difflib import SequenceMatcher

# --------------------------------------------------------------------------
# Текст и числа
# --------------------------------------------------------------------------

_EMPTY = {"", "-", "--", "—", "н/д", "нд", "нет", "nan", "none", "null", "?"}


def clean_text(value) -> str:
    """Приводит значение к строке без лишних пробелов и невидимых символов."""
    if value is None:
        return ""
    if isinstance(value, float) and value != value:  # NaN без импорта pandas
        return ""
    text = str(value)
    text = text.replace("\u00a0", " ").replace("\u2009", " ").replace("\t", " ")
    return re.sub(r"\s+", " ", text).strip()


def parse_number(value) -> float | None:
    """«1 350 000 ₽» → 1350000.0, «1,6» → 1.6, «132 тыс. км» → 132000.0.

    Возвращает None, если число выделить нельзя (лучше честный пропуск, чем 0).
    """
    if isinstance(value, bool):
        return None
    if isinstance(value, (int, float)):
        if value != value or value in (float("inf"), float("-inf")):
            return None
        return float(value)

    text = clean_text(value).lower()
    if text in _EMPTY:
        return None

    multiplier = 1.0
    if "тыс" in text:
        multiplier = 1_000.0
    elif "млн" in text:
        multiplier = 1_000_000.0

    # оставляем только цифры и разделители
    digits = re.sub(r"[^0-9,.\-]", "", text)
    if not digits or not any(ch.isdigit() for ch in digits):
        return None

    has_comma, has_dot = "," in digits, "." in digits
    if has_comma and has_dot:
        if digits.rfind(",") > digits.rfind("."):   # 1.234,56 — европейский формат
            digits = digits.replace(".", "").replace(",", ".")
        else:                                        # 1,234.56 — англо-формат
            digits = digits.replace(",", "")
    elif has_comma:
        head, _, tail = digits.rpartition(",")
        # «1,350» — это тысячный разделитель, «1,6» — десятичный
        digits = head + tail if len(tail) == 3 else head + "." + tail
    elif has_dot and digits.count(".") == 1:
        head, _, tail = digits.rpartition(".")
        if len(tail) == 3 and len(head) <= 3 and head != "":
            digits = head + tail  # «1.350» → 1350
    elif digits.count(".") > 1:
        digits = digits.replace(".", "")

    try:
        return float(digits) * multiplier
    except ValueError:
        return None


def parse_int(value) -> int | None:
    number = parse_number(value)
    if number is None:
        return None
    return int(round(number))


# --------------------------------------------------------------------------
# Словари синонимов
# --------------------------------------------------------------------------

FUEL_SYNONYMS: dict[str, tuple[str, ...]] = {
    "Бензин": ("бензин", "бенз", "petrol", "gasoline", "аи-92", "аи-95", "аи92", "аи95", "аи 95"),
    "Дизель": ("дизель", "диз", "diesel", "tdi", "дт", "солярка"),
    "Гибрид": ("гибрид", "hybrid", "hev", "phev"),
    "Электро": ("электро", "электр", "electric", "ev", "electron"),
    "Газ": ("газ", "lpg", "метан", "пропан"),
}

TRANSMISSION_SYNONYMS: dict[str, tuple[str, ...]] = {
    "МКПП": ("мкпп", "механика", "механическая", "manual", "mt", "мех"),
    "АКПП": ("акпп", "автомат", "автоматическая", "auto", "at", "гидроавтомат"),
    "Вариатор": ("вариатор", "cvt"),
    "Робот": ("робот", "роботизированная", "dsg", "dct", "amt", "ркпп"),
}

BODY_SYNONYMS: dict[str, tuple[str, ...]] = {
    "Седан": ("седан", "sedan"),
    "Хэтчбек": ("хэтчбек", "хетчбек", "hatchback", "хэтч"),
    "Универсал": ("универсал", "wagon", "estate"),
    "Кроссовер": ("кроссовер", "crossover", "suv", "паркетник"),
    "Внедорожник": ("внедорожник", "джип", "jeep", "4x4", "рамный"),
    "Купе": ("купе", "coupe", "кабриолет", "convertible"),
    "Минивэн": ("минивэн", "минивен", "minivan", "van", "микроавтобус"),
}

BRAND_ALIASES: dict[str, str] = {
    "ваз": "lada", "лада": "lada", "lada": "lada",
    "хендай": "hyundai", "хёндэ": "hyundai", "хендэ": "hyundai", "солярис": "hyundai",
    "киа": "kia", "тойота": "toyota", "фольксваген": "volkswagen", "vw": "volkswagen",
    "шкода": "skoda", "ниссан": "nissan", "мазда": "mazda", "мицубиси": "mitsubishi",
    "рено": "renault", "форд": "ford", "шевроле": "chevrolet", "бмв": "bmw",
    "мерседес": "mercedes", "мерседес-бенц": "mercedes", "ауди": "audi",
    "хавал": "haval", "чери": "chery", "джили": "geely", "эксид": "exeed",
    "хонда": "honda", "субару": "subaru", "лексус": "lexus", "вольво": "volvo",
    "опель": "opel", "пежо": "peugeot", "ситроен": "citroen", "дэу": "daewoo",
    "уаз": "uaz", "газ": "gaz", "москвич": "moskvich", "джип": "jeep",
    "лендровер": "landrover", "порше": "porsche", "инфинити": "infiniti",
    "сеат": "seat", "лифан": "lifan", "дацун": "datsun", "дженсис": "genesis",
    "хендэ": "hyundai", "белджи": "belgee", "омода": "omoda", "джитур": "jetour",
}


def _match_synonym(value, table: dict[str, tuple[str, ...]], default: str = "") -> str:
    """Ищет каноническое значение по словарю синонимов (точное, затем по вхождению)."""
    text = clean_text(value).lower()
    if not text:
        return default
    if text in _EMPTY:
        return default
    for canonical, synonyms in table.items():
        if text == canonical.lower():
            return canonical
    for canonical, synonyms in table.items():
        for synonym in synonyms:
            if synonym in text:
                return canonical
    return default


def normalize_fuel(value) -> str:
    return _match_synonym(value, FUEL_SYNONYMS, "Бензин")


def normalize_transmission(value) -> str:
    return _match_synonym(value, TRANSMISSION_SYNONYMS, "Не указано")


def normalize_body(value) -> str:
    return _match_synonym(value, BODY_SYNONYMS, clean_text(value))


def brand_key(value) -> str:
    """Ключ марки для группировки: «ЛАДА (ВАЗ)» и «Lada» → lada."""
    text = clean_text(value).lower().replace("(", " ").replace(")", " ")
    text = re.sub(r"[^a-zа-яё0-9\- ]", "", text)
    first = text.split(" ")[0] if text.split(" ") else text
    if first in BRAND_ALIASES:
        return BRAND_ALIASES[first]
    return first


def normalize_year(value) -> int | None:
    """«2019», «2019 г.», «19» → 2019. Мусор и выдуманные годы — None."""
    year = parse_int(value)
    if year is None:
        return None
    if 1950 <= year <= 2100:
        return year
    if 0 <= year < 100:            # двузначный год: 19 → 2019, 95 → 1995
        return 2000 + year if year < 30 else 1900 + year
    return None


# --------------------------------------------------------------------------
# Определение колонок файла
# --------------------------------------------------------------------------

COLUMN_ALIASES: dict[str, tuple[str, ...]] = {
    "brand": ("марка", "марка авто", "производитель", "бренд", "brand", "make", "автомобиль"),
    "model": ("модель", "модель авто", "model"),
    "price": ("цена", "стоимость", "цена руб", "стоимость руб", "price", "price rub", "цена автомобиля"),
    "mileage": ("пробег", "пробег км", "пробег автомобиля", "mileage"),
    "year": ("год", "год выпуска", "год производства", "year", "release year"),
    "fuel": ("топливо", "тип топлива", "вид топлива", "fuel", "тип двигателя"),
    "transmission": ("кпп", "коробка", "коробка передач", "трансмиссия", "transmission", "кп"),
    "body": ("кузов", "тип кузова", "body"),
    "engine_volume": ("объем", "объём", "объем двигателя", "объём двигателя", "engine", "engine volume", "литраж"),
}

REQUIRED_COLUMNS = ("brand", "price", "mileage")
COLUMN_TITLES = {
    "brand": "Марка", "model": "Модель", "price": "Цена", "mileage": "Пробег",
    "year": "Год выпуска", "fuel": "Топливо", "transmission": "КПП",
    "body": "Кузов", "engine_volume": "Объём двигателя",
}


class DataError(Exception):
    """Ошибка в данных или структуре файла — показывается пользователю как есть."""


def _key(header: str) -> str:
    return re.sub(r"[^a-zа-яё0-9]+", "", clean_text(header).lower())


def detect_columns(df) -> dict[str, str]:
    """Сопоставляет колонки файла с нашими полями.

    Три прохода — от строгого к мягкому, чтобы точное имя всегда побеждало
    догадку: сначала точные совпадения по ВСЕМ полям, затем вхождение подстроки,
    и только потом похожесть строк. Без разделения на проходы колонка
    «Объём двигателя» перехватывалась полем «топливо» по слову «двигатель».
    """
    headers = {_key(col): col for col in df.columns}
    mapping: dict[str, str] = {}
    used: set[str] = set()

    def find_exact(keys: list[str]) -> str | None:
        for k in keys:
            if k in headers and headers[k] not in used:
                return headers[k]
        return None

    def find_substring(keys: list[str]) -> str | None:
        for k, original in headers.items():
            if original in used:
                continue
            if any(key and (key in k or k in key) for key in keys):
                return original
        return None

    def find_fuzzy(keys: list[str]) -> str | None:
        best, best_ratio = None, 0.0
        for k, original in headers.items():
            if original in used:
                continue
            ratio = max((SequenceMatcher(None, key, k).ratio() for key in keys), default=0.0)
            if ratio > best_ratio:
                best, best_ratio = original, ratio
        return best if best_ratio >= 0.72 else None

    alias_keys = {canon: [_key(a) for a in aliases] for canon, aliases in COLUMN_ALIASES.items()}
    for finder in (find_exact, find_substring, find_fuzzy):
        for canon, keys in alias_keys.items():
            if canon in mapping:
                continue
            found = finder(keys)
            if found is not None:
                mapping[canon] = found
                used.add(found)
    return mapping


def missing_required(mapping: dict[str, str]) -> list[str]:
    return [COLUMN_TITLES[c] for c in REQUIRED_COLUMNS if c not in mapping]
