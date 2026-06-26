"use client";

import type { MonteCarloResult } from "@/lib/types";

// Fan chart: banda p5–p95 (area) + mediana p50. Tutto in base 100.
export default function MonteCarloChart({ mc }: { mc: MonteCarloResult }) {
  const { band } = mc;
  if (!band || band.x.length < 2) return null;

  const W = 720;
  const H = 260;
  const pad = { top: 16, right: 16, bottom: 28, left: 44 };

  const all = [...band.p5, ...band.p95, 100];
  const minV = Math.min(...all);
  const maxV = Math.max(...all);
  const range = maxV - minV || 1;

  const xOf = (t: number) => pad.left + t * (W - pad.left - pad.right);
  const yOf = (v: number) => pad.top + (1 - (v - minV) / range) * (H - pad.top - pad.bottom);

  const line = (arr: number[]) =>
    arr.map((v, i) => `${i === 0 ? "M" : "L"} ${xOf(band.x[i]).toFixed(1)} ${yOf(v).toFixed(1)}`).join(" ");

  // Area tra p5 e p95
  const areaPath =
    band.p95.map((v, i) => `${i === 0 ? "M" : "L"} ${xOf(band.x[i]).toFixed(1)} ${yOf(v).toFixed(1)}`).join(" ") +
    " " +
    band.p5.map((v, i) => `L ${xOf(band.x[band.x.length - 1 - i]).toFixed(1)} ${yOf(band.p5[band.p5.length - 1 - i]).toFixed(1)}`).join(" ") +
    " Z";

  const yTicks = [0, 0.5, 1].map((f) => {
    const v = minV + f * range;
    return { v, y: yOf(v) };
  });

  return (
    <div className="w-full overflow-x-auto">
      <svg viewBox={`0 0 ${W} ${H}`} className="w-full" style={{ minWidth: 480 }}>
        {yTicks.map((t, i) => (
          <g key={i}>
            <line x1={pad.left} y1={t.y} x2={W - pad.right} y2={t.y} stroke="#1e293b" strokeWidth="1" />
            <text x={pad.left - 6} y={t.y + 3} textAnchor="end" fontSize="10" fill="#64748b">{t.v.toFixed(0)}</text>
          </g>
        ))}
        <path d={areaPath} fill="#3b82f6" opacity="0.15" />
        <path d={line(band.p95)} fill="none" stroke="#3b82f6" strokeWidth="1" opacity="0.5" />
        <path d={line(band.p5)} fill="none" stroke="#3b82f6" strokeWidth="1" opacity="0.5" />
        <path d={line(band.p50)} fill="none" stroke="#22c55e" strokeWidth="2" />
        <text x={(pad.left + W - pad.right) / 2} y={H - 6} textAnchor="middle" fontSize="10" fill="#475569">
          progressione del periodo →
        </text>
      </svg>
      <div className="mt-2 flex flex-wrap gap-4 text-xs text-slate-400">
        <span className="flex items-center gap-1.5"><span className="inline-block h-0.5 w-4 bg-green-500" /> scenario mediano (p50)</span>
        <span className="flex items-center gap-1.5"><span className="inline-block h-2.5 w-4 bg-blue-500/20" /> banda p5–p95 (90% degli scenari)</span>
      </div>
    </div>
  );
}
