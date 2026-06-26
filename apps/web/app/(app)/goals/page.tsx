"use client";

import { useEffect, useState } from "react";
import { apiRequest } from "@/lib/api";
import { pct, money } from "@/lib/format";
import type { GoalPlanResult, InvestorProfile } from "@/lib/types";

export default function GoalsPage() {
  const [form, setForm] = useState({
    target: 100000, horizon_years: 15, initial_capital: 10000,
    monthly_contribution: 300, risk_profile: "bilanciato",
  });
  const [currency, setCurrency] = useState("EUR");
  const [result, setResult] = useState<GoalPlanResult | null>(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    apiRequest<InvestorProfile>("/me/profile")
      .then((p) => { setCurrency(p.base_currency); setForm((f) => ({ ...f, risk_profile: p.risk_profile })); })
      .catch(() => {});
  }, []);

  function up<K extends keyof typeof form>(k: K, v: (typeof form)[K]) {
    setForm((f) => ({ ...f, [k]: v }));
  }

  async function run() {
    setLoading(true); setError(null);
    try {
      setResult(await apiRequest<GoalPlanResult>("/portfolio/goal-plan", { method: "POST", body: form }));
    } catch (e) {
      setError(e instanceof Error ? e.message : "Errore");
    } finally {
      setLoading(false);
    }
  }

  const prob = result?.projection.probability_success ?? 0;
  const probTone = prob >= 0.7 ? "text-green-400" : prob >= 0.4 ? "text-yellow-400" : "text-red-400";

  return (
    <div>
      <h1 className="mb-1 text-3xl font-bold">Obiettivi</h1>
      <p className="mb-6 text-slate-400">
        Imposta un obiettivo e scopri la probabilità di raggiungerlo e quanto versare.
      </p>

      <section className="mb-6 rounded-lg border border-slate-800 p-6">
        <div className="grid grid-cols-1 gap-4 sm:grid-cols-3">
          <F label={`Obiettivo (${currency})`}><input type="number" min={0} step={1000} value={form.target}
            onChange={(e) => up("target", parseFloat(e.target.value) || 0)} className={cls} /></F>
          <F label="Orizzonte (anni)"><input type="number" min={1} max={50} value={form.horizon_years}
            onChange={(e) => up("horizon_years", parseInt(e.target.value) || 1)} className={cls} /></F>
          <F label="Profilo di rischio">
            <select value={form.risk_profile} onChange={(e) => up("risk_profile", e.target.value)} className={cls}>
              <option value="conservativo">Conservativo</option>
              <option value="bilanciato">Bilanciato</option>
              <option value="aggressivo">Aggressivo</option>
            </select>
          </F>
          <F label={`Capitale iniziale (${currency})`}><input type="number" min={0} step={500} value={form.initial_capital}
            onChange={(e) => up("initial_capital", parseFloat(e.target.value) || 0)} className={cls} /></F>
          <F label={`Versamento mensile (${currency})`}><input type="number" min={0} step={50} value={form.monthly_contribution}
            onChange={(e) => up("monthly_contribution", parseFloat(e.target.value) || 0)} className={cls} /></F>
          <div className="flex items-end">
            <button onClick={run} disabled={loading || form.target <= 0}
              className="w-full rounded-lg bg-green-500 py-2.5 font-semibold text-slate-950 transition hover:bg-green-400 disabled:opacity-50">
              {loading ? "Calcolo…" : "Calcola"}
            </button>
          </div>
        </div>
      </section>

      {error && <div className="mb-6 rounded bg-red-950 px-4 py-3 text-sm text-red-400">{error}</div>}

      {result && (
        <>
          <section className="mb-4 grid grid-cols-1 gap-4 sm:grid-cols-3">
            <Card label="Probabilità di successo" value={`${Math.round(prob * 100)}%`} tone={probTone} big />
            <Card label="Versamento per ~75%"
              value={result.required_monthly_contribution === null ? "—"
                : money(result.required_monthly_contribution, currency) + "/mese"} />
            <Card label="Totale versato" value={money(result.projection.total_contributed, currency)} />
          </section>

          <section className="mb-4 rounded-lg border border-slate-800 p-6">
            <h2 className="mb-3 text-sm font-semibold text-slate-400">Valore finale stimato</h2>
            <div className="grid grid-cols-3 gap-4 text-center">
              <Range label="Sfavorevole (p10)" value={money(result.projection.final_value.p10, currency)} tone="text-red-400" />
              <Range label="Mediano (p50)" value={money(result.projection.final_value.p50, currency)} tone="text-white" />
              <Range label="Favorevole (p90)" value={money(result.projection.final_value.p90, currency)} tone="text-green-400" />
            </div>
          </section>

          <p className="text-xs text-slate-500">
            Riferimento {result.reference_period.from}–{result.reference_period.to} (profilo {result.risk_profile}):
            rendimento storico {pct(result.reference_stats.annual_return)}/anno, volatilità {pct(result.reference_stats.annual_volatility)}.
            {" "}{result.disclaimer}
          </p>
        </>
      )}
    </div>
  );
}

const cls = "mt-1 w-full rounded bg-slate-900 px-3 py-2 text-white focus:outline-none focus:ring-2 focus:ring-green-500";
function F({ label, children }: { label: string; children: React.ReactNode }) {
  return <label className="block"><span className="text-sm text-slate-400">{label}</span>{children}</label>;
}
function Card({ label, value, tone = "text-white", big }: { label: string; value: string; tone?: string; big?: boolean }) {
  return (
    <div className="rounded-lg border border-slate-800 bg-slate-900/50 p-5">
      <div className={`font-bold ${big ? "text-4xl" : "text-2xl"} ${tone}`}>{value}</div>
      <div className="mt-1 text-xs text-slate-400">{label}</div>
    </div>
  );
}
function Range({ label, value, tone }: { label: string; value: string; tone: string }) {
  return (
    <div>
      <div className={`text-lg font-bold ${tone}`}>{value}</div>
      <div className="text-xs text-slate-400">{label}</div>
    </div>
  );
}
