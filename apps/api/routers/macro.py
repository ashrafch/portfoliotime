"""
Router /macro — dati macroeconomici reali da FRED per pre-compilare le simulazioni.

Se FRED_API_KEY non è configurata, restituisce source="none" e il frontend
mantiene i valori di default (il prodotto resta pienamente funzionante).
"""

from fastapi import APIRouter, Depends
from datetime import date
from pydantic import BaseModel

from security import get_current_user
from models.user import User
from data import fred_client

router = APIRouter()


class MacroSuggestion(BaseModel):
    source: str  # "fred" | "none"
    tasso_fed: float | None = None
    delta_tasso: float | None = None
    tasso_nominale: float | None = None
    inflazione: float | None = None
    tassi_in_calo: bool | None = None
    message: str | None = None


@router.get("/suggest", response_model=MacroSuggestion)
async def suggest_macro(
    date_from: str,
    date_to: str,
    _: User = Depends(get_current_user),
):
    """Suggerisce i parametri macro reali (tasso FED, inflazione, ecc.) per il periodo."""
    # Validazione date
    try:
        date.fromisoformat(date_from)
        date.fromisoformat(date_to)
    except ValueError:
        return MacroSuggestion(source="none", message="Date non valide")

    if not fred_client.is_configured():
        return MacroSuggestion(
            source="none",
            message="FRED non configurato: imposta FRED_API_KEY per i dati storici reali.",
        )

    try:
        snap = await fred_client.macro_snapshot(date_from, date_to)
    except Exception as e:  # noqa: BLE001
        return MacroSuggestion(source="none", message=f"FRED non raggiungibile: {e}")

    if snap is None:
        return MacroSuggestion(source="none", message="Dati FRED non disponibili per il periodo.")

    return MacroSuggestion(**snap)
