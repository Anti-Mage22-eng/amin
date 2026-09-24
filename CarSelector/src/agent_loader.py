"""Загрузка ИИ-агентов: конфиги из .agent/ + навыки из .skill/.

Агент = конфиг (роль, вес, какой скилл использовать) + модуль скилла с логикой.
Загрузчик проверяет, что у каждого включённого агента есть папка со скиллом,
и падает с понятной ошибкой, если конфиг рассинхронизирован с кодом.
"""

from __future__ import annotations

import importlib.util
import json
from dataclasses import dataclass, field
from pathlib import Path
from types import ModuleType

from paths import AGENT_DIR, SKILL_DIR


class AgentConfigError(Exception):
    """Конфиг агента не сходится с кодом скиллов — сообщаем явно."""


@dataclass
class AgentSpec:
    """Один ИИ-агент: паспорт из .agent/*.json + подключённый модуль скилла."""

    id: str
    title: str
    role: str
    skill: str | None = None
    weight: float = 0.0
    enabled: bool = True
    kind: str = "scoring"          # scoring | filter | coordinator
    config_path: str = ""
    module: ModuleType | None = None
    description: str = ""
    extra: dict = field(default_factory=dict)

    @property
    def skill_dir(self) -> Path | None:
        return SKILL_DIR / self.skill if self.skill else None


def load_skill_module(skill_name: str) -> ModuleType:
    """Импортирует .skill/<skill_name>/skill.py по пути (папка с точкой — не пакет)."""
    skill_file = SKILL_DIR / skill_name / "skill.py"
    if not skill_file.exists():
        raise AgentConfigError(
            f"Не найден файл скилла: {skill_file}. "
            "Проверьте, что для агента есть папка в .skill с файлом skill.py."
        )
    module_name = f"carselector_skill_{skill_name}"
    spec = importlib.util.spec_from_file_location(module_name, skill_file)
    if spec is None or spec.loader is None:
        raise AgentConfigError(f"Не удалось загрузить модуль скилла {skill_file}")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def load_agents(agent_dir: Path = AGENT_DIR, only_enabled: bool = True) -> list[AgentSpec]:
    """Читает .agent/*.json, подключает скиллы. Координатор (expert) идёт последним."""
    if not agent_dir.exists():
        raise AgentConfigError(f"Нет папки с конфигами агентов: {agent_dir}")

    agents: list[AgentSpec] = []
    for config_path in sorted(agent_dir.glob("*.agent.json")):
        try:
            config = json.loads(config_path.read_text(encoding="utf-8"))
        except json.JSONDecodeError as exc:
            raise AgentConfigError(f"Некорректный JSON в {config_path.name}: {exc}") from exc

        agent = AgentSpec(
            id=str(config.get("id") or config_path.stem.replace(".agent", "")),
            title=str(config.get("title") or config.get("id")),
            role=str(config.get("role", "")),
            skill=config.get("skill"),
            weight=float(config.get("weight", 0.0)),
            enabled=bool(config.get("enabled", True)),
            kind=str(config.get("kind", "scoring")),
            config_path=str(config_path),
            extra=config,
        )
        if only_enabled and not agent.enabled:
            continue
        if agent.skill:
            agent.module = load_skill_module(agent.skill)
            agent.description = str(
                getattr(agent.module, "DESCRIPTION", "") or (agent.module.__doc__ or "").strip()
            )
        agents.append(agent)

    agents.sort(key=lambda a: (a.kind == "coordinator", -a.weight))
    if not agents:
        raise AgentConfigError(f"В {agent_dir} нет включённых агентов.")
    return agents


def load_expert_config(agent_dir: Path = AGENT_DIR) -> dict:
    """Настройки координатора: профили приоритетов клиента и размер топа."""
    path = agent_dir / "expert.agent.json"
    if not path.exists():
        raise AgentConfigError(f"Не найден конфиг координатора: {path}")
    return json.loads(path.read_text(encoding="utf-8"))
