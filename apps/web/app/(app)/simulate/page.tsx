"use client";

import { useEffect, useState } from "react";
import { useRouter } from "next/navigation";
import { apiRequest } from "@/lib/api";
import type { SimulateRequest, Scenario, SimulationRecord } from "@/lib/types";

const DEFAULTS: SimulateRequest = {
  eta: 40,
  tasso_fed: 5.25,
  delta_tasso: 0,
  btc_prezzo_corrente: 0,
  btc_ath: 0,
  is_post_halving: false,
  tasso_nominale: 5.25,
  inflazione: 3.5,
  tassi_in_calo: false,
  qe_attivo: false,
  date_from: "2007-10-09",
  date_to: "2009-03-09",
  benchmark_ticker: "SPY",
};

export default function SimulatePage() {
  const [form, setForm] = useState<SimulateRequest>(DEFAULTS);
  const [scenarios, setScenarios] = useState<Scenario[]>([]);
  const [submitting, setSubmitting] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const router = useRouter();

  useEffect(() => {
    apiRequest<Scenario[]>("/scenarios", { auth: false })
      .then(setScenarios)
      .catch(() => setScenarios([]));
  }, []);

  function update<K extends keyof SimulateRequest>(key: K, value: SimulateRequest[K]) {
    setForm((p) => ({ ...p, [key]: value }));
  }

  function applyScenario(s: Scenario) {
    setForm((p) => ({ ...p, date_from: s.date_from, date_to: s.date_to }));
  }

  async function handleSubmit(e: React.FormEvent) {
    e.preventDefault();
    setSubmitting(true);
    setError(null);
    try {
      const rec = await apiRequest<SimulationRecord>("/simulate", { method: "POST", body: form });
      if (rec.status === "failed") {
        setError(rec.error || "Simulazione fallita");
        setSubmitting(false);
        return;
      }
      router.push(`/results/${rec.id}`);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Errore");
      setSubmitting(false);
    }
  }

  return (
    <div>
      <h1 className="mb-2 text-3xl font-bold">Nuova simulazione</h1>
      <p className="mb-8 text-slate-400">
        Configura il profilo e il periodo storico. Il motore Chameleon calcola l&apos;allocazione e le metriche su dati reali.
      </p>

      {/* Scenari rapidi */}
      {scenarios.length > 0 && (
        <div className="mb-8">
          <p className="mb-3 text-sm font-semibold text-slate-400">Scenari storici rapidi</p>
          <div className="flex flex-wrap gap-2">
            {scenarios.map((s) => (
              <button
                key={s.id}
                type="button"
                onClick={() => applyScenario(s)}
                className={`rounded-full border px-3 py-1.5 text-xs transition ${
                  form.date_from === s.date_from && form.date_to === s.date_to
                    ? "border-green-500 bg-green-500/10 text-green-400"
                    : "border-slate-700 text-slate-400 hover:border-slate-500"
                }`}
                title={s.description}
              >
                {s.label}
              </button>
            ))}
          </div>
        </div>
      )}

      <form onSubmit={handleSubmit} className="space-y-6">
        <section className="rounded-lg border border-slate-800 p-6">
          <h2 className="mb-4 text-lg font-semibold text-green-400">Profilo & periodo</h2>
          <div className="grid grid-cols-1 gap-4 sm:grid-cols-3">
            <Field label="Età">
              <input type="number" min={18} max={100} value={form.eta}
                onChange={(e) => update("eta", parseInt(e.target.value) || 0)}
                className={inputCls} />
            </Field>
            <Field label="Da">
              <input type="date" value={form.date_from}
                onChange={(e) => update("date_from", e.target.value)} className={inputCls} />
            </Field>
            <Field label="A">
              <input type="date" value={form.date_to}
                onChange={(e) => update("date_to", e.target.value)} className={inputCls} />
            </Field>
          </div>
        </section>

        <section className="rounded-lg border border-slate-800 p-6">
          <h2 className="mb-4 text-lg font-semibold text-green-400">Regime macro</h2>
          <div className="grid grid-cols-1 gap-4 sm:grid-cols-2">
            <Field label="Tasso FED (%)">
              <input type="number" step="0.25" value={form.tasso_fed}
                onChange={(e) => update("tasso_fed", parseFloat(e.target.value) || 0)} className={inputCls} />
            </Field>
            <Field label="Variazione tasso FED (pp)">
              <input type="number" step="0.25" value={form.delta_tasso}
                onChange={(e) => update("delta_tasso", parseFloat(e.target.value) || 0)} className={inputCls} />
            </Field>
            <Field label="Tasso nominale (%)">
              <input type="number" step="0.25" value={form.tasso_nominale}
                onChange={(e) => update("tasso_nominale", parseFloat(e.target.value) || 0)} className={inputCls} />
            </Field>
            <Field label="Inflazione CPI (%)">
              <input type="number" step="0.1" value={form.inflazione}
                onChange={(e) => update("inflazione", parseFloat(e.target.value) || 0)} className={inputCls} />
            </Field>
          </div>
          <div className="mt-4 flex flex-wrap gap-6">
            <Check label="QE attivo (esclude obbligazioni)" checked={form.qe_attivo}
              onChange={(v) => update("qe_attivo", v)} />
            <Check label="Tassi in calo" checked={form.tassi_in_calo}
              onChange={(v) => update("tassi_in_calo", v)} />
          </div>
        </section>

        <section className="rounded-lg border border-slate-800 p-6">
          <h2 className="mb-1 text-lg font-semibold text-green-400">Bitcoin (opzionale)</h2>
          <p className="mb-4 text-xs text-slate-500">
            Bitcoin entra in portafoglio solo in fase post-halving. Dati crypto dal 2013.
          </p>
          <div className="mb-4">
            <Check label="Periodo post-halving" checked={form.is_post_halving}
              onChange={(v) => update("is_post_halving", v)} />
          </div>
          {form.is_post_halving && (
            <div className="grid grid-cols-1 gap-4 sm:grid-cols-2">
              <Field label="Prezzo BTC corrente ($)">
                <input type="number" value={form.btc_prezzo_corrente}
                  onChange={(e) => update("btc_prezzo_corrente", parseFloat(e.target.value) || 0)} className={inputCls} />
              </Field>
              <Field label="BTC All-Time High ($)">
                <input type="number" value={form.btc_ath}
                  onChange={(e) => update("btc_ath", parseFloat(e.target.value) || 0)} className={inputCls} />
              </Field>
            </div>
          )}
        </section>

        {error && (
          <div className="rounded bg-red-950 px-4 py-3 text-sm text-red-400">{error}</div>
        )}

        <button type="submit" disabled={submitting}
          className="w-full rounded-lg bg-green-500 py-3 font-semibold text-slate-950 transition hover:bg-green-400 disabled:opacity-50">
          {submitting ? "Calcolo in corso… (download dati di mercato)" : "Esegui simulazione"}
        </button>
      </form>
    </div>
  );
}

const inputCls =
  "mt-1 w-full rounded bg-slate-900 px-3 py-2 text-white focus:outline-none focus:ring-2 focus:ring-green-500";

function Field({ label, children }: { label: string; children: React.ReactNode }) {
  return (
    <label className="block">
      <span className="text-sm text-slate-400">{label}</span>
      {children}
    </label>
  );
}

function Check({ label, checked, onChange }: { label: string; checked: boolean; onChange: (v: boolean) => void }) {
  return (
    <label className="flex items-center gap-2 text-sm">
      <input type="checkbox" checked={checked} onChange={(e) => onChange(e.target.checked)} className="h-4 w-4" />
      {label}
    </label>
  );
}
