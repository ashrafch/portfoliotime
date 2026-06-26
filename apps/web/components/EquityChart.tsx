"use client";

import type { EquityPoint, MarketEvent } from "@/lib/types";

// Grafico a linee SVG self-contained (nessuna libreria esterna).
export default function EquityChart({ data, events = [] }: { data: EquityPoint[]; events?: MarketEvent[] }) {
  if (!data || data.length < 2) {
    return <p className="text-sm text-slate-500">Curva non disponibile.</p>;
  }

  const W = 720;
  const H = 280;
  const pad = { top: 16, right: 16, bottom: 28, left: 44 };

  const hasBench = data.some((d) => typeof d.benchmark === "number");

  const allValues = data.flatMap((d) =>
    [d.portfolio, hasBench ? d.benchmark : undefined].filter((v): v is number => typeof v === "number")
  );
  const minV = Math.min(...allValues);
  const maxV = Math.max(...allValues);
  const range = maxV - minV || 1;

  const xOf = (i: number) =>
    pad.left + (i / (data.length - 1)) * (W - pad.left - pad.right);
  const yOf = (v: number) =>
    pad.top + (1 - (v - minV) / range) * (H - pad.top - pad.bottom);

  const linePath = (key: "portfolio" | "benchmark") =>
    data
      .map((d, i) => {
        const v = d[key];
        if (typeof v !== "number") return "";
        return `${i === 0 ? "M" : "L"} ${xOf(i).toFixed(1)} ${yOf(v).toFixed(1)}`;
      })
      .filter(Boolean)
      .join(" ");

  // 4 etichette sull'asse Y
  const yTicks = [0, 0.25, 0.5, 0.75, 1].map((t) => {
    const v = minV + t * range;
    return { v, y: yOf(v) };
  });

  // Etichette X: prima, metà, ultima
  const xLabels = [0, Math.floor(data.length / 2), data.length - 1];

  // Mappa ogni evento al punto dati più vicino per data
  const eventMarkers = events
    .map((ev, k) => {
      let best = -1;
      for (let i = 0; i < data.length; i++) {
        if (data[i].date <= ev.date) best = i;
        else break;
      }
      if (best < 0) return null;
      return { x: xOf(best), label: ev.label, date: ev.date, k };
    })
    .filter((m): m is { x: number; label: string; date: string; k: number } => m !== null);

  return (
    <div className="w-full overflow-x-auto">
      <svg viewBox={`0 0 ${W} ${H}`} className="w-full" style={{ minWidth: 480 }}>
        {/* griglia orizzontale */}
        {yTicks.map((t, i) => (
          <g key={i}>
            <line x1={pad.left} y1={t.y} x2={W - pad.right} y2={t.y} stroke="#1e293b" strokeWidth="1" />
            <text x={pad.left - 6} y={t.y + 3} textAnchor="end" fontSize="10" fill="#64748b">
              {t.v.toFixed(0)}
            </text>
          </g>
        ))}

        {/* marker eventi storici (linee verticali) */}
        {eventMarkers.map((m) => (
          <line key={m.k} x1={m.x} y1={pad.top} x2={m.x} y2={H - pad.bottom}
            stroke="#f59e0b" strokeWidth="1" strokeDasharray="2 2" opacity="0.55" />
        ))}

        {/* etichette X */}
        {xLabels.map((i) => (
          <text key={i} x={xOf(i)} y={H - 8} textAnchor="middle" fontSize="10" fill="#64748b">
            {data[i]?.date}
          </text>
        ))}

        {/* benchmark */}
        {hasBench && (
          <path d={linePath("benchmark")} fill="none" stroke="#64748b" strokeWidth="1.5" strokeDasharray="4 3" />
        )}
        {/* portfolio */}
        <path d={linePath("portfolio")} fill="none" stroke="#22c55e" strokeWidth="2" />
      </svg>

      <div className="mt-2 flex gap-4 text-xs text-slate-400">
        <span className="flex items-center gap-1">
          <span className="inline-block h-0.5 w-4 bg-green-500" /> Portafoglio Chameleon
        </span>
        {hasBench && (
          <span className="flex items-center gap-1">
            <span className="inline-block h-0.5 w-4 border-t border-dashed border-slate-500" /> Benchmark (S&amp;P 500)
          </span>
        )}
        {eventMarkers.length > 0 && (
          <span className="flex items-center gap-1">
            <span className="inline-block h-3 w-0 border-l border-dashed border-amber-500" /> Eventi storici
          </span>
        )}
      </div>

      {/* Elenco eventi nel periodo */}
      {eventMarkers.length > 0 && (
        <ul className="mt-3 grid grid-cols-1 gap-x-6 gap-y-1 text-xs text-slate-400 sm:grid-cols-2">
          {eventMarkers.map((m) => (
            <li key={m.k} className="flex gap-2">
              <span className="text-amber-500">▸</span>
              <span className="text-slate-500">{m.date}</span>
              <span>{m.label}</span>
            </li>
          ))}
        </ul>
      )}
    </div>
  );
}
