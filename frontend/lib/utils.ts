import { type ClassValue, clsx } from "clsx";
import { twMerge } from "tailwind-merge";

export function cn(...inputs: ClassValue[]) {
  return twMerge(clsx(inputs));
}

export function formatRelativeTime(isoString: string): string {
  const diff = Date.now() - new Date(isoString).getTime();
  const mins = Math.floor(diff / 60000);
  if (mins < 1) return "just now";
  if (mins < 60) return `${mins}m ago`;
  const hrs = Math.floor(mins / 60);
  if (hrs < 24) return `${hrs}h ago`;
  const days = Math.floor(hrs / 24);
  if (days < 7) return `${days}d ago`;
  return new Date(isoString).toLocaleDateString();
}

export function formatPrice(n?: number | null): string {
  if (n == null) return "—";
  return `$${n.toFixed(2)}`;
}

export function formatPct(n?: number | null): string {
  if (n == null) return "—";
  return `${n.toFixed(1)}%`;
}

export function formatDelta(n?: number | null): string {
  if (n == null) return "";
  const sign = n > 0 ? "+" : "";
  return `${sign}${n.toFixed(1)}%`;
}

export function severityColor(severity: string): string {
  return { critical: "text-red-400", warning: "text-yellow-400", info: "text-blue-400" }[severity] || "text-slate-400";
}

export function changeTypeIcon(type: string): string {
  return {
    price_change: "📉",
    new_product: "🆕",
    product_removed: "🗑️",
    discount_start: "🏷️",
    discount_end: "✅",
    availability_change: "📦",
  }[type] || "•";
}
