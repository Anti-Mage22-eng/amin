"""Проверка подбора: агенты, фильтр, веса, рейтинг с объяснениями."""

from __future__ import annotations

import pytest

from agent_loader import load_agents, load_expert_config
from data_loader import load_cars
from orchestrator import ClientRequest, Selector
from paths import DEMO_CSV


@pytest.fixture(scope="module")
def df():
    if not DEMO_CSV.exists():
        pytest.skip("Демо-файл не создан: запустите scripts/make_demo_data.py")
    return load_cars(DEMO_CSV).df


@pytest.fixture(scope="module")
def selector():
    return Selector()


@pytest.fixture(scope="module")
def client_request():
    return ClientRequest(
        budget_max=2_000_000, mileage_max=120_000, year_min=2016, priority="balanced", top_n=7
    )


@pytest.fixture(scope="module")
def result(selector, df, client_request):
    return selector.select(df, client_request)


def test_agents_are_loaded_from_configs():
    agents = load_agents()
    ids = {agent.id for agent in agents}
    assert {"fit", "budget", "mileage", "reliability", "market", "expert"} <= ids
    # у каждого оценивающего и фильтрующего агента подключён модуль скилла
    for agent in agents:
        if agent.skill:
            assert agent.module is not None
            assert agent.description
    # координатор идёт последним
    assert agents[-1].kind == "coordinator"


def test_expert_config_has_priority_profiles():
    config = load_expert_config()
    profiles = config["priority_profiles"]
    assert {"balanced", "economy", "low_mileage", "reliability", "market"} <= set(profiles)
    for profile in profiles.values():
        assert abs(sum(profile["weights"].values()) - 1.0) < 1e-6, "веса должны давать 1,0"


def test_weights_follow_priority(selector):
    balanced = selector.weights_for("balanced")
    reliable = selector.weights_for("reliability")
    economic = selector.weights_for("economy")
    assert reliable["reliability"] > balanced["reliability"]
    assert economic["budget"] > balanced["budget"]
    assert abs(sum(balanced.values()) - 1.0) < 1e-6


def test_filter_rejects_and_counts_reasons(result):
    assert result.eligible + result.rejected == result.considered
    assert result.eligible > 0
    assert result.rejected > 0
    assert result.rejected_reasons
    assert sum(count for _, count in result.rejected_reasons) <= result.rejected
    assert all(isinstance(reason, str) and reason for reason, _ in result.rejected_reasons)


def test_recommendations_respect_hard_limits(result):
    assert result.recommendations
    for rec in result.recommendations:
        assert rec.car["price"] <= 2_000_000
        assert rec.car["mileage"] <= 120_000
        assert int(rec.car["year"]) >= 2016


def test_recommendations_are_ranked_and_explained(result):
    assert [rec.rank for rec in result.recommendations] == list(range(1, len(result.recommendations) + 1))
    totals = [rec.total for rec in result.recommendations]
    assert totals == sorted(totals, reverse=True)
    assert all(0 <= total <= 100 for total in totals)
    for rec in result.recommendations:
        assert len(rec.scores) == 4, "четыре оценивающих агента"
        assert all(0 <= score.score <= 100 for score in rec.scores)
        assert rec.reasons, "у каждого варианта должно быть объяснение"


def test_top_n_is_honoured(selector, df):
    request = ClientRequest(budget_max=3_000_000, top_n=3)
    result = selector.select(df, request)
    assert len(result.recommendations) <= 3


def test_priority_changes_the_winner(selector, df):
    """При смене приоритета клиента победитель может измениться — это проверка весов."""
    base = ClientRequest(budget_max=2_000_000, mileage_max=120_000, year_min=2016, top_n=3)
    economy = selector.select(df, base)
    reliable_request = ClientRequest(
        budget_max=2_000_000, mileage_max=120_000, year_min=2016, priority="reliability", top_n=3
    )
    reliable = selector.select(df, reliable_request)
    winner_economy = economy.recommendations[0]
    winner_reliable = reliable.recommendations[0]
    assert winner_economy.score_of("budget") >= winner_reliable.score_of("budget")
    assert winner_reliable.score_of("reliability") >= winner_economy.score_of("reliability")


def test_empty_result_is_safe(selector, df):
    impossible = ClientRequest(budget_max=100_000, mileage_max=1_000, year_min=2024)
    result = selector.select(df, impossible)
    assert result.recommendations == []
    assert result.eligible == 0
    assert result.rejected == result.considered

