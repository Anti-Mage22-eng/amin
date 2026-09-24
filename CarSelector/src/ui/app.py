"""Главное окно приложения: навигация по экранам, состояние, обработчики событий."""

from __future__ import annotations

from pathlib import Path

import flet as ft

from agent_loader import AgentConfigError, load_agents, load_expert_config
from data_loader import DataError, load_cars
from orchestrator import ClientRequest, Selector
from paths import DEMO_CSV
from ui import screens
from ui import theme as t
from ui import widgets as w

DEFAULT_FILTERS = {
    "budget": "2000000",
    "mileage": "120000",
    "year_min": "2016",
    "year_max": "",
    "brand": "",
    "fuel": "",
    "transmission": "",
    "body": "",
    "priority": "balanced",
    "top_n": "10",
}

FUEL_OPTIONS = ["Бензин", "Дизель", "Гибрид", "Электро", "Газ"]
TRANSMISSION_OPTIONS = ["АКПП", "МКПП", "Вариатор", "Робот"]
BODY_OPTIONS = ["Седан", "Хэтчбек", "Универсал", "Кроссовер", "Внедорожник", "Купе", "Минивэн"]

FORMAT_HINT = (
    "Нужен CSV (разделитель «;» или «,», кодировка UTF-8 или Windows-1251) либо Excel (.xlsx). "
    "Обязательные колонки: марка, цена, пробег. Полезные дополнительные: модель, год выпуска, "
    "топливо, КПП, кузов, объём двигателя. Названия можно писать по-русски или по-английски — "
    "программа сопоставит их сама (например, «Пробег, км» и «mileage»). Цена и пробег могут быть "
    "строками: «1 350 000 ₽», «132 тыс. км» — числа разбираются автоматически."
)


class CarSelectorApp:
    """Приложение целиком: экраны, фильтры, вызов агентов и отрисовка."""

    NAV = [
        ("data", "Данные", ft.Icons.TABLE_CHART),
        ("select", "Подбор", ft.Icons.SEARCH),
        ("dashboard", "Дашборд", ft.Icons.BAR_CHART),
        ("agents", "Агенты", ft.Icons.SMART_TOY),
    ]

    def __init__(self, page: ft.Page):
        self.page = page
        self.screen = "data"
        self.message = ""
        self.load_result = None
        self.df = None
        self.result = None
        self.filters = dict(DEFAULT_FILTERS)
        self.file_picker = ft.FilePicker()

        self._setup_page()
        self._register_services()

        try:
            self.agents = load_agents()
            self.selector = Selector(self.agents, load_expert_config())
            self.agents_error = ""
        except AgentConfigError as exc:
            self.agents = []
            self.selector = None
            self.agents_error = str(exc)

        self.nav = ft.Row(spacing=8, wrap=True)
        self.filter_form = ft.Column(spacing=10)
        self.content = ft.Container(expand=True)
        self._build_filter_form()

        if DEMO_CSV.exists():
            self.load_path(DEMO_CSV, silent=True)
            self.message = f"Загружен демо-набор: {len(self.df)} автомобилей. Можно загрузить свой файл."
        self.render()

    # -- настройка окна -----------------------------------------------------
    def _setup_page(self) -> None:
        self.page.title = "CarSelector — подбор автомобиля по данным файла"
        self.page.padding = 20
        self.page.bgcolor = t.BG
        self.page.scroll = ft.ScrollMode.AUTO
        try:
            self.page.window.width = 1400
            self.page.window.height = 900
            self.page.window.min_width = 1100
            self.page.window.min_height = 700
        except Exception:
            pass  # размеры окна — не критично

    def _register_services(self) -> None:
        """FilePicker в Flet 1.0 — сервис страницы, а не элемент управления."""
        try:
            self.page.services.append(self.file_picker)
        except Exception:
            try:
                self.page.services = [self.file_picker]
            except Exception as exc:
                self.message = f"Не удалось подключить диалог выбора файла: {exc}"

    # -- навигация ----------------------------------------------------------
    def go(self, key: str) -> None:
        self.screen = key
        self.render()

    def _nav_button(self, key: str, label: str, icon) -> ft.Control:
        on_click = lambda event, target=key: self.go(target)  # noqa: E731
        if key == self.screen:
            return ft.FilledButton(
                label, icon=icon, bgcolor=t.ACCENT, color=t.PANEL_DEEP, on_click=on_click
            )
        return ft.OutlinedButton(label, icon=icon, style=t.OUTLINE_BUTTON_STYLE, on_click=on_click)

    def render(self) -> None:
        self.nav.controls = [self._nav_button(key, label, icon) for key, label, icon in self.NAV]
        if self.selector is None:
            self.content.content = ft.Column(
                [
                    ft.Text("Агенты не загрузились", size=24, weight=ft.FontWeight.BOLD, color=t.ON_RED),
                    w.panel(
                        "Ошибка конфигурации агентов",
                        ft.Text(self.agents_error, size=13, color=t.ON_RED, selectable=True),
                        subtitle="Проверьте папки .agent и .skill в корне проекта",
                        icon=ft.Icons.INFO_OUTLINE,
                    ),
                ],
                spacing=14,
            )
        else:
            builder = {
                "data": screens.data_screen,
                "select": screens.select_screen,
                "dashboard": screens.dashboard_screen,
                "agents": screens.agents_screen,
            }[self.screen]
            self.content.content = builder(self)

        self.page.controls.clear()
        self.page.add(
            ft.Text("CarSelector", size=28, weight=ft.FontWeight.BOLD, color=t.ON_RED),
            ft.Text(
                "Подбор автомобиля по данным из файла: ИИ-агенты, скиллы и анализ через pandas",
                size=13, color=t.ON_RED_DIM,
            ),
            ft.Divider(height=1, color=ft.Colors.RED_300),
            self.nav,
            self.content,
        )
        self.page.update()

    # -- форма параметров ---------------------------------------------------
    def _text_field(self, key: str, label: str, width: int = 200) -> ft.Control:
        def on_change(event):
            self.filters[key] = event.control.value or ""

        return ft.TextField(
            label=label,
            value=self.filters.get(key, ""),
            width=width,
            dense=True,
            on_change=on_change,
        )

    def _dropdown(self, key: str, label: str, options: list[tuple[str, str]], width: int = 220) -> ft.Control:
        def on_select(event):
            self.filters[key] = event.control.value or ""

        return ft.Dropdown(
            label=label,
            value=self.filters.get(key, ""),
            options=[ft.DropdownOption(key=value, text=text) for value, text in options],
            width=width,
            dense=True,
            on_select=on_select,
        )

    def _build_filter_form(self) -> None:
        brands: list[tuple[str, str]] = [("", "Любая")]
        if self.df is not None:
            brands += [(brand, brand) for brand in sorted({str(b) for b in self.df["brand"] if str(b).strip()})]

        fuel_options = [("", "Любое")] + [(value, value) for value in FUEL_OPTIONS]
        transmission_options = [("", "Любая")] + [(value, value) for value in TRANSMISSION_OPTIONS]
        body_options = [("", "Любой")] + [(value, value) for value in BODY_OPTIONS]

        profile_options = [("balanced", "Сбалансированный подбор")]
        if self.selector is not None:
            profile_options = [
                (key, profile.get("title", key))
                for key, profile in self.selector.priority_profiles().items()
            ]

        self.filter_form.controls = [
            ft.Row(
                [
                    self._text_field("budget", "Бюджет до, ₽"),
                    self._text_field("mileage", "Пробег до, км"),
                    self._text_field("year_min", "Год от", 130),
                    self._text_field("year_max", "Год до", 130),
                    self._text_field("top_n", "Сколько показать", 160),
                ],
                spacing=12, wrap=True,
            ),
            ft.Row(
                [
                    self._dropdown("brand", "Марка", brands, 240),
                    self._dropdown("fuel", "Топливо", fuel_options),
                    self._dropdown("transmission", "КПП", transmission_options),
                    self._dropdown("body", "Кузов", body_options),
                    self._dropdown("priority", "Приоритет клиента", profile_options, 300),
                ],
                spacing=12, wrap=True,
            ),
        ]

    def reset_filters(self, event=None) -> None:
        self.filters = dict(DEFAULT_FILTERS)
        self._build_filter_form()
        self.message = "Параметры сброшены к значениям по умолчанию."
        self.render()

    def priority_title(self) -> str:
        if self.selector is None:
            return "—"
        profile = self.selector.priority_profiles().get(self.filters.get("priority", "balanced"), {})
        return profile.get("title", self.filters.get("priority", "balanced"))

    # -- загрузка файла -----------------------------------------------------
    async def pick_file(self, event=None) -> None:
        try:
            files = await self.file_picker.pick_files(
                dialog_title="Выберите файл с автомобилями",
                file_type=ft.FilePickerFileType.CUSTOM,
                allowed_extensions=["csv", "txt", "xlsx", "xlsm", "xls"],
                allow_multiple=False,
            )
        except Exception as exc:
            self.message = f"Не удалось открыть диалог выбора файла: {exc}"
            self.render()
            return

        if not files:
            return
        path = getattr(files[0], "path", None)
        if not path:
            self.message = "Не удалось получить путь к выбранному файлу. Выберите файл ещё раз."
            self.render()
            return
        self.load_path(path)

    def load_demo(self, event=None) -> None:
        if not DEMO_CSV.exists():
            self.message = (
                "Демо-файл не найден. Создайте его командой: "
                "python scripts/make_demo_data.py"
            )
            self.render()
            return
        self.load_path(DEMO_CSV)

    def show_format_hint(self, event=None) -> None:
        self.message = FORMAT_HINT
        self.render()

    def load_path(self, path, silent: bool = False) -> None:
        try:
            self.load_result = load_cars(path)
        except DataError as exc:
            self.load_result = None
            self.df = None
            self.result = None
            self.message = f"Ошибка данных: {exc}"
        else:
            self.df = self.load_result.df
            self.result = None
            report = self.load_result.report
            self.message = (
                f"Файл «{Path(path).name}»: прочитано {report['rows_read']} строк, "
                f"после проверки осталось {report['rows_valid']} автомобилей "
                f"(дубликатов удалено: {report['duplicates_removed']})."
            )
            self._build_filter_form()

        if not silent:
            self.screen = "data"
            self.render()

    # -- подбор -------------------------------------------------------------
    def _read_request(self) -> ClientRequest | None:
        def number(key: str, title: str, required: bool = False) -> float | None:
            raw = str(self.filters.get(key, "")).strip().replace(" ", "").replace("\u00a0", "")
            if not raw:
                if required:
                    self.message = f"Укажите «{title}»."
                return None
            try:
                return float(raw.replace(",", "."))
            except ValueError:
                self.message = f"Поле «{title}» должно быть числом, а не «{raw}»."
                return None

        budget = number("budget", "Бюджет до", required=True)
        if budget is None:
            return None
        top_n = number("top_n", "Сколько показать") or 10

        return ClientRequest(
            budget_max=budget,
            mileage_max=number("mileage", "Пробег до"),
            year_min=int(number("year_min", "Год от")) if number("year_min", "Год от") else None,
            year_max=int(number("year_max", "Год до")) if number("year_max", "Год до") else None,
            brands=[self.filters["brand"]] if self.filters.get("brand") else [],
            fuel=self.filters.get("fuel") or None,
            transmission=self.filters.get("transmission") or None,
            body=self.filters.get("body") or None,
            priority=self.filters.get("priority") or "balanced",
            top_n=max(1, min(50, int(top_n))),
        )

    def run_selection(self, event=None) -> None:
        if self.df is None:
            self.message = "Сначала загрузите файл на экране «Данные»."
            self.render()
            return
        if self.selector is None:
            self.message = self.agents_error
            self.render()
            return

        request = self._read_request()
        if request is None:
            self.render()
            return

        self.result = self.selector.select(self.df, request)
        if self.result.recommendations:
            best = self.result.recommendations[0]
            self.message = (
                f"Подобрано {len(self.result.recommendations)} вариантов из {self.result.eligible} "
                f"прошедших фильтр. Лидер: {best.car['brand']} {best.car['model']} "
                f"с оценкой {best.total:.0f}/100."
            )
        else:
            self.message = (
                f"Подходящих вариантов нет: все {self.result.considered} автомобилей отклонены "
                "по обязательным параметрам. Ослабьте условия."
            )
        self.screen = "select"
        self.render()
