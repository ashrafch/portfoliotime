"use client";

import { useEffect, useState, useCallback } from "react";
import { useRouter } from "next/navigation";
import { apiRequest, ApiError } from "@/lib/api";
import { pct, formatDate } from "@/lib/format";
import { useAuth } from "@/lib/auth";
import type { AdminUser, PlatformStats, AdminSimulation } from "@/lib/types";

export default function AdminPage() {
  const { isSuperAdmin, loading: authLoading, user: me } = useAuth();
  const router = useRouter();

  const [stats, setStats] = useState<PlatformStats | null>(null);
  const [users, setUsers] = useState<AdminUser[]>([]);
  const [sims, setSims] = useState<AdminSimulation[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  const reload = useCallback(async () => {
    const [s, u, sim] = await Promise.all([
      apiRequest<PlatformStats>("/admin/stats"),
      apiRequest<AdminUser[]>("/admin/users"),
      apiRequest<AdminSimulation[]>("/admin/simulations"),
    ]);
    setStats(s);
    setUsers(u);
    setSims(sim);
  }, []);

  useEffect(() => {
    if (authLoading) return;
    if (!isSuperAdmin) {
      router.replace("/dashboard");
      return;
    }
    reload()
      .catch((e) => setError(e instanceof ApiError ? e.message : "Errore"))
      .finally(() => setLoading(false));
  }, [authLoading, isSuperAdmin, reload, router]);

  async function toggleActive(u: AdminUser) {
    await apiRequest(`/admin/users/${u.id}`, { method: "PATCH", body: { is_active: !u.is_active } });
    reload();
  }

  async function toggleRole(u: AdminUser) {
    const newRole = u.role === "super_admin" ? "user" : "super_admin";
    await apiRequest(`/admin/users/${u.id}`, { method: "PATCH", body: { role: newRole } });
    reload();
  }

  async function removeUser(u: AdminUser) {
    if (!confirm(`Eliminare ${u.email} e tutte le sue simulazioni?`)) return;
    await apiRequest(`/admin/users/${u.id}`, { method: "DELETE" });
    reload();
  }

  if (loading) return <p className="text-slate-500">Caricamento pannello admin…</p>;
  if (error) return <div className="rounded bg-red-950 px-4 py-3 text-red-400">{error}</div>;

  return (
    <div>
      <h1 className="mb-6 text-3xl font-bold">Pannello Amministrazione</h1>

      {/* Stats */}
      {stats && (
        <section className="mb-8 grid grid-cols-2 gap-3 sm:grid-cols-5">
          <Stat label="Utenti totali" value={stats.total_users} />
          <Stat label="Utenti attivi" value={stats.active_users} />
          <Stat label="Super admin" value={stats.super_admins} />
          <Stat label="Simulazioni" value={stats.total_simulations} />
          <Stat label="Fallite" value={stats.failed_simulations} danger={stats.failed_simulations > 0} />
        </section>
      )}

      {/* Utenti */}
      <section className="mb-8">
        <h2 className="mb-3 text-lg font-semibold">Utenti ({users.length})</h2>
        <div className="overflow-x-auto rounded-lg border border-slate-800">
          <table className="w-full text-left text-sm">
            <thead className="bg-slate-900 text-slate-400">
              <tr>
                <th className="px-4 py-3">Email</th>
                <th className="px-4 py-3">Nome</th>
                <th className="px-4 py-3">Ruolo</th>
                <th className="px-4 py-3 text-center">Sim.</th>
                <th className="px-4 py-3 text-center">Stato</th>
                <th className="px-4 py-3 text-right">Azioni</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-slate-800">
              {users.map((u) => (
                <tr key={u.id} className="hover:bg-slate-900/50">
                  <td className="px-4 py-3">{u.email}{u.id === me?.id && <span className="ml-2 text-xs text-green-400">(tu)</span>}</td>
                  <td className="px-4 py-3 text-slate-400">{u.full_name || "—"}</td>
                  <td className="px-4 py-3">
                    <span className={`rounded px-2 py-0.5 text-xs ${
                      u.role === "super_admin" ? "bg-purple-500/10 text-purple-400" : "bg-slate-700/50 text-slate-300"
                    }`}>
                      {u.role === "super_admin" ? "super admin" : "utente"}
                    </span>
                  </td>
                  <td className="px-4 py-3 text-center text-slate-400">{u.simulations_count}</td>
                  <td className="px-4 py-3 text-center">
                    <span className={`rounded px-2 py-0.5 text-xs ${
                      u.is_active ? "bg-green-500/10 text-green-400" : "bg-red-500/10 text-red-400"
                    }`}>
                      {u.is_active ? "attivo" : "disattivo"}
                    </span>
                  </td>
                  <td className="px-4 py-3">
                    <div className="flex justify-end gap-2 text-xs">
                      <button onClick={() => toggleRole(u)} disabled={u.id === me?.id}
                        className="rounded border border-slate-700 px-2 py-1 hover:border-purple-500 disabled:opacity-30">
                        {u.role === "super_admin" ? "→ utente" : "→ admin"}
                      </button>
                      <button onClick={() => toggleActive(u)} disabled={u.id === me?.id}
                        className="rounded border border-slate-700 px-2 py-1 hover:border-yellow-500 disabled:opacity-30">
                        {u.is_active ? "disattiva" : "attiva"}
                      </button>
                      <button onClick={() => removeUser(u)} disabled={u.id === me?.id}
                        className="rounded border border-slate-700 px-2 py-1 hover:border-red-500 hover:text-red-400 disabled:opacity-30">
                        elimina
                      </button>
                    </div>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </section>

      {/* Simulazioni piattaforma */}
      <section>
        <h2 className="mb-3 text-lg font-semibold">Simulazioni recenti ({sims.length})</h2>
        {sims.length === 0 ? (
          <p className="text-sm text-slate-500">Nessuna simulazione registrata.</p>
        ) : (
          <div className="overflow-x-auto rounded-lg border border-slate-800">
            <table className="w-full text-left text-sm">
              <thead className="bg-slate-900 text-slate-400">
                <tr>
                  <th className="px-4 py-3">Utente</th>
                  <th className="px-4 py-3">Periodo</th>
                  <th className="px-4 py-3">Data</th>
                  <th className="px-4 py-3 text-right">Rendimento</th>
                  <th className="px-4 py-3 text-right">Stato</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-slate-800">
                {sims.map((s) => (
                  <tr key={s.id} className="hover:bg-slate-900/50">
                    <td className="px-4 py-3">{s.user_email}</td>
                    <td className="px-4 py-3 text-slate-400">{s.label}</td>
                    <td className="px-4 py-3 text-slate-400">{formatDate(s.created_at)}</td>
                    <td className="px-4 py-3 text-right">{pct(s.total_return, true)}</td>
                    <td className="px-4 py-3 text-right">
                      <span className={`rounded px-2 py-0.5 text-xs ${
                        s.status === "completed" ? "bg-green-500/10 text-green-400" : "bg-red-500/10 text-red-400"
                      }`}>{s.status}</span>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )}
      </section>
    </div>
  );
}

function Stat({ label, value, danger }: { label: string; value: number; danger?: boolean }) {
  return (
    <div className="rounded-lg border border-slate-800 bg-slate-900/50 p-4">
      <div className={`text-2xl font-bold ${danger ? "text-red-400" : "text-white"}`}>{value}</div>
      <div className="mt-1 text-xs text-slate-400">{label}</div>
    </div>
  );
}
