"""Чтение файла с автомобилями и подготовка чистого набора данных через pandas.

Поддерживаются CSV (любой разделитель, UTF-8/Windows-1251) и Excel (.xlsx/.xls).
После чтения: автоопределение колонок, разбор чисел, удаление пустых строк и
дубликатов, расчёт производных полей (возраст, пробег в год) и отчёт о проверке.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import date
from pathlib import Path

import pandas as pd

from normalize import (
    COLUMN_TITLES,
    DataError,
    brand_key,
    clean_text,
    detect_columns,
    missing_required,
    normalize_body,
    normalize_fuel,
    normalize_transmission,
    normalize_year,
    parse_number,
)

CURRENT_YEAR = date.today().year
CSV_ENCODINGS = ("utf-8-sig", "cp1251", "utf-8")
CSV_SEPARATORS = (";", ",", "\t", "|")


@dataclass
class LoadResult:
    """Результат загрузки: чистые данные + отчёт о проверке (для экрана «Данные»)."""

    df: pd.DataFrame
    source: str
    column_map: dict[str, str] = field(default_factory=dict)
    warnings: list[str] = field(default_factory=list)

    @property
    def report(self) -> dict:
        return self._report

    def __post_init__(self):
        self._report: dict = {}


# --------------------------------------------------------------------------
# Чтение сырого файла
# --------------------------------------------------------------------------

def _sniff_separator(header_line: str) -> str:
    """Определяет разделитель по первой строке файла.

    Автоопределение pandas (sep=None) здесь не подходит: в заголовке «Цена, руб»
    есть запятая, и pandas ошибочно выбирает её как разделитель. Считаем символы
    сами и берём самый частый.
    """
    counts = {sep: header_line.count(sep) for sep in (";", ",", "\t", "|")}
    best = max(counts, key=lambda sep: counts[sep])
    return best if counts[best] > 0 else ","


def _read_csv(path: Path) -> pd.DataFrame:
    errors: list[str] = []
    for encoding in CSV_ENCODINGS:
        try:
            with path.open(encoding=encoding) as handle:
                first_line = handle.readline()
        except UnicodeDecodeError as exc:
            errors.append(f"{encoding}: {exc}")
            continue

        sniffed = _sniff_separator(first_line)
        order = [sniffed] + [sep for sep in (";", ",", "\t", "|") if sep != sniffed]
        for sep in order:
            try:
                df = pd.read_csv(
                    path, sep=sep, engine="python", encoding=encoding,
                    skip_blank_lines=True, dtype=str, keep_default_na=False,
                )
            except (UnicodeDecodeError, pd.errors.ParserError, pd.errors.EmptyDataError) as exc:
                errors.append(f"{encoding} / {sep!r}: {exc}")
                continue
            df = df.dropna(how="all")
            df = df.loc[:, [c for c in df.columns if clean_text(c)]]
            if not df.empty and df.shape[1] >= 2:
                return df
    raise DataError(
        "Не удалось прочитать CSV. Проверьте кодировку (UTF-8 или Windows-1251) "
        "и разделитель — «;» или «,». Детали: " + "; ".join(errors[:3])
    )


def _read_excel(path: Path) -> pd.DataFrame:
    try:
        sheets = pd.read_excel(path, sheet_name=None, dtype=str)
    except ImportError as exc:  # .xls требует xlrd
        raise DataError(
            f"Для чтения старого формата .xls нужен пакет xlrd ({exc}). "
            "Сохраните файл как .xlsx или .csv."
        ) from exc
    except Exception as exc:
        raise DataError(f"Не удалось прочитать Excel-файл: {exc}") from exc

    for name, sheet in sheets.items():
        sheet = sheet.dropna(how="all").loc[:, [c for c in sheet.columns if clean_text(c)]]
        if not sheet.empty and sheet.shape[1] >= 2:
            return sheet
    raise DataError("В файле нет непустых листов с данными.")


def read_table(path: str | Path) -> pd.DataFrame:
    """Читает CSV или Excel в «сырой» DataFrame (всё строками)."""
    path = Path(path)
    if not path.exists():
        raise DataError(f"Файл не найден: {path}")
    suffix = path.suffix.lower()
    if suffix in {".xlsx", ".xlsm", ".xltx"}:
        return _read_excel(path)
    if suffix == ".xls":
        return _read_excel(path)
    if suffix in {".csv", ".txt", ".tsv"}:
        return _read_csv(path)
    raise DataError(f"Формат «{suffix or 'без расширения'}» не поддерживается. Нужен CSV или Excel.")


# --------------------------------------------------------------------------
# Нормализация
# --------------------------------------------------------------------------

def _build_dataframe(raw: pd.DataFrame, mapping: dict[str, str]) -> tuple[pd.DataFrame, dict]:
    """Строит чистый DataFrame из сырого по найденному соответствию колонок."""
    df = pd.DataFrame()
    for canon, source_col in mapping.items():
        df[canon] = raw[source_col]

    stats = {"rows_read": int(len(df))}
    stats["missing_raw"] = {
        COLUMN_TITLES.get(canon, canon): int(df[canon].map(lambda v: clean_text(v) == "").sum())
        for canon in df.columns
    }

    # текстовые поля
    df["brand"] = df["brand"].map(clean_text)
    if "model" in df.columns:
        df["model"] = df["model"].map(clean_text)
    else:
        df["model"] = ""

    # числовые поля
    df["price"] = df["price"].map(parse_number)
    df["mileage"] = df["mileage"].map(parse_number)
    df["year"] = df["year"].map(normalize_year) if "year" in df.columns else pd.NA
    df["engine_volume"] = (
        df["engine_volume"].map(parse_number) if "engine_volume" in df.columns else pd.NA
    )

    # категории
    df["fuel"] = df["fuel"].map(normalize_fuel) if "fuel" in df.columns else "Не указано"
    df["transmission"] = (
        df["transmission"].map(normalize_transmission) if "transmission" in df.columns else "Не указано"
    )
    df["body"] = df["body"].map(normalize_body) if "body" in df.columns else "Не указано"

    stats["missing"] = {
        COLUMN_TITLES.get(col, col): int(df[col].isna().sum())
        for col in ("price", "mileage", "year", "engine_volume")
    }

    # строки без обязательных значений — в отбраковку
    before = len(df)
    required_ok = df["brand"].str.strip().ne("") & df["price"].notna() & df["mileage"].notna()
    df = df[required_ok]
    stats["dropped_bad_values"] = int(before - len(df))

    # полные дубликаты
    before = len(df)
    subset = ["brand", "model", "price", "mileage"] + (["year"] if df["year"].notna().any() else [])
    df = df.drop_duplicates(subset=subset)
    stats["duplicates_removed"] = int(before - len(df))

    # физически невозможные значения
    before = len(df)
    df = df[(df["price"] > 0) & (df["mileage"] >= 0)]
    stats["anomalies_removed"] = int(before - len(df))

    if df.empty:
        raise DataError(
            "После проверки данных не осталось ни одной корректной записи. "
            "Проверьте, что в колонках «Цена» и «Пробег» числа."
        )

    # производные поля
    df = df.reset_index(drop=True)
    df["car_id"] = range(1, len(df) + 1)
    df["brand_key"] = df["brand"].map(brand_key)
    df["age"] = df["year"].map(lambda y: max(0, CURRENT_YEAR - int(y)) if pd.notna(y) else None)
    df["mileage_per_year"] = [
        (row.mileage / row.age) if row.age and row.age > 0 else row.mileage
        for row in df.itertuples()
    ]
    df["mileage_per_year"] = df["mileage_per_year"].round(0)

    return df, stats


def _describe_series(series: pd.Series) -> dict:
    clean = series.dropna()
    if clean.empty:
        return {"min": None, "median": None, "mean": None, "max": None}
    return {
        "min": float(clean.min()),
        "median": float(clean.median()),
        "mean": float(clean.mean()),
        "max": float(clean.max()),
    }


def _build_report(df: pd.DataFrame, stats: dict, source: str, column_map: dict) -> dict:
    top_brands = df["brand"].value_counts().head(8)
    report = {
        "source": source,
        "rows_read": stats["rows_read"],
        "rows_valid": int(len(df)),
        "dropped_bad_values": stats["dropped_bad_values"],
        "duplicates_removed": stats["duplicates_removed"],
        "anomalies_removed": stats["anomalies_removed"],
        "missing_raw": stats["missing_raw"],
        "missing": stats["missing"],
        "price": _describe_series(df["price"]),
        "mileage": _describe_series(df["mileage"]),
        "year": {
            "min": int(df["year"].min()) if df["year"].notna().any() else None,
            "max": int(df["year"].max()) if df["year"].notna().any() else None,
        },
        "brands": int(df["brand"].nunique()),
        "brands_top": [(str(name), int(count)) for name, count in top_brands.items()],
        "fuel": {str(k): int(v) for k, v in df["fuel"].value_counts().items()},
        "transmission": {str(k): int(v) for k, v in df["transmission"].value_counts().items()},
        "body": {str(k): int(v) for k, v in df["body"].value_counts().items()},
        "columns_found": {COLUMN_TITLES.get(k, k): v for k, v in column_map.items()},
    }
    return report


def load_cars(path: str | Path) -> LoadResult:
    """Полный цикл: файл → сырые данные → проверка → чистый DataFrame + отчёт."""
    path = Path(path)
    raw = read_table(path)
    mapping = detect_columns(raw)
    missing = missing_required(mapping)
    if missing:
        found = ", ".join(clean_text(c) for c in raw.columns)
        raise DataError(
            "В файле не найдены обязательные колонки: " + ", ".join(missing)
            + f". Найденные колонки: {found}. Переименуйте колонки или добавьте их."
        )

    df, stats = _build_dataframe(raw, mapping)
    warnings: list[str] = []
    if str(mapping.get("year", "")) and df["year"].isna().all():
        warnings.append("Колонка с годом найдена, но ни один год не распознан.")

    result = LoadResult(df=df, source=str(path), column_map=mapping, warnings=warnings)
    result._report = _build_report(df, stats, str(path), mapping)
    return result
