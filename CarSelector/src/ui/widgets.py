"""Переиспользуемые элементы интерфейса: карточки, KPI, диаграммы, плашки оценок.

Все цвета берутся из ui/theme.py — здесь их нет, чтобы тему можно было менять
в одном месте.
"""

from __future__ import annotations

import flet as ft
import flet_charts as fc

import dashboard as dash
from ui import theme as t

# Палитра диаграмм (проверенные названия цветов Flet 1.0)
PALETTE = [
    ft.Colors.BLUE_700, ft.Colors.TEAL_400, ft.Colors.AMBER_400, ft.Colors.PURPLE_400,
    ft.Colors.GREEN_400, ft.Colors.PINK_400, ft.Colors.INDIGO_400, ft.Colors.ORANGE_400,
    ft.Colors.CYAN_400, ft.Colors.LIME_400, ft.Colors.BROWN_400, ft.Colors.RED_400,
]


def color_at(index: int) -> str:
    return PALETTE[index % len(PALETTE)]


def score_color(score: float) -> str:
    if score >= 80:
        return ft.Colors.GREEN_400
    if score >= 60:
        return ft.Colors.AMBER_400
    return ft.Colors.RED_400


def short_title(title: str) -> str:
    """«Агент "Бюджет"» → «Бюджет»."""
    if "«" in title and "»" in title:
        return title[title.index("«") + 1:title.index("»")]
    return title


def on_red(text: str, size: int = 13, dim: bool = False, bold: bool = False) -> ft.Control:
    return ft.Text(
        text,
        size=size,
        color=t.ON_RED_DIM if dim else t.ON_RED,
        weight=ft.FontWeight.BOLD if bold else ft.FontWeight.NORMAL,
    )


def paper(content: ft.Control, padding: int = 8) -> ft.Control:
    """Белая «бумага» внутри красной панели — для таблиц и мелкого текста."""
    return ft.Container(
        content=content,
        padding=padding,
        bgcolor=t.SURFACE,
        border_radius=10,
        expand=True,
    )


def number(text: str, size: int = t.CARD_NUMBER_SIZE, on_surface: bool = True,
           color: str | None = None) -> ft.Text:
    """Цифры делаем крупными и жирными — чтобы читались издалека."""
    return ft.Text(
        str(text),
        size=size,
        weight=ft.FontWeight.BOLD,
        color=color or (t.NUMBER_ON_SURFACE if on_surface else t.NUMBER_ON_RED),
    )


def kpi_card(label: str, value: str, hint: str = "") -> ft.Control:
    return ft.Container(
        content=ft.Column(
            [
                ft.Text(label, size=t.LABEL_SIZE, color=t.ON_RED_DIM),
                number(value, t.KPI_NUMBER_SIZE, on_surface=False),
                ft.Text(hint, size=t.SMALL_LABEL_SIZE, color=t.ON_RED_DIM),
            ],
            spacing=2,
        ),
        padding=ft.Padding.symmetric(vertical=14, horizontal=18),
        bgcolor=t.PANEL,
        border=t.BORDER,
        border_radius=10,
        expand=True,
    )


def kpi_row(kpis: list[dict]) -> ft.Control:
    return ft.Row([kpi_card(**kpi) for kpi in kpis], spacing=12)


def panel(title: str, content: ft.Control, subtitle: str = "", icon=None) -> ft.Control:
    """Красная карточка-панель с заголовком."""
    header: list[ft.Control] = []
    if icon is not None:
        header.append(ft.Icon(icon, size=18, color=t.ACCENT))
    header.append(ft.Text(title, size=16, weight=ft.FontWeight.BOLD, color=t.ON_RED))
    block: list[ft.Control] = [ft.Row(header, spacing=8)]
    if subtitle:
        block.append(ft.Text(subtitle, size=12, color=t.ON_RED_DIM))
    block.append(ft.Container(content=content, padding=ft.Padding.only(top=8)))
    return ft.Container(
        content=ft.Column(block, spacing=4),
        padding=16,
        bgcolor=t.PANEL,
        border=t.BORDER,
        border_radius=10,
        expand=True,
    )


def badge(text: str, color: str = t.PANEL_DEEP, bgcolor: str = t.ACCENT) -> ft.Control:
    return ft.Container(
        content=ft.Text(text, size=11, color=color, weight=ft.FontWeight.BOLD),
        padding=ft.Padding.symmetric(vertical=4, horizontal=10),
        bgcolor=bgcolor,
        border_radius=20,
    )


# --------------------------------------------------------------------------
# Диаграммы (flet-charts) — рисуются на белой «бумаге»
# --------------------------------------------------------------------------

def pie_chart(items: list[dict], label_key: str = "brand") -> ft.Control:
    """Круговая диаграмма.

    У PieChart, в отличие от остальных диаграмм, нет своего фона, поэтому кладём
    её на белую «бумагу» — иначе подписи теряются на красном.
    """
    sections = [
        fc.PieChartSection(
            value=item["count"],
            title=f"{item[label_key]} — {item['count']}",
            color=color_at(index),
            radius=72,
        )
        for index, item in enumerate(items)
    ]
    return paper(
        fc.PieChart(
            sections=sections,
            sections_space=2,
            center_space_radius=34,
            height=t.CHART_HEIGHT,
            expand=True,
        ),
        padding=4,
    )


def bar_chart(items: list[dict], label_key: str, value_key: str, formatter=None) -> ft.Control:
    formatter = formatter or (lambda value: f"{value:,.0f}")
    groups = [
        fc.BarChartGroup(
            x=index,
            rods=[
                fc.BarChartRod(
                    from_y=0,
                    to_y=item[value_key],
                    width=26,
                    color=color_at(index),
                    border_radius=4,
                    tooltip=f"{item[label_key]}: {formatter(item[value_key])}",
                )
            ],
        )
        for index, item in enumerate(items)
    ]
    bottom = fc.ChartAxis(
        labels=[fc.ChartAxisLabel(value=index, label=str(item[label_key])) for index, item in enumerate(items)],
        label_size=11,
        show_min=False,
        show_max=False,
    )
    return fc.BarChart(
        groups=groups,
        bottom_axis=bottom,
        group_spacing=14,
        bgcolor=t.SURFACE,
        height=t.CHART_HEIGHT,
        expand=True,
    )


def scatter_chart(points: list[dict]) -> ft.Control:
    spots = [
        fc.ScatterChartSpot(
            x=point["mileage"],
            y=point["price"],
            radius=5,
            color=color_at(index),
            tooltip=f"{point['label']}: {dash.format_car_price(point['price'])}, {dash.format_mileage(point['mileage'])}",
        )
        for index, point in enumerate(points)
    ]
    return fc.ScatterChart(
        spots=spots,
        bgcolor=t.SURFACE,
        height=t.CHART_HEIGHT,
        expand=True,
        tooltip=fc.ScatterChartTooltip(),
    )


def line_chart(points: list[dict]) -> ft.Control:
    data = [
        fc.LineChartData(
            points=[fc.LineChartDataPoint(x=point["year"], y=point["avg_price"]) for point in points],
            color=ft.Colors.RED_700,
            curved=True,
            stroke_width=3,
        )
    ]
    bottom = fc.ChartAxis(
        labels=[fc.ChartAxisLabel(value=point["year"], label=str(point["year"])) for point in points],
        label_size=11,
    )
    return fc.LineChart(
        data_series=data,
        bottom_axis=bottom,
        bgcolor=t.SURFACE,
        height=t.CHART_HEIGHT,
        expand=True,
    )


def placeholder(message: str) -> ft.Control:
    return ft.Container(
        content=ft.Text(message, size=13, color=t.ON_RED_DIM),
        padding=ft.Padding.symmetric(vertical=30, horizontal=12),
        alignment=ft.Alignment.CENTER,
        expand=True,
    )


# --------------------------------------------------------------------------
# Карточка рекомендации
# --------------------------------------------------------------------------

def _agent_score_block(score) -> ft.Control:
    return ft.Column(
        [
            ft.Text(short_title(score.title), size=t.LABEL_SIZE, color=t.MUTED_ON_SURFACE, width=150),
            number(f"{score.score:.0f}", t.SCORE_NUMBER_SIZE),
            ft.ProgressBar(
                value=max(0.0, min(1.0, score.score / 100)),
                color=score_color(score.score),
                bgcolor=ft.Colors.GREY_300,
                bar_height=8,
                width=150,
            ),
        ],
        spacing=4,
    )


def _spec_block(label: str, value) -> ft.Control:
    """Показатель автомобиля: цифры внутри — крупные и яркие."""
    if t.looks_numeric(str(value)):
        content = number(value, t.CARD_NUMBER_SIZE)
    else:
        content = ft.Text(str(value), size=t.BODY_SIZE, color=t.ON_SURFACE, weight=ft.FontWeight.BOLD)
    return ft.Column(
        [
            ft.Text(label, size=t.SMALL_LABEL_SIZE, color=t.MUTED_ON_SURFACE),
            content,
        ],
        spacing=2,
    )


def _price_block(value) -> ft.Control:
    """Цена — самое заметное число в карточке: на яркой подложке."""
    return ft.Container(
        content=ft.Column(
            [
                ft.Text("Цена", size=t.SMALL_LABEL_SIZE, color=t.PANEL_DEEP),
                number(value, t.BIG_NUMBER_SIZE, color=t.PANEL_DEEP),
            ],
            spacing=0,
        ),
        padding=ft.Padding.symmetric(vertical=6, horizontal=16),
        bgcolor=t.ACCENT,
        border_radius=10,
    )


def car_card(rec) -> ft.Control:
    """Карточка одного рекомендованного автомобиля с оценками агентов."""
    car = rec.car
    title = f"{car.get('brand', '')} {car.get('model', '')}".strip()
    year = car.get("year")

    head = ft.Row(
        [
            ft.Container(
                content=ft.Text(f"№ {rec.rank}", size=20, weight=ft.FontWeight.BOLD, color=t.ON_RED),
                bgcolor=t.PANEL_DEEP,
                border_radius=10,
                padding=ft.Padding.symmetric(vertical=8, horizontal=14),
            ),
            ft.Text(title or "Без названия", size=20, weight=ft.FontWeight.BOLD, color=t.ON_SURFACE, expand=True),
            ft.Container(
                content=ft.Text(f"{rec.total:.0f} / 100", size=t.BIG_NUMBER_SIZE, weight=ft.FontWeight.BOLD,
                                color=t.PANEL_DEEP),
                bgcolor=score_color(rec.total),
                border_radius=10,
                padding=ft.Padding.symmetric(vertical=8, horizontal=16),
            ),
        ],
        spacing=14,
        vertical_alignment=ft.CrossAxisAlignment.CENTER,
    )

    year = car.get("year")
    spec_row = ft.Row(
        [
            _price_block(dash.format_car_price(car.get("price"))),
            _spec_block("Пробег", dash.format_mileage(car.get("mileage"))),
            _spec_block("Год выпуска", str(int(year)) if year is not None and year == year else "—"),
            _spec_block("Топливо", str(car.get("fuel") or "—")),
            _spec_block("КПП", str(car.get("transmission") or "—")),
            _spec_block("Кузов", str(car.get("body") or "—")),
        ],
        spacing=18,
        wrap=True,
        vertical_alignment=ft.CrossAxisAlignment.CENTER,
    )

    reasons = ft.Column(
        [
            ft.Row(
                [
                    ft.Icon(ft.Icons.CHECK_CIRCLE, size=15, color=ft.Colors.RED_700),
                    ft.Text(reason, size=t.LABEL_SIZE, color=t.ON_SURFACE, expand=True),
                ],
                spacing=6,
            )
            for reason in rec.reasons
        ],
        spacing=4,
    )

    return ft.Container(
        content=ft.Column(
            [
                head,
                spec_row,
                ft.Divider(height=1, color=ft.Colors.RED_300),
                ft.Row([_agent_score_block(score) for score in rec.scores], spacing=16, wrap=True),
                ft.Divider(height=1, color=ft.Colors.RED_300),
                reasons,
            ],
            spacing=10,
        ),
        padding=16,
        bgcolor=t.SURFACE,
        border=t.BORDER,
        border_radius=10,
    )
