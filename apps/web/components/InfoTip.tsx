"use client";

import { useState } from "react";

// Definizioni in linguaggio semplice (1 frase) per chi non è esperto.
export const GLOSSARY: Record<string, string> = {
  total_return: "Quanto è cresciuto (o sceso) il portafoglio in tutto il periodo, in percentuale.",
  cagr: "Il rendimento medio per anno, come se fosse costante: utile per confrontare periodi di durata diversa.",
  max_drawdown: "La perdita massima dal punto più alto al più basso: il momento peggiore che avresti vissuto.",
  annualized_volatility: "Quanto oscilla il valore in un anno tipico: più è alta, più il percorso è movimentato.",
  sharpe_ratio: "Rendimento ottenuto per ogni unità di rischio. Sopra 1 è buono, sopra 2 è molto buono.",
  sortino_ratio: "Come lo Sharpe, ma conta solo le oscillazioni negative: premia chi rende senza grandi cadute.",
  calmar_ratio: "Rendimento annuo diviso la perdita massima: quanto guadagni rispetto al dolore peggiore.",
  var_95: "Nel 5% dei giorni peggiori si perde più di questa percentuale (in un singolo giorno).",
  cvar_95: "La perdita media proprio in quei giorni peggiori: più severa del VaR.",
  beta: "Quanto si muove rispetto al mercato (S&P 500). 1 = come il mercato, sotto 1 = più tranquillo.",
  real_return: "Il rendimento al netto dell'inflazione: il potere d'acquisto realmente guadagnato.",
  recovery: "Quanto tempo il portafoglio è rimasto sotto il suo massimo precedente prima di recuperarlo.",
  money_return: "Rendimento sul totale effettivamente versato (versamenti inclusi). Diverso dal rendimento della strategia.",
};

export default function InfoTip({ term, label }: { term?: keyof typeof GLOSSARY | string; label?: string }) {
  const [open, setOpen] = useState(false);
  const text = label ?? (term ? GLOSSARY[term as string] : "");
  if (!text) return null;

  return (
    <span className="relative inline-flex">
      <button
        type="button"
        onClick={() => setOpen((o) => !o)}
        onMouseEnter={() => setOpen(true)}
        onMouseLeave={() => setOpen(false)}
        aria-label="Spiegazione"
        className="flex h-4 w-4 items-center justify-center rounded-full border border-slate-600 text-[10px] text-slate-400 hover:border-green-500 hover:text-green-400"
      >
        i
      </button>
      {open && (
        <span className="absolute bottom-full left-1/2 z-20 mb-1.5 w-56 -translate-x-1/2 rounded-md border border-slate-700 bg-slate-800 p-2.5 text-xs font-normal leading-snug text-slate-200 shadow-lg">
          {text}
        </span>
      )}
    </span>
  );
}
