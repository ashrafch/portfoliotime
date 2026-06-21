"""
Test integrazione per engine/simulator.py.

Usa prezzi sintetici per testare la pipeline end-to-end senza dipendenze esterne.
"""

import pytest
import pandas as pd
import numpy as np
from datetime import datetime
from engine.simulator import SimulationInput, run_simulation


def _make_prices(n: int = 500, seed: int = 42) -> pd.DataFrame:
    """Genera prezzi sintetici per SPY, TLT, GLD, GSG, BTC-USD."""
    rng = np.random.default_rng(seed)
    idx = pd.date_range("2020-01-01", periods=n, freq="B")
    data = {
        "SPY": 100 * (1 + rng.normal(0.0004, 0.012, n)).cumprod(),
        "TLT": 100 * (1 + rng.normal(0.0001, 0.007, n)).cumprod(),
        "GLD": 100 * (1 + rng.normal(0.0002, 0.008, n)).cumprod(),
        "GSG": 100 * (1 + rng.normal(0.0001, 0.015, n)).cumprod(),
        "BTC-USD": 100 * (1 + rng.normal(0.002, 0.04, n)).cumprod(),
    }
    return pd.DataFrame(data, index=idx)


def _default_input(**overrides) -> SimulationInput:
    defaults = dict(
        eta=40,
        tasso_fed=5.0,
        delta_tasso=0.0,
        btc_prezzo_corrente=30000.0,
        btc_ath=69000.0,
        is_post_halving=True,
        tasso_nominale=5.0,
        inflazione=3.0,
        tassi_in_calo=False,
        qe_attivo=False,
        date_from="2020-01-01",
        date_to="2021-12-31",
    )
    defaults.update(overrides)
    return SimulationInput(**defaults)


class TestRunSimulation:

    def test_risultato_ha_tutti_i_campi(self):
        prices = _make_prices()
        sim = run_simulation(_default_input(), prices)
        assert isinstance(sim.allocazione, dict)
        assert set(sim.allocazione.keys()) == {"azioni", "bitcoin", "oro", "materie_prime", "obbligazioni"}
        assert not np.isnan(sim.cagr)
        assert not np.isnan(sim.max_drawdown)
        assert not np.isnan(sim.total_return)

    def test_drawdown_non_positivo(self):
        prices = _make_prices()
        sim = run_simulation(_default_input(), prices)
        assert sim.max_drawdown <= 0.0

    def test_qe_attivo_obbligazioni_zero(self):
        prices = _make_prices()
        sim = run_simulation(_default_input(qe_attivo=True), prices)
        assert sim.allocazione["obbligazioni"] == 0.0

    def test_prezzi_vuoti_produce_nan(self):
        empty = pd.DataFrame(columns=["SPY", "TLT", "GLD", "GSG", "BTC-USD"])
        sim = run_simulation(_default_input(), empty)
        assert np.isnan(sim.cagr)
        assert len(sim.warnings) > 0

    def test_sources_contiene_yahoo_finance(self):
        prices = _make_prices()
        sim = run_simulation(_default_input(), prices)
        assert any(v == "yahoo_finance" for v in sim.sources.values())
