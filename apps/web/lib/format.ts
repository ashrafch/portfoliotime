export function pct(v: number | null | undefined, signed = false): string {
  if (v === null || v === undefined || Number.isNaN(v)) return "—";
  const s = (v * 100).toFixed(2);
  const prefix = signed && v > 0 ? "+" : "";
  return `${prefix}${s}%`;
}

export function num(v: number | null | undefined): string {
  if (v === null || v === undefined || Number.isNaN(v)) return "—";
  return v.toFixed(2);
}

const CURRENCY_SYMBOLS: Record<string, string> = { EUR: "€", USD: "$", GBP: "£", CHF: "CHF " };

export function money(value: number | null | undefined, currency = "EUR"): string {
  if (value === null || value === undefined || Number.isNaN(value)) return "—";
  const sym = CURRENCY_SYMBOLS[currency] ?? "€";
  const formatted = Math.round(value).toLocaleString("it-IT");
  return `${sym}${formatted}`;
}

export function formatDate(iso: string | null | undefined): string {
  if (!iso) return "—";
  try {
    return new Date(iso).toLocaleDateString("it-IT", {
      day: "2-digit", month: "2-digit", year: "numeric",
    });
  } catch {
    return iso;
  }
}
