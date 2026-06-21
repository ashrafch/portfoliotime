import type { Scenario } from "@portfoliotime/types";

// Fonte di verità per gli scenari storici — sincronizzata con routers/scenarios.py
// Modificare questo file richiede di aggiornare anche il backend.
export const SCENARIOS: Scenario[] = [
  {
    id: "2000-dotcom-crash",
    label: "Dot-com Crash",
    date_from: "2000-03-10",
    date_to: "2002-10-09",
    description: "Crollo del mercato tech dopo la bolla speculativa di internet",
    tags: ["tech", "bear", "nasdaq"],
  },
  {
    id: "2007-grande-recessione",
    label: "Grande Recessione",
    date_from: "2007-10-09",
    date_to: "2009-03-09",
    description: "Crisi finanziaria globale innescata dal mercato immobiliare USA",
    tags: ["crisi", "bear", "subprime"],
  },
  {
    id: "2009-recovery-bull",
    label: "Recovery Bull 2009-2020",
    date_from: "2009-03-09",
    date_to: "2020-02-19",
    description: "Il più lungo mercato toro della storia USA post-crisi",
    tags: ["bull", "recovery", "long"],
  },
  {
    id: "2017-crypto-mania",
    label: "Crypto Mania 2017",
    date_from: "2017-01-01",
    date_to: "2017-12-31",
    description: "Bitcoin da $1.000 a $20.000 in 12 mesi",
    tags: ["crypto", "bull", "bitcoin"],
  },
  {
    id: "2018-crypto-winter",
    label: "Crypto Winter 2018",
    date_from: "2018-01-01",
    date_to: "2018-12-31",
    description: "Bitcoin perde l'80% dopo il picco del 2017",
    tags: ["crypto", "bear", "bitcoin"],
  },
  {
    id: "2020-covid-crash",
    label: "COVID Crash",
    date_from: "2020-02-19",
    date_to: "2020-03-23",
    description: "Crollo più rapido del 30%+ nella storia USA",
    tags: ["covid", "bear", "crash"],
  },
  {
    id: "2020-covid-recovery",
    label: "COVID Recovery",
    date_from: "2020-03-23",
    date_to: "2021-12-31",
    description: "Recupero record guidato da FED, stimoli fiscali e vaccini",
    tags: ["covid", "bull", "recovery"],
  },
  {
    id: "2021-crypto-bull",
    label: "Crypto Bull 2021",
    date_from: "2021-01-01",
    date_to: "2021-11-10",
    description: "Bitcoin a $69.000, ETH, NFT e DeFi decollano",
    tags: ["crypto", "bull", "bitcoin"],
  },
  {
    id: "2022-inflazione-bear",
    label: "Bear Inflazione 2022",
    date_from: "2022-01-01",
    date_to: "2022-12-31",
    description: "FED alza i tassi 7 volte — azioni e obbligazioni crollano insieme",
    tags: ["inflazione", "bear", "fed"],
  },
  {
    id: "2023-ai-bull",
    label: "AI Bull 2023",
    date_from: "2023-01-01",
    date_to: "2023-12-31",
    description: "Rally AI — Magnificent 7 traina S&P 500 al +26%",
    tags: ["ai", "bull", "tech"],
  },
];

export function getScenarioById(id: string): Scenario | undefined {
  return SCENARIOS.find((s) => s.id === id);
}
