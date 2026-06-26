"use client";

import { useEffect, useState } from "react";
import Link from "next/link";
import { useRouter } from "next/navigation";
import { apiRequest } from "@/lib/api";
import { pct, num, formatDate } from "@/lib/format";
import { useAuth } from "@/lib/auth";
import type { SimulationSummary, PersonalAnalytics } from "@/lib/types";

export default function DashboardPage() {
  const { user } = useAuth();
  const [sims, setSims] = useState<SimulationSummary[]>([]);
  const [analytics, setAnalytics] = useState<PersonalAnalytics | null>(null);
  const [loading, setLoading] = useState(true);
  const router = useRouter();

  useEffect(() => {
    Promise.all([
      apiRequest<SimulationSummary[]>("/simulate").then(setSims).catch(() => setSims([])),
      apiRequest<PersonalAnalytics>("/me/analytics").then(setAnalytics).catch(() => setAnalytics(null)),
    ]).finally(() => setLoading(false));
  }, []);

  return (
    <div>
      <div className="mb-8 flex items-center justify-between">
        <div>
          <h1 className="text-3xl font-bold">Ciao, {user?.full_name || "investitore"}</h1>
          <p className="text-slate-400">Le tue simulazioni di portafoglio</p>
        </div>
        <Link
          href="/simulate"
          className="rounded-lg bg-green-500 px-5 py-2.5 font-semibold text-slate-950 transition hover:bg-green-400"
        >
          + Nuova simulazione
        </Link>
      </div>

      {/* Analytics personali */}
      {analytics && analytics.completed > 0 && (
        <section className="mb-8 grid grid-cols-2 gap-3 sm:grid-cols-4">
          <AnalyticCard label="Simulazioni" value={String(analytics.completed)} />
          <AnalyticCard label="Rendimento medio" value={pct(analytics.avg_total_return, true)}
            tone={(analytics.avg_total_return ?? 0) >= 0 ? "pos" : "neg"} />
          <AnalyticCard label="Sharpe medio" value={num(analytics.avg_sharpe)} />
          <AnalyticCard label="Battuto il benchmark"
            value={analytics.benchmark_win_rate === null ? "—" : `${Math.round(analytics.benchmark_win_rate * 100)}%`}
            tone={(analytics.benchmark_win_rate ?? 0) >= 0.5 ? "pos" : undefined} />
          {analytics.best && (
            <div className="col-span-2 rounded-lg border border-green-900 bg-green-950/20 p-4 sm:col-span-2">
              <div className="text-xs text-slate-400">Migliore simulazione</div>
              <div className="mt-1 flex items-baseline justify-between">
                <span className="text-sm">{analytics.best.label}</span>
                <span className="font-bold text-green-400">{pct(analytics.best.total_return, true)}</span>
              </div>
            </div>
          )}
          {analytics.worst && (
            <div className="col-span-2 rounded-lg border border-red-900 bg-red-950/20 p-4 sm:col-span-2">
              <div className="text-xs text-slate-400">Peggiore simulazione</div>
              <div className="mt-1 flex items-baseline justify-between">
                <span className="text-sm">{analytics.worst.label}</span>
                <span className="font-bold text-red-400">{pct(analytics.worst.total_return, true)}</span>
              </div>
            </div>
          )}
        </section>
      )}

      {loading ? (
        <p className="text-slate-500">Caricamento…</p>
      ) : sims.length === 0 ? (
        <div className="rounded-lg border border-dashed border-slate-800 p-12 text-center">
          <p className="mb-4 text-slate-400">Non hai ancora eseguito simulazioni.</p>
          <Link href="/simulate" className="text-green-400 hover:underline">
            Avvia la tua prima simulazione →
          </Link>
        </div>
      ) : (
        <div className="overflow-hidden rounded-lg border border-slate-800">
          <table className="w-full text-left text-sm">
            <thead className="bg-slate-900 text-slate-400">
              <tr>
                <th className="px-4 py-3">Periodo</th>
                <th className="px-4 py-3">Data</th>
                <th className="px-4 py-3 text-right">Rendimento</th>
                <th className="px-4 py-3 text-right">CAGR</th>
                <th className="px-4 py-3 text-right">Stato</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-slate-800">
              {sims.map((s) => (
                <tr
                  key={s.id}
                  onClick={() => router.push(`/results/${s.id}`)}
                  className="cursor-pointer transition hover:bg-slate-900"
                >
                  <td className="px-4 py-3 font-medium">{s.label}</td>
                  <td className="px-4 py-3 text-slate-400">{formatDate(s.created_at)}</td>
                  <td className={`px-4 py-3 text-right font-semibold ${
                    (s.total_return ?? 0) >= 0 ? "text-green-400" : "text-red-400"
                  }`}>
                    {pct(s.total_return, true)}
                  </td>
                  <td className="px-4 py-3 text-right text-slate-300">{pct(s.cagr)}</td>
                  <td className="px-4 py-3 text-right">
                    <span className={`rounded px-2 py-0.5 text-xs ${
                      s.status === "completed"
                        ? "bg-green-500/10 text-green-400"
                        : "bg-red-500/10 text-red-400"
                    }`}>
                      {s.status === "completed" ? "completata" : "fallita"}
                    </span>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}
    </div>
  );
}

function AnalyticCard({ label, value, tone }: { label: string; value: string; tone?: "pos" | "neg" }) {
  const color = tone === "pos" ? "text-green-400" : tone === "neg" ? "text-red-400" : "text-white";
  return (
    <div className="rounded-lg border border-slate-800 bg-slate-900/50 p-4">
      <div className={`text-2xl font-bold ${color}`}>{value}</div>
      <div className="mt-1 text-xs text-slate-400">{label}</div>
    </div>
  );
}
