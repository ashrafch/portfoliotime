"use client";

import { useEffect, useState } from "react";
import { useParams } from "next/navigation";

const API = process.env.NEXT_PUBLIC_API_URL ?? "http://localhost:8000";

interface SimResult {
  allocazione: Record<string, number>;
  cagr: number;
  max_drawdown: number;
  sharpe_ratio: number;
  annualized_volatility: number;
  total_return: number;
  benchmark_cagr: number;
  benchmark_max_drawdown: number;
  sources: Record<string, string>;
  warnings: string[];
}

function fmt(v: number, pct = true): string {
  if (isNaN(v)) return "—";
  return pct ? `${(v * 100).toFixed(2)}%` : v.toFixed(2);
}

export default function ResultsPage() {
  const { jobId } = useParams<{ jobId: string }>();
  const [status, setStatus] = useState("loading");
  const [result, setResult] = useState<SimResult | null>(null);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    let timer: ReturnType<typeof setInterval>;
    async function poll() {
      try {
        const res = await fetch(`${API}/simulate/${jobId}/result`);
        const data = await res.json();
        setStatus(data.status);
        if (data.status === "completed") {
          setResult(data.result);
          clearInterval(timer);
        } else if (data.status === "failed") {
          setError(data.error ?? "Simulazione fallita");
          clearInterval(timer);
        }
      } catch {
        setError("Errore di connessione all'API");
        clearInterval(timer);
      }
    }
    poll();
    timer = setInterval(poll, 2000);
    return () => clearInterval(timer);
  }, [jobId]);

  if (status === "loading" || status === "queued" || status === "running") {
    return (
      <main className="flex min-h-screen items-center justify-center">
        <div className="text-center">
          <div className="mb-4 text-green-400 text-4xl animate-pulse">⏳</div>
          <p className="text-slate-400">Simulazione in corso...</p>
        </div>
      </main>
    );
  }

  if (error) {
    return (
      <main className="mx-auto max-w-2xl px-4 py-12">
        <div className="rounded bg-red-950 px-4 py-3 text-red-400">{error}</div>
      </main>
    );
  }

  if (!result) return null;

  return (
    <main className="mx-auto max-w-4xl px-4 py-12">
      <h1 className="mb-8 text-3xl font-bold">Risultati simulazione</h1>

      {/* Allocazione */}
      <section className="mb-8 rounded-lg border border-slate-800 p-6">
        <h2 className="mb-4 text-lg font-semibold text-green-400">Allocazione Chameleon</h2>
        <div className="grid grid-cols-2 gap-3 sm:grid-cols-5">
          {Object.entries(result.allocazione).map(([asset, pct]) => (
            <div key={asset} className="rounded bg-slate-900 p-3 text-center">
              <div className="text-xl font-bold text-green-400">{pct.toFixed(1)}%</div>
              <div className="text-xs text-slate-400 capitalize">{asset.replace("_", " ")}</div>
            </div>
          ))}
        </div>
      </section>

      {/* Metriche */}
      <section className="mb-8 rounded-lg border border-slate-800 p-6">
        <h2 className="mb-4 text-lg font-semibold text-green-400">Performance metriche</h2>
        <div className="grid grid-cols-2 gap-4 sm:grid-cols-3">
          {[
            { label: "Rendimento totale", value: fmt(result.total_return) },
            { label: "CAGR annualizzato", value: fmt(result.cagr) },
            { label: "Max Drawdown", value: fmt(result.max_drawdown) },
            { label: "Sharpe Ratio", value: fmt(result.sharpe_ratio, false) },
            { label: "Volatilità annua", value: fmt(result.annualized_volatility) },
            { label: "Benchmark CAGR (SPY)", value: fmt(result.benchmark_cagr) },
          ].map((m) => (
            <div key={m.label} className="rounded bg-slate-900 p-4">
              <div className="text-xl font-bold">{m.value}</div>
              <div className="text-xs text-slate-400">{m.label}</div>
            </div>
          ))}
        </div>
      </section>

      {result.warnings.length > 0 && (
        <div className="rounded bg-yellow-950 px-4 py-3 text-sm text-yellow-400">
          {result.warnings.map((w, i) => <p key={i}>⚠ {w}</p>)}
        </div>
      )}
    </main>
  );
}
