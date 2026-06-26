"use client";

import type { EquityPoint } from "@/lib/types";

interface Props {
  seriesA: EquityPoint[];
  seriesB: EquityPoint[];
  labelA: string;
  labelB: string;
}

// Confronto di due curve normalizzate a base 100, sull'asse "progressione del periodo"
// (0% = inizio, 100% = fine). Così due periodi diversi restano comparabili a colpo d'occhio.
export default function CompareChart({ seriesA, seriesB, labelA, labelB }: Props) {
  if (seriesA.length < 2 || seriesB.length < 2) {
    return <p className="text-sm text-slate-500">Curve non disponibili per il confronto.</p>;
  }

  const W = 720;
  const H = 300;
  const pad = { top: 16, right: 16, bottom: 36, left: 44 };

  const normA = normalize(seriesA);
  const normB = normalize(seriesB);

  const allValues = [...normA, ...normB].map((p) => p.v);
  const minV = Math.min(...allValues, 100);
  const maxV = Math.max(...allValues, 100);
  const range = maxV - minV || 1;

  const xOf = (t: number) => pad.left + t * (W - pad.left - pad.right); // t in 0..1
  const yOf = (v: number) => pad.top + (1 - (v - minV) / range) * (H - pad.top - pad.bottom);

  const pathOf = (pts: { t: number; v: number }[]) =>
    pts.map((p, i) => `${i === 0 ? "M" : "L"} ${xOf(p.t).toFixed(1)} ${yOf(p.v).toFixed(1)}`).join(" ");

  const yTicks = [0, 0.25, 0.5, 0.75, 1].map((f) => {
    const v = minV + f * range;
    return { v, y: yOf(v) };
  });
  const xTicks = [0, 0.25, 0.5, 0.75, 1];

  // Linea di riferimento a 100 (capitale iniziale)
  const baseY = yOf(100);

  return (
    <div className="w-full overflow-x-auto">
      <svg viewBox={`0 0 ${W} ${H}`} className="w-full" style={{ minWidth: 480 }}>
        {yTicks.map((t, i) => (
          <g key={i}>
            <line x1={pad.left} y1={t.y} x2={W - pad.right} y2={t.y} stroke="#1e293b" strokeWidth="1" />
            <text x={pad.left - 6} y={t.y + 3} textAnchor="end" fontSize="10" fill="#64748b">
              {t.v.toFixed(0)}
            </text>
          </g>
        ))}

        {/* riferimento capitale iniziale (100) */}
        {baseY >= pad.top && baseY <= H - pad.bottom && (
          <line x1={pad.left} y1={baseY} x2={W - pad.right} y2={baseY}
            stroke="#475569" strokeWidth="1" strokeDasharray="2 3" />
        )}

        {xTicks.map((t, i) => (
          <text key={i} x={xOf(t)} y={H - 18} textAnchor="middle" fontSize="10" fill="#64748b">
            {Math.round(t * 100)}%
          </text>
        ))}
        <text x={(pad.left + W - pad.right) / 2} y={H - 4} textAnchor="middle" fontSize="10" fill="#475569">
          progressione del periodo
        </text>

        <path d={pathOf(normA)} fill="none" stroke="#22c55e" strokeWidth="2.5" />
        <path d={pathOf(normB)} fill="none" stroke="#3b82f6" strokeWidth="2.5" />
      </svg>

      <div className="mt-2 flex flex-wrap gap-4 text-xs">
        <span className="flex items-center gap-1.5 text-slate-300">
          <span className="inline-block h-0.5 w-4 bg-green-500" /> A — {labelA}
        </span>
        <span className="flex items-center gap-1.5 text-slate-300">
          <span className="inline-block h-0.5 w-4 bg-blue-500" /> B — {labelB}
        </span>
        <span className="flex items-center gap-1.5 text-slate-500">
          <span className="inline-block h-0.5 w-4 border-t border-dashed border-slate-500" /> capitale iniziale (100)
        </span>
      </div>
    </div>
  );
}

function normalize(series: EquityPoint[]): { t: number; v: number }[] {
  const base = series[0]?.portfolio || 100;
  const n = series.length;
  return series.map((p, i) => ({ t: n > 1 ? i / (n - 1) : 0, v: (p.portfolio / base) * 100 }));
}
