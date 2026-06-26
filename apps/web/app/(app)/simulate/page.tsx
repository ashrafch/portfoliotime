"use client";

import { useEffect, useState } from "react";
import { useRouter } from "next/navigation";
import { apiRequest } from "@/lib/api";
import type {
  SimulateRequest, Scenario, SimulationRecord, InvestorProfile,
  MacroSuggestion, Allocation,
} from "@/lib/types";

const DEFAULTS: SimulateRequest = {
  eta: 40, tasso_fed: 5.25, delta_tasso: 0, btc_prezzo_corrente: 0, btc_ath: 0,
  is_post_halving: false, tasso_nominale: 5.25, inflazione: 3.5,
  tassi_in_calo: false, qe_attivo: false,
  date_from: "2007-10-09", date_to: "2009-03-09", benchmark_ticker: "SPY",
  initial_capital: 10000, contribution: 0, contribution_frequency: "none",
};

const DEFAULT_ALLOC: Allocation = {
  azioni: 60, obbligazioni: 25, oro: 5, materie_prime: 5, bitcoin: 5,
};

const ALLOC_LABELS: Record<keyof Allocation, string> = {
  azioni: "Azioni", obbligazioni: "Obbligazioni", oro: "Oro",
  materie_prime: "Materie Prime", bitcoin: "Bitcoin",
};

export default function SimulatePage() {
  const [form, setForm] = useState<SimulateRequest>(DEFAULTS);
  const [scenarios, setScenarios] = useState<Scenario[]>([]);
  const [mode, setMode] = useState<"chameleon" | "custom">("chameleon");
  const [alloc, setAlloc] = useState<Allocation>(DEFAULT_ALLOC);
  const [submitting, setSubmitting] = useState(false);
  const [fredMsg, setFredMsg] = useState<string | null>(null);
  const [fredLoading, setFredLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const router = useRouter();

  useEffect(() => {
    apiRequest<Scenario[]>("/scenarios", { auth: false }).then(setScenarios).catch(() => {});
    // Prefill dal profilo
    apiRequest<InvestorProfile>("/me/profile")
      .then((p) => setForm((f) => ({
        ...f, eta: p.eta, tasso_fed: p.default_tasso_fed,
        tasso_nominale: p.default_tasso_fed, inflazione: p.default_inflazione,
      })))
      .catch(() => {});
  }, []);

  function update<K extends keyof SimulateRequest>(key: K, value: SimulateRequest[K]) {
    setForm((p) => ({ ...p, [key]: value }));
  }

  function applyScenario(s: Scenario) {
    setForm((p) => ({ ...p, date_from: s.date_from, date_to: s.date_to }));
  }

  async function autofillFred() {
    setFredLoading(true);
    setFredMsg(null);
    try {
      const s = await apiRequest<MacroSuggestion>(
        `/macro/suggest?date_from=${form.date_from}&date_to=${form.date_to}`
      );
      if (s.source === "fred") {
        setForm((p) => ({
          ...p,
          tasso_fed: s.tasso_fed ?? p.tasso_fed,
          delta_tasso: s.delta_tasso ?? p.delta_tasso,
          tasso_nominale: s.tasso_nominale ?? p.tasso_nominale,
          inflazione: s.inflazione ?? p.inflazione,
          tassi_in_calo: s.tassi_in_calo ?? p.tassi_in_calo,
        }));
        setFredMsg("✓ Parametri compilati con dati storici reali (FRED)");
      } else {
        setFredMsg(s.message ?? "Dati FRED non disponibili");
      }
    } catch (e) {
      setFredMsg(e instanceof Error ? e.message : "Errore FRED");
    } finally {
      setFredLoading(false);
    }
  }

  const allocSum = Object.values(alloc).reduce((a, b) => a + b, 0);

  async function handleSubmit(e: React.FormEvent) {
    e.preventDefault();
    setSubmitting(true);
    setError(null);
    try {
      const body: SimulateRequest = { ...form };
      if (mode === "custom") body.custom_allocation = alloc;
      const rec = await apiRequest<SimulationRecord>("/simulate", { method: "POST", body });
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
        Configura il periodo e i parametri. Il motore calcola l&apos;allocazione e le metriche su dati reali.
      </p>

      {scenarios.length > 0 && (
        <div className="mb-8">
          <p className="mb-3 text-sm font-semibold text-slate-400">Scenari storici rapidi</p>
          <div className="flex flex-wrap gap-2">
            {scenarios.map((s) => (
              <button key={s.id} type="button" onClick={() => applyScenario(s)}
                className={`rounded-full border px-3 py-1.5 text-xs transition ${
                  form.date_from === s.date_from && form.date_to === s.date_to
                    ? "border-green-500 bg-green-500/10 text-green-400"
                    : "border-slate-700 text-slate-400 hover:border-slate-500"
                }`} title={s.description}>
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
                onChange={(e) => update("eta", parseInt(e.target.value) || 0)} className={inputCls} />
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

        {/* Modalità allocazione */}
        <section className="rounded-lg border border-slate-800 p-6">
          <h2 className="mb-4 text-lg font-semibold text-green-400">Modalità allocazione</h2>
          <div className="mb-4 flex gap-2">
            <button type="button" onClick={() => setMode("chameleon")}
              className={`flex-1 rounded-lg border p-3 text-sm transition ${
                mode === "chameleon" ? "border-green-500 bg-green-500/10" : "border-slate-700 hover:border-slate-500"
              }`}>
              <div className="font-semibold">Chameleon (automatica)</div>
              <div className="mt-1 text-xs text-slate-400">Le formule calcolano i pesi dai parametri macro</div>
            </button>
            <button type="button" onClick={() => setMode("custom")}
              className={`flex-1 rounded-lg border p-3 text-sm transition ${
                mode === "custom" ? "border-green-500 bg-green-500/10" : "border-slate-700 hover:border-slate-500"
              }`}>
              <div className="font-semibold">Personalizzata</div>
              <div className="mt-1 text-xs text-slate-400">Definisci tu i pesi di ogni asset</div>
            </button>
          </div>

          {mode === "custom" && (
            <div className="space-y-3">
              {(Object.keys(alloc) as (keyof Allocation)[]).map((k) => (
                <div key={k} className="flex items-center gap-3">
                  <span className="w-32 text-sm text-slate-300">{ALLOC_LABELS[k]}</span>
                  <input type="range" min={0} max={100} value={alloc[k]}
                    onChange={(e) => setAlloc((a) => ({ ...a, [k]: parseInt(e.target.value) }))}
                    className="flex-1" />
                  <span className="w-12 text-right text-sm font-semibold">{alloc[k]}%</span>
                </div>
              ))}
              <div className={`text-right text-sm ${Math.abs(allocSum - 100) < 0.5 ? "text-green-400" : "text-yellow-400"}`}>
                Somma: {allocSum}% {Math.abs(allocSum - 100) >= 0.5 && "(verrà normalizzata a 100%)"}
              </div>
            </div>
          )}
        </section>

        {/* Regime macro (solo per Chameleon) */}
        {mode === "chameleon" && (
          <section className="rounded-lg border border-slate-800 p-6">
            <div className="mb-4 flex items-center justify-between">
              <h2 className="text-lg font-semibold text-green-400">Regime macro</h2>
              <button type="button" onClick={autofillFred} disabled={fredLoading}
                className="rounded border border-slate-700 px-3 py-1.5 text-xs text-slate-300 hover:border-green-500 disabled:opacity-50">
                {fredLoading ? "…" : "Compila da dati storici (FRED)"}
              </button>
            </div>
            {fredMsg && <p className="mb-3 text-xs text-slate-400">{fredMsg}</p>}
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
              <Check label="Periodo post-halving (BTC)" checked={form.is_post_halving}
                onChange={(v) => update("is_post_halving", v)} />
            </div>
            {form.is_post_halving && (
              <div className="mt-4 grid grid-cols-1 gap-4 sm:grid-cols-2">
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
        )}

        {/* Importi: capitale e piano di accumulo */}
        <section className="rounded-lg border border-slate-800 p-6">
          <h2 className="mb-1 text-lg font-semibold text-green-400">Importi</h2>
          <p className="mb-4 text-xs text-slate-500">
            Per vedere i risultati anche in denaro. I rendimenti sono calcolati su asset
            quotati in USD e non includono l&apos;effetto del cambio.
          </p>
          <div className="grid grid-cols-1 gap-4 sm:grid-cols-3">
            <Field label="Capitale iniziale">
              <input type="number" min={0} step={500} value={form.initial_capital}
                onChange={(e) => update("initial_capital", parseFloat(e.target.value) || 0)} className={inputCls} />
            </Field>
            <Field label="Versamento periodico (DCA)">
              <input type="number" min={0} step={50} value={form.contribution}
                onChange={(e) => update("contribution", parseFloat(e.target.value) || 0)} className={inputCls} />
            </Field>
            <Field label="Frequenza versamento">
              <select value={form.contribution_frequency}
                onChange={(e) => update("contribution_frequency", e.target.value as SimulateRequest["contribution_frequency"])}
                className={inputCls}>
                <option value="none">Nessuno (solo capitale iniziale)</option>
                <option value="monthly">Mensile</option>
                <option value="quarterly">Trimestrale</option>
              </select>
            </Field>
          </div>
        </section>

        {error && <div className="rounded bg-red-950 px-4 py-3 text-sm text-red-400">{error}</div>}

        <button type="submit" disabled={submitting}
          className="w-full rounded-lg bg-green-500 py-3 font-semibold text-slate-950 transition hover:bg-green-400 disabled:opacity-50">
          {submitting ? "Calcolo in corso…" : "Esegui simulazione"}
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
