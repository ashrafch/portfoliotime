"use client";

import { useState } from "react";
import Link from "next/link";
import { useRouter } from "next/navigation";

const API = process.env.NEXT_PUBLIC_API_URL ?? "http://localhost:8000";

export default function RegisterPage() {
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [error, setError] = useState<string | null>(null);
  const router = useRouter();

  async function handleSubmit(e: React.FormEvent) {
    e.preventDefault();
    setError(null);
    try {
      const res = await fetch(`${API}/auth/register`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ email, password }),
      });
      if (!res.ok) throw new Error("Errore registrazione");
      router.push("/login");
    } catch (err) {
      setError(err instanceof Error ? err.message : "Errore");
    }
  }

  return (
    <main className="flex min-h-screen items-center justify-center px-4">
      <div className="w-full max-w-sm rounded-lg border border-slate-800 bg-slate-900 p-8">
        <h1 className="mb-6 text-2xl font-bold">Crea account</h1>
        <form onSubmit={handleSubmit} className="space-y-4">
          <input
            type="email" placeholder="Email" value={email}
            onChange={(e) => setEmail(e.target.value)}
            className="w-full rounded bg-slate-800 px-4 py-2 text-white placeholder-slate-500"
            required
          />
          <input
            type="password" placeholder="Password (min 8 caratteri)" value={password}
            onChange={(e) => setPassword(e.target.value)}
            minLength={8}
            className="w-full rounded bg-slate-800 px-4 py-2 text-white placeholder-slate-500"
            required
          />
          {error && <p className="text-sm text-red-400">{error}</p>}
          <button
            type="submit"
            className="w-full rounded bg-green-500 py-2 font-semibold text-slate-950 hover:bg-green-400"
          >
            Registrati
          </button>
        </form>
        <p className="mt-4 text-center text-sm text-slate-400">
          Hai già un account?{" "}
          <Link href="/login" className="text-green-400 hover:underline">Accedi</Link>
        </p>
      </div>
    </main>
  );
}
