import { describe, it, expect, beforeEach } from "vitest";
import {
  extractFacts, deriveStats, deriveFallbackFindings, chooseFindings,
  deriveEvidence, revealScreenIds, isRevealComplete, markRevealComplete,
  readRevealStep, writeRevealStep, REVEAL_DONE_PREFIX,
  type BriefCardLike,
} from "@/lib/reveal";

// A realistic persisted snapshot_data blob (the shape the scan pipeline writes)
const FULL_SNAPSHOT = {
  catalog: { total_products: 142 },
  pricing: { median: 58, min: 20, max: 180 },
  discounts: { discounted_pct: 32 },
  positioning: { market_position: { label: "premium" } },
  launch_timeline: { launch_counts: { "30d": { count: 6 } } },
  gap_analysis: { total: 4 },
  store_profile: { collections: { count: 9 } },
};

describe("extractFacts — persisted data only", () => {
  it("pulls every fact from the snapshot blob", () => {
    const f = extractFacts(FULL_SNAPSHOT);
    expect(f).toMatchObject({
      products: 142, median: 58, priceMin: 20, priceMax: 180,
      promoRate: 32, launches30: 6, collectionsCount: 9,
      positionLabel: "premium", gapsTotal: 4,
    });
  });

  it("returns all-undefined for an empty/absent snapshot (no invented values)", () => {
    for (const v of [null, undefined, {}]) {
      const f = extractFacts(v as Record<string, unknown> | null);
      expect(Object.values(f).every((x) => x === undefined)).toBe(true);
    }
  });

  it("ignores non-numeric junk rather than coercing it", () => {
    const f = extractFacts({ catalog: { total_products: "lots" }, pricing: { median: null } });
    expect(f.products).toBeUndefined();
    expect(f.median).toBeUndefined();
  });
});

describe("deriveStats — adaptive, never empty cells", () => {
  it("emits a card only for facts that exist", () => {
    const stats = deriveStats(extractFacts(FULL_SNAPSHOT));
    expect(stats.map((s) => s.label)).toEqual([
      "Products analyzed", "Median price", "Catalog discounted",
      "Launches · 30d", "Collections", "Positioning",
    ]);
    expect(stats.find((s) => s.label === "Median price")?.sub).toBe("$20 – $180");
  });

  it("drops missing facts instead of showing empty/zero cards (sparse snapshot)", () => {
    const stats = deriveStats(extractFacts({ catalog: { total_products: 10 } }));
    expect(stats).toHaveLength(1);
    expect(stats[0]).toMatchObject({ label: "Products analyzed", value: "10", kind: "observed" });
  });
});

describe("findings — grounded, adaptive, no forbidden claims", () => {
  it("no valid finding → empty list (screen will be skipped)", () => {
    expect(deriveFallbackFindings(extractFacts({}))).toEqual([]);
    expect(chooseFindings(null, extractFacts({}))).toEqual([]);
  });

  it("one valid finding → single grounded finding", () => {
    const findings = chooseFindings(null, extractFacts({ discounts: { discounted_pct: 40 } }));
    expect(findings).toHaveLength(1);
    expect(findings[0].headline).toContain("40%");
  });

  it("multiple findings from a full snapshot", () => {
    const findings = chooseFindings(null, extractFacts(FULL_SNAPSHOT));
    expect(findings.length).toBeGreaterThanOrEqual(2);
  });

  it("prefers the AI brief when it has >=2 non-action cards", () => {
    const cards: BriefCardLike[] = [
      { type: "signal", headline: "AI signal", body: "b1" },
      { type: "opportunity", headline: "AI opp", body: "b2" },
      { type: "action", headline: "do this", body: "b3" },
    ];
    const findings = chooseFindings(cards, extractFacts(FULL_SNAPSHOT));
    expect(findings.map((f) => f.headline)).toEqual(["AI signal", "AI opp"]); // action filtered out
  });

  it("falls back to snapshot facts when the brief is thin (optional-AI failure)", () => {
    const oneCard: BriefCardLike[] = [{ type: "signal", headline: "only one", body: "b" }];
    const findings = chooseFindings(oneCard, extractFacts(FULL_SNAPSHOT));
    expect(findings.some((f) => f.headline === "only one")).toBe(false); // used fallback
    expect(findings.length).toBeGreaterThanOrEqual(2);
  });

  it("never claims product overlap, SEO, reviews, intent-as-fact, or guaranteed outcomes", () => {
    const text = deriveFallbackFindings(extractFacts(FULL_SNAPSHOT))
      .flatMap((f) => [f.headline, f.why]).join(" ").toLowerCase();
    for (const banned of ["overlap", "you both sell", "seo", "review", "guarantee", "will rank", "will increase revenue"]) {
      expect(text).not.toContain(banned);
    }
    // interpretation is hedged, not asserted as fact
    expect(text).toMatch(/often|can|suggests|could/);
  });
});

describe("deriveEvidence — observed facts backing a recommendation", () => {
  it("lists only measured facts", () => {
    expect(deriveEvidence(extractFacts(FULL_SNAPSHOT))).toEqual([
      "142 products scanned", "32% of catalog discounted",
      "6 launches in 30 days", "median price $58",
    ]);
  });
  it("empty when nothing measured", () => {
    expect(deriveEvidence(extractFacts({}))).toEqual([]);
  });
});

describe("revealScreenIds — adapts, always ends on monitors+done", () => {
  it("full data → all five screens in order", () => {
    const f = extractFacts(FULL_SNAPSHOT);
    expect(revealScreenIds({ stats: deriveStats(f), findings: chooseFindings(null, f), hasOpportunity: true }))
      .toEqual(["analyzed", "findings", "opportunity", "monitors", "done"]);
  });

  it("no findings and no opportunity → skips those screens (no empty cards)", () => {
    expect(revealScreenIds({ stats: deriveStats(extractFacts({ catalog: { total_products: 5 } })), findings: [], hasOpportunity: false }))
      .toEqual(["analyzed", "monitors", "done"]);
  });

  it("no stats at all → still shows monitors + done", () => {
    expect(revealScreenIds({ stats: [], findings: [], hasOpportunity: false }))
      .toEqual(["monitors", "done"]);
  });
});

describe("completion persistence — refresh must not replay a finished reveal", () => {
  let store: Record<string, string>;
  const fake = {
    getItem: (k: string) => (k in store ? store[k] : null),
    setItem: (k: string, v: string) => { store[k] = v; },
    removeItem: (k: string) => { delete store[k]; },
  };
  beforeEach(() => { store = {}; });

  it("incomplete by default; complete after marking", () => {
    expect(isRevealComplete("abc", fake)).toBe(false);
    markRevealComplete("abc", fake);
    expect(isRevealComplete("abc", fake)).toBe(true);
    expect(store[REVEAL_DONE_PREFIX + "abc"]).toBe("1");
  });

  it("completion is per-competitor", () => {
    markRevealComplete("abc", fake);
    expect(isRevealComplete("xyz", fake)).toBe(false);
  });

  it("step resumes across a refresh, and is cleared on completion", () => {
    writeRevealStep("abc", 2, fake);
    expect(readRevealStep("abc", fake)).toBe(2);
    markRevealComplete("abc", fake);
    expect(readRevealStep("abc", fake)).toBe(0); // cleared
  });

  it("readRevealStep is defensive against junk", () => {
    store["ss_reveal_step_abc"] = "not-a-number";
    expect(readRevealStep("abc", fake)).toBe(0);
  });
});
