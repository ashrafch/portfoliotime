"use client";

import { useState } from "react";
import { useRouter } from "next/navigation";

const API = process.env.NEXT_PUBLIC_API_URL ?? "http://localhost:8000";

interface SimulateForm {
  eta: number;
  tasso_fed: number;
  delta_tasso: number;
  btc_prezzo_corrente: number;
  btc_ath: number;
  is_post_halving: boolean;
  tasso_nominale: number;
  inflazione: number;
  tassi_in_calo: boolean;
  qe_attivo: boolean;
  date_from: string;
  date_to: string;
}

const DEFAULTS: SimulateForm = {
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
  date_from: "2007-01-01",
  date_to: "2009-12-31",
};

export default function SimulatePage() {
  const [form, setForm] = useState<SimulateForm>(DEFAULTS);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const router = useRouter();

  function update<K extends keyof SimulateForm>(key: K, value: SimulateForm[K]) {
    setForm((prev) => ({ ...prev, [key]: value }));
  }

  async function handleSubmit(e: React.FormEvent) {
    e.preventDefault();
    setLoading(true);
    setError(null);
    try {
      const res = await fetch(`${API}/simulate`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify(form),
      });
      if (!res.ok) throw new Error(`Errore API: ${res.status}`);
      const data = await res.json();
      router.push(`/results/${data.job_id}`);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Errore sconosciuto");
      setLoading(false);
    }
  }

  return (
    <main className="mx-auto max-w-2xl px-4 py-12">
      <h1 className="mb-8 text-3xl font-bold">Configura la simulazione</h1>
      <form onSubmit={handleSubmit} className="space-y-6">

        {/* Profilo investitore */}
        <section className="rounded-lg border border-slate-800 p-6">
          <h2 className="mb-4 text-lg font-semibold text-green-400">Profilo investitore</h2>
          <label className="block">
            <span className="text-sm text-slate-400">Età</span>
            <input
              type="number" min={18} max={100}
              value={form.eta}
              onChange={(e) => update("eta", parseInt(e.target.value))}
              className="mt-1 w-full rounded bg-slate-900 px-3 py-2 text-white"
            />
          </label>
        </section>

        {/* Scenario temporale */}
        <section className="rounded-lg border border-slate-800 p-6">
          <h2 className="mb-4 text-lg font-semibold text-green-400">Periodo storico</h2>
          <div className="grid grid-cols-2 gap-4">
            <label className="block">
              <span className="text-sm text-slate-400">Da</span>
              <input
                type="date" value={form.date_from}
                onChange={(e) => update("date_from", e.target.value)}
                className="mt-1 w-full rounded bg-slate-900 px-3 py-2 text-white"
              />
            </label>
            <label className="block">
              <span className="text-sm text-slate-400">A</span>
              <input
                type="date" value={form.date_to}
                onChange={(e) => update("date_to", e.target.value)}
                className="mt-1 w-full rounded bg-slate-900 px-3 py-2 text-white"
              />
            </label>
          </div>
        </section>

        {/* Parametri macro */}
        <section className="rounded-lg border border-slate-800 p-6">
          <h2 className="mb-4 text-lg font-semibold text-green-400">Regime macro</h2>
          <div className="grid grid-cols-2 gap-4">
            <label className="block">
              <span className="text-sm text-slate-400">Tasso FED (%)</span>
              <input type="number" step="0.25" value={form.tasso_fed}
                onChange={(e) => update("tasso_fed", parseFloat(e.target.value))}
                className="mt-1 w-full rounded bg-slate-900 px-3 py-2 text-white" />
            </label>
            <label className="block">
              <span className="text-sm text-slate-400">Inflazione CPI (%)</span>
              <input type="number" step="0.1" value={form.inflazione}
                onChange={(e) => update("inflazione", parseFloat(e.target.value))}
                className="mt-1 w-full rounded bg-slate-900 px-3 py-2 text-white" />
            </label>
          </div>
          <div className="mt-4 flex gap-6">
            <label className="flex items-center gap-2 text-sm">
              <input type="checkbox" checked={form.qe_attivo}
                onChange={(e) => update("qe_attivo", e.target.checked)}
                className="h-4 w-4" />
              QE attivo
            </label>
            <label className="flex items-center gap-2 text-sm">
              <input type="checkbox" checked={form.tassi_in_calo}
                onChange={(e) => update("tassi_in_calo", e.target.checked)}
                className="h-4 w-4" />
              Tassi in calo
            </label>
          </div>
        </section>

        {error && (
          <div className="rounded bg-red-950 px-4 py-3 text-sm text-red-400">{error}</div>
        )}

        <button
          type="submit"
          disabled={loading}
          className="w-full rounded-lg bg-green-500 py-3 font-semibold text-slate-950 transition hover:bg-green-400 disabled:opacity-50"
        >
          {loading ? "Avvio simulazione..." : "Simula portafoglio"}
        </button>
      </form>
    </main>
  );
}
