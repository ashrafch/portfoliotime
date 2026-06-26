"use client";

import { useEffect, useState } from "react";
import { apiRequest } from "@/lib/api";
import { pct, money } from "@/lib/format";
import type { StressTestResult, InvestorProfile, Allocation } from "@/lib/types";

const LABELS: Record<keyof Allocation, string> = {
  azioni: "Azioni", obbligazioni: "Obbligazioni", oro: "Oro",
  materie_prime: "Materie Prime", bitcoin: "Bitcoin",
};

export default function StressTestPage() {
  const [holdings, setHoldings] = useState<Record<string, number>>({
    azioni: 12000, obbligazioni: 6000, oro: 2000, materie_prime: 0, bitcoin: 0,
  });
  const [currency, setCurrency] = useState("EUR");
  const [result, setResult] = useState<StressTestResult | null>(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    apiRequest<InvestorProfile>("/me/profile").then((p) => setCurrency(p.base_currency)).catch(() => {});
  }, []);

  const total = Object.values(holdings).reduce((a, b) => a + (b || 0), 0);

  async function run() {
    setLoading(true);
    setError(null);
    try {
      setResult(await apiRequest<StressTestResult>("/portfolio/stress-test", { method: "POST", body: { holdings } }));
    } catch (e) {
      setError(e instanceof Error ? e.message : "Errore");
    } finally {
      setLoading(false);
    }
  }

  return (
    <div>
      <h1 className="mb-1 text-3xl font-bold">Il mio portafoglio</h1>
      <p className="mb-6 text-slate-400">
        Inserisci quanto possiedi per categoria e scopri come avrebbe retto nelle crisi storiche reali.
      </p>

      <section className="mb-6 rounded-lg border border-slate-800 p-6">
        <div className="grid grid-cols-1 gap-4 sm:grid-cols-3">
          {(Object.keys(LABELS) as (keyof Allocation)[]).map((k) => (
            <label key={k} className="block">
              <span className="text-sm text-slate-400">{LABELS[k]} ({currency})</span>
              <input type="number" min={0} step={500} value={holdings[k]}
                onChange={(e) => setHoldings((h) => ({ ...h, [k]: parseFloat(e.target.value) || 0 }))}
                className="mt-1 w-full rounded bg-slate-900 px-3 py-2 text-white focus:outline-none focus:ring-2 focus:ring-green-500" />
            </label>
          ))}
        </div>
        <div className="mt-4 flex items-center justify-between">
          <span className="text-sm text-slate-400">Totale: <strong className="text-white">{money(total, currency)}</strong></span>
          <button onClick={run} disabled={loading || total <= 0}
            className="rounded-lg bg-green-500 px-5 py-2.5 font-semibold text-slate-950 transition hover:bg-green-400 disabled:opacity-50">
            {loading ? "Calcolo…" : "Stress test"}
          </button>
        </div>
      </section>

      {error && <div className="mb-6 rounded bg-red-950 px-4 py-3 text-sm text-red-400">{error}</div>}

      {result && (
        <section className="grid grid-cols-1 gap-4 sm:grid-cols-2">
          {result.scenarios.map((s) => {
            const neg = (s.total_return ?? 0) < 0;
            return (
              <div key={s.label} className="rounded-lg border border-slate-800 p-5">
                <h3 className="font-semibold">{s.label}</h3>
                <p className="text-xs text-slate-500">{s.date_from} → {s.date_to}</p>
                <div className="mt-3 flex items-end justify-between">
                  <div>
                    <div className={`text-2xl font-bold ${neg ? "text-red-400" : "text-green-400"}`}>
                      {pct(s.total_return, true)}
                    </div>
                    <div className="text-xs text-slate-400">valore finale: {money(s.final_value, currency)}</div>
                  </div>
                  <div className="text-right">
                    <div className="text-sm font-semibold text-amber-400">{pct(s.max_drawdown)}</div>
                    <div className="text-xs text-slate-400">caduta peggiore</div>
                  </div>
                </div>
              </div>
            );
          })}
        </section>
      )}

      {result && (
        <p className="mt-6 text-xs text-slate-500">
          Le categorie sono mappate su indici reali (azioni=S&P 500, obbligazioni=Treasury, ecc.).
          Risultati su dati storici reali; il passato non garantisce il futuro.
        </p>
      )}
    </div>
  );
}
