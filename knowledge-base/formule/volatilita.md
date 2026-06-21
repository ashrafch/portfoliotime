# Volatilità Annualizzata

## Definizione

La volatilità annualizzata misura la variabilità dei rendimenti di un investimento su base annua. È la deviazione standard dei rendimenti giornalieri moltiplicata per la radice quadrata del numero di giorni di trading per anno.

## Formula matematica

$$\sigma_{annua} = \sigma_{giornaliera} \times \sqrt{252}$$

dove:

$$\sigma_{giornaliera} = \sqrt{\frac{1}{n-1} \sum_{i=1}^{n} (r_i - \bar{r})^2}$$

- $r_i$ = rendimento giornaliero del giorno $i$
- $\bar{r}$ = media dei rendimenti giornalieri
- $n$ = numero di osservazioni

## Volatilità tipiche per asset class

| Asset | Volatilità annualizzata tipica |
|-------|-------------------------------|
| T-Bill USA | 0.5% - 1% |
| Bond 10Y USA | 5% - 8% |
| S&P 500 | 15% - 20% |
| Small Cap | 20% - 30% |
| Oro | 15% - 20% |
| Bitcoin | 60% - 100% |
| Singole azioni tech | 30% - 70% |

## Il VIX

Il VIX è l'indice di volatilità implicita del S&P 500, derivato dai prezzi delle opzioni. Misura la volatilità attesa dal mercato nei prossimi 30 giorni:
- VIX < 20: mercato calmo
- VIX 20-30: preoccupazione
- VIX > 40: panico (2008, 2020)
- VIX = 85: massimo storico (marzo 2020)

## Relazione con il Sharpe Ratio

La volatilità è il denominatore del Sharpe Ratio. Un portafoglio con alta volatilità deve avere rendimenti proporzionalmente più alti per ottenere lo stesso Sharpe di uno a bassa volatilità.

## Volatilità non è rischio

Distinzione importante: la volatilità misura la variabilità statistica, non il rischio di perdita permanente. Bitcoin ha volatilità al 80% ma non è andato a zero. Alcune obbligazioni "sicure" hanno volatilità bassa ma rischio di default reale.
