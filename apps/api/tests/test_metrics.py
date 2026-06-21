"""
Test unitari per engine/metrics.py.

STRATO 1: Test formule PDF cliente — valori calcolati a mano.
STRATO 2: Test metriche standard.

Eseguire con: pytest tests/ -v
"""

import pytest
import pandas as pd
import numpy as np
from engine.metrics import (
    chameleon_azioni,
    chameleon_bitcoin,
    chameleon_oro,
    chameleon_materie_prime,
    chameleon_portafoglio,
    calc_cagr,
    calc_max_drawdown,
    calc_sharpe_ratio,
    calc_annualized_volatility,
    calc_real_return,
)


# ─────────────────────────────────────────────────────────────────────────────
# STRATO 1 — Formule PDF cliente
# ─────────────────────────────────────────────────────────────────────────────

class TestChameleonAzioni:
    """Fonte: PDF cliente — Formula Azioni = 125 - eta - (tasso_fed * 5) - (delta_tasso * 3)"""

    def test_caso_base(self):
        # 125 - 40 - (5.0 * 5) - (0.0 * 3) = 125 - 40 - 25 - 0 = 60
        result = chameleon_azioni(eta=40, tasso_fed=5.0, delta_tasso=0.0)
        assert result == pytest.approx(60.0, abs=1e-6)

    def test_con_delta_positivo(self):
        # 125 - 35 - (5.25 * 5) - (0.25 * 3) = 125 - 35 - 26.25 - 0.75 = 63.0
        result = chameleon_azioni(eta=35, tasso_fed=5.25, delta_tasso=0.25)
        assert result == pytest.approx(63.0, abs=1e-6)

    def test_clamp_zero_eta_alta_e_tassi_alti(self):
        # 125 - 80 - (10.0 * 5) - (2.0 * 3) = 125 - 80 - 50 - 6 = -11 → clamp a 0
        result = chameleon_azioni(eta=80, tasso_fed=10.0, delta_tasso=2.0)
        assert result == 0.0

    def test_clamp_cento_giovane_senza_tassi(self):
        # 125 - 18 - (0.0 * 5) - (0.0 * 3) = 107 → clamp a 100
        result = chameleon_azioni(eta=18, tasso_fed=0.0, delta_tasso=0.0)
        assert result == 100.0

    def test_delta_negativo_aumenta_azioni(self):
        # 125 - 40 - (5.0 * 5) - (-0.5 * 3) = 125 - 40 - 25 + 1.5 = 61.5
        result = chameleon_azioni(eta=40, tasso_fed=5.0, delta_tasso=-0.5)
        assert result == pytest.approx(61.5, abs=1e-6)


class TestChameleonBitcoin:
    """Fonte: PDF cliente — Bitcoin = max(0, 5 - 10 * ((P_cur/P_ath) - 1)) se post-halving"""

    def test_non_post_halving_sempre_zero(self):
        result = chameleon_bitcoin(30000, 69000, is_post_halving=False)
        assert result == 0.0

    def test_all_ath(self):
        # P_cur = P_ath → ratio = 1 → 5 - 10 * 0 = 5
        result = chameleon_bitcoin(69000, 69000, is_post_halving=True)
        assert result == pytest.approx(5.0, abs=1e-6)

    def test_meta_ath(self):
        # P_cur/P_ath = 0.5 → 5 - 10 * (0.5 - 1) = 5 - 10 * (-0.5) = 5 + 5 = 10
        result = chameleon_bitcoin(34500, 69000, is_post_halving=True)
        assert result == pytest.approx(10.0, abs=1e-6)

    def test_sopra_ath_clamp_zero(self):
        # P_cur > P_ath → ratio > 1 → 5 - 10 * (1.5 - 1) = 5 - 5 = 0
        result = chameleon_bitcoin(103500, 69000, is_post_halving=True)
        assert result == pytest.approx(0.0, abs=1e-6)

    def test_btc_ath_zero_ritorna_zero(self):
        # Edge case: ATH = 0 → divisione per zero → restituisce 0
        result = chameleon_bitcoin(30000, 0, is_post_halving=True)
        assert result == 0.0

    def test_btc_corrente_zero(self):
        # P_cur = 0, P_ath = 69000 → ratio = 0 → 5 - 10*(0-1) = 5 + 10 = 15 → non clampato a max
        # La formula non ha cap superiore, quindi ritorna 15
        result = chameleon_bitcoin(0, 69000, is_post_halving=True)
        assert result == pytest.approx(15.0, abs=1e-6)


class TestChameleonOro:
    """Fonte: PDF cliente — Oro = max(5, min(10, 5 + (1 - tasso_reale/2) * 5))"""

    def test_tasso_reale_zero(self):
        # tasso_reale = 3 - 3 = 0 → 5 + (1 - 0) * 5 = 10 → clamp [5,10] = 10
        result = chameleon_oro(tasso_nominale=3.0, inflazione=3.0)
        assert result == pytest.approx(10.0, abs=1e-6)

    def test_tasso_reale_positivo_alto(self):
        # tasso_reale = 5.25 - 2.0 = 3.25 → 5 + (1 - 3.25/2) * 5 = 5 + (1 - 1.625)*5 = 5 - 3.125 = 1.875 → clamp a 5
        result = chameleon_oro(tasso_nominale=5.25, inflazione=2.0)
        assert result == 5.0

    def test_tasso_reale_negativo_repressione(self):
        # tasso_reale = 1.0 - 6.0 = -5 → 5 + (1 - (-5/2)) * 5 = 5 + (1 + 2.5)*5 = 5 + 17.5 = 22.5 → clamp a 10
        result = chameleon_oro(tasso_nominale=1.0, inflazione=6.0)
        assert result == 10.0

    def test_valore_medio(self):
        # tasso_reale = 5.0 - 3.0 = 2.0 → 5 + (1 - 2/2) * 5 = 5 + 0 = 5 → clamp [5,10] = 5
        result = chameleon_oro(tasso_nominale=5.0, inflazione=3.0)
        assert result == pytest.approx(5.0, abs=1e-6)


class TestChameleonMateriePrime:
    """Fonte: PDF cliente — MP = 0 se tassi in calo, altrimenti max(0, min(10, 5 + (inf-tr)*2))"""

    def test_tassi_in_calo_forza_zero(self):
        result = chameleon_materie_prime(inflazione=6.0, tasso_nominale=4.0, tassi_in_calo=True)
        assert result == 0.0

    def test_inflazione_alta_tassi_stabili(self):
        # tasso_reale = 4.0 - 6.0 = -2.0 → 5 + (6 - (-2)) * 2 = 5 + 16 = 21 → clamp a 10
        result = chameleon_materie_prime(inflazione=6.0, tasso_nominale=4.0, tassi_in_calo=False)
        assert result == 10.0

    def test_inflazione_bassa(self):
        # tasso_reale = 5.0 - 2.0 = 3.0 → 5 + (2 - 3)*2 = 5 - 2 = 3 → clamp [0,10] = 3
        result = chameleon_materie_prime(inflazione=2.0, tasso_nominale=5.0, tassi_in_calo=False)
        assert result == pytest.approx(3.0, abs=1e-6)

    def test_inflazione_zero(self):
        # tasso_reale = 3.0 → 5 + (0 - 3)*2 = 5 - 6 = -1 → clamp a 0
        result = chameleon_materie_prime(inflazione=0.0, tasso_nominale=3.0, tassi_in_calo=False)
        assert result == 0.0


class TestChameleonPortafoglio:
    """Test integrazione: portafoglio completo Chameleon."""

    def test_somma_senza_qe(self):
        """Senza QE, la somma delle allocazioni deve essere <= 100."""
        result = chameleon_portafoglio(
            eta=40, tasso_fed=5.0, delta_tasso=0.0,
            btc_prezzo_corrente=0.0, btc_ath=0.0, is_post_halving=False,
            tasso_nominale=5.0, inflazione=3.0,
            tassi_in_calo=False, qe_attivo=False,
        )
        total = sum(result.values())
        assert total == pytest.approx(100.0, abs=0.01)

    def test_qe_attivo_obbligazioni_zero(self):
        """Con QE attivo, obbligazioni deve essere esattamente 0."""
        result = chameleon_portafoglio(
            eta=40, tasso_fed=0.25, delta_tasso=0.0,
            btc_prezzo_corrente=0.0, btc_ath=0.0, is_post_halving=False,
            tasso_nominale=0.25, inflazione=2.0,
            tassi_in_calo=False, qe_attivo=True,
        )
        assert result["obbligazioni"] == 0.0

    def test_tutte_le_chiavi_presenti(self):
        result = chameleon_portafoglio(
            eta=50, tasso_fed=3.0, delta_tasso=0.0,
            btc_prezzo_corrente=30000.0, btc_ath=69000.0, is_post_halving=True,
            tasso_nominale=3.0, inflazione=2.5,
            tassi_in_calo=False, qe_attivo=False,
        )
        assert set(result.keys()) == {"azioni", "bitcoin", "oro", "materie_prime", "obbligazioni"}


# ─────────────────────────────────────────────────────────────────────────────
# STRATO 2 — Metriche standard
# ─────────────────────────────────────────────────────────────────────────────

class TestCalcCagr:

    def test_raddoppio_in_un_anno(self):
        idx = pd.date_range("2020-01-01", "2021-01-01", periods=2)
        prices = pd.Series([100.0, 200.0], index=idx)
        cagr = calc_cagr(prices)
        assert cagr == pytest.approx(1.0, abs=0.01)

    def test_serie_singola_nan(self):
        idx = pd.date_range("2020-01-01", periods=1, freq="D")
        prices = pd.Series([100.0], index=idx)
        assert np.isnan(calc_cagr(prices))

    def test_serie_vuota_nan(self):
        assert np.isnan(calc_cagr(pd.Series(dtype=float)))

    def test_prezzo_iniziale_zero_nan(self):
        idx = pd.date_range("2020-01-01", "2021-01-01", periods=2)
        prices = pd.Series([0.0, 100.0], index=idx)
        assert np.isnan(calc_cagr(prices))


class TestCalcMaxDrawdown:

    def test_drawdown_classico(self):
        # Picco 150, minimo 80 → (80-150)/150 = -0.4667
        prices = pd.Series([100.0, 150.0, 80.0, 120.0])
        dd = calc_max_drawdown(prices)
        assert dd == pytest.approx(-0.4667, abs=0.001)

    def test_serie_crescente_zero_drawdown(self):
        prices = pd.Series([100.0, 110.0, 120.0, 130.0])
        assert calc_max_drawdown(prices) == pytest.approx(0.0, abs=1e-6)

    def test_serie_vuota_nan(self):
        assert np.isnan(calc_max_drawdown(pd.Series(dtype=float)))


class TestCalcSharpeRatio:

    def test_rendimenti_uniformi_positivi(self):
        returns = pd.Series([0.001] * 252)
        sharpe = calc_sharpe_ratio(returns, risk_free_rate=0.0)
        assert sharpe > 0

    def test_deviazione_zero_nan(self):
        returns = pd.Series([0.001] * 252)
        sharpe = calc_sharpe_ratio(pd.Series([0.0] * 252))
        assert np.isnan(sharpe)

    def test_serie_vuota_nan(self):
        assert np.isnan(calc_sharpe_ratio(pd.Series(dtype=float)))


class TestCalcAnnualizedVolatility:

    def test_serie_costante_zero(self):
        returns = pd.Series([0.01] * 100)
        # std di serie costante = 0
        vol = calc_annualized_volatility(returns)
        assert vol == pytest.approx(0.0, abs=1e-9)

    def test_valori_positivi(self):
        rng = np.random.default_rng(42)
        returns = pd.Series(rng.normal(0.001, 0.01, 252))
        vol = calc_annualized_volatility(returns)
        assert vol > 0.0


class TestCalcRealReturn:

    def test_inflazione_media_3_percent(self):
        # nominal = 20%, avg_inflation = 3% → (1.20 / 1.03) - 1 ≈ 0.1650
        inflation = pd.Series([0.03, 0.03, 0.03])
        real = calc_real_return(0.20, inflation)
        assert real == pytest.approx((1.20 / 1.03) - 1, abs=1e-6)

    def test_inflazione_zero_uguale_nominale(self):
        inflation = pd.Series([0.0, 0.0])
        real = calc_real_return(0.15, inflation)
        assert real == pytest.approx(0.15, abs=1e-6)

    def test_inflazione_vuota_nan(self):
        assert np.isnan(calc_real_return(0.15, pd.Series(dtype=float)))
