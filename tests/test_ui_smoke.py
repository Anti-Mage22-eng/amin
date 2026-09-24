"""Проверка интерфейса без запуска окна: все экраны должны собираться.

Flet-контролы создаются и до подключения к странице, поэтому мы можем пройти
по всем экранам с заглушкой приложения и поймать ошибки API до запуска окна.
"""

from __future__ import annotations

import pytest

import flet as ft

from data_loader import load_cars
from orchestrator import ClientRequest, Selector
from paths import DEMO_CSV
from ui import screens

DEFAULT_FILTERS = {
    "budget": "2000000", "mileage": "120000", "year_min": "2016", "year_max": "",
    "brand": "", "fuel": "", "transmission": "", "body": "", "priority": "balanced", "top_n": "10",
}


class StubApp:
    """Заглушка вместо CarSelectorApp: экранам нужны только данные и обработчики."""

    def __init__(self, with_data: bool = True, with_result: bool = True):
        self.message = "Тестовое сообщение"
        self.filters = dict(DEFAULT_FILTERS)
        self.selector = Selector()
        self.filter_form = ft.Column()
        self.load_result = None
        self.df = None
        self.result = None
        if with_data and DEMO_CSV.exists():
            self.load_result = load_cars(DEMO_CSV)
            self.df = self.load_result.df
        if with_result and self.df is not None:
            self.result = self.selector.select(
                self.df, ClientRequest(budget_max=2_000_000, mileage_max=120_000, year_min=2016)
            )

    # обработчики, которые экраны передают в on_click
    def pick_file(self, event=None): ...
    def load_demo(self, event=None): ...
    def show_format_hint(self, event=None): ...
    def reset_filters(self, event=None): ...
    def run_selection(self, event=None): ...

    def priority_title(self) -> str:
        return "Сбалансированный подбор"


BUILDERS = [screens.data_screen, screens.select_screen, screens.dashboard_screen, screens.agents_screen]


@pytest.fixture(scope="module")
def app_with_data():
    if not DEMO_CSV.exists():
        pytest.skip("Демо-файл не создан: запустите scripts/make_demo_data.py")
    return StubApp(with_data=True, with_result=True)


def test_all_screens_build_with_result(app_with_data):
    for builder in BUILDERS:
        control = builder(app_with_data)
        assert control is not None, builder.__name__


def test_screens_build_without_data():
    empty_app = StubApp(with_data=False, with_result=False)
    for builder in BUILDERS:
        assert builder(empty_app) is not None


def test_screens_build_with_data_but_without_selection():
    app = StubApp(with_data=True, with_result=False)
    for builder in BUILDERS:
        assert builder(app) is not None


def test_car_card_shows_scores_and_reasons(app_with_data):
    from ui import widgets

    card = widgets.car_card(app_with_data.result.recommendations[0])
    assert card is not None
    assert widgets.short_title("Агент «Бюджет»") == "Бюджет"
    assert widgets.score_color(95) != widgets.score_color(30)


def test_charts_build_from_pandas_data(app_with_data):
    import dashboard as dash
    from ui import widgets

    df = app_with_data.df
    assert widgets.pie_chart(dash.brand_shares(df), "brand") is not None
    assert widgets.bar_chart(dash.price_by_brand(df), "brand", "avg_price") is not None
    assert widgets.scatter_chart(dash.price_mileage_points(df)) is not None
    assert widgets.line_chart(dash.avg_price_by_year(df)) is not None


def test_money_formatting_is_russian_style():
    import dashboard as dash

    assert dash.format_car_price(1_350_000) == "1 350 000 ₽"
    assert dash.format_mileage(95_000) == "95 000 км"
    assert dash.format_car_price(None) == "—"
