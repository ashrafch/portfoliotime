"use client";

import { useEffect, useState } from "react";
import Link from "next/link";
import { apiRequest } from "@/lib/api";
import { pct } from "@/lib/format";
import type { CategoryGuidance } from "@/lib/types";

const COLORS: Record<string, string> = {
  azioni: "border-green-700", obbligazioni: "border-blue-700", oro: "border-yellow-700",
  materie_prime: "border-orange-700", bitcoin: "border-purple-700",
};

export default function CategoriePage() {
  const [data, setData] = useState<CategoryGuidance | null>(null);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    apiRequest<CategoryGuidance>("/portfolio/category-guidance")
      .then(setData)
      .catch((e) => setError(e instanceof Error ? e.message : "Errore"));
  }, []);

  if (error) return <div className="rounded bg-red-950 px-4 py-3 text-red-400">{error}</div>;
  if (!data) return <p className="text-slate-500">Caricamento guida…</p>;

  return (
    <div>
      <h1 className="mb-1 text-3xl font-bold">Guida alle categorie</h1>
      <p className="mb-6 max-w-2xl text-slate-400">
        Cosa sono, a cosa servono e <strong>cosa guardare per scegliere</strong> in ogni categoria.
        Con il rendimento storico reale e una stima prospettica — onesta: dove non è stimabile, lo diciamo.
      </p>

      <div className="space-y-4">
        {data.categories.map((c) => (
          <section key={c.asset} className={`rounded-lg border ${COLORS[c.asset] ?? "border-slate-700"} bg-slate-900/40 p-5`}>
            <div className="mb-2 flex flex-wrap items-center justify-between gap-2">
              <h2 className="text-lg font-semibold">{c.label}</h2>
              <div className="flex gap-2 text-xs">
                <span className="rounded bg-slate-800 px-2 py-1 text-slate-300">
                  Storico: {pct(c.historical_annual)}/anno
                </span>
                <span className={`rounded px-2 py-1 ${c.forward.estimable ? "bg-green-500/10 text-green-400" : "bg-slate-800 text-slate-400"}`}>
                  Prospettico: {c.forward.estimable ? `${pct(c.forward.value)}/anno` : "non stimabile"}
                </span>
              </div>
            </div>
            <p className="mb-3 text-sm text-slate-300">{c.role}</p>

            <div className="grid grid-cols-1 gap-4 sm:grid-cols-2">
              <div>
                <h3 className="mb-1 text-xs font-semibold uppercase tracking-wide text-green-400">Cosa scegliere</h3>
                <ul className="space-y-1 text-sm text-slate-400">
                  {c.what_to_choose.map((w, i) => <li key={i}>• {w}</li>)}
                </ul>
              </div>
              <div>
                <h3 className="mb-1 text-xs font-semibold uppercase tracking-wide text-amber-400">Rischi</h3>
                <ul className="space-y-1 text-sm text-slate-400">
                  {c.risks.map((w, i) => <li key={i}>• {w}</li>)}
                </ul>
              </div>
            </div>

            <p className="mt-3 text-xs text-slate-500">Stima prospettica: {c.forward.method}</p>
          </section>
        ))}
      </div>

      <p className="mt-6 text-xs text-slate-500">
        {data.note} Periodo di riferimento storico: {data.reference_period.from}–{data.reference_period.to}.
        {" "}<Link href="/plan" className="text-green-400 hover:underline">Vai al tuo piano →</Link>
      </p>
    </div>
  );
}
