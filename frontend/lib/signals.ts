import type { ElementType } from "react";
import {
  Rocket, Zap, TrendingDown, TrendingUp, Tag, Trash2,
  Package, Plus, ArrowUpDown, Percent, Minus,
} from "lucide-react";
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
  your_move?: string;
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
  maxSeverity: "info" | "warning" | "critical" = "info",
): { type: SignalType; tier: SignalTier; headline: string } {
  const down = (avgDelta ?? 0) < 0;
  const deepCut = (avgDelta ?? 0) < -10;

  if (changeType === "new_product") {
    if (count >= 5) return { type: "launch_burst",       tier: "strategic", headline: "Launch Burst" };
    if (count >= 2) return { type: "tactical_launches",  tier: "tactical",  headline: "New Products" };
  }
  if (changeType === "price_change") {
    if (count >= 3 && down && deepCut) return { type: "flash_sale",     tier: "strategic", headline: "Flash Sale" };
    if (count >= 5 && down)           return { type: "price_wave",      tier: "strategic", headline: "Price Drop Wave" };
    if (count >= 5)                   return { type: "price_increase",  tier: "strategic", headline: "Prices Rising" };
    if (count >= 2)                   return { type: "tactical_prices", tier: "tactical",  headline: "Price Changes" };
  }
  if (changeType === "discount_start") {
    if (count >= 5) return { type: "discount_wave",      tier: "strategic", headline: "Discount Campaign" };
    if (count >= 2) return { type: "tactical_discounts", tier: "tactical",  headline: "Discounts Started" };
  }
  if (changeType === "product_removed") {
    if (count >= 5) return { type: "product_removals",   tier: "strategic", headline: "Products Delisted" };
    if (count >= 2) return { type: "product_removals",   tier: "tactical",  headline: "Products Removed" };
  }
  if (changeType === "availability_change") {
    if (maxSeverity === "info") {
      // Restock noise — demote to tactical only, never strategic
      if (count >= 2) return { type: "availability_shift", tier: "tactical", headline: "Stock Changes" };
    } else {
      // warning/critical = real stock-out = positioning opportunity
      if (count >= 5) return { type: "availability_shift", tier: "strategic", headline: "Stock-Out Opportunity" };
      if (count >= 2) return { type: "availability_shift", tier: "tactical",  headline: "Stock Changes" };
    }
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

function makeYourMove(type: SignalType, count: number, hostname: string, avgDelta?: number): string | undefined {
  switch (type) {
    case "flash_sale":
      return `Open Meta Ads Manager, duplicate your best ad set, and narrow the audience to followers of ${hostname}. Test "${hostname} is on sale. We never are." as headline copy — run $10/day for 5 days and compare CTR to your control.`;
    case "price_wave":
      return `Cross-reference the ${count} repriced products against your catalog. If there's overlap, hold your price and push quality messaging this week — their value-focused customers are now comparison shopping.`;
    case "price_increase":
      return `${hostname} raised prices on ${count} products. Launch a Google Shopping campaign targeting their product names — their price-sensitive customers are now actively looking for alternatives.`;
    case "launch_burst":
      return `Watch ${hostname}'s social and email over the next 72h to see how they position this. If they're entering a category you also cover, get your version into ads before their campaign peaks.`;
    case "discount_wave":
      return `Don't race them. Send your email list this week with a full-price quality angle — ${hostname}'s discount-fatigued customers are your best acquisition target right now.`;
    case "product_removals":
      return `${hostname} pulled ${count} products. If you carry anything similar, update your Google Shopping feed and ad copy now — you have less direct competition for those searches.`;
    case "availability_shift":
      return `${hostname} has stock issues on ${count} products. If you're reliably in-stock on similar items, push that as a competitive advantage in your ads and email this week.`;
    default:
      return undefined;
  }
}

// ── Main export ───────────────────────────────────────────────────────────

// Backend collapses N same-type changes into one DB row when count > 10:
//   bulk_removal / bulk_new_products / bulk_price_change
// Map them back to their base type so classify() thresholds work correctly,
// and extract the real count from old_value.count instead of using 1.
const BULK_TYPE_MAP: Record<string, string> = {
  bulk_removal:      "product_removed",
  bulk_new_products: "new_product",
  bulk_price_change: "price_change",
};

function bulkEffectiveCount(event: AlertEvent): number {
  const stored = ((event.old_value || {}) as Record<string, unknown>).count;
  return typeof stored === "number" && stored > 0 ? stored : 1;
}

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
    // Normalise bulk types so they bucket with their base siblings (rare but possible)
    const normalizedType = BULK_TYPE_MAP[event.change_type] ?? event.change_type;
    const bucket = buckets.find(
      (b) =>
        b.competitorId === event.competitor_id &&
        (BULK_TYPE_MAP[b.changeType] ?? b.changeType) === normalizedType &&
        t - b.windowStart <= FOUR_HOURS_MS
    );
    if (bucket) {
      bucket.events.push(event);
    } else {
      buckets.push({ competitorId: event.competitor_id, changeType: event.change_type, windowStart: t, events: [event] });
    }
  }

  const groups: SignalGroup[] = buckets.map((b, i) => {
    // For a single bulk event, use the count stored in old_value.count
    const rawCount = b.events.length;
    const isSingleBulk = rawCount === 1 && b.changeType in BULK_TYPE_MAP;
    const count = isSingleBulk ? bulkEffectiveCount(b.events[0]) : rawCount;

    const classifyType = BULK_TYPE_MAP[b.changeType] ?? b.changeType;
    const avgDelta = computeAvgDelta(b.events);
    const avgPrice = computeAvgPrice(b.events);
    const category = inferCategory(b.events);
    const maxSeverity: "info" | "warning" | "critical" =
      b.events.some((e) => e.severity === "critical") ? "critical" :
      b.events.some((e) => e.severity === "warning")  ? "warning"  : "info";
    const { type, tier, headline } = classify(classifyType, count, avgDelta, maxSeverity);

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
      your_move: tier === "strategic" ? makeYourMove(type, count, b.events[0].hostname, avgDelta) : undefined,
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

// ── Impact level ─────────────────────────────────────────────────────────

export function impactLevel(group: SignalGroup): "High" | "Medium" | "Low" {
  if (group.events.some((e) => e.severity === "critical") || group.count >= 10) return "High";
  if (group.count >= 5 || group.events.some((e) => e.severity === "warning")) return "Medium";
  return "Low";
}

// ── Detection explanation ─────────────────────────────────────────────────
// Every alert is an investigation, and investigations show their working:
// this states, deterministically, why the detector fired — never AI copy.

export function detectionExplanation(group: SignalGroup): string {
  const n = group.count;
  const delta = group.avg_delta_pct != null ? `${Math.abs(Math.round(group.avg_delta_pct))}%` : null;
  switch (group.type) {
    case "flash_sale":
      return `${n} price drops landed within a single 4-hour window${delta ? ` averaging −${delta}` : ""} — coordinated timing like this is a sale event, not routine repricing.`;
    case "price_wave":
      return `${n} prices moved down together inside a 4-hour window — clustered drops signal a deliberate repricing decision.`;
    case "discount_wave":
      return `${n} products entered discount together — a campaign start, not item-level markdowns.`;
    case "price_increase":
      return `${n} prices moved up inside one window${delta ? ` averaging +${delta}` : ""} — margin-taking or input costs; either way, room opened above them.`;
    case "launch_burst":
      return `${n} products appeared in one scan window — a drop or collection launch, not catalog housekeeping.`;
    case "product_removals":
      return `${n} products left the catalog together — clearing a line, or a supplier change.`;
    case "availability_shift":
      return `${n} stock states flipped in one window — sell-through or an inventory event.`;
    default:
      return `${n} related change${n === 1 ? "" : "s"} detected inside one scan window.`;
  }
}

// ── Signal type → visual config ──────────────────────────────────────────
// Semantic color only — color carries meaning, nothing decorative:
//   red   = competitor cutting prices / discounting (downward, aggressive)
//   green = competitor raising prices (upward)
//   slate = informational, no price direction (launches, removals, stock)

export const SIGNAL_CONFIG: Record<SignalType, { color: string; icon: ElementType }> = {
  launch_burst:       { color: "#2F9FC9", icon: Rocket },        // market activity (cyan)
  flash_sale:         { color: "#F2555A", icon: Zap },           // threat
  price_wave:         { color: "#F2555A", icon: TrendingDown },  // threat
  price_increase:     { color: "#4CC38A", icon: TrendingUp },    // opportunity
  discount_wave:      { color: "#F2555A", icon: Tag },           // threat
  product_removals:   { color: "#6C7164", icon: Trash2 },        // informational
  availability_shift: { color: "#6C7164", icon: Package },       // informational
  tactical_launches:  { color: "#6C7164", icon: Plus },
  tactical_prices:    { color: "#6C7164", icon: ArrowUpDown },   // mixed direction — neutral
  tactical_discounts: { color: "#F2555A", icon: Percent },       // price down
  single:             { color: "#6C7164", icon: Minus },
};
