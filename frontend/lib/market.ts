/**
 * Market intelligence — the interpretation layer that turns raw competitor
 * activity and stats into executive-level reads: cross-competitor MARKET
 * SIGNALS (many rivals doing the same thing at once → one strategic call),
 * strategic per-competitor METRICS (positioning, aggressiveness, launch
 * velocity — strategy, not statistics), and QUIET-DAY intelligence (what the
 * market looks like even when nothing moved today, so the user always leaves
 * having learned something).
 *
 * Pure functions, no I/O — reused by the dashboard, Watch Station, and
 * competitor pages so every surface speaks the same strategic language.
 */
import type { Competitor } from "@/lib/api";
import type { SignalGroup, SignalType } from "@/lib/signals";
import type { InsightKind } from "@/lib/insight";

// ── Cross-competitor Market Signals ────────────────────────────────────────
// A single competitor cutting prices is an event. THREE competitors cutting
// prices in the same window is a market condition — and a different decision.

export interface MarketSignalMember {
  competitor_id: string;
  hostname: string;
  count: number;
  label: string;
}

export interface MarketSignal {
  id: string;
  type: SignalType;
  kind: InsightKind;          // drives the shared insight color/vocabulary
  headline: string;           // "Category-wide inventory pressure"
  whatHappened: string;       // "Three competitors are running low on stock at once."
  whyItMatters: string;       // the interpretation — what this condition means
  yourMove: string;           // the strategic call
  members: MarketSignalMember[];
  groups: SignalGroup[];      // underlying per-competitor groups (details live here)
  competitorCount: number;
  totalCount: number;
}

// Signal types that mean the same strategic thing get pooled together so a
// flash sale at one store and a discount wave at another read as one
// "promotional wave" rather than two unrelated cards.
const THEME: Record<string, { key: string; types: SignalType[] }> = {
  inventory:   { key: "inventory",   types: ["availability_shift"] },
  promotion:   { key: "promotion",   types: ["discount_wave", "flash_sale", "tactical_discounts"] },
  expansion:   { key: "expansion",   types: ["launch_burst", "tactical_launches"] },
  price_drop:  { key: "price_drop",  types: ["price_wave"] },
  price_up:    { key: "price_up",    types: ["price_increase"] },
  contraction: { key: "contraction", types: ["product_removals"] },
};

function themeOf(type: SignalType): string | null {
  for (const t of Object.values(THEME)) if (t.types.includes(type)) return t.key;
  return null;
}

function countWord(n: number): string {
  return n === 2 ? "Two" : n === 3 ? "Three" : n === 4 ? "Four" : `${n}`;
}

function narrate(themeKey: string, n: number): {
  headline: string; kind: InsightKind; whatHappened: string; whyItMatters: string; yourMove: string; type: SignalType;
} {
  const word = countWord(n);
  switch (themeKey) {
    case "inventory":
      return {
        type: "availability_shift", kind: "opportunity",
        headline: "Category-wide inventory pressure",
        whatHappened: `${word} competitors are running low or out of stock at the same time.`,
        whyItMatters: "When several sellers in a category run dry together, it's demand outrunning supply — a spike, not isolated operations problems. Their stockouts are unmet demand sitting in the market right now.",
        yourMove: "Lead with availability. Push “in stock, ships today” messaging and lift paid spend on the overlapping products while competitors physically can’t fulfill — you’re capturing demand they created but can’t serve.",
      };
    case "promotion":
      return {
        type: "discount_wave", kind: "signal",
        headline: "A promotional wave is sweeping the category",
        whatHappened: `${word} competitors started discounting within the same window.`,
        whyItMatters: "Simultaneous promotions signal a category-wide event — seasonal pressure or softening demand pushing everyone to buy volume with margin. The whole category is training its customers to wait for a deal.",
        yourMove: "Don’t race to the bottom. Hold price and run a full-price quality angle this week — the discount-fatigued buyers these sales create are your cheapest acquisition target once the promotions end.",
      };
    case "expansion":
      return {
        type: "launch_burst", kind: "signal",
        headline: "Competitors are expanding catalogs in unison",
        whatHappened: `${word} competitors are pushing new products at once.`,
        whyItMatters: "Coordinated launches mean the category is heating up ahead of peak demand — rivals are placing inventory bets now to own the season before ad costs climb.",
        yourMove: "Get your hero products into ads before their campaigns peak. If they’re all entering a lane you cover, claim the search and social real estate first — being early is cheaper than being loud later.",
      };
    case "price_drop":
      return {
        type: "price_wave", kind: "signal",
        headline: "Downward price pressure is building",
        whatHappened: `${word} competitors cut prices across their catalogs together.`,
        whyItMatters: "Clustered price drops point to margin pressure or an emerging price war. Once one anchor moves, the rest follow — and customers recalibrate what “normal” costs.",
        yourMove: "Don’t reflexively match. Hold your price, reinforce quality and service where your catalog overlaps theirs, and only move on the specific SKUs where you’ll actually lose the sale.",
      };
    case "price_up":
      return {
        type: "price_increase", kind: "opportunity",
        headline: "The category is repricing upward",
        whatHappened: `${word} competitors raised prices at the same time.`,
        whyItMatters: "When several rivals lift prices together, the category’s price ceiling just rose — either input costs are climbing or demand is strong enough to test. Either way, headroom opened above you.",
        yourMove: "You have room to raise prices without losing your value position — or to hold and capture their newly price-sensitive switchers with Shopping ads on the products they just made more expensive.",
      };
    case "contraction":
      return {
        type: "product_removals", kind: "watch",
        headline: "Competitors are trimming catalogs together",
        whatHappened: `${word} competitors delisted products in the same window.`,
        whyItMatters: "Synchronized delisting is usually a seasonal reset or a shared supply constraint — either way, competition just thinned for those specific searches.",
        yourMove: "If you carry anything similar, refresh your Google Shopping feed and ad copy now — there’s less direct competition for those queries until they restock.",
      };
    default:
      return {
        type: "single", kind: "watch",
        headline: "Coordinated market movement",
        whatHappened: `${word} competitors made similar moves at once.`,
        whyItMatters: "Several rivals acting together usually signals a shared market condition rather than individual decisions.",
        yourMove: "Open the details below to see who moved and decide whether it touches your catalog.",
      };
  }
}

/**
 * Cluster per-competitor strategic signal groups into cross-competitor Market
 * Signals. Only themes where 2+ DISTINCT competitors moved qualify — that's
 * what separates a market condition from a single competitor's tactic.
 * Returns them ranked by breadth (how many competitors) then volume.
 */
export function deriveMarketSignals(groups: SignalGroup[]): MarketSignal[] {
  const byTheme = new Map<string, SignalGroup[]>();
  for (const g of groups) {
    if (g.tier === "raw") continue;
    const key = themeOf(g.type);
    if (!key) continue;
    (byTheme.get(key) ?? byTheme.set(key, []).get(key)!).push(g);
  }

  const signals: MarketSignal[] = [];
  for (const [key, themeGroups] of byTheme) {
    const byComp = new Map<string, SignalGroup[]>();
    for (const g of themeGroups) {
      (byComp.get(g.competitor_id) ?? byComp.set(g.competitor_id, []).get(g.competitor_id)!).push(g);
    }
    if (byComp.size < 2) continue; // needs multiple competitors to be a market signal

    const members: MarketSignalMember[] = [];
    let total = 0;
    for (const [cid, gs] of byComp) {
      const count = gs.reduce((s, g) => s + g.count, 0);
      total += count;
      members.push({
        competitor_id: cid, hostname: gs[0].hostname, count,
        label: gs[0].label || gs[0].headline,
      });
    }
    members.sort((a, b) => b.count - a.count);

    const n = narrate(key, byComp.size);
    signals.push({
      id: `ms-${key}`,
      type: n.type, kind: n.kind, headline: n.headline,
      whatHappened: n.whatHappened, whyItMatters: n.whyItMatters, yourMove: n.yourMove,
      members, groups: themeGroups,
      competitorCount: byComp.size, totalCount: total,
    });
  }

  const kindRank: Record<InsightKind, number> = { opportunity: 0, signal: 1, action: 1, prediction: 2, watch: 3 };
  return signals.sort((a, b) =>
    (b.competitorCount - a.competitorCount) ||
    (kindRank[a.kind] - kindRank[b.kind]) ||
    (b.totalCount - a.totalCount),
  );
}

// ── Strategic per-competitor metrics ───────────────────────────────────────
// Strategy, not statistics: what a number MEANS, not the number.

export type Tone = "hot" | "warm" | "neutral" | "cool";

export interface StrategicMetric {
  label: string;      // "Positioning"
  value: string;      // "Premium"
  detail?: string;    // "$120 median"
  tone: Tone;
}

export function positioning(medianPrice?: number): StrategicMetric | null {
  if (medianPrice == null || medianPrice <= 0) return null;
  const p = medianPrice;
  const [value, tone]: [string, Tone] =
    p < 35 ? ["Budget", "cool"] :
    p < 90 ? ["Mid-market", "neutral"] :
    p < 200 ? ["Premium", "warm"] : ["Luxury", "hot"];
  return { label: "Positioning", value, detail: `$${Math.round(p)} median`, tone };
}

export function promotionFrequency(promoRate?: number): StrategicMetric | null {
  if (promoRate == null) return null;
  const r = promoRate;
  const [value, tone]: [string, Tone] =
    r < 5 ? ["Rarely discounts", "cool"] :
    r < 15 ? ["Occasional promos", "neutral"] :
    r < 35 ? ["Frequently on sale", "warm"] : ["Always discounting", "hot"];
  return { label: "Promotion frequency", value, detail: `${Math.round(r)}% of catalog`, tone };
}

export function launchVelocity(new30d?: number): StrategicMetric | null {
  if (new30d == null) return null;
  const n = new30d;
  const [value, tone]: [string, Tone] =
    n === 0 ? ["Dormant", "cool"] :
    n <= 5 ? ["Steady cadence", "neutral"] :
    n <= 15 ? ["Actively launching", "warm"] : ["Aggressive expansion", "hot"];
  return { label: "Launch velocity", value, detail: `${n} new in 30d`, tone };
}

export function assortmentBreadth(productCount?: number): StrategicMetric | null {
  if (productCount == null || productCount <= 0) return null;
  const p = productCount;
  const [value, tone]: [string, Tone] =
    p < 50 ? ["Focused range", "neutral"] :
    p < 300 ? ["Moderate range", "neutral"] :
    p < 1000 ? ["Broad range", "warm"] : ["Vast catalog", "hot"];
  return { label: "Assortment breadth", value, detail: `${p.toLocaleString()} products`, tone };
}

/**
 * Market aggressiveness — a composite read of how hard a competitor is pushing
 * right now (launch velocity + promo intensity). The single most useful "how
 * worried should I be about this rival" indicator.
 */
export function aggressiveness(c: Competitor): StrategicMetric | null {
  const promo = c.promo_rate;
  const launches = c.new_30d;
  if (promo == null && launches == null) return null;
  let score = 0;
  if (launches != null) score += Math.min(50, launches * 4);
  if (promo != null) score += Math.min(50, promo * 1.4);
  const [value, tone]: [string, Tone] =
    score < 15 ? ["Low", "cool"] :
    score < 40 ? ["Moderate", "neutral"] :
    score < 70 ? ["High", "warm"] : ["Very high", "hot"];
  return { label: "Market aggressiveness", value, tone };
}

/** The strategic metric row for a competitor — only the ones we can derive. */
export function competitorMetrics(c: Competitor): StrategicMetric[] {
  return [
    positioning(c.median_price),
    aggressiveness(c),
    launchVelocity(c.new_30d),
    promotionFrequency(c.promo_rate),
    assortmentBreadth(c.product_count),
  ].filter((m): m is StrategicMetric => m != null);
}

// ── Watch Station indicators ───────────────────────────────────────────────
// A per-competitor pulse the user can read without opening anyone.

export type IndicatorKey = "pricing" | "launches" | "inventory" | "promotions" | "activity";

export interface WatchIndicators {
  pricing: boolean;
  launches: boolean;
  inventory: boolean;
  promotions: boolean;
  activityLevel: "quiet" | "moving" | "active";
}

export function watchIndicators(competitorId: string, groups: SignalGroup[], c?: Competitor): WatchIndicators {
  const mine = groups.filter((g) => g.competitor_id === competitorId);
  const has = (types: SignalType[]) => mine.some((g) => types.includes(g.type));
  const strategicCount = mine.filter((g) => g.tier === "strategic").length;
  const total = mine.reduce((s, g) => s + g.count, 0);
  return {
    pricing: has(["price_wave", "price_increase", "flash_sale", "tactical_prices"]),
    launches: has(["launch_burst", "tactical_launches"]) || (c?.new_30d ?? 0) > 0,
    inventory: has(["availability_shift"]),
    promotions: has(["discount_wave", "tactical_discounts", "flash_sale"]),
    activityLevel: strategicCount >= 1 || total >= 8 ? "active" : total >= 1 ? "moving" : "quiet",
  };
}

// ── Quiet-day intelligence ─────────────────────────────────────────────────
// A dashboard should never feel empty just because nobody moved today. When
// there's no fresh activity, we surface what we already KNOW about the market.

export interface MarketFact {
  label: string;
  value: string;
  detail: string;
}

function avg(nums: number[]): number | null {
  const v = nums.filter((n) => n != null && !Number.isNaN(n));
  return v.length ? v.reduce((a, b) => a + b, 0) / v.length : null;
}

/**
 * Baseline market facts derived from the tracked set — always available, even
 * on a dead-quiet day. Ordered most-strategic first.
 */
export function deriveQuietIntelligence(competitors: Competitor[]): MarketFact[] {
  const scanned = competitors.filter((c) => c.scan_status === "done" || c.product_count != null);
  if (scanned.length < 1) return [];
  const facts: MarketFact[] = [];

  const avgLaunch = avg(scanned.map((c) => c.new_30d ?? 0));
  if (avgLaunch != null) {
    facts.push({
      label: "Typical launch cadence",
      value: avgLaunch < 0.5 ? "Slow" : avgLaunch <= 5 ? "Steady" : "Fast",
      detail: `Your set ships ~${Math.round(avgLaunch)} new products / month on average`,
    });
  }

  const avgPromo = avg(scanned.map((c) => c.promo_rate ?? 0));
  if (avgPromo != null) {
    facts.push({
      label: "Discount climate",
      value: avgPromo < 5 ? "Full-price" : avgPromo < 20 ? "Selective" : "Promotional",
      detail: `~${Math.round(avgPromo)}% of the average competitor’s catalog is discounted right now`,
    });
  }

  const prices = scanned.map((c) => c.median_price).filter((p): p is number => p != null && p > 0);
  if (prices.length >= 2) {
    const lo = Math.min(...prices), hi = Math.max(...prices);
    const spread = hi / Math.max(1, lo);
    facts.push({
      label: "Pricing spread",
      value: spread >= 2.5 ? "Wide" : spread >= 1.5 ? "Moderate" : "Tight",
      detail: `Market runs $${Math.round(lo)}–$${Math.round(hi)} — ${spread >= 2 ? "room to position on either end" : "everyone is clustered on price"}`,
    });
  }

  const depths = scanned.map((c) => c.product_count).filter((p): p is number => p != null && p > 0);
  if (depths.length >= 1) {
    const a = avg(depths)!;
    facts.push({
      label: "Catalog depth",
      value: a < 50 ? "Focused" : a < 300 ? "Moderate" : "Broad",
      detail: `Competitors carry ~${Math.round(a).toLocaleString()} products on average`,
    });
  }

  // Who is pushing hardest right now — a always-useful orientation fact.
  const ranked = [...scanned].sort((a, b) =>
    ((b.new_30d ?? 0) * 4 + (b.promo_rate ?? 0)) - ((a.new_30d ?? 0) * 4 + (a.promo_rate ?? 0)));
  const top = ranked[0];
  if (top && ((top.new_30d ?? 0) > 0 || (top.promo_rate ?? 0) > 0)) {
    facts.push({
      label: "Most aggressive right now",
      value: top.display_name || top.hostname,
      detail: `Leading on ${(top.new_30d ?? 0) >= (top.promo_rate ?? 0) / 4 ? "new launches" : "promotions"} across your set`,
    });
  }

  return facts;
}
