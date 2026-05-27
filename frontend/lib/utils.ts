import type { ElementType } from "react";
import { type ClassValue, clsx } from "clsx";
import { twMerge } from "tailwind-merge";
import { TrendingDown, Plus, Trash2, Tag, CheckCircle2, Package, HelpCircle } from "lucide-react";

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

export function getChangeAction(
  change_type: string,
  delta_pct?: number | null,
  severity?: string,
  hostname?: string,
): string | null {
  if (!severity || severity === "info") return null;
  const h = hostname || "this competitor";
  const delta = delta_pct ?? 0;
  const abs_d = Math.abs(delta);

  if (change_type === "price_change" && delta <= -15 && severity === "critical") {
    return `Flash sale — run a competing offer before ${h}'s sale ends (typically 48–72h).`;
  }
  if (change_type === "price_change" && delta < -5) {
    return `${h} cut prices ${abs_d.toFixed(0)}%. Their price-sensitive shoppers are comparing right now.`;
  }
  if (change_type === "price_change" && delta > 15) {
    return `${h} raised prices ${abs_d.toFixed(0)}%. Their value customers are now comparison shopping.`;
  }
  if (change_type === "bulk_price_change") {
    return `${h} repriced several products — check if any of your pricing overlaps.`;
  }
  if (change_type === "discount_start") {
    return `${h} started discounting. Watch for it spreading site-wide in the next 48h.`;
  }
  if (change_type === "discount_end") {
    return `${h}'s sale just ended — their price-sensitive customers are back in the market.`;
  }
  if (change_type === "availability_change") {
    return `${h} has stock gaps — being in-stock is a positioning advantage right now.`;
  }
  return null;
}

export function changeTypeIcon(type: string): ElementType {
  return ({
    price_change:        TrendingDown,
    new_product:         Plus,
    product_removed:     Trash2,
    discount_start:      Tag,
    discount_end:        CheckCircle2,
    availability_change: Package,
    bulk_price_change:   TrendingDown,
    bulk_new_products:   Plus,
    bulk_removal:        Trash2,
  } as Record<string, ElementType>)[type] ?? HelpCircle;
}

export function changeTypeColor(type: string): string {
  return ({
    price_change:        "var(--red)",
    new_product:         "var(--emerald)",
    product_removed:     "var(--muted)",
    discount_start:      "var(--amber)",
    discount_end:        "var(--blue)",
    availability_change: "var(--amber)",
    bulk_price_change:   "var(--red)",
    bulk_new_products:   "var(--emerald)",
    bulk_removal:        "var(--muted)",
  } as Record<string, string>)[type] ?? "var(--muted)";
}

export function changeTypeLabel(type: string): string {
  return ({
    price_change:        "Price changed",
    new_product:         "New product",
    product_removed:     "Delisted",
    discount_start:      "Sale started",
    discount_end:        "Sale ended",
    availability_change: "Stock changed",
    bulk_price_change:   "Prices repriced",
    bulk_new_products:   "Products added",
    bulk_removal:        "Products delisted",
  } as Record<string, string>)[type] ?? type.replace(/_/g, " ").replace(/\b\w/g, (c) => c.toUpperCase());
}
