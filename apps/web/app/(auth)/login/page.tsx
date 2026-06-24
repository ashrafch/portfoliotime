"use client";

import { useState, useEffect } from "react";
import Link from "next/link";
import { useRouter } from "next/navigation";
import { useAuth } from "@/lib/auth";

export default function LoginPage() {
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [error, setError] = useState<string | null>(null);
  const [submitting, setSubmitting] = useState(false);
  const { login, user } = useAuth();
  const router = useRouter();

  useEffect(() => {
    if (user) router.replace("/dashboard");
  }, [user, router]);

  async function handleSubmit(e: React.FormEvent) {
    e.preventDefault();
    setError(null);
    setSubmitting(true);
    try {
      await login(email, password);
      router.push("/dashboard");
    } catch (err) {
      setError(err instanceof Error ? err.message : "Errore di accesso");
      setSubmitting(false);
    }
  }

  function fill(role: "admin" | "user") {
    if (role === "admin") {
      setEmail("admin@portfoliotime.com");
      setPassword("Admin123!");
    } else {
      setEmail("user@portfoliotime.com");
      setPassword("User123!");
    }
  }

  return (
    <main className="flex min-h-screen items-center justify-center px-4">
      <div className="w-full max-w-sm rounded-lg border border-slate-800 bg-slate-900 p-8">
        <Link href="/" className="mb-6 block text-center text-xl font-bold">
          <span className="text-green-400">Portfolio</span>Time
        </Link>
        <h1 className="mb-6 text-2xl font-bold">Accedi</h1>
        <form onSubmit={handleSubmit} className="space-y-4">
          <input
            type="email" placeholder="Email" value={email}
            onChange={(e) => setEmail(e.target.value)}
            className="w-full rounded bg-slate-800 px-4 py-2 text-white placeholder-slate-500 focus:outline-none focus:ring-2 focus:ring-green-500"
            required
          />
          <input
            type="password" placeholder="Password" value={password}
            onChange={(e) => setPassword(e.target.value)}
            className="w-full rounded bg-slate-800 px-4 py-2 text-white placeholder-slate-500 focus:outline-none focus:ring-2 focus:ring-green-500"
            required
          />
          {error && <p className="text-sm text-red-400">{error}</p>}
          <button
            type="submit" disabled={submitting}
            className="w-full rounded bg-green-500 py-2 font-semibold text-slate-950 transition hover:bg-green-400 disabled:opacity-50"
          >
            {submitting ? "Accesso…" : "Accedi"}
          </button>
        </form>

        <div className="mt-4 flex gap-2">
          <button onClick={() => fill("admin")} className="flex-1 rounded border border-slate-700 py-1.5 text-xs text-slate-400 hover:border-slate-500">
            Demo Admin
          </button>
          <button onClick={() => fill("user")} className="flex-1 rounded border border-slate-700 py-1.5 text-xs text-slate-400 hover:border-slate-500">
            Demo Utente
          </button>
        </div>

        <p className="mt-4 text-center text-sm text-slate-400">
          Non hai un account?{" "}
          <Link href="/register" className="text-green-400 hover:underline">Registrati</Link>
        </p>
      </div>
    </main>
  );
}
