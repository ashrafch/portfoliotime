# CAGR — Compound Annual Growth Rate

## Definizione

Il CAGR è il tasso di crescita annuale composto che un investimento avrebbe dovuto avere per crescere dal valore iniziale al valore finale in un dato periodo di tempo, assumendo che i rendimenti vengano reinvestiti ogni anno.

## Formula matematica

$$\text{CAGR} = \left(\frac{P_{end}}{P_{start}}\right)^{\frac{1}{n}} - 1$$

dove:
- $P_{end}$ = valore finale dell'investimento
- $P_{start}$ = valore iniziale dell'investimento
- $n$ = numero di anni del periodo

## Esempio pratico

Investimento iniziale: €10.000
Valore finale dopo 5 anni: €16.105

$$\text{CAGR} = \left(\frac{16.105}{10.000}\right)^{\frac{1}{5}} - 1 = 1.6105^{0.2} - 1 \approx 10\%$$

## Quando usarlo

Il CAGR è utile per:
- Confrontare performance di investimenti su periodi diversi
- "Levigare" la volatilità annuale mostrando la crescita media composta
- Confrontare portafogli vs benchmark nello stesso periodo

## Limiti

- Non mostra la volatilità del percorso (un portafoglio che va -50% e poi +100% ha CAGR 0% ma percorso drammatico)
- È un numero singolo — non descrive la distribuzione dei rendimenti
- Non considera i contributi intermedi (non è un IRR)

## Relazione con altre metriche

Il CAGR da solo non basta: affiancarlo sempre con Max Drawdown (quanto si perde lungo il percorso) e Sharpe Ratio (quanto rendimento per unità di rischio).
