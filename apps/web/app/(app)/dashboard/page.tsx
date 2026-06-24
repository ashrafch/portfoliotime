"use client";

import { useEffect, useState } from "react";
import Link from "next/link";
import { useRouter } from "next/navigation";
import { apiRequest } from "@/lib/api";
import { pct, formatDate } from "@/lib/format";
import { useAuth } from "@/lib/auth";
import type { SimulationSummary } from "@/lib/types";

export default function DashboardPage() {
  const { user } = useAuth();
  const [sims, setSims] = useState<SimulationSummary[]>([]);
  const [loading, setLoading] = useState(true);
  const router = useRouter();

  useEffect(() => {
    apiRequest<SimulationSummary[]>("/simulate")
      .then(setSims)
      .catch(() => setSims([]))
      .finally(() => setLoading(false));
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
