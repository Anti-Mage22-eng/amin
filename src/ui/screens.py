"""Экраны приложения: «Данные», «Подбор», «Дашборд», «Агенты»."""

from __future__ import annotations

import flet as ft

import dashboard as dash
from ui import theme as t
from ui import widgets as w

PREVIEW_FIELDS = [
    ("car_id", "№"),
    ("brand", "Марка"),
    ("model", "Модель"),
    ("price", "Цена, ₽"),
    ("mileage", "Пробег, км"),
    ("year", "Год"),
    ("fuel", "Топливо"),
    ("transmission", "КПП"),
    ("body", "Кузов"),
]

HEADER = dict(size=24, weight=ft.FontWeight.BOLD, color=t.ON_RED)
INTRO = dict(size=14, color=t.ON_RED_DIM)


def _title(text: str, intro: str = "") -> list[ft.Control]:
    blocks: list[ft.Control] = [ft.Text(text, **HEADER)]
    if intro:
        blocks.append(ft.Text(intro, **INTRO))
    return blocks


def _table(headers: list[str], rows: list[list[str]]) -> ft.DataTable:
    return ft.DataTable(
        columns=[
            ft.DataColumn(
                label=ft.Text(header, size=t.LABEL_SIZE, weight=ft.FontWeight.BOLD, color=t.ON_SURFACE)
            )
            for header in headers
        ],
        rows=[
            ft.DataRow(
                cells=[
                    ft.DataCell(
                        w.number(cell, t.TABLE_NUMBER_SIZE) if t.looks_numeric(cell)
                        else ft.Text(cell, size=t.LABEL_SIZE, color=t.ON_SURFACE)
                    )
                    for cell in row
                ]
            )
            for row in rows
        ],
        column_spacing=20,
        heading_row_height=42,
        data_row_min_height=38,
        data_row_max_height=52,
    )


def _num(value) -> str:
    return f"{value:,}".replace(",", " ") if isinstance(value, (int, float)) else str(value)


def _money_row(stats: dict) -> str:
    return " / ".join(dash.format_car_price(stats[key]) for key in ("min", "median", "mean", "max"))


def _km_row(stats: dict) -> str:
    return " / ".join(dash.format_mileage(stats[key]) for key in ("min", "median", "mean", "max"))


# --------------------------------------------------------------------------
# Экран «Данные»
# --------------------------------------------------------------------------

def data_screen(app) -> ft.Control:
    blocks: list[ft.Control] = _title(
        "Данные",
        "Загрузите CSV или Excel с автомобилями: марка, цена, пробег и, если есть, модель, год, "
        "топливо, КПП, кузов. Колонки распознаются автоматически, данные проверяются через pandas.",
    )
    blocks.append(
        ft.Row(
            [
                ft.FilledButton(
                    "Загрузить файл (CSV / Excel)",
                    icon=ft.Icons.UPLOAD_FILE,
                    bgcolor=t.ACCENT,
                    color=t.PANEL_DEEP,
                    on_click=app.pick_file,
                ),
                ft.OutlinedButton(
                    "Взять демо-набор",
                    icon=ft.Icons.TABLE_CHART,
                    style=t.OUTLINE_BUTTON_STYLE,
                    on_click=app.load_demo,
                ),
                ft.OutlinedButton(
                    "Как готовится файл",
                    icon=ft.Icons.INFO_OUTLINE,
                    style=t.OUTLINE_BUTTON_STYLE,
                    on_click=app.show_format_hint,
                ),
            ],
            spacing=12,
            wrap=True,
        )
    )

    if app.message:
        blocks.append(
            w.panel("Сообщение", ft.Text(app.message, size=13, color=t.ON_RED), icon=ft.Icons.INFO_OUTLINE)
        )

    if app.load_result is None:
        blocks.append(
            w.panel(
                "Файл не загружен",
                w.placeholder("Выберите файл или возьмите демо-набор из папки data/cars.csv"),
                icon=ft.Icons.FOLDER_OPEN,
            )
        )
        return ft.Column(blocks, spacing=14, scroll=ft.ScrollMode.AUTO, expand=True)

    report = app.load_result.report
    blocks.append(w.kpi_row(dash.dataset_kpis(app.df)))

    check_rows = [
        ["Прочитано строк в файле", _num(report["rows_read"])],
        ["Корректных записей после проверки", _num(report["rows_valid"])],
        ["Отброшено: нет цены или пробега", _num(report["dropped_bad_values"])],
        ["Удалено дубликатов", _num(report["duplicates_removed"])],
        ["Отброшено как выбросы (цена ≤ 0, пробег < 0)", _num(report["anomalies_removed"])],
        ["Цена: мин / медиана / среднее / макс", _money_row(report["price"])],
        ["Пробег: мин / медиана / среднее / макс", _km_row(report["mileage"])],
        ["Годы выпуска", f"{report['year']['min']} – {report['year']['max']}"],
        ["Уникальных марок", _num(report["brands"])],
        ["Топ марок", ", ".join(f"{brand} ({count})" for brand, count in report["brands_top"][:5])],
        ["Источник", report["source"]],
    ]
    blocks.append(
        w.panel(
            "Отчёт о проверке данных (pandas)",
            w.paper(_table(["Показатель", "Значение"], check_rows), padding=4),
            subtitle="Что именно сделал модуль проверки: пропуски, дубликаты, выбросы, итоговые диапазоны",
            icon=ft.Icons.CHECK_CIRCLE,
        )
    )

    column_rows = [[title, original] for title, original in report["columns_found"].items()]
    blocks.append(
        w.panel(
            "Распознанные колонки файла",
            w.paper(_table(["Поле программы", "Колонка в файле"], column_rows), padding=4),
            subtitle="Сопоставление выполняется по названиям и синонимам — переименовывать файл не нужно",
            icon=ft.Icons.SEARCH,
        )
    )

    preview_rows = [
        [
            str(int(row["car_id"])),
            str(row["brand"]),
            str(row["model"]),
            dash.format_car_price(row["price"]),
            dash.format_mileage(row["mileage"]),
            str(int(row["year"])) if row["year"] is not None and row["year"] == row["year"] else "—",
            str(row["fuel"]),
            str(row["transmission"]),
            str(row["body"]),
        ]
        for row in app.df.head(12).to_dict("records")
    ]
    blocks.append(
        w.panel(
            "Первые 12 записей после проверки",
            w.paper(_table([title for _, title in PREVIEW_FIELDS], preview_rows), padding=4),
            subtitle="Полный набор используется в подборе и на дашборде",
            icon=ft.Icons.TABLE_CHART,
        )
    )
    return ft.Column(blocks, spacing=14, scroll=ft.ScrollMode.AUTO, expand=True)


# --------------------------------------------------------------------------
# Экран «Подбор»
# --------------------------------------------------------------------------

def select_screen(app) -> ft.Control:
    blocks: list[ft.Control] = _title(
        "Подбор автомобиля",
        "Задайте параметры клиента. Агенты оценивают каждую подходящую машину по 100-балльной "
        "шкале и объясняют, из чего сложилась оценка.",
    )
    blocks.append(
        w.panel(
            "Параметры клиента",
            ft.Column(
                [
                    w.paper(app.filter_form, padding=12),
                    ft.Row(
                        [
                            ft.FilledButton(
                                "Подобрать",
                                icon=ft.Icons.SEARCH,
                                bgcolor=t.ACCENT,
                                color=t.PANEL_DEEP,
                                on_click=app.run_selection,
                            ),
                            ft.OutlinedButton(
                                "Сбросить",
                                icon=ft.Icons.REFRESH,
                                style=t.OUTLINE_BUTTON_STYLE,
                                on_click=app.reset_filters,
                            ),
                        ],
                        spacing=12,
                    ),
                ],
                spacing=14,
            ),
            icon=ft.Icons.TUNE,
        )
    )

    if app.result is None:
        blocks.append(
            w.panel(
                "Результат появится здесь",
                w.placeholder("Нажмите «Подобрать» — покажем лучшие варианты с оценками и объяснениями"),
                icon=ft.Icons.DIRECTIONS_CAR,
            )
        )
        return ft.Column(blocks, spacing=14, scroll=ft.ScrollMode.AUTO, expand=True)

    result = app.result
    blocks.append(w.kpi_row(dash.selection_kpis(result)))

    weights_text = ", ".join(
        f"{w.short_title(agent.title)} × {result.weights.get(agent.id, 0):.2f}"
        for agent in app.selector.scoring_agents
    )
    blocks.append(
        w.panel(
            "Как считали итог",
            ft.Column(
                [
                    ft.Text(f"Запрос: {result.request.describe()}", size=t.LABEL_SIZE, color=t.ON_RED),
                    ft.Text(f"Веса агентов (профиль «{app.priority_title()}»): {weights_text}",
                            size=t.LABEL_SIZE, color=t.ON_RED),
                    ft.Text(
                        f"Прошли фильтр: {result.eligible} из {result.considered}; отклонено: {result.rejected}",
                        size=t.LABEL_SIZE, color=t.ON_RED_DIM,
                    ),
                ],
                spacing=4,
            ),
            icon=ft.Icons.ANALYTICS,
        )
    )

    if not result.recommendations:
        reason_rows = [[reason, _num(count)] for reason, count in result.rejected_reasons]
        blocks.append(
            w.panel(
                "Подходящих вариантов нет",
                ft.Column(
                    [
                        ft.Text("Ослабьте условия: увеличьте бюджет или лимит пробега.",
                                size=t.BODY_SIZE, color=t.ON_RED),
                        w.paper(_table(["Причина отказа", "Машин"], reason_rows), padding=4),
                    ],
                    spacing=10,
                ),
                icon=ft.Icons.INFO_OUTLINE,
            )
        )
        return ft.Column(blocks, spacing=14, scroll=ft.ScrollMode.AUTO, expand=True)

    cards = [w.car_card(rec) for rec in result.recommendations]
    blocks.append(
        w.panel(
            f"Лучшие варианты — топ-{len(cards)}",
            ft.Column(cards, spacing=12),
            subtitle="Отсортировано по итоговой оценке агентов",
            icon=ft.Icons.DIRECTIONS_CAR,
        )
    )
    return ft.Column(blocks, spacing=14, scroll=ft.ScrollMode.AUTO, expand=True)


# --------------------------------------------------------------------------
# Экран «Дашборд»
# --------------------------------------------------------------------------

def dashboard_screen(app) -> ft.Control:
    if app.df is None:
        return ft.Column(
            _title("Дашборд") + [
                w.panel("Нет данных", w.placeholder("Сначала загрузите файл на экране «Данные»"),
                        icon=ft.Icons.BAR_CHART)
            ],
            spacing=14, scroll=ft.ScrollMode.AUTO, expand=True,
        )

    blocks: list[ft.Control] = _title(
        "Дашборд",
        "Статистика по базе и по результату подбора — все показатели считает pandas.",
    )
    blocks.append(w.kpi_row(dash.dataset_kpis(app.df)))

    if app.result is not None:
        blocks.append(w.kpi_row(dash.selection_kpis(app.result)))

    brand_shares = dash.brand_shares(app.df, top_n=6)
    prices = dash.price_by_brand(app.df, top_n=8)
    points = dash.price_mileage_points(app.df)
    years = dash.avg_price_by_year(app.df)
    fuel_shares = dash.category_shares(app.df, "fuel")

    blocks.append(
        ft.Row(
            [
                w.panel("Доли марок в базе", w.pie_chart(brand_shares, "brand"), icon=ft.Icons.PIE_CHART),
                w.panel("Средняя цена по маркам",
                        w.bar_chart(prices, "brand", "avg_price", dash.format_car_price),
                        icon=ft.Icons.BAR_CHART),
            ],
            spacing=14,
        )
    )
    blocks.append(
        ft.Row(
            [
                w.panel("Топливо в базе", w.pie_chart(fuel_shares, "label"), icon=ft.Icons.LOCAL_GAS_STATION),
                w.panel("Средняя цена по годам выпуска", w.line_chart(years), icon=ft.Icons.ANALYTICS),
            ],
            spacing=14,
        )
    )

    blocks.append(
        w.panel(
            "Цена и пробег: где находятся выгодные варианты",
            w.scatter_chart(points),
            subtitle="Каждая точка — автомобиль. Левый низ — недорогие машины с малым пробегом",
            icon=ft.Icons.SHOW_CHART,
        )
    )

    if app.result is not None and app.result.recommendations:
        top_models = dash.top_models_by_score(app.result.recommendations, top_n=5)
        blocks.append(
            w.panel(
                "Топ-5 подобранных моделей по оценке агентов",
                w.bar_chart(top_models, "model", "avg_score", lambda value: f"{value:.0f}/100"),
                subtitle="Данные из текущего подбора — смените параметры на экране «Подбор»",
                icon=ft.Icons.SMART_TOY,
            )
        )
    return ft.Column(blocks, spacing=14, scroll=ft.ScrollMode.AUTO, expand=True)


# --------------------------------------------------------------------------
# Экран «Агенты»
# --------------------------------------------------------------------------

def agents_screen(app) -> ft.Control:
    blocks: list[ft.Control] = _title(
        "ИИ-агенты и скиллы",
        "Каждый агент — отдельный эксперт с одним скиллом. Паспорта агентов лежат в папке .agent, "
        "код скиллов — в .skill. Координатор «Эксперт» складывает оценки в итоговый рейтинг.",
    )

    for agent in app.selector.agents:
        if agent.kind == "coordinator":
            kind_badge = w.badge("координатор", t.PANEL_DEEP, t.ACCENT)
        elif agent.kind == "filter":
            kind_badge = w.badge("фильтр", t.ON_RED, ft.Colors.RED_900)
        else:
            kind_badge = w.badge(f"вес {agent.weight:.2f}")

        rows: list[ft.Control] = [
            ft.Row(
                [
                    ft.Text(agent.title, size=16, weight=ft.FontWeight.BOLD, color=t.ON_RED, expand=True),
                    kind_badge,
                ],
                spacing=10,
            ),
            ft.Text(agent.role, size=13, color=t.ON_RED),
        ]
        if agent.description:
            rows.append(ft.Text(agent.description, size=12, color=t.ON_RED_DIM))
        rows.append(
            ft.Row(
                [
                    w.badge(
                        f"скилл: {agent.skill}" if agent.skill else "без скилла (агрегация)",
                        t.PANEL_DEEP, ft.Colors.RED_100,
                    ),
                    w.badge(str(agent.extra.get("formula", "")), t.PANEL_DEEP, ft.Colors.RED_100)
                    if agent.extra.get("formula") else ft.Container(),
                ],
                spacing=8,
                wrap=True,
            )
        )
        if agent.skill_dir:
            rows.append(
                ft.Text(
                    f"файлы: {agent.config_path} · {agent.skill_dir / 'SKILL.md'} · {agent.skill_dir / 'skill.py'}",
                    size=10, color=t.ON_RED_DIM, selectable=True,
                )
            )
        blocks.append(w.panel(agent.title, ft.Column(rows, spacing=6), icon=ft.Icons.SMART_TOY))

    profiles = app.selector.priority_profiles()
    profile_rows = []
    for profile in profiles.values():
        weights = profile.get("weights", {})
        profile_rows.append([
            profile.get("title", ""),
            ", ".join(f"{key} × {value:.2f}" for key, value in weights.items()),
            profile.get("hint", ""),
        ])
    blocks.append(
        w.panel(
            "Профили приоритета клиента",
            w.paper(_table(["Профиль", "Веса агентов", "Когда используется"], profile_rows), padding=4),
            subtitle="Координатор подставляет веса автоматически — это и есть «настройка» агентов под клиента",
            icon=ft.Icons.TUNE,
        )
    )
    return ft.Column(blocks, spacing=14, scroll=ft.ScrollMode.AUTO, expand=True)
