# Maximum Drawdown (Max DD)

## Definizione

Il Maximum Drawdown misura la perdita massima dal picco al minimo successivo nella storia di un investimento. Risponde alla domanda: "Qual è la perdita peggiore che avrei subito se avessi comprato nel momento peggiore?"

## Formula matematica

$$\text{MDD} = \min_{t \in [0,T]} \left( \frac{P_t - \max_{s \leq t}(P_s)}{\max_{s \leq t}(P_s)} \right)$$

dove:
- $P_t$ = prezzo al tempo $t$
- $\max_{s \leq t}(P_s)$ = massimo prezzo fino al tempo $t$ (rolling peak)

## Esempio pratico

Serie di prezzi: 100 → 150 → 80 → 120

- Picco: 150
- Minimo successivo: 80
- MDD = (80 - 150) / 150 = **-46.7%**

## Interpretazione pratica

| Max Drawdown | Caratteristica |
|-------------|----------------|
| 0% - 10% | Investimento molto conservativo |
| 10% - 20% | Moderato (portafogli bilanciati) |
| 20% - 40% | Aggressivo (azionario puro) |
| 40% - 70% | Molto aggressivo (growth, small cap, crypto) |
| > 70% | Speculativo (crypto altcoin, singole azioni tech) |

## Riferimenti storici

| Asset/Indice | Max Drawdown storico |
|-------------|----------------------|
| S&P 500 (2007-2009) | -57% |
| NASDAQ (2000-2002) | -78% |
| Bitcoin (2017-2018) | -84% |
| Oro (1980-2000) | -65% |

## Relazione con il recovery time

Il drawdown non include il tempo di recupero, ma è fondamentale sapere quanto tempo ci vuole per tornare al precedente massimo:
- S&P 500 crash 2008: 5 anni e mezzo per recuperare
- NASDAQ crash 2000: **15 anni** per recuperare il massimo del 2000

## Importanza per il Chameleon Portfolio

Il Max Drawdown è la metrica di rischio principale per valutare la protezione del portafoglio negli scenari storici negativi. Un buon portafoglio Chameleon dovrebbe avere MDD inferiore al benchmark (SPY) negli scenari bear.
