import { describe, it, expect } from "vitest";
import { deriveMarketSignals, deriveQuietIntelligence, competitorMetrics } from "@/lib/market";
import type { SignalGroup, SignalType, SignalTier } from "@/lib/signals";
import type { Competitor } from "@/lib/api";

function group(id: string, competitor_id: string, type: SignalType, tier: SignalTier, count: number): SignalGroup {
  return {
    id, type, tier, competitor_id, hostname: `${competitor_id}.com`,
    events: [], count, detected_at: "2026-01-01T00:00:00Z", started_at: "2026-01-01T00:00:00Z",
    label: `${count} ${type}`, headline: type,
  };
}

function comp(over: Partial<Competitor>): Competitor {
  return {
    id: over.id ?? "c", user_id: "u", store_url: "https://x.com", hostname: over.hostname ?? "x.com",
    is_active: true, scan_status: "done", created_at: "2026-01-01T00:00:00Z", ...over,
  };
}

describe("deriveMarketSignals — cross-competitor clustering", () => {
  it("collapses the same theme across 2+ competitors into ONE market signal", () => {
    const groups = [
      group("1", "a", "availability_shift", "strategic", 6),
      group("2", "b", "availability_shift", "tactical", 3),
      group("3", "c", "availability_shift", "strategic", 8),
    ];
    const signals = deriveMarketSignals(groups);
    const inv = signals.find((s) => s.type === "availability_shift");
    expect(inv).toBeTruthy();
    expect(inv!.competitorCount).toBe(3);
    expect(inv!.totalCount).toBe(17);
  });

  it("does NOT create a market signal when only one competitor moved", () => {
    const signals = deriveMarketSignals([group("1", "a", "launch_burst", "strategic", 7)]);
    expect(signals).toHaveLength(0);
  });

  it("pools related signal types (discount wave + flash sale) into one promotion theme", () => {
    const signals = deriveMarketSignals([
      group("1", "a", "discount_wave", "strategic", 5),
      group("2", "b", "flash_sale", "strategic", 4),
    ]);
    expect(signals).toHaveLength(1);
    expect(signals[0].competitorCount).toBe(2);
  });

  it("ignores raw-tier noise", () => {
    const signals = deriveMarketSignals([
      group("1", "a", "single", "raw", 1),
      group("2", "b", "single", "raw", 1),
    ]);
    expect(signals).toHaveLength(0);
  });

  it("ranks an opportunity above lower-priority signals", () => {
    const signals = deriveMarketSignals([
      group("1", "a", "availability_shift", "strategic", 2), // opportunity
      group("2", "b", "availability_shift", "strategic", 2),
      group("3", "a", "product_removals", "strategic", 2),   // watch
      group("4", "b", "product_removals", "strategic", 2),
    ]);
    expect(signals[0].kind).toBe("opportunity");
  });
});

describe("deterministic signal copy — honest claims", () => {
  it("separates observed fact from a hedged, confidence-labeled interpretation", () => {
    const [s] = deriveMarketSignals([
      group("1", "a", "availability_shift", "strategic", 3),
      group("2", "b", "availability_shift", "strategic", 3),
    ]);
    // observed fact stays factual (what we measured)
    expect(s.whatHappened.toLowerCase()).toContain("stock");
    // interpretation is hedged, not asserted as proven
    expect(s.whyItMatters.toLowerCase()).toMatch(/often|likely|possibl|usually|can also|most likely/);
    // and carries a confidence level
    expect(["high", "medium", "low"]).toContain(s.confidence);
  });

  it("labels catalog-contraction inference as low confidence", () => {
    const [s] = deriveMarketSignals([
      group("1", "a", "product_removals", "strategic", 2),
      group("2", "b", "product_removals", "strategic", 2),
    ]);
    expect(s.confidence).toBe("low");
  });
});

describe("deriveQuietIntelligence", () => {
  it("returns baseline market facts from the tracked set", () => {
    const facts = deriveQuietIntelligence([
      comp({ id: "a", hostname: "a.com", median_price: 120, promo_rate: 30, new_30d: 12, product_count: 500 }),
      comp({ id: "b", hostname: "b.com", median_price: 40, promo_rate: 5, new_30d: 2, product_count: 80 }),
    ]);
    expect(facts.length).toBeGreaterThan(0);
    const labels = facts.map((f) => f.label);
    expect(labels).toContain("Pricing spread");
  });

  it("returns nothing when there is no scanned competitor", () => {
    expect(deriveQuietIntelligence([])).toHaveLength(0);
  });
});

describe("competitorMetrics — strategy not statistics", () => {
  it("translates raw numbers into strategic descriptors", () => {
    const metrics = competitorMetrics(comp({ median_price: 150, promo_rate: 40, new_30d: 20, product_count: 800 }));
    const byLabel = Object.fromEntries(metrics.map((m) => [m.label, m.value]));
    expect(byLabel["Positioning"]).toBe("Premium");
    expect(byLabel["Market aggressiveness"]).toBe("Very high");
  });
});
