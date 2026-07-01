"""
Generazione narrativa contestuale.

R1: I numeri arrivano SEMPRE dal motore. Qui si genera solo l'interpretazione.
Se ANTHROPIC_API_KEY è configurata → narrativa via Claude (ai.client, asincrono).
Altrimenti (o su errore/rifiuto) → narrativa deterministica da template.
"""

from __future__ import annotations

import math
from config import get_settings
from engine.simulator import SimulationInput, SimulationResult
from ai import client as ai_client

settings = get_settings()

# Istruzioni di sistema: definiscono ruolo, lunghezza, tono e i vincoli R1.
_SYSTEM_PROMPT = (
    "Sei un analista finanziario. Il tuo compito è interpretare in italiano, in modo "
    "chiaro e comprensibile, i risultati GIÀ CALCOLATI di una simulazione di portafoglio.\n"
    "Regole tassative:\n"
    "- Usa esclusivamente i numeri forniti nei DATI. NON inventare, arrotondare in modo "
    "diverso, né dedurre altri numeri.\n"
    "- Non dare consigli d'investimento personalizzati.\n"
    "- Spiega cosa significano i risultati (rendimento, rischio, confronto col mercato), "
    "collegandoli al contesto e, se presente, al profilo dell'utente.\n"
    "- Massimo ~130 parole, un solo paragrafo, niente elenchi puntati.\n"
    "- Chiudi ricordando che è un'analisi educativa su dati storici, non una raccomandazione."
)


def _pct(x: float | None) -> str:
    if x is None or (isinstance(x, float) and math.isnan(x)):
        return "n/d"
    return f"{x * 100:+.1f}%"


def _num(x: float | None) -> str:
    if x is None or (isinstance(x, float) and math.isnan(x)):
        return "n/d"
    return f"{x:.2f}"


async def build_narrative(sim_input: SimulationInput, result: SimulationResult, profile=None) -> str:
    """Narrativa in italiano. Prova Claude (async); su assenza chiave/errore usa il template.

    profile (InvestorProfile, opzionale) personalizza l'interpretazione.
    """
    text = await ai_client.generate(_SYSTEM_PROMPT, _facts(sim_input, result, profile))
    return text or _template_narrative(sim_input, result, profile)


def _facts(sim_input: SimulationInput, result: SimulationResult, profile) -> str:
    """Costruisce il blocco DATI passato a Claude — SOLO valori già calcolati (R1)."""
    lines = [
        f"periodo: {sim_input.date_from} → {sim_input.date_to}",
        f"eta_investitore: {sim_input.eta}",
        f"tipo_allocazione: {result.allocation_source}",
        f"allocazione_%: {result.allocazione}",
        f"rendimento_totale: {_pct(result.total_return)}",
        f"cagr_annuo: {_pct(result.cagr)}",
        f"volatilita_annua: {_pct(result.annualized_volatility)}",
        f"max_drawdown: {_pct(result.max_drawdown)}",
        f"sharpe_ratio: {_num(result.sharpe_ratio)}",
        f"rendimento_reale: {_pct(result.real_return)}",
        f"benchmark_SP500_rendimento_totale: {_pct(result.benchmark_total_return)}",
        f"contesto_QE_attivo: {sim_input.qe_attivo}",
        f"contesto_tassi_in_calo: {sim_input.tassi_in_calo}",
        f"contesto_post_halving_BTC: {sim_input.is_post_halving}",
    ]
    if profile is not None:
        risk = getattr(profile, "risk_profile", None)
        goal = getattr(profile, "goal", "") or ""
        if risk:
            lines.append(f"profilo_rischio_utente: {risk}")
        if goal:
            lines.append(f"obiettivo_utente: {goal}")
    return "DATI (già calcolati dal motore, non modificarli):\n" + "\n".join(lines)


def _profile_note(profile, result) -> str:
    """Frase personalizzata sul profilo di rischio dell'utente (per il template)."""
    if profile is None:
        return ""
    risk = getattr(profile, "risk_profile", None)
    goal = getattr(profile, "goal", "") or ""
    if not risk:
        return ""

    dd = result.max_drawdown
    note = f" Per un profilo «{risk}»"
    if risk == "conservativo" and isinstance(dd, float) and not math.isnan(dd) and dd < -0.25:
        note += ", il drawdown registrato è elevato rispetto alla tua tolleranza al rischio"
    elif risk == "aggressivo":
        note += ", questo livello di rischio è in linea con le tue preferenze"
    else:
        note += ", il profilo rischio/rendimento appare bilanciato"
    if goal:
        note += f"; obiettivo dichiarato: {goal}"
    return note + "."


def _template_narrative(sim_input: SimulationInput, result: SimulationResult, profile=None) -> str:
    """Fallback deterministico: interpretazione costruita dai numeri, senza AI."""
    alloc = result.allocazione
    top_asset = max(alloc, key=alloc.get) if alloc else "n/d"
    alloc_kind = "personalizzata" if result.allocation_source == "custom" else "Chameleon"

    vs_bench = ""
    if not (isinstance(result.benchmark_total_return, float) and math.isnan(result.benchmark_total_return)):
        delta = result.total_return - result.benchmark_total_return
        verbo = "sovraperformato" if delta >= 0 else "sottoperformato"
        vs_bench = (
            f" Rispetto al benchmark S&P 500 ({_pct(result.benchmark_total_return)}), "
            f"il portafoglio ha {verbo} di {_pct(abs(delta)).replace('+','')}."
        )

    regime = []
    if sim_input.qe_attivo:
        regime.append("stimolo monetario (QE) attivo, con esclusione delle obbligazioni")
    if sim_input.tassi_in_calo:
        regime.append("tassi in calo")
    if sim_input.is_post_halving:
        regime.append("fase post-halving di Bitcoin")
    regime_txt = (" Contesto: " + ", ".join(regime) + ".") if regime else ""

    return (
        f"Nel periodo {sim_input.date_from} → {sim_input.date_to}, l'allocazione {alloc_kind} "
        f"per un investitore di {sim_input.eta} anni ha prodotto un rendimento totale di "
        f"{_pct(result.total_return)} (CAGR {_pct(result.cagr)}), con una volatilità annualizzata "
        f"del {_pct(result.annualized_volatility)} e un drawdown massimo di {_pct(result.max_drawdown)}. "
        f"Lo Sharpe ratio è {_num(result.sharpe_ratio)} e il rendimento reale (al netto di "
        f"un'inflazione stimata del {sim_input.inflazione:.1f}%) è {_pct(result.real_return)}. "
        f"La componente con peso maggiore è '{top_asset}' ({alloc.get(top_asset, 0):.1f}%)."
        f"{vs_bench}{regime_txt}{_profile_note(profile, result)} "
        f"Nota: tutti i valori sono calcolati dal motore finanziario su dati di mercato reali; "
        f"questa è un'interpretazione, non una raccomandazione d'investimento."
    )
