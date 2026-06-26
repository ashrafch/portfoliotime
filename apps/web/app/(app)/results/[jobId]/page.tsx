"use client";

import { useEffect, useState } from "react";
import Link from "next/link";
import { useParams } from "next/navigation";
import { apiRequest } from "@/lib/api";
import { pct, num } from "@/lib/format";
import EquityChart from "@/components/EquityChart";
import type { SimulationRecord } from "@/lib/types";

const ASSET_LABELS: Record<string, string> = {
  azioni: "Azioni",
  obbligazioni: "Obbligazioni",
  oro: "Oro",
  materie_prime: "Materie Prime",
  bitcoin: "Bitcoin",
};

const ASSET_COLORS: Record<string, string> = {
  azioni: "bg-green-500",
  obbligazioni: "bg-blue-500",
  oro: "bg-yellow-500",
  materie_prime: "bg-orange-500",
  bitcoin: "bg-purple-500",
};

export default function ResultsPage() {
  const { jobId } = useParams<{ jobId: string }>();
  const [record, setRecord] = useState<SimulationRecord | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    apiRequest<SimulationRecord>(`/simulate/${jobId}`)
      .then(setRecord)
      .catch((e) => setError(e instanceof Error ? e.message : "Errore"))
      .finally(() => setLoading(false));
  }, [jobId]);

  if (loading) return <p className="text-slate-500">Caricamento risultati…</p>;
  if (error) return <div className="rounded bg-red-950 px-4 py-3 text-red-400">{error}</div>;
  if (!record) return null;

  if (record.status === "failed" || !record.result) {
    return (
      <div>
        <Link href="/dashboard" className="text-sm text-slate-400 hover:text-white">← Dashboard</Link>
        <div className="mt-4 rounded bg-red-950 px-4 py-3 text-red-400">
          Simulazione fallita: {record.error || "errore sconosciuto"}
        </div>
      </div>
    );
  }

  const r = record.result;
  const metrics = [
    { label: "Rendimento totale", value: pct(r.total_return, true), big: true },
    { label: "CAGR annualizzato", value: pct(r.cagr) },
    { label: "Max Drawdown", value: pct(r.max_drawdown) },
    { label: "Sharpe Ratio", value: num(r.sharpe_ratio) },
    { label: "Volatilità annua", value: pct(r.annualized_volatility) },
    { label: "Rendimento reale", value: pct(r.real_return) },
  ];

  return (
    <div>
      <div className="mb-6 flex items-center justify-between">
        <div>
          <Link href="/dashboard" className="text-sm text-slate-400 hover:text-white">← Dashboard</Link>
          <h1 className="mt-1 text-3xl font-bold">{record.label}</h1>
        </div>
        <Link href="/simulate" className="rounded border border-slate-700 px-4 py-2 text-sm hover:border-slate-500">
          Nuova
        </Link>
      </div>

      {/* Metriche */}
      <section className="mb-6 grid grid-cols-2 gap-3 sm:grid-cols-3 lg:grid-cols-6">
        {metrics.map((m) => (
          <div key={m.label} className="rounded-lg border border-slate-800 bg-slate-900/50 p-4">
            <div className={`font-bold ${m.big ? "text-2xl text-green-400" : "text-xl"}`}>{m.value}</div>
            <div className="mt-1 text-xs text-slate-400">{m.label}</div>
          </div>
        ))}
      </section>

      <div className="grid grid-cols-1 gap-6 lg:grid-cols-3">
        {/* Grafico */}
        <section className="rounded-lg border border-slate-800 p-6 lg:col-span-2">
          <h2 className="mb-4 text-lg font-semibold">Andamento (base 100)</h2>
          <EquityChart data={r.equity_curve} />
        </section>

        {/* Allocazione */}
        <section className="rounded-lg border border-slate-800 p-6">
          <h2 className="mb-4 flex items-center gap-2 text-lg font-semibold">
            <span>Allocazione</span>
            <span className="rounded bg-slate-800 px-2 py-0.5 text-xs font-normal text-slate-400">
              {r.allocation_source === "custom" ? "personalizzata" : "Chameleon"}
            </span>
          </h2>
          <div className="space-y-3">
            {Object.entries(r.allocazione).map(([asset, val]) => (
              <div key={asset}>
                <div className="mb-1 flex justify-between text-sm">
                  <span className="text-slate-300">{ASSET_LABELS[asset] ?? asset}</span>
                  <span className="font-semibold">{val.toFixed(1)}%</span>
                </div>
                <div className="h-2 overflow-hidden rounded-full bg-slate-800">
                  <div className={`h-full ${ASSET_COLORS[asset] ?? "bg-slate-500"}`}
                    style={{ width: `${Math.min(val, 100)}%` }} />
                </div>
              </div>
            ))}
          </div>
        </section>
      </div>

      {/* Narrativa AI */}
      {record.narrative && (
        <section className="mt-6 rounded-lg border border-slate-800 bg-slate-900/50 p-6">
          <h2 className="mb-3 flex items-center gap-2 text-lg font-semibold">
            <span>Interpretazione</span>
            <span className="rounded bg-slate-800 px-2 py-0.5 text-xs text-slate-400">AI</span>
          </h2>
          <p className="leading-relaxed text-slate-300">{record.narrative}</p>
        </section>
      )}

      {/* Benchmark + warnings */}
      <section className="mt-6 grid grid-cols-1 gap-4 sm:grid-cols-2">
        <div className="rounded-lg border border-slate-800 p-4 text-sm">
          <h3 className="mb-2 font-semibold text-slate-300">Confronto benchmark (S&amp;P 500)</h3>
          <div className="flex justify-between text-slate-400">
            <span>Rendimento benchmark</span><span>{pct(r.benchmark_total_return, true)}</span>
          </div>
          <div className="flex justify-between text-slate-400">
            <span>CAGR benchmark</span><span>{pct(r.benchmark_cagr)}</span>
          </div>
          <div className="flex justify-between text-slate-400">
            <span>Max DD benchmark</span><span>{pct(r.benchmark_max_drawdown)}</span>
          </div>
        </div>
        {r.warnings.length > 0 && (
          <div className="rounded-lg border border-yellow-900 bg-yellow-950/30 p-4 text-sm text-yellow-400">
            {r.warnings.map((w, i) => <p key={i}>⚠ {w}</p>)}
          </div>
        )}
      </section>
    </div>
  );
}
