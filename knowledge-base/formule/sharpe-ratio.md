# Sharpe Ratio

## Definizione

Il Sharpe Ratio misura il rendimento extra ottenuto per ogni unità di rischio aggiuntiva assunta. È la metrica standard per confrontare investimenti con diversi profili rischio/rendimento su base aggiustata per il rischio.

## Formula matematica

$$\text{Sharpe} = \frac{R_p - R_f}{\sigma_p} \times \sqrt{252}$$

dove:
- $R_p$ = rendimento medio periodico del portafoglio
- $R_f$ = tasso risk-free periodico (es. T-Bill a 3 mesi / 252)
- $\sigma_p$ = deviazione standard dei rendimenti periodici
- $\sqrt{252}$ = fattore di annualizzazione (252 giorni di trading per anno)

## Interpretazione

| Sharpe Ratio | Interpretazione |
|-------------|-----------------|
| < 0 | Peggio del risk-free — inutile |
| 0 - 0.5 | Scarso |
| 0.5 - 1.0 | Accettabile |
| 1.0 - 2.0 | Buono |
| 2.0 - 3.0 | Molto buono |
| > 3.0 | Eccellente (raro in mercati efficienti) |

## Esempio pratico

Portafoglio con:
- Rendimento medio giornaliero: 0.06% (≈15% annuo)
- Deviazione standard giornaliera: 1.0%
- Risk-free rate annuale: 3% (→ 0.012% al giorno)

$$\text{Sharpe} = \frac{0.06\% - 0.012\%}{1.0\%} \times \sqrt{252} = 0.048 \times 15.87 \approx 0.76$$

## Limiti

- Assume distribuzione normale dei rendimenti (crypto e azioni hanno code spesse — non normale)
- Penalizza la volatilità positiva (upside) quanto quella negativa (downside) → Sortino Ratio è meglio in questi casi
- Il risk-free rate cambia nel tempo — confronti tra periodi diversi possono essere distorti

## Vs Sortino Ratio

Il Sortino divide per la sola downside deviation invece della volatilità totale — più equo per asset con alta volatilità positiva come Bitcoin.
