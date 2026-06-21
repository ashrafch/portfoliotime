// Tipi condivisi tra web, mobile (futuro) e SDK

export interface Allocation {
  azioni: number;
  bitcoin: number;
  oro: number;
  materie_prime: number;
  obbligazioni: number;
}

export interface SimulationInput {
  eta: number;
  tasso_fed: number;
  delta_tasso: number;
  btc_prezzo_corrente: number;
  btc_ath: number;
  is_post_halving: boolean;
  tasso_nominale: number;
  inflazione: number;
  tassi_in_calo: boolean;
  qe_attivo: boolean;
  date_from: string;
  date_to: string;
  benchmark_ticker?: string;
}

export interface SimulationResult {
  allocazione: Allocation;
  cagr: number;
  max_drawdown: number;
  sharpe_ratio: number;
  annualized_volatility: number;
  real_return: number | null;
  total_return: number;
  benchmark_cagr: number;
  benchmark_max_drawdown: number;
  sources: Record<string, "yahoo_finance" | "coingecko" | "fred" | "calculated">;
  warnings: string[];
}

export interface SimulationJob {
  job_id: string;
  status: "queued" | "running" | "completed" | "failed";
  result?: SimulationResult;
  error?: string;
}

export interface Scenario {
  id: string;
  label: string;
  date_from: string;
  date_to: string;
  description: string;
  tags: string[];
}

export interface User {
  id: string;
  email: string;
}
