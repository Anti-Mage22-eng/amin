"""Точка входа: запускает окно Flet.

Запуск:
    .venv\\Scripts\\python.exe src\\main.py
"""

from __future__ import annotations

import os
import sys
from pathlib import Path

import flet as ft

# чтобы работали импорты вида `from ui.app import ...` и `import dashboard`
SRC_DIR = Path(__file__).resolve().parent
if str(SRC_DIR) not in sys.path:
    sys.path.insert(0, str(SRC_DIR))

from ui.app import CarSelectorApp  # noqa: E402


def main(page: ft.Page) -> None:
    CarSelectorApp(page)


if __name__ == "__main__":
    if os.environ.get("CARSELECTOR_HEADLESS"):
        # проверка сборки интерфейса без видимого окна (используется при отладке)
        ft.run(main, assets_dir=None, view=ft.AppView.FLET_APP_HIDDEN)
    else:
        ft.run(main, assets_dir=None)

