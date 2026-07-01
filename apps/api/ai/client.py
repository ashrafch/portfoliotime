"""
Client AI (Anthropic Claude) — wrapper asincrono, sicuro e opzionale.

Scelte professionali (vedi docs/GUIDA-SVILUPPATORE.md § AI):
- SDK ufficiale `anthropic`, client ASINCRONO (`AsyncAnthropic`): non blocca
  l'event loop di FastAPI (il vecchio client sincrono lo bloccava).
- Nessun parametro di sampling (temperature/top_p/top_k) e nessun `thinking`:
  il compito è una sintesi breve e va servita velocemente nel percorso della
  request; così il codice è anche portabile su tutti i modelli (opus-4-8,
  sonnet-4-6, ...), alcuni dei quali rifiutano quei parametri.
- Guardrail (R1): il modello riceve SOLO fatti/numeri già calcolati dal motore
  e li interpreta; non genera mai valori numerici.
- Robustezza: se la chiave non è configurata, se l'API dà errore, o se la
  risposta è un rifiuto (`stop_reason == "refusal"`), restituisce None e il
  chiamante usa un fallback deterministico. Nessuna eccezione propagata.
"""

from __future__ import annotations

import logging
from typing import Optional

from config import get_settings

settings = get_settings()
logger = logging.getLogger("portfoliotime.ai")

# Client riusato tra le richieste (connessioni HTTP in pool). Creato pigramente.
_client = None


def is_configured() -> bool:
    """True se è impostata una vera ANTHROPIC_API_KEY (non un placeholder)."""
    key = settings.anthropic_api_key or ""
    return key.startswith("sk-") and "INSERISCI" not in key


def _get_client():
    global _client
    if _client is None:
        from anthropic import AsyncAnthropic

        _client = AsyncAnthropic(
            api_key=settings.anthropic_api_key,
            timeout=float(settings.http_timeout_seconds),
            max_retries=2,  # ritenta automaticamente 429/5xx/errori di rete
        )
    return _client


async def generate(system: str, user: str, max_tokens: Optional[int] = None) -> Optional[str]:
    """Genera testo con Claude. Restituisce None se non configurato o su errore.

    Args:
        system: istruzioni di sistema (ruolo, vincoli, regole R1).
        user: contenuto della richiesta (SOLO fatti/numeri già calcolati).
        max_tokens: cap output; default da config (breve, no rischio timeout).
    """
    if not is_configured():
        return None

    try:
        client = _get_client()
        message = await client.messages.create(
            model=settings.claude_model,
            max_tokens=max_tokens or settings.claude_max_tokens,
            system=system,
            messages=[{"role": "user", "content": user}],
        )

        # Gestione esplicita del rifiuto di sicurezza (HTTP 200, stop_reason refusal)
        if getattr(message, "stop_reason", None) == "refusal":
            logger.warning("Claude ha rifiutato la richiesta (stop_reason=refusal).")
            return None

        text = "".join(
            block.text for block in message.content if getattr(block, "type", None) == "text"
        ).strip()
        return text or None

    except Exception as exc:  # noqa: BLE001 — l'AI è opzionale: mai far fallire la request
        logger.warning("Chiamata a Claude fallita, uso il fallback: %s", exc)
        return None
