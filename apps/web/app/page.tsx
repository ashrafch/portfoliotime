import Link from "next/link";

export default function Home() {
  return (
    <main className="flex min-h-screen flex-col items-center justify-center px-4 text-center">
      <h1 className="mb-4 text-4xl font-bold tracking-tight sm:text-6xl">
        <span className="text-green-400">Portfolio</span>Time
      </h1>
      <p className="mb-8 max-w-xl text-lg text-slate-400">
        Scopri come avrebbe performato il tuo portafoglio durante i grandi
        scenari storici. Dati reali. Nessuna finzione numerica.
      </p>
      <div className="flex flex-col gap-4 sm:flex-row">
        <Link
          href="/simulate"
          className="rounded-lg bg-green-500 px-8 py-3 font-semibold text-slate-950 transition hover:bg-green-400"
        >
          Inizia la simulazione
        </Link>
        <Link
          href="/dashboard"
          className="rounded-lg border border-slate-700 px-8 py-3 font-semibold text-slate-300 transition hover:border-slate-500"
        >
          Dashboard
        </Link>
      </div>
    </main>
  );
}
