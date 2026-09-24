"""Пути проекта. Все модули берут директории отсюда, чтобы не хардкодить пути."""

from __future__ import annotations

from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]

AGENT_DIR = ROOT / ".agent"      # конфиги ИИ-агентов (JSON)
SKILL_DIR = ROOT / ".skill"      # навыки агентов (SKILL.md + skill.py)
DATA_DIR = ROOT / "data"         # данные пользователя
DEMO_CSV = DATA_DIR / "cars.csv"  # демо-набор для первого запуска
