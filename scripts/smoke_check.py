"""Дымовая проверка приложения в «живом» окне без участия пользователя.

Запускает настоящее приложение Flet (в скрытом режиме), прогоняет сценарий
«загрузить демо → подобрать → открыть все экраны» и печатает результат.
Если что-то падает в интерфейсе — это видно здесь, до запуска руками.

Запуск:  $env:CARSELECTOR_HEADLESS=1; .venv\\Scripts\\python.exe scripts\\smoke_check.py
"""

from __future__ import annotations

import asyncio
import os
import sys
from pathlib import Path

import flet as ft

ROOT = Path(__file__).resolve().parents[1]
SRC = ROOT / "src"
if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))

from data_loader import load_cars  # noqa: E402
from orchestrator import ClientRequest, Selector  # noqa: E402
from paths import DEMO_CSV  # noqa: E402
from ui.app import CarSelectorApp  # noqa: E402


def check(label: str, condition: bool, detail: str = "") -> bool:
    print(f"[{'OK ' if condition else 'FAIL'}] {label}{(' — ' + detail) if detail else ''}", flush=True)
    return condition


async def scenario(page: ft.Page, app: CarSelectorApp) -> None:
    await asyncio.sleep(1.5)
    results: list[bool] = []

    results.append(check("приложение построило главный экран", len(page.controls) > 0,
                         f"элементов на странице: {len(page.controls)}"))
    results.append(check("демо-данные загружены", app.df is not None and len(app.df) > 50,
                         f"автомобилей: {len(app.df) if app.df is not None else 0}"))

    app.run_selection()
    results.append(check("подбор выполнен", app.result is not None and bool(app.result.recommendations),
                         f"вариантов: {len(app.result.recommendations) if app.result else 0}"))
    if app.result and app.result.recommendations:
        best = app.result.recommendations[0]
        results.append(check("лидер подбора с оценкой и объяснением",
                             best.total > 0 and bool(best.reasons),
                             f"{best.car['brand']} {best.car['model']} — {best.total:.0f}/100"))

    for screen in ("dashboard", "agents", "data", "select"):
        app.go(screen)
        results.append(check(f"экран «{screen}» отрисован", len(page.controls) > 0))

    # отдельная проверка слоя агентов без интерфейса
    selector = Selector()
    result = selector.select(load_cars(DEMO_CSV).df, ClientRequest(budget_max=2_500_000, top_n=5))
    results.append(check("агенты и скиллы работают напрямую", bool(result.recommendations),
                         f"прошли фильтр: {result.eligible}, в топе: {len(result.recommendations)}"))

    print(f"\nИТОГ: {sum(results)} из {len(results)} проверок пройдено", flush=True)
    print("SMOKE_OK" if all(results) else "SMOKE_FAILED", flush=True)
    await asyncio.sleep(0.3)
    os._exit(0 if all(results) else 1)


def main(page: ft.Page) -> None:
    app = CarSelectorApp(page)
    page.run_task(scenario, page, app)


if __name__ == "__main__":
    view = ft.AppView.FLET_APP_HIDDEN if os.environ.get("CARSELECTOR_HEADLESS") else ft.AppView.FLET_APP
    ft.run(main, assets_dir=None, view=view)
