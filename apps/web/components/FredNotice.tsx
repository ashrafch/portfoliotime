"use client";

import { useEffect, useState } from "react";
import { apiRequest } from "@/lib/api";

// Avviso mostrato solo quando FRED non è configurato: spiega perché alcuni dati
// (macro reale, stime prospettiche) non sono disponibili e come attivarli.
export default function FredNotice() {
  const [show, setShow] = useState(false);

  useEffect(() => {
    apiRequest<{ fred_configured: boolean }>("/config", { auth: false })
      .then((c) => setShow(!c.fred_configured))
      .catch(() => {});
  }, []);

  if (!show) return null;

  return (
    <div className="mb-4 rounded-lg border border-amber-800 bg-amber-950/20 px-4 py-3 text-sm text-amber-300">
      <strong>FRED non configurato.</strong> Senza i dati ufficiali su tassi e inflazione,
      la macro reale e le stime prospettiche per azioni/obbligazioni non sono disponibili
      (vedrai &quot;non stimabile&quot; e le assunzioni del profilo). Per attivarli: chiave
      gratuita su <span className="whitespace-nowrap">fred.stlouisfed.org</span>, poi
      aggiungi <code className="rounded bg-slate-800 px-1">FRED_API_KEY</code> nel file
      {" "}<code className="rounded bg-slate-800 px-1">.env</code> e riavvia l&apos;API.
    </div>
  );
}
