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

export interface MoneyProjection {
  initial_capital: number;
  final_value: number;
  total_invested: number;
  gain: number;
  money_return: number | null;
  contribution: number;
  contribution_frequency: string;
  contributions_count: number;
  is_dca: boolean;
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
  // metriche avanzate (opzionali: i record vecchi potrebbero non averle)
  sortino_ratio?: number | null;
  calmar_ratio?: number | null;
  var_95?: number | null;
  cvar_95?: number | null;
  beta?: number | null;
  max_underwater_days?: number | null;
  drawdown_recovered?: boolean;
  money?: MoneyProjection | null;
  sources: Record<string, string>;
  warnings: string[];
}

export interface MonteCarloResult {
  n_simulations: number;
  horizon_days: number;
  final_return: { p5: number; p25: number; p50: number; p75: number; p95: number };
  prob_loss: number;
  band: { x: number[]; p5: number[]; p50: number[]; p95: number[] };
  method: string;
  disclaimer: string;
}

export interface MarketEvent {
  date: string;
  label: string;
}

export interface StressScenarioResult {
  label: string;
  date_from: string;
  date_to: string;
  total_return: number | null;
  max_drawdown: number | null;
  final_value: number | null;
  warnings: string[];
}

export interface StressTestResult {
  total_value: number;
  weights: Allocation;
  scenarios: StressScenarioResult[];
}

export interface GoalPlanResult {
  risk_profile: string;
  allocation: Allocation;
  reference_period: { from: string; to: string };
  reference_stats: { annual_return: number | null; annual_volatility: number | null };
  projection: {
    probability_success: number;
    final_value: { p10: number; p50: number; p90: number };
    total_contributed: number;
    target: number;
    horizon_years: number;
    monthly_contribution: number;
  };
  required_monthly_contribution: number | null;
  disclaimer: string;
}

export interface RecommendedResult {
  allocazione: Allocation;
  source: "fred" | "profilo";
  macro_used: {
    tasso_fed: number; inflazione: number; tasso_nominale: number;
    delta_tasso: number; tassi_in_calo: boolean;
  };
  changes: { asset: string; da: number; a: number }[];
  previous_at: string | null;
  note: string;
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
  initial_capital?: number;
  contribution?: number;
  contribution_frequency?: "none" | "monthly" | "quarterly";
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
