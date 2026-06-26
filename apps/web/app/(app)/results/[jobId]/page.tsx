"use client";

import { useEffect, useState } from "react";
import Link from "next/link";
import { useParams } from "next/navigation";
import { apiRequest, getToken, API_BASE_URL } from "@/lib/api";
import { pct, num, money } from "@/lib/format";
import EquityChart from "@/components/EquityChart";
import MonteCarloChart from "@/components/MonteCarloChart";
import InfoTip from "@/components/InfoTip";
import type {
  SimulationRecord, InvestorProfile, MarketEvent, MonteCarloResult,
} from "@/lib/types";

const ASSET_LABELS: Record<string, string> = {
  azioni: "Azioni", obbligazioni: "Obbligazioni", oro: "Oro",
  materie_prime: "Materie Prime", bitcoin: "Bitcoin",
};
const ASSET_COLORS: Record<string, string> = {
  azioni: "bg-green-500", obbligazioni: "bg-blue-500", oro: "bg-yellow-500",
  materie_prime: "bg-orange-500", bitcoin: "bg-purple-500",
};

export default function ResultsPage() {
  const { jobId } = useParams<{ jobId: string }>();
  const [record, setRecord] = useState<SimulationRecord | null>(null);
  const [currency, setCurrency] = useState("EUR");
  const [events, setEvents] = useState<MarketEvent[]>([]);
  const [mc, setMc] = useState<MonteCarloResult | null>(null);
  const [mcLoading, setMcLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    apiRequest<SimulationRecord>(`/simulate/${jobId}`)
      .then(async (rec) => {
        setRecord(rec);
        const p = rec.input_params as { date_from?: string; date_to?: string } | undefined;
        if (p?.date_from && p?.date_to) {
          apiRequest<MarketEvent[]>(`/scenarios/events?date_from=${p.date_from}&date_to=${p.date_to}`, { auth: false })
            .then(setEvents).catch(() => {});
        }
      })
      .catch((e) => setError(e instanceof Error ? e.message : "Errore"))
      .finally(() => setLoading(false));
    apiRequest<InvestorProfile>("/me/profile").then((p) => setCurrency(p.base_currency)).catch(() => {});
  }, [jobId]);

  async function loadMonteCarlo() {
    setMcLoading(true);
    try {
      setMc(await apiRequest<MonteCarloResult>(`/simulate/${jobId}/montecarlo?n_sims=500`));
    } catch (e) {
      setError(e instanceof Error ? e.message : "Errore Monte Carlo");
    } finally {
      setMcLoading(false);
    }
  }

  async function downloadCsv() {
    const res = await fetch(`${API_BASE_URL}/simulate/${jobId}/export.csv`, {
      headers: { Authorization: `Bearer ${getToken()}` },
    });
    const blob = await res.blob();
    const url = URL.createObjectURL(blob);
    const a = document.createElement("a");
    a.href = url;
    a.download = `portfoliotime_${jobId.slice(0, 8)}.csv`;
    a.click();
    URL.revokeObjectURL(url);
  }

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
  const m = r.money;

  // Semaforo di sintesi
  const rendTone = (r.total_return ?? 0) >= 0 ? "green" : "red";
  const ddVal = r.max_drawdown ?? 0;
  const rischioTone = ddVal > -0.15 ? "green" : ddVal > -0.35 ? "yellow" : "red";
  const beatBench =
    r.benchmark_total_return != null && r.total_return != null && r.total_return > r.benchmark_total_return;

  return (
    <div className="print-light">
      <div className="mb-6 flex flex-wrap items-center justify-between gap-3">
        <div>
          <Link href="/dashboard" className="no-print text-sm text-slate-400 hover:text-white">← Dashboard</Link>
          <h1 className="mt-1 text-3xl font-bold">{record.label}</h1>
          <p className="text-xs text-slate-500">
            Allocazione {r.allocation_source === "custom" ? "personalizzata" : "Chameleon"}
          </p>
        </div>
        <div className="no-print flex gap-2">
          <button onClick={downloadCsv}
            className="rounded border border-slate-700 px-3 py-2 text-sm text-slate-300 hover:border-green-500">
            Esporta CSV
          </button>
          <button onClick={() => window.print()}
            className="rounded border border-slate-700 px-3 py-2 text-sm text-slate-300 hover:border-green-500">
            Esporta PDF
          </button>
          <Link href="/simulate" className="rounded bg-green-500 px-4 py-2 text-sm font-semibold text-slate-950 hover:bg-green-400">
            Nuova
          </Link>
        </div>
      </div>

      {/* Semaforo di sintesi */}
      <section className="mb-6 grid grid-cols-1 gap-3 sm:grid-cols-3">
        <Light tone={rendTone} title="Rendimento"
          value={pct(r.total_return, true)}
          note={rendTone === "green" ? "Il portafoglio ha guadagnato" : "Il portafoglio ha perso"} />
        <Light tone={rischioTone} title="Rischio (perdita max)"
          value={pct(r.max_drawdown)}
          note={rischioTone === "green" ? "Cadute contenute" : rischioTone === "yellow" ? "Oscillazioni medie" : "Cadute marcate"} />
        <Light tone={beatBench ? "green" : "yellow"} title="Vs mercato (S&P 500)"
          value={beatBench ? "Meglio" : "Peggio"}
          note={`Benchmark ${pct(r.benchmark_total_return, true)}`} />
      </section>

      {/* Pannello denaro */}
      {m && (
        <section className="mb-6 rounded-lg border border-slate-800 bg-slate-900/50 p-6">
          <h2 className="mb-4 text-lg font-semibold">In denaro</h2>
          <div className="grid grid-cols-2 gap-4 sm:grid-cols-4">
            <Money label={m.is_dca ? "Totale versato" : "Capitale iniziale"} value={money(m.total_invested, currency)} />
            <Money label="Valore finale" value={money(m.final_value, currency)} accent />
            <Money label="Guadagno/Perdita" value={money(m.gain, currency)} tone={m.gain >= 0 ? "pos" : "neg"} />
            <Money label={<span className="inline-flex items-center gap-1">Rendimento {m.is_dca && <InfoTip term="money_return" />}</span>}
              value={pct(m.money_return, true)} tone={(m.money_return ?? 0) >= 0 ? "pos" : "neg"} />
          </div>
          {m.is_dca && (
            <p className="mt-3 text-xs text-slate-500">
              Piano di accumulo: {m.contributions_count} versamenti da {money(m.contribution, currency)}.
              Il rendimento sul capitale versato differisce da quello della strategia perché i versamenti
              più recenti hanno avuto meno tempo per crescere.
            </p>
          )}
          <p className="mt-2 text-xs text-slate-500">
            Importi in {currency} nominale. I rendimenti sono su asset quotati in USD e non includono l&apos;effetto cambio.
          </p>
        </section>
      )}

      {/* Spiegazione in chiaro */}
      <section className="mb-6 rounded-lg border border-slate-800 p-6">
        <h2 className="mb-3 text-lg font-semibold">In parole semplici</h2>
        <ul className="space-y-2 text-sm text-slate-300">
          <li>
            • Nel periodo, il valore è {(r.total_return ?? 0) >= 0 ? "cresciuto" : "sceso"} del{" "}
            <strong>{pct(r.total_return, true)}</strong> ({pct(r.cagr)} all&apos;anno in media).
          </li>
          <li>
            • In un anno tipico il valore poteva oscillare di circa{" "}
            <strong>±{pct(r.annualized_volatility)}</strong> (volatilità).
          </li>
          <li>
            • Nel momento peggiore avresti visto il capitale scendere del{" "}
            <strong>{pct(r.max_drawdown)}</strong> dal punto più alto
            {r.max_underwater_days != null && r.max_underwater_days > 0 && (
              <>, restando sotto il massimo per circa <strong>{r.max_underwater_days} giorni</strong>
              {r.drawdown_recovered === false && " (non ancora recuperato a fine periodo)"}</>
            )}.
          </li>
        </ul>
      </section>

      <div className="grid grid-cols-1 gap-6 lg:grid-cols-3">
        {/* Grafico con eventi */}
        <section className="rounded-lg border border-slate-800 p-6 lg:col-span-2">
          <h2 className="mb-4 text-lg font-semibold">Andamento (base 100)</h2>
          <EquityChart data={r.equity_curve} events={events} />
        </section>

        {/* Allocazione */}
        <section className="rounded-lg border border-slate-800 p-6">
          <h2 className="mb-4 text-lg font-semibold">Allocazione</h2>
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

      {/* Metriche dettagliate */}
      <section className="mt-6 rounded-lg border border-slate-800 p-6">
        <h2 className="mb-4 text-lg font-semibold">Metriche dettagliate</h2>
        <div className="grid grid-cols-2 gap-4 sm:grid-cols-3 lg:grid-cols-4">
          <Metric term="cagr" label="CAGR" value={pct(r.cagr)} />
          <Metric term="sharpe_ratio" label="Sharpe" value={num(r.sharpe_ratio)} />
          <Metric term="sortino_ratio" label="Sortino" value={num(r.sortino_ratio)} />
          <Metric term="calmar_ratio" label="Calmar" value={num(r.calmar_ratio)} />
          <Metric term="annualized_volatility" label="Volatilità" value={pct(r.annualized_volatility)} />
          <Metric term="var_95" label="VaR 95% (giorno)" value={pct(r.var_95)} />
          <Metric term="cvar_95" label="CVaR 95% (giorno)" value={pct(r.cvar_95)} />
          <Metric term="beta" label="Beta" value={num(r.beta)} />
          <Metric term="real_return" label="Rend. reale" value={pct(r.real_return, true)} />
          <Metric term="max_drawdown" label="Max Drawdown" value={pct(r.max_drawdown)} />
        </div>
      </section>

      {/* Monte Carlo */}
      <section className="mt-6 rounded-lg border border-slate-800 p-6">
        <div className="mb-2 flex items-center justify-between">
          <h2 className="text-lg font-semibold">Proiezione Monte Carlo</h2>
          {!mc && (
            <button onClick={loadMonteCarlo} disabled={mcLoading}
              className="no-print rounded border border-slate-700 px-3 py-1.5 text-sm text-slate-300 hover:border-green-500 disabled:opacity-50">
              {mcLoading ? "Calcolo…" : "Calcola proiezione"}
            </button>
          )}
        </div>
        {!mc ? (
          <p className="text-sm text-slate-500">
            Genera una distribuzione di scenari plausibili ricampionando i rendimenti del periodo.
          </p>
        ) : (
          <div>
            <div className="mb-4 grid grid-cols-2 gap-3 sm:grid-cols-4">
              <Money label="Scenario sfavorevole (p5)" value={pct(mc.final_return.p5, true)} tone="neg" />
              <Money label="Scenario mediano (p50)" value={pct(mc.final_return.p50, true)} />
              <Money label="Scenario favorevole (p95)" value={pct(mc.final_return.p95, true)} tone="pos" />
              <Money label="Probabilità di perdita" value={`${Math.round(mc.prob_loss * 100)}%`} />
            </div>
            <MonteCarloChart mc={mc} />
            <p className="mt-3 rounded bg-slate-900/60 p-3 text-xs text-slate-500">
              ⚠ {mc.disclaimer} Metodo: {mc.method}, {mc.n_simulations} simulazioni.
            </p>
          </div>
        )}
      </section>

      {/* Narrativa */}
      {record.narrative && (
        <section className="mt-6 rounded-lg border border-slate-800 bg-slate-900/50 p-6">
          <h2 className="mb-3 flex items-center gap-2 text-lg font-semibold">
            <span>Interpretazione</span>
            <span className="no-print rounded bg-slate-800 px-2 py-0.5 text-xs text-slate-400">AI</span>
          </h2>
          <p className="leading-relaxed text-slate-300">{record.narrative}</p>
        </section>
      )}

      {r.warnings.length > 0 && (
        <div className="mt-6 rounded-lg border border-yellow-900 bg-yellow-950/30 p-4 text-sm text-yellow-400">
          {r.warnings.map((w, i) => <p key={i}>⚠ {w}</p>)}
        </div>
      )}
    </div>
  );
}

function Light({ tone, title, value, note }: {
  tone: "green" | "yellow" | "red"; title: string; value: string; note: string;
}) {
  const map = {
    green: "border-green-700 bg-green-950/20 text-green-400",
    yellow: "border-yellow-700 bg-yellow-950/20 text-yellow-400",
    red: "border-red-700 bg-red-950/20 text-red-400",
  }[tone];
  return (
    <div className={`rounded-lg border p-4 ${map}`}>
      <div className="text-xs uppercase tracking-wide opacity-80">{title}</div>
      <div className="mt-1 text-2xl font-bold">{value}</div>
      <div className="mt-1 text-xs opacity-90">{note}</div>
    </div>
  );
}

function Money({ label, value, accent, tone }: {
  label: React.ReactNode; value: string; accent?: boolean; tone?: "pos" | "neg";
}) {
  const color = tone === "pos" ? "text-green-400" : tone === "neg" ? "text-red-400" : accent ? "text-green-400" : "text-white";
  return (
    <div className="rounded-lg border border-slate-800 bg-slate-900/40 p-4">
      <div className={`text-xl font-bold ${color}`}>{value}</div>
      <div className="mt-1 text-xs text-slate-400">{label}</div>
    </div>
  );
}

function Metric({ term, label, value }: { term: string; label: string; value: string }) {
  return (
    <div className="rounded-lg border border-slate-800 bg-slate-900/40 p-4">
      <div className="text-xl font-bold">{value}</div>
      <div className="mt-1 flex items-center gap-1 text-xs text-slate-400">
        {label} <InfoTip term={term} />
      </div>
    </div>
  );
}
