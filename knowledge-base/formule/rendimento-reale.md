# Rendimento Reale (corretto per inflazione)

## Definizione

Il rendimento reale è il rendimento di un investimento al netto dell'inflazione. Risponde alla domanda: "Dopo aver pagato l'aumento del costo della vita, quanto ho guadagnato effettivamente?"

## Formula matematica (Fisher)

$$R_{reale} = \frac{1 + R_{nominale}}{1 + \pi} - 1$$

dove:
- $R_{nominale}$ = rendimento nominale del periodo
- $\pi$ = inflazione del periodo (CPI)

## Approssimazione (per inflazione bassa)

$$R_{reale} \approx R_{nominale} - \pi$$

Valida solo per inflazioni < 5-6%. A inflazione alta (es. 9%), l'approssimazione introduce errori significativi.

## Esempio

Anno 2022:
- Rendimento nominale S&P 500: **-18.1%**
- Inflazione CPI USA: **+8.0%**

$$R_{reale} = \frac{1 + (-0.181)}{1 + 0.080} - 1 = \frac{0.819}{1.080} - 1 \approx -24.2\%$$

Il portafoglio ha perso **-24.2%** in termini reali nel 2022 — ben peggio del -18.1% nominale.

## Fonti dati in PortfolioTime

L'inflazione viene scaricata da FRED usando la serie `CPIAUCSL` (Consumer Price Index, All Urban Consumers). È mensile — per confronti su periodi multi-anno si usa la media del periodo.

## Tasso Reale FED

$$T_{reale} = T_{FED} - \pi_{CPI}$$

Quando il tasso reale è negativo (tasso FED < inflazione), si chiama "repressione finanziaria". In questo contesto:
- L'oro tipicamente sale
- Le obbligazioni rendono meno dell'inflazione
- Gli asset reali (immobili, commodity) outperformano

Il Chameleon Portfolio usa esplicitamente il tasso reale nelle formule di Oro e Materie Prime.
