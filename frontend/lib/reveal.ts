/**
 * First-scan reveal — pure derivations + completion persistence.
 *
 * Pulled out of the page component so the trust-critical logic is unit
 * testable and provably grounded: every displayed fact is read from the
 * persisted scan snapshot, findings adapt to how much data actually exists,
 * and the reveal's "done" state survives a refresh. No claim here asserts
 * product overlap, SEO, reviews, competitor intent, or a guaranteed outcome —
 * enforced by tests.
 */

export interface RevealStat {
  label: string;
  value: string;
  sub?: string;
  /** observed = a raw measured metric; computed = derived from measured metrics */
  kind: "observed" | "computed";
}

export interface RevealFinding {
  type: string;      // signal | watch | opportunity — drives the card motif
  headline: string;  // an OBSERVED fact, stated plainly
  why: string;       // clearly-framed INTERPRETATION of that fact ("often", "can")
}

/** The only facts the reveal is allowed to speak from — all from the snapshot. */
export interface SnapshotFacts {
  products?: number;
  median?: number;
  priceMin?: number;
  priceMax?: number;
  promoRate?: number;
  launches30?: number;
  collectionsCount?: number;
  positionLabel?: string;
  gapsTotal?: number;
}

export interface BriefCardLike {
  type: string;
  headline: string;
  body: string;
}

const num = (v: unknown): number | undefined =>
  typeof v === "number" && Number.isFinite(v) ? v : undefined;
const str = (v: unknown): string | undefined =>
  typeof v === "string" && v.trim() ? v : undefined;

export function fmtMoney(n?: number): string {
  return n != null ? `$${n.toLocaleString(undefined, { maximumFractionDigits: 0 })}` : "—";
}

/** Read the flat fact set out of a raw `snapshot_data` blob — persisted only. */
export function extractFacts(snapshotData: Record<string, unknown> | null | undefined): SnapshotFacts {
  const d = (snapshotData ?? {}) as Record<string, Record<string, unknown>>;
  const catalog = (d.catalog ?? {}) as Record<string, unknown>;
  const pricing = (d.pricing ?? {}) as Record<string, unknown>;
  const discounts = (d.discounts ?? {}) as Record<string, unknown>;
  const positioning = (d.positioning ?? {}) as Record<string, Record<string, unknown>>;
  const launch = (d.launch_timeline ?? {}) as Record<string, Record<string, Record<string, Record<string, number>>>>;
  const gaps = (d.gap_analysis ?? {}) as Record<string, unknown>;
  const storeProfile = (d.store_profile ?? {}) as Record<string, Record<string, unknown>>;

  return {
    products: num(catalog.total_products),
    median: num(pricing.median),
    priceMin: num(pricing.min),
    priceMax: num(pricing.max),
    promoRate: num(discounts.discounted_pct),
    launches30: num(launch.launch_counts?.["30d"]?.count),
    collectionsCount: num(storeProfile.collections?.count),
    positionLabel: str(positioning.market_position?.label),
    gapsTotal: num(gaps.total),
  };
}

/** Screen 1 — observed/computed metrics; only rows we truly have. */
export function deriveStats(f: SnapshotFacts): RevealStat[] {
  const stats: (RevealStat | false)[] = [
    f.products != null && { label: "Products analyzed", value: f.products.toLocaleString(), kind: "observed" },
    f.median != null && {
      label: "Median price", value: fmtMoney(f.median), kind: "computed",
      sub: f.priceMin != null && f.priceMax != null ? `${fmtMoney(f.priceMin)} – ${fmtMoney(f.priceMax)}` : undefined,
    },
    f.promoRate != null && { label: "Catalog discounted", value: `${f.promoRate}%`, kind: "computed" },
    f.launches30 != null && { label: "Launches · 30d", value: String(f.launches30), kind: "observed" },
    f.collectionsCount != null && { label: "Collections", value: String(f.collectionsCount), kind: "observed" },
    f.positionLabel != null && { label: "Positioning", value: f.positionLabel, kind: "computed" },
  ];
  return stats.filter(Boolean) as RevealStat[];
}

/** Truthful findings derived from the snapshot when the AI brief is absent.
 * Headlines are measured facts; the "why" is framed as interpretation. */
export function deriveFallbackFindings(f: SnapshotFacts): RevealFinding[] {
  const out: (RevealFinding | false)[] = [
    f.promoRate != null && {
      type: "signal",
      headline: `${f.promoRate}% of their catalog is discounted right now`,
      why: f.promoRate >= 25
        ? "Heavy discounting often points to pricing pressure or a clearance cycle — margin you may not have to give up."
        : "Light discounting suggests they're holding margin — undercutting selectively could win price-sensitive shoppers.",
    },
    f.launches30 != null && {
      type: "watch",
      headline: `${f.launches30} product launch${f.launches30 === 1 ? "" : "es"} in the last 30 days`,
      why: f.launches30 >= 5
        ? "That's an active release pace — worth watching which launches gain traction."
        : "A slower release cadence can mean a focus on best-sellers — or room for you to out-ship them.",
    },
    f.median != null && {
      type: "opportunity",
      headline: `Median price ${fmtMoney(f.median)}${f.positionLabel ? ` — ${f.positionLabel}` : ""}`,
      why: "Knowing where they sit lets you position deliberately above or below instead of guessing.",
    },
  ];
  return out.filter(Boolean) as RevealFinding[];
}

/** Prefer the AI brief's cards when it produced enough; else the grounded
 * fallback. Never mixes — so the reveal is either all-AI or all-snapshot. */
export function chooseFindings(briefCards: BriefCardLike[] | null | undefined, f: SnapshotFacts): RevealFinding[] {
  const brief = (briefCards ?? [])
    .filter((c) => c.type !== "action")
    .slice(0, 3)
    .map((c) => ({ type: c.type, headline: c.headline, why: c.body }));
  return brief.length >= 2 ? brief : deriveFallbackFindings(f);
}

/** The observed facts an opportunity/recommendation is grounded in. */
export function deriveEvidence(f: SnapshotFacts): string[] {
  return [
    f.products != null && `${f.products.toLocaleString()} products scanned`,
    f.promoRate != null && `${f.promoRate}% of catalog discounted`,
    f.launches30 != null && `${f.launches30} launches in 30 days`,
    f.median != null && `median price ${fmtMoney(f.median)}`,
  ].filter(Boolean) as string[];
}

/** Which content screens the reveal should show — adaptive, never empty.
 * Screens 1 (analyzed), 4 (monitors) and 5 (done) are always present;
 * findings and opportunity screens appear only when they have real content. */
export type RevealScreenId = "analyzed" | "findings" | "opportunity" | "monitors" | "done";

export function revealScreenIds(opts: {
  stats: RevealStat[];
  findings: RevealFinding[];
  hasOpportunity: boolean;
}): RevealScreenId[] {
  const ids: RevealScreenId[] = [];
  if (opts.stats.length > 0) ids.push("analyzed");
  if (opts.findings.length > 0) ids.push("findings");
  if (opts.hasOpportunity) ids.push("opportunity");
  ids.push("monitors", "done");
  return ids;
}

// ── Completion persistence — a refresh must not replay a finished reveal ────

export const REVEAL_DONE_PREFIX = "ss_reveal_done_";
export const REVEAL_STEP_PREFIX = "ss_reveal_step_";

type StorageLike = Pick<Storage, "getItem" | "setItem" | "removeItem">;

function safeStorage(explicit?: StorageLike): StorageLike | null {
  if (explicit) return explicit;
  try {
    if (typeof window !== "undefined" && window.localStorage) return window.localStorage;
  } catch { /* access can throw in privacy modes */ }
  return null;
}

export function isRevealComplete(id: string, storage?: StorageLike): boolean {
  const s = safeStorage(storage);
  try { return s?.getItem(REVEAL_DONE_PREFIX + id) === "1"; } catch { return false; }
}

export function markRevealComplete(id: string, storage?: StorageLike): void {
  const s = safeStorage(storage);
  try { s?.setItem(REVEAL_DONE_PREFIX + id, "1"); s?.removeItem(REVEAL_STEP_PREFIX + id); } catch { /* ignore */ }
}

export function readRevealStep(id: string, storage?: StorageLike): number {
  const s = safeStorage(storage);
  try {
    const v = parseInt(s?.getItem(REVEAL_STEP_PREFIX + id) ?? "", 10);
    return Number.isFinite(v) && v >= 0 ? v : 0;
  } catch { return 0; }
}

export function writeRevealStep(id: string, step: number, storage?: StorageLike): void {
  const s = safeStorage(storage);
  try { s?.setItem(REVEAL_STEP_PREFIX + id, String(step)); } catch { /* ignore */ }
}
