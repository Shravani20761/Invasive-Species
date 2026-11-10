export function formatDate(value?: string | null): string {
  if (!value) return "—";
  const date = new Date(value);
  if (Number.isNaN(date.getTime())) return "—";
  return new Intl.DateTimeFormat("en-IN", { dateStyle: "medium", timeStyle: "short" }).format(date);
}

export function formatPercent(value?: number | null): string {
  if (value == null || Number.isNaN(value)) return "—";
  return `${Math.round(value * 100)}%`;
}

export function markerColor(classification?: string | null, risk?: string | null): string {
  if (classification === "native") return "#64748B";
  if (risk === "critical" || risk === "high") return "#DC2626";
  if (risk === "medium") return "#F59E0B";
  return "#1B513C";
}

export function riskBadge(risk?: string | null): string {
  if (risk === "critical" || risk === "high") return "bg-red-50 text-alert";
  if (risk === "medium") return "bg-amber-50 text-amber-700";
  if (risk === "low") return "bg-pale text-deep";
  return "bg-slate-100 text-muted";
}

export function statusBadge(status?: string | null): string {
  if (status === "verified") return "bg-pale text-deep";
  if (status === "rejected") return "bg-red-50 text-alert";
  if (status === "reviewed") return "bg-slate-100 text-muted";
  return "bg-amber-50 text-amber-700";
}

export function localDateTimeValue(date = new Date()): string {
  const copy = new Date(date.getTime() - date.getTimezoneOffset() * 60000);
  return copy.toISOString().slice(0, 16);
}
