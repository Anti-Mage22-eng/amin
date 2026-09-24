"""Оркестратор подбора: прогоняет агентов по базе и собирает итоговый рейтинг.

Роли агентов:
  * filter      — скилл «Соответствие»: жёсткий отбор по обязательным параметрам клиента;
  * scoring     — бюджет, пробег, надёжность, рынок: оценки 0–100 с обоснованием;
  * coordinator — «Эксперт»: взвешивает оценки по приоритету клиента и объясняет выбор.
"""

from __future__ import annotations

from collections import Counter
from dataclasses import dataclass, field

import pandas as pd

from agent_loader import AgentSpec, load_agents, load_expert_config

MIN_GROUP_SIZE = 4  # меньше аналогов — статистике не доверяем


@dataclass
class ClientRequest:
    """Параметры клиента, по которым подбираем автомобиль."""

    budget_max: float = 2_000_000
    mileage_max: float | None = 150_000
    year_min: int | None = None
    year_max: int | None = None
    brands: list[str] = field(default_factory=list)
    fuel: str | None = None
    transmission: str | None = None
    body: str | None = None
    priority: str = "balanced"
    top_n: int = 10

    def as_dict(self) -> dict:
        return {
            "budget_max": self.budget_max,
            "mileage_max": self.mileage_max,
            "year_min": self.year_min,
            "year_max": self.year_max,
            "brands": list(self.brands),
            "fuel": self.fuel,
            "transmission": self.transmission,
            "body": self.body,
            "priority": self.priority,
            "top_n": self.top_n,
        }

    def describe(self) -> str:
        parts = [f"бюджет до {self.budget_max:,.0f} ₽".replace(",", " ")]
        if self.mileage_max:
            parts.append(f"пробег до {self.mileage_max:,.0f} км".replace(",", " "))
        if self.year_min:
            parts.append(f"год от {self.year_min}")
        if self.year_max:
            parts.append(f"год до {self.year_max}")
        if self.brands:
            parts.append("марки: " + ", ".join(self.brands))
        if self.fuel:
            parts.append(f"топливо: {self.fuel}")
        if self.transmission:
            parts.append(f"КПП: {self.transmission}")
        if self.body:
            parts.append(f"кузов: {self.body}")
        return "; ".join(parts)


@dataclass
class AgentScore:
    agent_id: str
    title: str
    score: float
    reasons: list[str] = field(default_factory=list)
    weight: float = 0.0


@dataclass
class Recommendation:
    rank: int
    car: dict
    total: float
    scores: list[AgentScore] = field(default_factory=list)
    reasons: list[str] = field(default_factory=list)

    def score_of(self, agent_id: str) -> float | None:
        for score in self.scores:
            if score.agent_id == agent_id:
                return score.score
        return None


@dataclass
class SelectionResult:
    request: ClientRequest
    considered: int = 0
    eligible: int = 0
    rejected: int = 0
    rejected_reasons: list[tuple[str, int]] = field(default_factory=list)
    recommendations: list[Recommendation] = field(default_factory=list)
    weights: dict[str, float] = field(default_factory=dict)
    median_price: float | None = None
    market_source: str = ""


def build_market_stats(df: pd.DataFrame) -> dict:
    """Медианы цен по аналогам: марка+модель и просто марка (для скилла «Рынок»)."""
    stats: dict = {"global_median": float(df["price"].median()) if not df.empty else None}
    if df.empty:
        stats["by_model"] = {}
        stats["by_brand"] = {}
        return stats

    with_model = df[df["model"].astype(str).str.strip() != ""]
    stats["by_model"] = {
        (str(row.brand_key), str(row.model)): {"median": float(row.median_price), "size": int(row.size)}
        for row in with_model.groupby(["brand_key", "model"])["price"]
        .agg(median_price="median", size="size")
        .reset_index()
        .itertuples()
    }
    stats["by_brand"] = {
        str(row.brand_key): {"median": float(row.median_price), "size": int(row.size)}
        for row in df.groupby("brand_key")["price"].agg(median_price="median", size="size").reset_index().itertuples()
    }
    return stats


def _median_for(car: dict, stats: dict) -> tuple[float | None, str]:
    """Медиана цены аналогов для конкретной машины + на чём основана."""
    key_model = (str(car.get("brand_key", "")), str(car.get("model", "")))
    if car.get("model"):
        group = stats["by_model"].get(key_model)
        if group and group["size"] >= MIN_GROUP_SIZE:
            return group["median"], "одна модель"
    brand = stats["by_brand"].get(str(car.get("brand_key", "")))
    if brand and brand["size"] >= MIN_GROUP_SIZE:
        return brand["median"], "та же марка"
    return stats.get("global_median"), "вся база"


class Selector:
    """Координирует агентов: фильтр → оценки → взвешенный итог с объяснением."""

    def __init__(self, agents: list[AgentSpec] | None = None, expert_config: dict | None = None):
        self.agents = agents if agents is not None else load_agents()
        self.expert = expert_config if expert_config is not None else load_expert_config()
        self.filter_agents = [a for a in self.agents if a.kind == "filter"]
        self.scoring_agents = [a for a in self.agents if a.kind == "scoring"]

    # -- конфигурация -------------------------------------------------------
    def priority_profiles(self) -> dict:
        return self.expert.get("priority_profiles", {})

    def weights_for(self, priority: str) -> dict[str, float]:
        """Веса агентов под приоритет клиента (из конфига координатора)."""
        profile = self.priority_profiles().get(priority) or {}
        weights = profile.get("weights") or {}
        return {
            agent.id: float(weights.get(agent.id, agent.weight))
            for agent in self.scoring_agents
        }

    # -- основной проход ----------------------------------------------------
    def select(self, df: pd.DataFrame, request: ClientRequest) -> SelectionResult:
        result = SelectionResult(request=request, weights=self.weights_for(request.priority))
        if df.empty:
            return result

        stats = build_market_stats(df)
        ctx = {"request": request.as_dict(), "market": stats}
        result.considered = int(len(df))

        rejected = Counter()
        eligible_cars: list[dict] = []
        for car in df.to_dict("records"):
            ok, reason = True, ""
            for agent in self.filter_agents:
                ok, reason = agent.module.is_eligible(car, ctx)
                if not ok:
                    break
            if not ok and self.filter_agents:
                rejected[reason or "не подошёл"] += 1
                continue
            eligible_cars.append(car)

        result.eligible = len(eligible_cars)
        result.rejected = result.considered - result.eligible
        result.rejected_reasons = [(reason, count) for reason, count in rejected.most_common(6)]

        if not eligible_cars:
            return result

        eligible_df = pd.DataFrame(eligible_cars)
        result.median_price = float(eligible_df["price"].median())

        scored: list[Recommendation] = []
        for car in eligible_cars:
            median, source = _median_for(car, stats)
            local_ctx = dict(ctx)
            local_ctx["market"] = {"median_price": median, "source": source}
            scores: list[AgentScore] = []
            for agent in self.scoring_agents:
                score, reasons = agent.module.evaluate(car, local_ctx)
                scores.append(
                    AgentScore(
                        agent_id=agent.id,
                        title=agent.title,
                        score=round(float(score), 1),
                        reasons=list(reasons)[:3],
                        weight=result.weights.get(agent.id, agent.weight),
                    )
                )
            total_weight = sum(s.weight for s in scores) or 1.0
            total = sum(s.score * s.weight for s in scores) / total_weight

            reasons: list[str] = []
            for s in scores:
                for reason in s.reasons[:2]:
                    reasons.append(f"{s.title}: {reason}")
            scored.append(
                Recommendation(rank=0, car=car, total=round(total, 1), scores=scores, reasons=reasons)
            )

        scored.sort(key=lambda r: (-r.total, r.car.get("price") or 0))
        top_n = max(1, int(request.top_n or 10))
        for index, rec in enumerate(scored[:top_n], start=1):
            rec.rank = index
        result.recommendations = scored[:top_n]
        return result


def default_selector() -> Selector:
    return Selector()
