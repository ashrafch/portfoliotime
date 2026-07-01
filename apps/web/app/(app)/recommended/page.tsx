"use client";

import { useEffect, useState, useCallback } from "react";
import Link from "next/link";
import { apiRequest } from "@/lib/api";
import { pct } from "@/lib/format";
import FredNotice from "@/components/FredNotice";
import type { RecommendedResult, Allocation } from "@/lib/types";

const LABELS: Record<string, string> = {
  azioni: "Azioni", obbligazioni: "Obbligazioni", oro: "Oro",
  materie_prime: "Materie Prime", bitcoin: "Bitcoin",
};
const COLORS: Record<string, string> = {
  azioni: "bg-green-500", obbligazioni: "bg-blue-500", oro: "bg-yellow-500",
  materie_prime: "bg-orange-500", bitcoin: "bg-purple-500",
};

export default function RecommendedPage() {
  const [data, setData] = useState<RecommendedResult | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  const load = useCallback(() => {
    setLoading(true);
    apiRequest<RecommendedResult>("/portfolio/recommended")
      .then(setData)
      .catch((e) => setError(e instanceof Error ? e.message : "Errore"))
      .finally(() => setLoading(false));
  }, []);

  useEffect(() => { load(); }, [load]);

  if (loading) return <p className="text-slate-500">Calcolo allocazione…</p>;
  if (error) return <div className="rounded bg-red-950 px-4 py-3 text-red-400">{error}</div>;
  if (!data) return null;

  const m = data.macro_used;

  return (
    <div>
      <FredNotice />
      <div className="mb-1 flex items-center gap-2">
        <h1 className="text-3xl font-bold">Allocazione di oggi</h1>
        <span className={`rounded px-2 py-0.5 text-xs ${data.source === "fred" ? "bg-green-500/10 text-green-400" : "bg-slate-700/50 text-slate-300"}`}>
          fonte: {data.source === "fred" ? "FRED (dati reali)" : "profilo"}
        </span>
      </div>
      <p className="mb-6 text-slate-400">Cosa suggerisce il modello Chameleon nella situazione attuale.</p>

      {/* Cambiamenti rispetto all'ultimo calcolo */}
      {data.changes.length > 0 ? (
        <div className="mb-6 rounded-lg border border-amber-700 bg-amber-950/20 p-4">
          <p className="mb-2 text-sm font-semibold text-amber-400">È cambiata rispetto all&apos;ultimo calcolo:</p>
          <ul className="space-y-1 text-sm text-slate-300">
            {data.changes.map((c) => (
              <li key={c.asset}>
                {LABELS[c.asset] ?? c.asset}: <span className="text-slate-400">{c.da}%</span> → <strong>{c.a}%</strong>
              </li>
            ))}
          </ul>
        </div>
      ) : (
        <div className="mb-6 rounded-lg border border-slate-800 bg-slate-900/40 p-4 text-sm text-slate-400">
          Nessun cambiamento rispetto all&apos;ultimo calcolo.
        </div>
      )}

      {/* Allocazione */}
      <section className="mb-6 rounded-lg border border-slate-800 p-6">
        <div className="space-y-3">
          {Object.entries(data.allocazione).map(([asset, val]) => (
            <div key={asset}>
              <div className="mb-1 flex justify-between text-sm">
                <span className="text-slate-300">{LABELS[asset] ?? asset}</span>
                <span className="font-semibold">{(val as number).toFixed(1)}%</span>
              </div>
              <div className="h-2 overflow-hidden rounded-full bg-slate-800">
                <div className={`h-full ${COLORS[asset] ?? "bg-slate-500"}`} style={{ width: `${Math.min(val as number, 100)}%` }} />
              </div>
            </div>
          ))}
        </div>
      </section>

      <section className="mb-4 rounded-lg border border-slate-800 p-4 text-sm text-slate-400">
        <span className="font-semibold text-slate-300">Situazione macro usata: </span>
        tasso FED {m.tasso_fed}% · inflazione {m.inflazione}% · tasso nominale {m.tasso_nominale}%
        {m.tassi_in_calo ? " · tassi in calo" : ""}
      </section>

      <div className="flex items-center gap-4">
        <button onClick={load} className="rounded border border-slate-700 px-4 py-2 text-sm text-slate-300 hover:border-green-500">
          Ricalcola
        </button>
        <p className="text-xs text-slate-500">
          {data.note} <Link href="/categorie" className="text-green-400 hover:underline">Cosa scegliere per categoria →</Link>
        </p>
      </div>
    </div>
  );
}
