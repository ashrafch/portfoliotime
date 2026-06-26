"""Test metriche di rischio avanzate — valori verificati a mano."""

import pytest
import numpy as np
import pandas as pd

from engine.metrics import (
    calc_sortino_ratio,
    calc_calmar_ratio,
    calc_historical_var,
    calc_historical_cvar,
    calc_beta,
    calc_underwater_recovery,
)


class TestSortino:
    def test_penalizza_solo_downside(self):
        # Con soli rendimenti positivi non c'è downside → NaN (downside dev = 0)
        r = pd.Series([0.01, 0.02, 0.015])
        assert np.isnan(calc_sortino_ratio(r, risk_free_rate=0.0))

    def test_maggiore_di_sharpe_con_upside_volatile(self):
        from engine.metrics import calc_sharpe_ratio
        r = pd.Series([0.03, -0.01, 0.04, -0.01, 0.05, -0.01])
        sortino = calc_sortino_ratio(r, risk_free_rate=0.0)
        sharpe = calc_sharpe_ratio(r, risk_free_rate=0.0)
        # Con upside ampio e downside contenuto, Sortino > Sharpe
        assert sortino > sharpe

    def test_serie_vuota_nan(self):
        assert np.isnan(calc_sortino_ratio(pd.Series(dtype=float)))


class TestCalmar:
    def test_calcolo_base(self):
        # 0.12 / 0.30 = 0.4
        assert calc_calmar_ratio(0.12, -0.30) == pytest.approx(0.4, abs=1e-9)

    def test_drawdown_zero_nan(self):
        assert np.isnan(calc_calmar_ratio(0.10, 0.0))

    def test_drawdown_nan_nan(self):
        assert np.isnan(calc_calmar_ratio(0.10, float("nan")))


class TestVaR:
    def test_quantile_5pct(self):
        # 100 valori 0.00..0.99 (in centesimi). quantile 5% (np 'linear')
        r = pd.Series([i / 100 for i in range(100)])
        var = calc_historical_var(r, 0.95)
        expected = float(np.quantile(r, 0.05))
        assert var == pytest.approx(expected, abs=1e-9)

    def test_var_negativo_su_perdite(self):
        r = pd.Series([-0.10, -0.05, -0.02, 0.0, 0.01, 0.02, 0.03, 0.04])
        var = calc_historical_var(r, 0.95)
        assert var < 0  # la coda sinistra è negativa

    def test_serie_vuota_nan(self):
        assert np.isnan(calc_historical_var(pd.Series(dtype=float)))


class TestCVaR:
    def test_cvar_peggiore_o_uguale_var(self):
        r = pd.Series([-0.10, -0.08, -0.05, -0.02, 0.0, 0.01, 0.02, 0.03, 0.04, 0.05])
        var = calc_historical_var(r, 0.90)
        cvar = calc_historical_cvar(r, 0.90)
        # CVaR è la media della coda → <= VaR (più negativo o uguale)
        assert cvar <= var

    def test_serie_vuota_nan(self):
        assert np.isnan(calc_historical_cvar(pd.Series(dtype=float)))


class TestBeta:
    def test_beta_proporzionale(self):
        rng = np.random.default_rng(123)
        b = pd.Series(rng.normal(0, 0.01, 500))
        p = 1.5 * b  # beta atteso 1.5 (correlazione perfetta)
        assert calc_beta(p, b) == pytest.approx(1.5, abs=1e-6)

    def test_beta_uno_se_uguale(self):
        rng = np.random.default_rng(1)
        b = pd.Series(rng.normal(0, 0.01, 300))
        assert calc_beta(b.copy(), b.copy()) == pytest.approx(1.0, abs=1e-6)

    def test_varianza_zero_nan(self):
        b = pd.Series([0.0] * 100)
        p = pd.Series(np.random.default_rng(2).normal(0, 0.01, 100))
        assert np.isnan(calc_beta(p, b))


class TestUnderwaterRecovery:
    def test_recupero_completo(self):
        idx = pd.to_datetime(["2020-01-01", "2020-02-01", "2020-06-01", "2020-12-01"])
        # 100 → 80 (underwater) → 100 (recupera il picco) → 120
        res = calc_underwater_recovery(pd.Series([100, 80, 100, 120], index=idx))
        assert res["recovered"] is True
        # underwater dal 2020-01-01 al 2020-06-01
        assert res["max_underwater_days"] == (pd.Timestamp("2020-06-01") - pd.Timestamp("2020-01-01")).days

    def test_non_recuperato_a_fine_periodo(self):
        idx = pd.to_datetime(["2020-01-01", "2020-06-01", "2020-12-01"])
        # 100 → 70 → 90: non torna mai a 100
        res = calc_underwater_recovery(pd.Series([100, 70, 90], index=idx))
        assert res["recovered"] is False
        assert res["max_underwater_days"] > 0

    def test_sempre_crescente_nessun_underwater(self):
        idx = pd.to_datetime(["2020-01-01", "2020-02-01", "2020-03-01"])
        res = calc_underwater_recovery(pd.Series([100, 110, 120], index=idx))
        assert res["recovered"] is True
        assert res["max_underwater_days"] == 0
