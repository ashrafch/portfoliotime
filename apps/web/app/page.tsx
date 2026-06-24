"use client";

import Link from "next/link";
import { useAuth } from "@/lib/auth";

export default function Home() {
  const { user } = useAuth();

  return (
    <main className="flex min-h-screen flex-col items-center justify-center px-4 text-center">
      <h1 className="mb-4 text-4xl font-bold tracking-tight sm:text-6xl">
        <span className="text-green-400">Portfolio</span>Time
      </h1>
      <p className="mb-2 max-w-xl text-lg text-slate-400">
        Scopri come avrebbe performato il tuo portafoglio durante i grandi scenari storici.
      </p>
      <p className="mb-8 max-w-xl text-sm text-slate-500">
        Dati di mercato reali. Il motore calcola i numeri, l&apos;AI li interpreta — mai il contrario.
      </p>

      <div className="flex flex-col gap-4 sm:flex-row">
        {user ? (
          <Link
            href="/dashboard"
            className="rounded-lg bg-green-500 px-8 py-3 font-semibold text-slate-950 transition hover:bg-green-400"
          >
            Vai alla dashboard
          </Link>
        ) : (
          <>
            <Link
              href="/login"
              className="rounded-lg bg-green-500 px-8 py-3 font-semibold text-slate-950 transition hover:bg-green-400"
            >
              Accedi
            </Link>
            <Link
              href="/register"
              className="rounded-lg border border-slate-700 px-8 py-3 font-semibold text-slate-300 transition hover:border-slate-500"
            >
              Crea account
            </Link>
          </>
        )}
      </div>

      <div className="mt-12 max-w-md rounded-lg border border-slate-800 bg-slate-900/50 p-4 text-left text-xs text-slate-500">
        <p className="mb-1 font-semibold text-slate-400">Account demo</p>
        <p>Admin: <span className="text-green-400">admin@portfoliotime.com</span> / Admin123!</p>
        <p>Utente: <span className="text-green-400">user@portfoliotime.com</span> / User123!</p>
      </div>
    </main>
  );
}
