export type UserRole = "super_admin" | "user";

export interface User {
  id: string;
  email: string;
  full_name: string;
  role: UserRole;
  is_active: boolean;
}

export interface AuthResponse {
  access_token: string;
  token_type: string;
  user: User;
}

export interface Allocation {
  azioni: number;
  bitcoin: number;
  oro: number;
  materie_prime: number;
  obbligazioni: number;
}

export interface EquityPoint {
  date: string;
  portfolio: number;
  benchmark?: number;
}

export interface SimulationResultData {
  allocazione: Allocation;
  allocation_source?: "chameleon" | "custom";
  cagr: number | null;
  max_drawdown: number | null;
  sharpe_ratio: number | null;
  annualized_volatility: number | null;
  real_return: number | null;
  total_return: number | null;
  benchmark_cagr: number | null;
  benchmark_max_drawdown: number | null;
  benchmark_total_return: number | null;
  equity_curve: EquityPoint[];
  sources: Record<string, string>;
  warnings: string[];
}

export interface SimulationRecord {
  id: string;
  status: string;
  label: string;
  result: SimulationResultData | null;
  narrative: string | null;
  error: string | null;
  input_params?: Record<string, unknown>;
  created_at?: string;
}

export interface SimulationSummary {
  id: string;
  label: string;
  status: string;
  created_at: string | null;
  total_return: number | null;
  cagr: number | null;
}

export interface SimulateRequest {
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
  benchmark_ticker: string;
  custom_allocation?: Allocation | null;
}

export interface InvestorProfile {
  eta: number;
  risk_profile: "conservativo" | "bilanciato" | "aggressivo";
  base_currency: string;
  goal: string;
  default_tasso_fed: number;
  default_inflazione: number;
}

export interface PersonalAnalytics {
  total_simulations: number;
  completed: number;
  avg_total_return: number | null;
  avg_max_drawdown: number | null;
  avg_sharpe: number | null;
  best: { label: string; total_return: number; id: string } | null;
  worst: { label: string; total_return: number; id: string } | null;
  benchmark_win_rate: number | null;
}

export interface MacroSuggestion {
  source: "fred" | "none";
  tasso_fed: number | null;
  delta_tasso: number | null;
  tasso_nominale: number | null;
  inflazione: number | null;
  tassi_in_calo: boolean | null;
  message: string | null;
}

export interface Scenario {
  id: string;
  label: string;
  date_from: string;
  date_to: string;
  description: string;
  tags: string[];
}

export interface AdminUser {
  id: string;
  email: string;
  full_name: string;
  role: UserRole;
  is_active: boolean;
  created_at: string | null;
  simulations_count: number;
}

export interface PlatformStats {
  total_users: number;
  active_users: number;
  super_admins: number;
  total_simulations: number;
  failed_simulations: number;
}

export interface AdminSimulation {
  id: string;
  user_email: string;
  label: string;
  status: string;
  total_return: number | null;
  created_at: string | null;
}
