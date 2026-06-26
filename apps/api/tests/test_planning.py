"""Test del motore di pianificazione per obiettivi (goal-based)."""

import numpy as np
import pandas as pd

from engine.planning import (
    project_goal,
    required_monthly_contribution,
    reference_stats,
    REFERENCE_ALLOCATIONS,
)


def _positive_drift_returns(n=2000, mu=0.0004, sigma=0.008, seed=1):
    rng = np.random.default_rng(seed)
    return pd.Series(rng.normal(mu, sigma, n))


class TestProjectGoal:
    def test_struttura_e_range(self):
        r = _positive_drift_returns()
        out = project_goal(r, horizon_years=10, initial=10000, monthly_contribution=200, target=50000)
        assert 0.0 <= out["probability_success"] <= 1.0
        # percentili ordinati
        fv = out["final_value"]
        assert fv["p10"] <= fv["p50"] <= fv["p90"]
        # totale versato = iniziale + 200 * mesi (10 anni → ~119 versamenti, day0 escluso)
        assert out["total_contributed"] > 10000

    def test_target_basso_alta_probabilita(self):
        r = _positive_drift_returns()
        out = project_goal(r, horizon_years=10, initial=10000, monthly_contribution=200, target=1)
        assert out["probability_success"] > 0.99

    def test_target_irraggiungibile_bassa_probabilita(self):
        r = _positive_drift_returns()
        out = project_goal(r, horizon_years=5, initial=1000, monthly_contribution=0, target=10_000_000)
        assert out["probability_success"] < 0.01

    def test_dati_insufficienti(self):
        out = project_goal(pd.Series([0.01, 0.02]), 10, 1000, 100, 5000)
        assert "error" in out


class TestRequiredContribution:
    def test_monotonia_e_soglia(self):
        r = _positive_drift_returns()
        c = required_monthly_contribution(r, horizon_years=10, initial=0, target=50000, success_threshold=0.75)
        assert c is not None and c > 0
        # con quel contributo la probabilità deve raggiungere ~la soglia
        out = project_goal(r, 10, 0, c, 50000)
        assert out["probability_success"] >= 0.70

    def test_capitale_gia_sufficiente(self):
        r = _positive_drift_returns()
        # target minuscolo → nessun versamento necessario
        c = required_monthly_contribution(r, 10, initial=100000, target=1, success_threshold=0.75)
        assert c == 0.0


class TestGlidePath:
    def test_glide_riduce_variabilita_finale(self):
        # allocazione "inizio" volatile, "fine" tranquilla → il glide deve ridurre
        # la dispersione degli esiti rispetto al solo inizio volatile
        rng = np.random.default_rng(3)
        r_start = pd.Series(rng.normal(0.0004, 0.015, 2000))  # volatile
        r_end = pd.Series(rng.normal(0.0002, 0.003, 2000))    # tranquilla

        base = project_goal(r_start, 10, 10000, 200, 50000, seed=5)
        glide = project_goal(r_start, 10, 10000, 200, 50000, seed=5, returns_end=r_end)

        spread_base = base["final_value"]["p90"] - base["final_value"]["p10"]
        spread_glide = glide["final_value"]["p90"] - glide["final_value"]["p10"]
        assert spread_glide < spread_base  # meno incertezza con il glide

    def test_glide_struttura_ok(self):
        r_start = _positive_drift_returns()
        r_end = _positive_drift_returns(mu=0.0002, sigma=0.003, seed=9)
        out = project_goal(r_start, 12, 5000, 150, 40000, returns_end=r_end)
        assert 0.0 <= out["probability_success"] <= 1.0
        assert out["final_value"]["p10"] <= out["final_value"]["p90"]


class TestReference:
    def test_allocazioni_sommano_100(self):
        for profile, alloc in REFERENCE_ALLOCATIONS.items():
            assert abs(sum(alloc.values()) - 100) < 1e-6, profile

    def test_stats(self):
        r = _positive_drift_returns()
        s = reference_stats(r)
        assert s["annual_return"] is not None
        assert s["annual_volatility"] > 0
