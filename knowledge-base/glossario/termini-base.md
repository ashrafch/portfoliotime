# Glossario — Termini Base

## A

**All-Time High (ATH):** Il prezzo massimo mai raggiunto da un asset nella sua storia. Nel Chameleon Portfolio, l'ATH di Bitcoin è parametro diretto della formula di allocazione.

**Asset Allocation:** La distribuzione del capitale tra diverse classi di investimento (azioni, obbligazioni, oro, ecc.). Il Chameleon Portfolio calcola l'asset allocation in modo dinamico in base all'età, ai tassi e al contesto macro.

**Asset Class:** Categoria omogenea di investimenti con comportamento simile: azioni, obbligazioni, oro, materie prime, crypto.

## B

**Bear Market:** Mercato in calo di almeno il 20% dai massimi. La durata media storica è 14 mesi.

**Bitcoin Halving:** Evento che dimezza la ricompensa dei miner di Bitcoin ogni ~210.000 blocchi (~4 anni). Date storiche: nov 2012, lug 2016, mag 2020, apr 2024. Storicamente associato a bull market 12-18 mesi dopo.

**Benchmark:** L'indice di riferimento contro cui si misura la performance di un portafoglio. Default in PortfolioTime: SPY (S&P 500 ETF).

**Bull Market:** Mercato in crescita di almeno il 20% dai minimi.

## C

**CAGR:** Compound Annual Growth Rate — tasso di crescita annuale composto. Vedi `formule/cagr.md`.

**Cash:** Liquidità in valuta. Nel Chameleon Portfolio, la quota non allocata tra le 5 asset class rimane in cash/money market.

**CPI:** Consumer Price Index — l'indice dei prezzi al consumo usato per misurare l'inflazione. FRED serie: `CPIAUCSL`.

## D

**Drawdown:** Perdita dal picco al minimo successivo. Vedi `formule/max-drawdown.md`.

**Duration:** Misura la sensibilità di un'obbligazione ai movimenti dei tassi. Un'obbligazione con duration 10 perde ~10% se i tassi salgono dell'1%.

## E

**ETF (Exchange Traded Fund):** Fondo quotato in borsa che replica un indice. SPY replica l'S&P 500, TLT i Treasury USA a 20+ anni, GLD l'oro, GSG le commodity.

## F

**FED (Federal Reserve):** Banca centrale degli USA. Controlla il Federal Funds Rate — il parametro principale della formula Chameleon per le azioni.

**Federal Funds Rate:** Il tasso di interesse overnight interbancario USA, deciso dalla FED. Principale strumento di politica monetaria.

**FRED:** Federal Reserve Economic Data — database di serie economiche gratuite della FED di St. Louis. URL: https://fred.stlouisfed.org/

## H

**Halving:** Vedi Bitcoin Halving.

## I

**Inflazione:** Aumento generale dei prezzi nel tempo. Misurata dal CPI. Alta inflazione → repressione finanziaria → favorisce oro e commodity.

## M

**Max Drawdown:** Vedi `formule/max-drawdown.md`.

## P

**Post-Halving:** Periodo di 12-18 mesi successivo a un halving Bitcoin. Nel Chameleon Portfolio, solo in questo periodo Bitcoin viene allocato in portafoglio.

## Q

**QE (Quantitative Easing):** Politica monetaria non convenzionale in cui la banca centrale acquista asset (bond, MBS) per immettere liquidità. In QE attivo, il Chameleon Portfolio azzeea le obbligazioni (regola override).

## R

**Risk-Free Rate:** Il rendimento teorico di un investimento privo di rischio. Usato come baseline nel Sharpe Ratio. In pratica: T-Bill USA a 3 mesi.

## S

**Sharpe Ratio:** Rapporto rendimento/rischio aggiustato. Vedi `formule/sharpe-ratio.md`.

**SPY:** ETF che replica l'indice S&P 500. Ticker principale di benchmark in PortfolioTime.

## T

**Tasso Reale:** Tasso nominale meno inflazione. Formula Chameleon usa il tasso reale per calcolare Oro e Materie Prime.

**TLT:** ETF iShares 20+ Year Treasury Bond — usato come proxy obbligazioni a lunga duration.

## V

**VIX:** Indice di volatilità implicita del S&P 500. Detto "indice della paura". VIX > 40 indica panico.

**Volatilità:** Deviazione standard dei rendimenti, misura del rischio. Vedi `formule/volatilita.md`.
