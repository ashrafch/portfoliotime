"""Test dell'integrazione AI: configurazione, guardrail R1, fallback."""

import math
import pytest
import pandas as pd
import numpy as np

from ai import client as ai_client
from engine import narrative
from engine.simulator import SimulationInput, run_simulation


def _prices(n=400, seed=3):
    rng = np.random.default_rng(seed)
    idx = pd.date_range("2020-01-01", periods=n, freq="B")
    return pd.DataFrame(
        {t: 100 * (1 + rng.normal(0.0003, 0.01, n)).cumprod() for t in ["SPY", "TLT", "GLD", "GSG"]},
        index=idx,
    )


def _input(**kw):
    d = dict(
        eta=40, tasso_fed=5.0, delta_tasso=0.0, btc_prezzo_corrente=0, btc_ath=0,
        is_post_halving=False, tasso_nominale=5.0, inflazione=3.0, tassi_in_calo=False,
        qe_attivo=False, date_from="2020-01-01", date_to="2021-08-01",
    )
    d.update(kw)
    return SimulationInput(**d)


class TestIsConfigured:
    def test_placeholder_non_valido(self, monkeypatch):
        monkeypatch.setattr(ai_client.settings, "anthropic_api_key", "sk-ant-INSERISCI_QUI")
        assert ai_client.is_configured() is False

    def test_vuoto_non_valido(self, monkeypatch):
        monkeypatch.setattr(ai_client.settings, "anthropic_api_key", "")
        assert ai_client.is_configured() is False

    def test_chiave_valida(self, monkeypatch):
        monkeypatch.setattr(ai_client.settings, "anthropic_api_key", "sk-ant-abc123realkey")
        assert ai_client.is_configured() is True


class TestGenerateFallback:
    async def test_none_se_non_configurato(self, monkeypatch):
        monkeypatch.setattr(ai_client, "is_configured", lambda: False)
        out = await ai_client.generate("sys", "user")
        assert out is None


class TestBuildNarrative:
    async def test_usa_template_senza_chiave(self, monkeypatch):
        # forza "non configurato" → deve usare il template deterministico
        monkeypatch.setattr(narrative.ai_client, "is_configured", lambda: False)
        prices = _prices()
        result = run_simulation(_input(), prices)
        text = await narrative.build_narrative(_input(), result)
        assert "raccomandazione" in text.lower()
        assert "%" in text  # contiene i numeri del template

    async def test_usa_claude_se_disponibile(self, monkeypatch):
        # simula una risposta Claude senza rete
        async def fake_generate(system, user, max_tokens=None):
            assert "non inventare" in system.lower() or "usa esclusivamente" in system.lower()
            return "Interpretazione generata dall'AI."
        monkeypatch.setattr(narrative.ai_client, "generate", fake_generate)
        prices = _prices()
        result = run_simulation(_input(), prices)
        text = await narrative.build_narrative(_input(), result)
        assert text == "Interpretazione generata dall'AI."

    async def test_fallback_se_claude_ritorna_none(self, monkeypatch):
        async def fake_generate(system, user, max_tokens=None):
            return None  # es. errore o refusal
        monkeypatch.setattr(narrative.ai_client, "generate", fake_generate)
        prices = _prices()
        result = run_simulation(_input(), prices)
        text = await narrative.build_narrative(_input(), result)
        assert "raccomandazione" in text.lower()  # template


class TestR1Guardrail:
    def test_facts_contengono_solo_numeri_calcolati(self):
        prices = _prices()
        result = run_simulation(_input(), prices)
        facts = narrative._facts(_input(), result, None)
        # i fatti riportano i numeri del motore, non testo inventato
        assert "rendimento_totale:" in facts
        assert "max_drawdown:" in facts
        assert "già calcolati" in facts

    def test_facts_includono_profilo_se_presente(self):
        class P:
            risk_profile = "conservativo"
            goal = "pensione"
        prices = _prices()
        result = run_simulation(_input(), prices)
        facts = narrative._facts(_input(), result, P())
        assert "profilo_rischio_utente: conservativo" in facts
        assert "obiettivo_utente: pensione" in facts
