"""Router /portfolio — calcolo allocazione Chameleon in tempo reale."""

from fastapi import APIRouter
from pydantic import BaseModel, Field
from engine.metrics import chameleon_portafoglio

router = APIRouter()


class AllocationRequest(BaseModel):
    eta: int = Field(..., ge=18, le=100)
    tasso_fed: float = Field(..., ge=0.0, le=25.0)
    delta_tasso: float = Field(0.0)
    btc_prezzo_corrente: float = Field(0.0, ge=0.0)
    btc_ath: float = Field(0.0, ge=0.0)
    is_post_halving: bool = False
    tasso_nominale: float = Field(..., ge=0.0, le=25.0)
    inflazione: float = Field(..., ge=-5.0, le=50.0)
    tassi_in_calo: bool = False
    qe_attivo: bool = False


class AllocationResponse(BaseModel):
    allocazione: dict[str, float]
    somma_totale: float
    note: list[str]


@router.post("/allocation", response_model=AllocationResponse)
async def calc_allocation(request: AllocationRequest):
    """Calcola l'allocazione Chameleon per il profilo fornito.

    Questo endpoint è sincrono e < 1ms — nessun dato esterno richiesto.
    Utile per il preview live nel frontend mentre l'utente modifica i parametri.
    """
    allocazione = chameleon_portafoglio(
        eta=request.eta,
        tasso_fed=request.tasso_fed,
        delta_tasso=request.delta_tasso,
        btc_prezzo_corrente=request.btc_prezzo_corrente,
        btc_ath=request.btc_ath,
        is_post_halving=request.is_post_halving,
        tasso_nominale=request.tasso_nominale,
        inflazione=request.inflazione,
        tassi_in_calo=request.tassi_in_calo,
        qe_attivo=request.qe_attivo,
    )

    somma = sum(allocazione.values())
    note: list[str] = []

    if request.qe_attivo:
        note.append("QE attivo: obbligazioni escluse dal portafoglio.")
    if somma < 99.0:
        note.append(f"Somma allocazioni: {somma:.1f}% — la liquidità residua rimane in cash/money market.")
    if not request.is_post_halving:
        note.append("Bitcoin non incluso: non siamo in periodo post-halving.")

    return AllocationResponse(allocazione=allocazione, somma_totale=round(somma, 2), note=note)
