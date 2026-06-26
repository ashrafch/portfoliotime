"""
Generazione narrativa contestuale.

R1: I numeri arrivano SEMPRE dal motore. Qui si genera solo l'interpretazione.
Se ANTHROPIC_API_KEY è configurata → narrativa via Claude.
Altrimenti → narrativa deterministica da template basata sui numeri calcolati.
"""

from __future__ import annotations

import math
from config import get_settings
from engine.simulator import SimulationInput, SimulationResult

settings = get_settings()


def _pct(x: float | None) -> str:
    if x is None or (isinstance(x, float) and math.isnan(x)):
        return "n/d"
    return f"{x * 100:+.1f}%"


def _num(x: float | None) -> str:
    if x is None or (isinstance(x, float) and math.isnan(x)):
        return "n/d"
    return f"{x:.2f}"


def build_narrative(sim_input: SimulationInput, result: SimulationResult, profile=None) -> str:
    """Restituisce una narrativa in italiano. Prova Claude, poi fallback template.

    profile (InvestorProfile, opzionale) personalizza l'interpretazione.
    """
    if settings.anthropic_api_key:
        try:
            return _claude_narrative(sim_input, result, profile)
        except Exception:  # noqa: BLE001 — fallback robusto se l'API non risponde
            pass
    return _template_narrative(sim_input, result, profile)


def _profile_note(profile, result) -> str:
    """Frase personalizzata sul profilo di rischio dell'utente."""
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


def _claude_narrative(sim_input: SimulationInput, result: SimulationResult, profile=None) -> str:
    """Genera la narrativa con Claude passando SOLO numeri già calcolati (R1)."""
    import anthropic

    client = anthropic.Anthropic(api_key=settings.anthropic_api_key)
    facts = {
        "periodo": f"{sim_input.date_from} → {sim_input.date_to}",
        "eta": sim_input.eta,
        "profilo_rischio": getattr(profile, "risk_profile", None),
        "obiettivo": getattr(profile, "goal", None),
        "tipo_allocazione": result.allocation_source,
        "allocazione_pct": result.allocazione,
        "rendimento_totale": result.total_return,
        "cagr": result.cagr,
        "volatilita_annua": result.annualized_volatility,
        "max_drawdown": result.max_drawdown,
        "sharpe": result.sharpe_ratio,
        "rendimento_reale": result.real_return,
        "benchmark_rendimento_totale": result.benchmark_total_return,
        "qe_attivo": sim_input.qe_attivo,
        "tassi_in_calo": sim_input.tassi_in_calo,
        "post_halving": sim_input.is_post_halving,
    }
    prompt = (
        "Sei un analista finanziario. Interpreta in italiano (max 150 parole) i seguenti "
        "RISULTATI GIÀ CALCOLATI di una simulazione di portafoglio. NON inventare numeri, "
        "usa solo quelli forniti. Concludi che non è una raccomandazione d'investimento.\n\n"
        f"DATI: {facts}"
    )
    msg = client.messages.create(
        model=settings.claude_model,
        max_tokens=settings.claude_max_tokens,
        messages=[{"role": "user", "content": prompt}],
    )
    return msg.content[0].text.strip()
