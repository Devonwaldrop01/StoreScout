import { type AlertEvent } from "@/lib/api";

// ── Types ─────────────────────────────────────────────────────────────────

export type SignalType =
  | "launch_burst"
  | "flash_sale"
  | "price_wave"
  | "price_increase"
  | "discount_wave"
  | "product_removals"
  | "availability_shift"
  | "tactical_launches"
  | "tactical_prices"
  | "tactical_discounts"
  | "single";

export type SignalTier = "strategic" | "tactical" | "raw";

export interface SignalGroup {
  id: string;
  type: SignalType;
  tier: SignalTier;
  competitor_id: string;
  hostname: string;
  events: AlertEvent[];
  count: number;
  detected_at: string;  // most recent event in group
  started_at: string;   // earliest event in group
  avg_price?: number;
  avg_delta_pct?: number;
  category_hint?: string;
  why_this_matters?: string;
  label: string;        // e.g. "19 products launched"
  headline: string;     // e.g. "Launch Burst"
}

// ── Constants ─────────────────────────────────────────────────────────────

const FOUR_HOURS_MS = 4 * 60 * 60 * 1000;

const CATEGORY_KEYWORDS: Array<{ name: string; keywords: string[] }> = [
  { name: "swimwear",   keywords: ["bikini", "swimsuit", "swim", "beach", "bathing", "board short"] },
  { name: "denim",      keywords: ["jeans", "denim"] },
  { name: "dresses",    keywords: ["dress", "gown", "maxi", "jumpsuit", "romper"] },
  { name: "tops",       keywords: ["top", "shirt", "blouse", "tank", "tee", "crop"] },
  { name: "bottoms",    keywords: ["shorts", "pants", "skirt", "leggings", "jogger"] },
  { name: "footwear",   keywords: ["shoes", "boots", "sneakers", "heels", "sandals", "loafer"] },
  { name: "accessories",keywords: ["bag", "purse", "wallet", "belt", "hat", "sunglasses", "jewelry"] },
  { name: "activewear", keywords: ["workout", "yoga", "gym", "sport", "active", "athletic"] },
  { name: "outerwear",  keywords: ["jacket", "coat", "hoodie", "sweater", "cardigan"] },
];

// ── Helpers ───────────────────────────────────────────────────────────────

function inferCategory(events: AlertEvent[]): string | undefined {
  const combined = events.map((e) => (e.product_title ?? "").toLowerCase()).join(" ");
  let best: { name: string; hits: number } | null = null;
  for (const { name, keywords } of CATEGORY_KEYWORDS) {
    const hits = keywords.filter((kw) => combined.includes(kw)).length;
    if (hits > 0 && (!best || hits > best.hits)) best = { name, hits };
  }
  return best?.name;
}

function computeAvgDelta(events: AlertEvent[]): number | undefined {
  const deltas = events.map((e) => e.delta_pct).filter((d): d is number => d != null);
  if (deltas.length === 0) return undefined;
  return deltas.reduce((s, d) => s + d, 0) / deltas.length;
}

function computeAvgPrice(events: AlertEvent[]): number | undefined {
  const prices = events
    .map((e) => {
      const nv = e.new_value as Record<string, unknown> | undefined;
      return (nv?.price_min ?? nv?.price) as number | undefined;
    })
    .filter((p): p is number => p != null);
  if (prices.length === 0) return undefined;
  return prices.reduce((s, p) => s + p, 0) / prices.length;
}

function classify(
  changeType: string,
  count: number,
  avgDelta: number | undefined,
): { type: SignalType; tier: SignalTier; headline: string } {
  const down = (avgDelta ?? 0) < 0;
  const deepCut = (avgDelta ?? 0) < -10;

  if (changeType === "new_product") {
    if (count >= 5) return { type: "launch_burst",       tier: "strategic", headline: "Launch Burst" };
    if (count >= 2) return { type: "tactical_launches",  tier: "tactical",  headline: "New Products" };
  }
  if (changeType === "price_change") {
    if (count >= 3 && down && deepCut) return { type: "flash_sale",          tier: "strategic", headline: "Flash Sale Detected" };
    if (count >= 5 && down)           return { type: "price_wave",           tier: "strategic", headline: "Price Compression" };
    if (count >= 5)                   return { type: "price_increase",       tier: "strategic", headline: "Price Increase Wave" };
    if (count >= 2)                   return { type: "tactical_prices",      tier: "tactical",  headline: "Price Changes" };
  }
  if (changeType === "discount_start") {
    if (count >= 5) return { type: "discount_wave",      tier: "strategic", headline: "Discount Campaign" };
    if (count >= 2) return { type: "tactical_discounts", tier: "tactical",  headline: "Discounts Started" };
  }
  if (changeType === "product_removed") {
    if (count >= 5) return { type: "product_removals",   tier: "strategic", headline: "Catalog Purge" };
    if (count >= 2) return { type: "product_removals",   tier: "tactical",  headline: "Products Removed" };
  }
  if (changeType === "availability_change") {
    if (count >= 5) return { type: "availability_shift", tier: "strategic", headline: "Availability Shift" };
    if (count >= 2) return { type: "availability_shift", tier: "tactical",  headline: "Availability Changes" };
  }
  return { type: "single", tier: "raw", headline: "" };
}

function makeLabel(type: SignalType, count: number, category?: string): string {
  const cat = category ? ` ${category}` : "";
  switch (type) {
    case "launch_burst":       return `${count}${cat} products launched`;
    case "flash_sale":         return `${count} products price-dropped`;
    case "price_wave":         return `${count} price reductions`;
    case "price_increase":     return `${count} price increases`;
    case "discount_wave":      return `${count} discount campaigns`;
    case "product_removals":   return `${count} products removed`;
    case "availability_shift": return `${count} availability changes`;
    case "tactical_launches":  return `${count} new products`;
    case "tactical_prices":    return `${count} price changes`;
    case "tactical_discounts": return `${count} discounts`;
    default:                   return "";
  }
}

function makeWhyThisMatters(
  type: SignalType,
  count: number,
  hostname: string,
  category?: string,
  avgDelta?: number,
): string {
  const cat = category ? `${category} ` : "";
  switch (type) {
    case "launch_burst":
      return `${hostname} launching ${count} ${cat}SKUs in a short window signals a coordinated inventory push — likely tied to an upcoming campaign. Expect these products in paid social within 1–2 weeks.`;
    case "flash_sale":
      return `Aggressive price cuts (avg ${Math.abs(Math.round(avgDelta ?? 0))}% off) across ${count} products signals a clearance event or competitive pricing move. Monitor whether this spreads to other categories.`;
    case "price_wave":
      return `Broad price reductions across ${count} products suggests strategic repositioning or a margin trade-off to drive volume — potentially signaling inventory pressure.`;
    case "price_increase":
      return `${count} price increases suggests margin recovery or demand testing. ${hostname} may be pulling back on promotional pricing after a sale period.`;
    case "discount_wave":
      return `${count} simultaneous discounts suggests a coordinated promotional event — likely a site-wide sale, seasonal clearance, or loyalty push.`;
    case "product_removals":
      return `${count} products delisted in quick succession could signal a catalog refresh, end-of-season clearance, or supply issue. Worth watching for what replaces them.`;
    case "availability_shift":
      return `${count} availability changes in quick succession suggests inventory pressure — either fast sell-through or a restock event.`;
    default:
      return "";
  }
}

// ── Main export ───────────────────────────────────────────────────────────

export function groupAlertEvents(alerts: AlertEvent[]): SignalGroup[] {
  if (alerts.length === 0) return [];

  // Sort oldest-first so window logic is correct
  const sorted = [...alerts].sort(
    (a, b) => new Date(a.detected_at).getTime() - new Date(b.detected_at).getTime()
  );

  type Bucket = { competitorId: string; changeType: string; windowStart: number; events: AlertEvent[] };
  const buckets: Bucket[] = [];

  for (const event of sorted) {
    const t = new Date(event.detected_at).getTime();
    const bucket = buckets.find(
      (b) =>
        b.competitorId === event.competitor_id &&
        b.changeType === event.change_type &&
        t - b.windowStart <= FOUR_HOURS_MS
    );
    if (bucket) {
      bucket.events.push(event);
    } else {
      buckets.push({ competitorId: event.competitor_id, changeType: event.change_type, windowStart: t, events: [event] });
    }
  }

  const groups: SignalGroup[] = buckets.map((b, i) => {
    const count = b.events.length;
    const avgDelta = computeAvgDelta(b.events);
    const avgPrice = computeAvgPrice(b.events);
    const category = inferCategory(b.events);
    const { type, tier, headline } = classify(b.changeType, count, avgDelta);

    const times = b.events.map((e) => e.detected_at).sort();
    const detected_at = times[times.length - 1];
    const started_at = times[0];

    // Sort events newest-first for display
    const eventsDesc = [...b.events].sort(
      (a, c) => new Date(c.detected_at).getTime() - new Date(a.detected_at).getTime()
    );

    return {
      id: `sg-${i}-${b.competitorId}-${b.changeType}`,
      type,
      tier,
      competitor_id: b.competitorId,
      hostname: b.events[0].hostname,
      events: eventsDesc,
      count,
      detected_at,
      started_at,
      avg_price: avgPrice,
      avg_delta_pct: avgDelta,
      category_hint: category,
      why_this_matters: tier === "strategic" ? makeWhyThisMatters(type, count, b.events[0].hostname, category, avgDelta) : undefined,
      label: count === 1 ? "" : makeLabel(type, count, category),
      headline,
    };
  });

  // Sort: strategic → tactical → raw, then newest-first within each tier
  const tierOrder: Record<SignalTier, number> = { strategic: 0, tactical: 1, raw: 2 };
  return groups.sort((a, b) => {
    const td = tierOrder[a.tier] - tierOrder[b.tier];
    if (td !== 0) return td;
    return new Date(b.detected_at).getTime() - new Date(a.detected_at).getTime();
  });
}

// ── Narrative summary for the dashboard header ─────────────────────────────

export function generateNarrative(groups: SignalGroup[]): string | null {
  const total = groups.reduce((s, g) => s + g.count, 0);
  if (total === 0) return null;

  const strategic = groups.filter((g) => g.tier === "strategic");
  if (strategic.length === 0) {
    return `${total} change${total !== 1 ? "s" : ""} detected`;
  }

  const top = strategic[0];
  const otherCount = strategic.length - 1;
  const suffix = otherCount > 0 ? ` · ${otherCount} other signal${otherCount > 1 ? "s" : ""}` : "";
  return `${top.hostname}: ${top.label}${suffix} · ${total} total`;
}

// ── Signal type → visual config ──────────────────────────────────────────

export const SIGNAL_CONFIG: Record<SignalType, { color: string; bg: string; border: string; icon: string }> = {
  launch_burst:       { color: "#a8ff00", bg: "rgba(168,255,0,.08)",   border: "rgba(168,255,0,.25)",   icon: "🚀" },
  flash_sale:         { color: "#ef4444", bg: "rgba(239,68,68,.08)",   border: "rgba(239,68,68,.25)",   icon: "⚡" },
  price_wave:         { color: "#60a5fa", bg: "rgba(96,165,250,.08)",  border: "rgba(96,165,250,.25)",  icon: "📉" },
  price_increase:     { color: "#10b981", bg: "rgba(16,185,129,.08)",  border: "rgba(16,185,129,.25)",  icon: "📈" },
  discount_wave:      { color: "#f59e0b", bg: "rgba(245,158,11,.08)",  border: "rgba(245,158,11,.25)",  icon: "🏷️" },
  product_removals:   { color: "#a78bfa", bg: "rgba(167,139,250,.08)", border: "rgba(167,139,250,.25)", icon: "🗑️" },
  availability_shift: { color: "#22d3ee", bg: "rgba(34,211,238,.08)",  border: "rgba(34,211,238,.25)",  icon: "📦" },
  tactical_launches:  { color: "#a8ff00", bg: "rgba(168,255,0,.05)",   border: "rgba(168,255,0,.15)",   icon: "✦" },
  tactical_prices:    { color: "#60a5fa", bg: "rgba(96,165,250,.05)",  border: "rgba(96,165,250,.15)",  icon: "↕" },
  tactical_discounts: { color: "#f59e0b", bg: "rgba(245,158,11,.05)",  border: "rgba(245,158,11,.15)",  icon: "%" },
  single:             { color: "#5a6a82", bg: "transparent",           border: "var(--border)",         icon: "·" },
};
