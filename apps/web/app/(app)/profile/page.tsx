"use client";

import { useEffect, useState } from "react";
import { apiRequest } from "@/lib/api";
import { useAuth } from "@/lib/auth";
import type { InvestorProfile } from "@/lib/types";

const RISK_OPTIONS: { value: InvestorProfile["risk_profile"]; label: string; desc: string }[] = [
  { value: "conservativo", label: "Conservativo", desc: "Priorità alla protezione del capitale" },
  { value: "bilanciato", label: "Bilanciato", desc: "Equilibrio tra rischio e rendimento" },
  { value: "aggressivo", label: "Aggressivo", desc: "Massima crescita, alta tolleranza al rischio" },
];

export default function ProfilePage() {
  const { user } = useAuth();
  const [profile, setProfile] = useState<InvestorProfile | null>(null);
  const [saved, setSaved] = useState(false);
  const [saving, setSaving] = useState(false);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    apiRequest<InvestorProfile>("/me/profile")
      .then(setProfile)
      .catch((e) => setError(e instanceof Error ? e.message : "Errore"));
  }, []);

  function set<K extends keyof InvestorProfile>(key: K, value: InvestorProfile[K]) {
    setProfile((p) => (p ? { ...p, [key]: value } : p));
    setSaved(false);
  }

  async function save() {
    if (!profile) return;
    setSaving(true);
    setError(null);
    try {
      const updated = await apiRequest<InvestorProfile>("/me/profile", { method: "PUT", body: profile });
      setProfile(updated);
      setSaved(true);
    } catch (e) {
      setError(e instanceof Error ? e.message : "Errore");
    } finally {
      setSaving(false);
    }
  }

  if (error) return <div className="rounded bg-red-950 px-4 py-3 text-red-400">{error}</div>;
  if (!profile) return <p className="text-slate-500">Caricamento profilo…</p>;

  return (
    <div className="max-w-2xl">
      <h1 className="mb-1 text-3xl font-bold">Il tuo profilo</h1>
      <p className="mb-8 text-slate-400">
        {user?.email} — questi dati pre-compilano le tue simulazioni e personalizzano l&apos;interpretazione AI.
      </p>

      <div className="space-y-6">
        <section className="rounded-lg border border-slate-800 p-6">
          <h2 className="mb-4 text-lg font-semibold text-green-400">Profilo di rischio</h2>
          <div className="grid gap-3 sm:grid-cols-3">
            {RISK_OPTIONS.map((o) => (
              <button
                key={o.value}
                onClick={() => set("risk_profile", o.value)}
                className={`rounded-lg border p-4 text-left transition ${
                  profile.risk_profile === o.value
                    ? "border-green-500 bg-green-500/10"
                    : "border-slate-700 hover:border-slate-500"
                }`}
              >
                <div className="font-semibold">{o.label}</div>
                <div className="mt-1 text-xs text-slate-400">{o.desc}</div>
              </button>
            ))}
          </div>
        </section>

        <section className="rounded-lg border border-slate-800 p-6">
          <h2 className="mb-4 text-lg font-semibold text-green-400">Dati personali</h2>
          <div className="grid grid-cols-1 gap-4 sm:grid-cols-2">
            <label className="block">
              <span className="text-sm text-slate-400">Età</span>
              <input type="number" min={18} max={100} value={profile.eta}
                onChange={(e) => set("eta", parseInt(e.target.value) || 0)} className={inputCls} />
            </label>
            <label className="block">
              <span className="text-sm text-slate-400">Valuta base</span>
              <select value={profile.base_currency}
                onChange={(e) => set("base_currency", e.target.value)} className={inputCls}>
                <option value="EUR">EUR</option>
                <option value="USD">USD</option>
                <option value="GBP">GBP</option>
                <option value="CHF">CHF</option>
              </select>
            </label>
            <label className="block sm:col-span-2">
              <span className="text-sm text-slate-400">Obiettivo d&apos;investimento</span>
              <input type="text" value={profile.goal} placeholder="es. pensione, crescita capitale, casa"
                onChange={(e) => set("goal", e.target.value)} className={inputCls} />
            </label>
          </div>
        </section>

        <section className="rounded-lg border border-slate-800 p-6">
          <h2 className="mb-1 text-lg font-semibold text-green-400">Assunzioni macro di default</h2>
          <p className="mb-4 text-xs text-slate-500">Pre-compilano il form della nuova simulazione.</p>
          <div className="grid grid-cols-1 gap-4 sm:grid-cols-2">
            <label className="block">
              <span className="text-sm text-slate-400">Tasso FED di default (%)</span>
              <input type="number" step="0.25" value={profile.default_tasso_fed}
                onChange={(e) => set("default_tasso_fed", parseFloat(e.target.value) || 0)} className={inputCls} />
            </label>
            <label className="block">
              <span className="text-sm text-slate-400">Inflazione di default (%)</span>
              <input type="number" step="0.1" value={profile.default_inflazione}
                onChange={(e) => set("default_inflazione", parseFloat(e.target.value) || 0)} className={inputCls} />
            </label>
          </div>
        </section>

        <div className="flex items-center gap-4">
          <button onClick={save} disabled={saving}
            className="rounded-lg bg-green-500 px-6 py-2.5 font-semibold text-slate-950 transition hover:bg-green-400 disabled:opacity-50">
            {saving ? "Salvataggio…" : "Salva profilo"}
          </button>
          {saved && <span className="text-sm text-green-400">✓ Salvato</span>}
        </div>
      </div>
    </div>
  );
}

const inputCls =
  "mt-1 w-full rounded bg-slate-900 px-3 py-2 text-white focus:outline-none focus:ring-2 focus:ring-green-500";
