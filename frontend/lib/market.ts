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
  headline: string;           // "Multiple competitors low on stock"
  whatHappened: string;       // the OBSERVED FACT — measured, high confidence
  whyItMatters: string;       // the INTERPRETATION — an inference, explicitly hedged
  confidence: Confidence;     // confidence in the interpretation (not the fact)
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

export type Confidence = "high" | "medium" | "low";

// Narratives separate the OBSERVED FACT (whatHappened — measured, high
// confidence) from the INTERPRETATION (whyItMatters — an inference from a
// correlation, so it is explicitly hedged and carries a confidence level). We
// only observe that several competitors moved together; we do NOT observe
// demand, supply constraints, margin pressure, or intent — so those are named
// as likely/possible, never as proven fact.
function narrate(themeKey: string, n: number): {
  headline: string; kind: InsightKind; whatHappened: string; whyItMatters: string;
  yourMove: string; type: SignalType; confidence: Confidence;
} {
  const word = countWord(n);
  switch (themeKey) {
    case "inventory":
      return {
        type: "availability_shift", kind: "opportunity", confidence: "medium",
        headline: "Multiple competitors low on stock",
        whatHappened: `${word} competitors went low or out of stock within the same window.`,
        whyItMatters: "Several sellers running dry at once often means demand is outpacing supply in the category — though it can also be a shared supplier delay or seasonal gap. Either reading points the same way: their empty shelves are demand you may be able to serve right now.",
        yourMove: "Lead with availability. Push “in stock, ships today” messaging and lift paid spend on any products you both sell while competitors can’t fulfill — you capture the demand whatever its cause.",
      };
    case "promotion":
      return {
        type: "discount_wave", kind: "signal", confidence: "medium",
        headline: "Simultaneous discounting across the category",
        whatHappened: `${word} competitors started discounting within the same window.`,
        whyItMatters: "Promotions clustering like this usually points to a category-wide event — a seasonal push or softening demand — rather than coincidence. The likely effect either way: shoppers get trained to wait for a deal.",
        yourMove: "Don’t reflexively race to the bottom. Hold price and run a full-price quality angle this week — the discount-fatigued buyers these sales create are a cheap acquisition target once the promotions end.",
      };
    case "expansion":
      return {
        type: "launch_burst", kind: "signal", confidence: "medium",
        headline: "Competitors launching in unison",
        whatHappened: `${word} competitors pushed new products within the same window.`,
        whyItMatters: "Coordinated launches often mean rivals expect rising demand and are placing bets before peak — though some may just be routine drops. Worth treating as a category that could be heating up.",
        yourMove: "Get your hero products into ads before their campaigns peak. If they’re entering a lane you cover, claim the search and social real estate early — it’s cheaper than catching up later.",
      };
    case "price_drop":
      return {
        type: "price_wave", kind: "signal", confidence: "medium",
        headline: "Clustered price cuts",
        whatHappened: `${word} competitors cut prices across their catalogs within the same window.`,
        whyItMatters: "Price cuts landing together often signal margin pressure or the opening of a price war — but a single shared sale can look the same. If it spreads, customers recalibrate what “normal” costs, so it’s worth watching whether more follow.",
        yourMove: "Don’t reflexively match. Hold your price, reinforce quality where your catalog overlaps theirs, and move only on the specific SKUs where you’d actually lose the sale.",
      };
    case "price_up":
      return {
        type: "price_increase", kind: "opportunity", confidence: "medium",
        headline: "Competitors raising prices together",
        whatHappened: `${word} competitors raised prices within the same window.`,
        whyItMatters: "Several rivals lifting prices at once likely means the category’s price ceiling is rising — possibly from input costs, possibly from confident demand. Either way, headroom may have opened above you.",
        yourMove: "Consider testing a price increase without losing your value position — or hold and capture their newly price-sensitive switchers with Shopping ads on the products they just made more expensive.",
      };
    case "contraction":
      return {
        type: "product_removals", kind: "watch", confidence: "low",
        headline: "Competitors trimming catalogs together",
        whatHappened: `${word} competitors delisted products within the same window.`,
        whyItMatters: "Synchronized delisting is most likely a seasonal reset or a shared supply constraint — the cause is hard to pin down from the outside. Whatever it is, competition has thinned for those specific searches for now.",
        yourMove: "If you carry anything similar, refresh your Google Shopping feed and ad copy now — there may be less direct competition for those queries until they restock.",
      };
    default:
      return {
        type: "single", kind: "watch", confidence: "low",
        headline: "Coordinated market movement",
        whatHappened: `${word} competitors made similar moves within the same window.`,
        whyItMatters: "Several rivals acting together more often than not reflects a shared market condition rather than coincidence — but the specific cause isn’t observable from here.",
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
      whatHappened: n.whatHappened, whyItMatters: n.whyItMatters,
      confidence: n.confidence, yourMove: n.yourMove,
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
