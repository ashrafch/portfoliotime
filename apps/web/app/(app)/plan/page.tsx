"use client";

import { useEffect, useState } from "react";
import Link from "next/link";
import { apiRequest } from "@/lib/api";
import { pct, money } from "@/lib/format";
import type { AdviceResult, InvestorProfile } from "@/lib/types";

const COLORS: Record<string, string> = {
  azioni: "bg-green-500", obbligazioni: "bg-blue-500", oro: "bg-yellow-500",
  materie_prime: "bg-orange-500", bitcoin: "bg-purple-500",
};
const LABELS: Record<string, string> = {
  azioni: "Azioni", obbligazioni: "Obbligazioni", oro: "Oro",
  materie_prime: "Materie Prime", bitcoin: "Bitcoin",
};

export default function PlanPage() {
  const [form, setForm] = useState({
    initial_capital: 10000, monthly_contribution: 300, horizon_years: 15,
    target: 100000, risk_profile: "bilanciato", basis: "strategic" as "strategic" | "chameleon",
  });
  const [currency, setCurrency] = useState("EUR");
  const [result, setResult] = useState<AdviceResult | null>(null);
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
      const body = { ...form, target: form.target > 0 ? form.target : undefined };
      setResult(await apiRequest<AdviceResult>("/portfolio/advice", { method: "POST", body }));
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
      <h1 className="mb-1 text-3xl font-bold">Il tuo piano</h1>
      <p className="mb-6 max-w-2xl text-slate-400">
        Un consiglio concreto su <strong>come ripartire i tuoi soldi</strong> e la
        probabilità di raggiungere il tuo obiettivo, calcolata su <strong>dati storici reali</strong>.
        Va bene anche se non hai mai investito: ti spieghiamo ogni passo.
      </p>

      {/* Input */}
      <section className="mb-6 rounded-lg border border-slate-800 p-6">
        {/* Preset rapidi: come vuoi investire */}
        <div className="mb-4 flex flex-wrap items-center gap-2 text-sm">
          <span className="text-slate-400">Come vuoi investire:</span>
          <button type="button" onClick={() => up("monthly_contribution", 0)}
            className="rounded-full border border-slate-700 px-3 py-1 text-xs text-slate-300 hover:border-green-500">
            Investo tutto subito
          </button>
          <button type="button" onClick={() => up("initial_capital", 0)}
            className="rounded-full border border-slate-700 px-3 py-1 text-xs text-slate-300 hover:border-green-500">
            Solo versamento mensile
          </button>
          <button type="button" onClick={() => { up("initial_capital", 10000); up("monthly_contribution", 300); }}
            className="rounded-full border border-slate-700 px-3 py-1 text-xs text-slate-300 hover:border-green-500">
            Misto
          </button>
        </div>

        <div className="grid grid-cols-1 gap-4 sm:grid-cols-3">
          <F label={`Quanto hai ora (${currency})`} hint="Il capitale di partenza. Può anche essere 0.">
            <input type="number" min={0} step={500} value={form.initial_capital}
              onChange={(e) => up("initial_capital", parseFloat(e.target.value) || 0)} className={cls} />
          </F>
          <F label={`Quanto versi al mese (${currency})`} hint="Quanto pensi di aggiungere ogni mese.">
            <input type="number" min={0} step={50} value={form.monthly_contribution}
              onChange={(e) => up("monthly_contribution", parseFloat(e.target.value) || 0)} className={cls} />
          </F>
          <F label="Tra quanti anni" hint="Il tuo orizzonte temporale.">
            <input type="number" min={1} max={50} value={form.horizon_years}
              onChange={(e) => up("horizon_years", parseInt(e.target.value) || 1)} className={cls} />
          </F>
          <F label={`Obiettivo (${currency}) — opzionale`} hint="La cifra che vorresti raggiungere.">
            <input type="number" min={0} step={1000} value={form.target}
              onChange={(e) => up("target", parseFloat(e.target.value) || 0)} className={cls} />
          </F>
          <F label="Quanto rischio accetti" hint="Più rischio = più crescita possibile ma più oscillazioni.">
            <select value={form.risk_profile} onChange={(e) => up("risk_profile", e.target.value)} className={cls}>
              <option value="conservativo">Conservativo</option>
              <option value="bilanciato">Bilanciato</option>
              <option value="aggressivo">Aggressivo</option>
            </select>
          </F>
          <div className="flex items-end">
            <button onClick={run} disabled={loading}
              className="w-full rounded-lg bg-green-500 py-2.5 font-semibold text-slate-950 transition hover:bg-green-400 disabled:opacity-50">
              {loading ? "Calcolo…" : "Crea il piano"}
            </button>
          </div>
        </div>

        {/* Toggle base allocazione */}
        <div className="mt-4 flex flex-wrap items-center gap-2 text-sm">
          <span className="text-slate-400">Base del consiglio:</span>
          <button onClick={() => up("basis", "strategic")}
            className={`rounded-full border px-3 py-1 text-xs ${form.basis === "strategic" ? "border-green-500 bg-green-500/10 text-green-400" : "border-slate-700 text-slate-400"}`}>
            Strategica (in base al rischio)
          </button>
          <button onClick={() => up("basis", "chameleon")}
            className={`rounded-full border px-3 py-1 text-xs ${form.basis === "chameleon" ? "border-green-500 bg-green-500/10 text-green-400" : "border-slate-700 text-slate-400"}`}>
            Chameleon (macro di oggi)
          </button>
        </div>
      </section>

      {error && <div className="mb-6 rounded bg-red-950 px-4 py-3 text-sm text-red-400">{error}</div>}

      {result && (
        <>
          {/* Risultato principale */}
          {result.projection.target > 0 && (
            <section className="mb-6 rounded-lg border border-slate-800 bg-slate-900/50 p-6">
              <div className="flex flex-wrap items-center justify-between gap-4">
                <div>
                  <div className="text-sm text-slate-400">Probabilità di raggiungere {money(result.projection.target, currency)}</div>
                  <div className={`text-5xl font-bold ${probTone}`}>{Math.round(prob * 100)}%</div>
                </div>
                {result.required_monthly_contribution !== null && (
                  <div className="rounded-lg border border-slate-700 p-4 text-center">
                    <div className="text-xs text-slate-400">Per una buona probabilità (~75%) versa</div>
                    <div className="text-2xl font-bold text-green-400">
                      {money(result.required_monthly_contribution, currency)}<span className="text-sm text-slate-400">/mese</span>
                    </div>
                  </div>
                )}
              </div>
              {result.explanations.probability && (
                <p className="mt-3 text-sm text-slate-400">{result.explanations.probability}</p>
              )}
            </section>
          )}

          {/* Cosa investire — la ripartizione concreta */}
          <section className="mb-6 rounded-lg border border-slate-800 p-6">
            <h2 className="mb-1 text-lg font-semibold">Come ripartire</h2>
            <p className="mb-3 text-sm text-slate-400">{result.explanations.mix}</p>
            <p className="mb-4 text-xs text-slate-500">
              {result.composition.initial > 0 && result.composition.months > 0
                ? `Le stesse percentuali valgono sia per i ${money(result.composition.initial, currency)} iniziali sia per ogni versamento di ${money(form.monthly_contribution, currency)}/mese.`
                : result.composition.months > 0
                ? `Le percentuali valgono per ogni versamento di ${money(form.monthly_contribution, currency)}/mese.`
                : `Ripartizione del capitale iniziale di ${money(form.initial_capital, currency)}.`}
            </p>

            {/* intestazioni colonne importi */}
            <div className="mb-1 flex items-center gap-3 text-[11px] uppercase tracking-wide text-slate-500">
              <span className="w-40 shrink-0">Categoria</span>
              <span className="flex-1" />
              {result.composition.initial > 0 && <span className="w-24 shrink-0 text-right">Iniziale</span>}
              {result.composition.months > 0 && <span className="w-24 shrink-0 text-right">Ogni mese</span>}
            </div>
            <div className="space-y-3">
              {result.breakdown.map((b) => (
                <div key={b.asset} className="flex items-center gap-3">
                  <div className="w-40 shrink-0">
                    <div className="text-sm font-medium">{LABELS[b.asset] ?? b.asset} <span className="text-xs text-slate-500">{b.weight_pct}%</span></div>
                    <div className="text-[11px] text-slate-500">{b.instrument}</div>
                  </div>
                  <div className="h-2 flex-1 overflow-hidden rounded-full bg-slate-800">
                    <div className={`h-full ${COLORS[b.asset] ?? "bg-slate-500"}`} style={{ width: `${Math.min(b.weight_pct, 100)}%` }} />
                  </div>
                  {result.composition.initial > 0 && (
                    <span className="w-24 shrink-0 text-right font-semibold">{money(b.amount_initial, currency)}</span>
                  )}
                  {result.composition.months > 0 && (
                    <span className="w-24 shrink-0 text-right font-semibold text-slate-300">{money(b.amount_monthly, currency)}</span>
                  )}
                </div>
              ))}
            </div>

            {/* composizione del totale versato */}
            <p className="mt-4 border-t border-slate-800 pt-3 text-xs text-slate-500">
              In tutto verserai <strong className="text-slate-300">{money(result.composition.total, currency)}</strong>
              {result.composition.initial > 0 && result.composition.monthly_total > 0 && (
                <> — {money(result.composition.initial, currency)} iniziali ({Math.round(result.composition.initial_share * 100)}%)
                {" "}+ {money(result.composition.monthly_total, currency)} di versamenti ({result.composition.months} mesi)</>
              )}
              {result.composition.initial === 0 && result.composition.monthly_total > 0 && (
                <> — interamente da versamenti mensili ({result.composition.months} mesi)</>
              )}
              {result.composition.monthly_total === 0 && (
                <> — interamente come capitale iniziale</>
              )}.
            </p>
          </section>

          {/* Scenari */}
          <section className="mb-6 rounded-lg border border-slate-800 p-6">
            <h2 className="mb-1 text-lg font-semibold">Cosa potresti ritrovarti</h2>
            <p className="mb-4 text-sm text-slate-400">{result.explanations.scenarios}</p>
            <div className="grid grid-cols-3 gap-4 text-center">
              <Sc label="Sfavorevole" value={money(result.projection.final_value.p10, currency)} tone="text-red-400" />
              <Sc label="Più probabile" value={money(result.projection.final_value.p50, currency)} tone="text-white" />
              <Sc label="Favorevole" value={money(result.projection.final_value.p90, currency)} tone="text-green-400" />
            </div>
            <p className="mt-3 text-xs text-slate-500">
              Su {result.reference_period.from}–{result.reference_period.to}: rendimento storico
              {" "}{pct(result.reference_stats.annual_return)}/anno, oscillazione {pct(result.reference_stats.annual_volatility)}.
              Totale versato nel piano: {money(result.projection.total_contributed, currency)}.
            </p>
          </section>

          <div className="rounded-lg border border-slate-800 bg-slate-900/40 p-4 text-xs text-slate-500">
            {result.disclaimer}
            {" "}Approfondisci: <Link href="/goals" className="text-green-400 hover:underline">Obiettivi</Link>
            {" · "}<Link href="/recommended" className="text-green-400 hover:underline">Allocazione di oggi</Link>
            {" · "}<Link href="/stress-test" className="text-green-400 hover:underline">Stress test</Link>.
          </div>
        </>
      )}
    </div>
  );
}

const cls = "mt-1 w-full rounded bg-slate-900 px-3 py-2 text-white focus:outline-none focus:ring-2 focus:ring-green-500";
function F({ label, hint, children }: { label: string; hint?: string; children: React.ReactNode }) {
  return (
    <label className="block">
      <span className="text-sm text-slate-400">{label}</span>
      {children}
      {hint && <span className="mt-1 block text-[11px] text-slate-500">{hint}</span>}
    </label>
  );
}
function Sc({ label, value, tone }: { label: string; value: string; tone: string }) {
  return (
    <div className="rounded-lg border border-slate-800 p-3">
      <div className={`text-lg font-bold ${tone}`}>{value}</div>
      <div className="text-xs text-slate-400">{label}</div>
    </div>
  );
}
