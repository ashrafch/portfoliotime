# Formule Cliente — Chameleon Portfolio

> Estratto da: `formule-cliente-original.pdf`
> Documento: *Chameleon Portfolio - Formule Complete e Regola Stimolo Monetario (QE)*

---

## Sezione 1: Elenco Formule con Notazione Matematica

### Formula 1 — Allocazione Azioni

$$\text{Azioni} = 125 - E - (T_{FED} \times 5) - (\Delta T \times 3)$$

| Parametro | Descrizione |
|-----------|-------------|
| $E$ | Età dell'investitore (anni) |
| $T_{FED}$ | Tasso di interesse corrente FED (in %) |
| $\Delta T$ | Variazione recente del tasso FED (in punti percentuali) |
| Output | Percentuale allocata ad azioni (es. 70 → 70%) |

**Nota:** Il risultato va clampato tra 0 e 100. Non è esplicito nel PDF ma è implicito dalla logica del portafoglio.

---

### Formula 2 — Allocazione Obbligazioni

$$\text{Obbligazioni} = 100\% - (\text{Azioni} + \text{Bitcoin} + \text{Oro} + \text{Materie Prime})$$

**Nota:** Dipende da tutte le altre formule. È l'ultima calcolata — è il "residuo" del portafoglio.
Se in regime QE attivo: **Obbligazioni = 0%** (regola override — vedi Formula 6).

---

### Formula 3 — Allocazione Bitcoin

$$\text{Bitcoin} = \begin{cases} \max\!\left(0,\ 5 - 10 \times \left(\dfrac{P_{cur}}{P_{ath}} - 1\right)\right) & \text{se periodo post-halving} \\ 0 & \text{altrimenti} \end{cases}$$

| Parametro | Descrizione |
|-----------|-------------|
| $P_{cur}$ | Prezzo corrente di Bitcoin (USD) |
| $P_{ath}$ | All-Time High storico di Bitcoin (USD) |
| Output | Percentuale allocata a Bitcoin |

**Interpretazione della formula:**
- Se Bitcoin è esattamente all'ATH: $\text{Bitcoin} = 5 - 10 \times 0 = 5\%$
- Se Bitcoin è al 50% dell'ATH: $\frac{P_{cur}}{P_{ath}} = 0.5$, quindi $5 - 10 \times (0.5 - 1) = 5 - 10 \times (-0.5) = 5 + 5 = 10\%$
- Se Bitcoin è al 150% dell'ATH (nuovo ATH): $5 - 10 \times (1.5 - 1) = 5 - 5 = 0\%$

La formula aumenta l'allocazione quando Bitcoin è lontano dall'ATH (undervalued vs peak) e la riduce quando è vicino o supera il vecchio ATH.

---

### Formula 4 — Allocazione Oro

$$\text{Oro} = \max\!\left(5,\ \min\!\left(10,\ 5 + \left(1 - \dfrac{T_R}{2}\right) \times 5\right)\right)$$

dove: $T_R = T_N - \pi$ (Tasso Reale = Tasso Nominale − Inflazione)

| Parametro | Descrizione |
|-----------|-------------|
| $T_N$ | Tasso nominale corrente (in %, es. 5.0) |
| $\pi$ | Inflazione corrente (in %, es. 3.0) |
| $T_R$ | Tasso reale = $T_N - \pi$ |
| Output | Percentuale allocata ad Oro, nell'intervallo $[5\%, 10\%]$ |

**Soglie esplicite dal PDF:** Min 5%, Max 10%.

**Interpretazione:** Tassi reali negativi → Oro alto (vicino a 10%). Tassi reali alti positivi → Oro basso (vicino a 5%).

---

### Formula 5 — Allocazione Materie Prime

$$\text{MP} = \begin{cases} 0\% & \text{se tassi in calo} \\ \max\!\left(0,\ \min\!\left(10,\ 5 + (\pi - T_R) \times 2\right)\right) & \text{altrimenti} \end{cases}$$

| Parametro | Descrizione |
|-----------|-------------|
| $\pi$ | Inflazione corrente (%) |
| $T_R$ | Tasso reale (%) |
| Output | Percentuale allocata a Materie Prime, in $[0\%, 10\%]$ |

**Nota:** Quando `tassi in calo = True` (il cliente probabilmente intende che il trend dei FED Funds Rate è discendente), l'allocazione è forzata a 0%.

---

### Formula 6 — Regola Stimolo Monetario (QE Override)

In caso di QE attivo da FED, BCE o BOJ:

| Asset | Comportamento |
|-------|---------------|
| Obbligazioni | **Override a 0%** (ignora Formula 2) |
| Azioni | Segue Formula 1 |
| Oro | Segue Formula 4 |
| Materie Prime | Segue Formula 5 |
| Bitcoin | Segue Formula 3 |

**Logica:** In QE si evitano le obbligazioni perché il rialzo dei tassi futuro creerebbe perdite in conto capitale.

---

## Sezione 2: Grafo di Dipendenza tra Formule

```
Input Esterni
│
├── Età (E)
├── Tasso FED corrente (T_FED)
├── Variazione tasso FED (ΔT)
├── Prezzo BTC corrente (P_cur)
├── ATH BTC storico (P_ath)
├── Flag post-halving
├── Tasso nominale (T_N)  ──┐
├── Inflazione (π)         ─┼──► T_R = T_N - π (calcolato internamente)
├── Flag tassi in calo      │
└── Flag QE attivo          │
                            │
Calcolo in ordine:          │
1. T_R = T_N - π            ┘
2. Azioni (Formula 1) ────────────────────────────────────────────────────────────┐
3. Bitcoin (Formula 3) ───────────────────────────────────────────────────────────┤
4. Oro (Formula 4) ───────────────────────────────────────────────────────────────┤
5. Materie Prime (Formula 5) ─────────────────────────────────────────────────────┤
6. Obbligazioni = 100 - (2+3+4+5), poi override a 0 se QE attivo ◄───────────────┘
7. Normalizzazione finale se somma ≠ 100%
```

**Ordine di calcolo obbligatorio:** Azioni → Bitcoin → Oro → Materie Prime → Obbligazioni → [QE Override]

---

## Sezione 3: Parametri di Input Totali (lista unificata senza duplicati)

| Parametro | Tipo | Fonte suggerita | Usato in |
|-----------|------|-----------------|----------|
| `eta` | `int` | Input utente | Formula 1 |
| `tasso_fed` | `float` | FRED (DFF) | Formula 1 |
| `delta_tasso` | `float` | Calcolo su FRED | Formula 1 |
| `btc_prezzo_corrente` | `float` | CoinGecko | Formula 3 |
| `btc_ath` | `float` | CoinGecko | Formula 3 |
| `is_post_halving` | `bool` | Logica data halving | Formula 3 |
| `tasso_nominale` | `float` | FRED (DFF o GS10) | Formula 4, 5 |
| `inflazione` | `float` | FRED (CPIAUCSL) | Formula 4, 5 |
| `tassi_in_calo` | `bool` | Trend FRED | Formula 5 |
| `qe_attivo` | `bool` | Input manuale / news | Formula 6 |

**Nota:** `tasso_fed` e `tasso_nominale` possono coincidere (FED Funds Rate) o differire (es. 10Y Treasury per obbligazioni). Chiarire col cliente.

---

## Sezione 4: Assunzioni e Convenzioni rilevate dal PDF

1. **Frequenza di ricalcolo:** Non specificata. Assunto: mensile (tipico per asset allocation strategica).
2. **Valuta:** Implicita USD. Bitcoin e commodity sono quotati in dollari.
3. **Risk-free rate:** Non usato esplicitamente nelle formule del PDF. Utilizzato solo nelle metriche standard aggiuntive.
4. **"Tassi in calo":** Il cliente usa un flag booleano, non una soglia precisa. Implementazione suggerita: trend degli ultimi 3 mesi del FED Funds Rate (media mobile a 3M in discesa).
5. **"Periodo post-halving":** Bitcoin dimezza le emissioni ogni ~4 anni. Ultimi halving: 2012-11-28, 2016-07-09, 2020-05-11, 2024-04-19. Il cliente considera "post-halving" il periodo di 12-18 mesi successivi.
6. **Somma allocazioni:** Il PDF non specifica esplicitamente che debbano sommare a 100%. La Formula 2 (Obbligazioni come residuo) garantisce la somma a 100 in condizioni normali. In QE (Obbligazioni=0), la somma potrebbe essere < 100 → la liquidità residua rimane in cash/money market.
7. **Clamp impliciti:** La formula Azioni può produrre valori negativi o > 100 → clampare a [0, 100]. Stessa logica per tutte le allocazioni.

---

## Sezione 5: Delta rispetto alle metriche standard

| Aspetto | Standard | Cliente (PDF) | Differenza |
|---------|----------|---------------|------------|
| Allocazione azioni | 100 - Età (regola classica) | 125 - Età - aggiustamenti tassi | Più aggressivo per giovani; sensibile ai tassi FED |
| Allocazione obbligazioni | Complemento fisso | Complemento dinamico + override QE | Le obbligazioni possono andare a 0 in QE |
| Bitcoin | Non incluso nei modelli classici | Incluso, funzione ATH + halving cycle | Formula originale del cliente |
| Oro | Peso fisso (es. 5-10%) | Formula dinamica su tassi reali | Risponde all'inflazione e ai tassi |
| Materie Prime | Non standard | Formula su inflazione-tasso reale | Risponde alla repressione finanziaria |
| CAGR, Sharpe, Drawdown | Metriche output standard | Non nel PDF (servono per valutare la strategia) | Da aggiungere nel motore come Strato 2 |

**Conclusione:** Il cliente ha sviluppato un modello di asset allocation tattica originale, non una rielaborazione di modelli esistenti. Le formule standard (CAGR, Sharpe, Drawdown, Volatilità) sono assenti dal PDF e vanno implementate come metriche di valutazione della strategia.

---

## Sezione 6: Note implementative — traduzione in Python con Pandas/NumPy

```python
# Struttura consigliata per engine/metrics.py

# === STRATO 1: Formule dal PDF cliente ===

def calc_allocazione_azioni(eta: int, tasso_fed: float, delta_tasso: float) -> float:
    """Formula da PDF cliente — Allocazione Azioni
    Formula: Azioni = 125 - eta - (tasso_fed * 5) - (delta_tasso * 3)
    """
    raw = 125 - eta - (tasso_fed * 5) - (delta_tasso * 3)
    return max(0.0, min(100.0, raw))

def calc_allocazione_bitcoin(
    btc_prezzo_corrente: float,
    btc_ath: float,
    is_post_halving: bool
) -> float:
    """Formula da PDF cliente — Allocazione Bitcoin
    Formula: Bitcoin = max(0, 5 - 10 * ((P_cur/P_ath) - 1))  se post-halving
    """
    if not is_post_halving:
        return 0.0
    ratio = btc_prezzo_corrente / btc_ath
    return max(0.0, 5 - 10 * (ratio - 1))

def calc_allocazione_oro(tasso_nominale: float, inflazione: float) -> float:
    """Formula da PDF cliente — Allocazione Oro
    Formula: Oro = max(5, min(10, 5 + (1 - (tasso_reale / 2)) * 5))
    tasso_reale = tasso_nominale - inflazione
    """
    tasso_reale = tasso_nominale - inflazione
    raw = 5 + (1 - (tasso_reale / 2)) * 5
    return max(5.0, min(10.0, raw))

def calc_allocazione_materie_prime(
    inflazione: float,
    tasso_nominale: float,
    tassi_in_calo: bool
) -> float:
    """Formula da PDF cliente — Allocazione Materie Prime
    Formula: 0 se tassi in calo, altrimenti max(0, min(10, 5 + (inflazione - tasso_reale) * 2))
    """
    if tassi_in_calo:
        return 0.0
    tasso_reale = tasso_nominale - inflazione
    raw = 5 + (inflazione - tasso_reale) * 2
    return max(0.0, min(10.0, raw))

def calc_portafoglio_chameleon(
    eta: int,
    tasso_fed: float,
    delta_tasso: float,
    btc_prezzo_corrente: float,
    btc_ath: float,
    is_post_halving: bool,
    tasso_nominale: float,
    inflazione: float,
    tassi_in_calo: bool,
    qe_attivo: bool
) -> dict[str, float]:
    """Formula da PDF cliente — Portafoglio Chameleon completo
    Restituisce le allocazioni percentuali per ogni asset class.
    Ordine calcolo: Azioni → Bitcoin → Oro → MP → Obbligazioni → QE override
    """
    azioni = calc_allocazione_azioni(eta, tasso_fed, delta_tasso)
    bitcoin = calc_allocazione_bitcoin(btc_prezzo_corrente, btc_ath, is_post_halving)
    oro = calc_allocazione_oro(tasso_nominale, inflazione)
    materie_prime = calc_allocazione_materie_prime(inflazione, tasso_nominale, tassi_in_calo)

    if qe_attivo:
        obbligazioni = 0.0
    else:
        obbligazioni = max(0.0, 100.0 - (azioni + bitcoin + oro + materie_prime))

    return {
        "azioni": azioni,
        "bitcoin": bitcoin,
        "oro": oro,
        "materie_prime": materie_prime,
        "obbligazioni": obbligazioni,
    }
```

**Edge case importanti:**
- `btc_ath` = 0 → divisione per zero → restituire 0
- Somma allocazioni > 100 (raro ma possibile con formula Azioni alta) → normalizzare proporzionalmente
- `inflazione` molto alta → Materie Prime al massimo 10%, Oro al massimo 10%
- `eta` < 25 → Azioni potrebbe superare 100 → clamp necessario
- `delta_tasso` negativo (tassi in calo) → aumenta allocazione azioni

**Dipendenze Python:** Solo `numpy` e `pandas` per le metriche standard. Le formule Chameleon usano solo aritmetica float pura — zero dipendenze aggiuntive.
