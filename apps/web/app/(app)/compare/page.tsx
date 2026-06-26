"use client";

import { Suspense, useEffect, useState } from "react";
import Link from "next/link";
import { useSearchParams } from "next/navigation";
import { apiRequest } from "@/lib/api";
import { pct, num } from "@/lib/format";
import CompareChart from "@/components/CompareChart";
import type { SimulationRecord, Allocation } from "@/lib/types";

const ASSET_LABELS: Record<string, string> = {
  azioni: "Azioni", obbligazioni: "Obbligazioni", oro: "Oro",
  materie_prime: "Materie Prime", bitcoin: "Bitcoin",
};

// metriche: higher = migliore quando true; per volatilità lower è meglio
const METRICS: { key: string; label: string; higherBetter: boolean; fmt: (v: number | null) => string }[] = [
  { key: "total_return", label: "Rendimento totale", higherBetter: true, fmt: (v) => pct(v, true) },
  { key: "cagr", label: "CAGR annualizzato", higherBetter: true, fmt: (v) => pct(v) },
  { key: "real_return", label: "Rendimento reale", higherBetter: true, fmt: (v) => pct(v, true) },
  { key: "max_drawdown", label: "Max Drawdown", higherBetter: true, fmt: (v) => pct(v) }, // -10% > -40%
  { key: "annualized_volatility", label: "Volatilità annua", higherBetter: false, fmt: (v) => pct(v) },
  { key: "sharpe_ratio", label: "Sharpe Ratio", higherBetter: true, fmt: (v) => num(v) },
];

function CompareContent() {
  const params = useSearchParams();
  const idA = params.get("a");
  const idB = params.get("b");

  const [a, setA] = useState<SimulationRecord | null>(null);
  const [b, setB] = useState<SimulationRecord | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    if (!idA || !idB) {
      setError("Seleziona due simulazioni da confrontare.");
      setLoading(false);
      return;
    }
    Promise.all([
      apiRequest<SimulationRecord>(`/simulate/${idA}`),
      apiRequest<SimulationRecord>(`/simulate/${idB}`),
    ])
      .then(([ra, rb]) => { setA(ra); setB(rb); })
      .catch((e) => setError(e instanceof Error ? e.message : "Errore"))
      .finally(() => setLoading(false));
  }, [idA, idB]);

  if (loading) return <p className="text-slate-500">Caricamento confronto…</p>;
  if (error) return <div className="rounded bg-red-950 px-4 py-3 text-red-400">{error}</div>;
  if (!a?.result || !b?.result) {
    return <div className="rounded bg-red-950 px-4 py-3 text-red-400">Una delle simulazioni non ha risultati.</div>;
  }

  const ra = a.result, rb = b.result;

  // Verdetto in linguaggio naturale sul rendimento totale
  const trA = ra.total_return ?? 0;
  const trB = rb.total_return ?? 0;
  const deltaPts = Math.abs(trA - trB) * 100;
  const winner = trA === trB ? null : trA > trB ? "A" : "B";

  return (
    <div>
      <Link href="/dashboard" className="text-sm text-slate-400 hover:text-white">← Dashboard</Link>
      <h1 className="mt-1 mb-6 text-3xl font-bold">Confronto simulazioni</h1>

      {/* Verdetto in chiaro */}
      <div className="mb-6 rounded-lg border border-slate-800 bg-slate-900/50 p-5">
        {winner ? (
          <p className="text-lg">
            <span className={winner === "A" ? "font-bold text-green-400" : "font-bold text-blue-400"}>
              {winner === "A" ? "A" : "B"}
            </span>{" "}
            ha reso <span className="font-bold">{deltaPts.toFixed(1)} punti percentuali</span> in più
            {" "}({winner === "A" ? pct(trA, true) : pct(trB, true)} contro{" "}
            {winner === "A" ? pct(trB, true) : pct(trA, true)}).
          </p>
        ) : (
          <p className="text-lg">Le due simulazioni hanno reso uguale.</p>
        )}
      </div>

      {/* Intestazioni colonne */}
      <div className="mb-4 grid grid-cols-2 gap-4">
        <ColHeader tag="A" color="green" label={a.label} source={ra.allocation_source} />
        <ColHeader tag="B" color="blue" label={b.label} source={rb.allocation_source} />
      </div>

      {/* Grafico sovrapposto */}
      <section className="mb-6 rounded-lg border border-slate-800 p-6">
        <h2 className="mb-4 text-lg font-semibold">Andamento a confronto</h2>
        <CompareChart
          seriesA={ra.equity_curve} seriesB={rb.equity_curve}
          labelA={a.label} labelB={b.label}
        />
      </section>

      {/* Tabella metriche con vincitore evidenziato */}
      <section className="mb-6 overflow-hidden rounded-lg border border-slate-800">
        <table className="w-full text-sm">
          <thead className="bg-slate-900 text-slate-400">
            <tr>
              <th className="px-4 py-3 text-left">Metrica</th>
              <th className="px-4 py-3 text-right">A</th>
              <th className="px-4 py-3 text-right">B</th>
              <th className="px-4 py-3 text-center">Migliore</th>
            </tr>
          </thead>
          <tbody className="divide-y divide-slate-800">
            {METRICS.map((m) => {
              const va = ra[m.key as keyof typeof ra] as number | null;
              const vb = rb[m.key as keyof typeof rb] as number | null;
              const better = pickBetter(va, vb, m.higherBetter);
              return (
                <tr key={m.key}>
                  <td className="px-4 py-3 text-slate-300">{m.label}</td>
                  <td className={`px-4 py-3 text-right font-semibold ${better === "A" ? "text-green-400" : ""}`}>
                    {m.fmt(va ?? null)}
                  </td>
                  <td className={`px-4 py-3 text-right font-semibold ${better === "B" ? "text-blue-400" : ""}`}>
                    {m.fmt(vb ?? null)}
                  </td>
                  <td className="px-4 py-3 text-center">
                    {better === "A" && <span className="rounded bg-green-500/10 px-2 py-0.5 text-xs text-green-400">A</span>}
                    {better === "B" && <span className="rounded bg-blue-500/10 px-2 py-0.5 text-xs text-blue-400">B</span>}
                    {better === null && <span className="text-slate-600">=</span>}
                  </td>
                </tr>
              );
            })}
          </tbody>
        </table>
      </section>

      {/* Allocazioni affiancate */}
      <section className="mb-6 grid grid-cols-1 gap-4 sm:grid-cols-2">
        <AllocCard title="Allocazione A" alloc={ra.allocazione} color="green" />
        <AllocCard title="Allocazione B" alloc={rb.allocazione} color="blue" />
      </section>

      {/* Narrative affiancate */}
      <section className="grid grid-cols-1 gap-4 sm:grid-cols-2">
        {[{ rec: a, tag: "A" }, { rec: b, tag: "B" }].map(({ rec, tag }) => (
          rec.narrative ? (
            <div key={tag} className="rounded-lg border border-slate-800 bg-slate-900/50 p-5">
              <h3 className="mb-2 text-sm font-semibold text-slate-400">Interpretazione {tag}</h3>
              <p className="text-sm leading-relaxed text-slate-300">{rec.narrative}</p>
            </div>
          ) : null
        ))}
      </section>
    </div>
  );
}

function pickBetter(a: number | null, b: number | null, higherBetter: boolean): "A" | "B" | null {
  if (a === null || b === null || Number.isNaN(a) || Number.isNaN(b)) return null;
  if (a === b) return null;
  const aWins = higherBetter ? a > b : a < b;
  return aWins ? "A" : "B";
}

function ColHeader({ tag, color, label, source }: {
  tag: string; color: "green" | "blue"; label: string; source?: string;
}) {
  const c = color === "green" ? "text-green-400 border-green-700" : "text-blue-400 border-blue-700";
  return (
    <div className={`rounded-lg border ${c} bg-slate-900/40 p-3`}>
      <div className="flex items-center gap-2">
        <span className={`flex h-6 w-6 items-center justify-center rounded-full border ${c} text-xs font-bold`}>{tag}</span>
        <span className="text-sm font-medium">{label}</span>
      </div>
      <div className="mt-1 text-xs text-slate-500">
        Allocazione {source === "custom" ? "personalizzata" : "Chameleon"}
      </div>
    </div>
  );
}

function AllocCard({ title, alloc, color }: { title: string; alloc: Allocation; color: "green" | "blue" }) {
  const bar = color === "green" ? "bg-green-500" : "bg-blue-500";
  return (
    <div className="rounded-lg border border-slate-800 p-5">
      <h3 className="mb-3 text-sm font-semibold text-slate-300">{title}</h3>
      <div className="space-y-2">
        {Object.entries(alloc).map(([k, v]) => (
          <div key={k}>
            <div className="mb-1 flex justify-between text-xs">
              <span className="text-slate-400">{ASSET_LABELS[k] ?? k}</span>
              <span className="font-semibold">{(v as number).toFixed(1)}%</span>
            </div>
            <div className="h-1.5 overflow-hidden rounded-full bg-slate-800">
              <div className={`h-full ${bar}`} style={{ width: `${Math.min(v as number, 100)}%` }} />
            </div>
          </div>
        ))}
      </div>
    </div>
  );
}

export default function ComparePage() {
  return (
    <Suspense fallback={<p className="text-slate-500">Caricamento…</p>}>
      <CompareContent />
    </Suspense>
  );
}
