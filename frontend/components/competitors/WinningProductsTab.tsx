"use client";

import { useEffect, useState, useMemo, useCallback } from "react";
import {
  Trophy, Sparkles, ExternalLink, Copy, Check,
  ChevronDown, ChevronUp, Flame, Bookmark,
} from "lucide-react";
import { LockedValueCard } from "@/components/ui";
import {
  competitors as api,
  watchlist as watchlistApi,
  type WinningProductsResponse,
  type WinningProduct,
  type NewestProduct,
} from "@/lib/api";
import { formatPrice } from "@/lib/utils";
import UpgradeModal from "@/components/UpgradeModal";

// ── verdict ──────────────────────────────────────────────────────────────────

function getVerdict(score: number): {
  label: string; color: string; bg: string; border: string;
} {
  if (score >= 75) return {
    label: "Worth Testing",
    color: "#4CC38A",
    bg: "rgba(76,195,138,0.10)",
    border: "rgba(76,195,138,0.22)",
  };
  if (score >= 50) return {
    label: "Watch First",
    color: "var(--amber)",
    bg: "rgba(255,178,36,0.10)",
    border: "rgba(255,178,36,0.22)",
  };
  return {
    label: "Skip",
    color: "#A8AC9E",
    bg: "rgba(148,163,184,0.06)",
    border: "rgba(148,163,184,0.15)",
  };
}

function getReasons(product: WinningProduct): string[] {
  const reasons: string[] = [];
  const signals = product.signals || {};

  if (product.available === false) {
    reasons.push("Out of stock — they sold through it, which confirms demand exists");
  } else {
    const avail = signals["availability"] ?? 0;
    if (avail >= 0.8) reasons.push("Fully in stock — actively reordering, not a clearance item");
    else reasons.push("Mostly in stock — limited variant gaps");
  }

  if (!product.discounted) {
    const fp = signals["full_price_confidence"] ?? 0;
    if (fp >= 0.8) reasons.push("Selling at full price — demand is not markdown-dependent");
    else reasons.push("Primarily full price — mostly not relying on discounts");
  } else if (product.discount_pct) {
    reasons.push(`Running at ${Math.round(product.discount_pct)}% off — demand may depend on the markdown`);
  }

  if (product.age_days != null) {
    if (product.age_days >= 365) {
      const yrs = (product.age_days / 365).toFixed(1);
      reasons.push(`${yrs} years in their catalog — a long-term proven seller`);
    } else if (product.age_days >= 90) {
      const mos = Math.round(product.age_days / 30);
      reasons.push(`${mos} months in catalog — survived the initial drop-off window`);
    } else if (product.age_days <= 30) {
      reasons.push(`Only ${product.age_days} days old — too early to confirm sustained demand`);
    } else {
      reasons.push(`${product.age_days} days old — still establishing demand`);
    }
  }

  if ((product.variants_count ?? 0) >= 8) {
    reasons.push(`${product.variants_count} variants — seller has conviction, invested in full option depth`);
  }

  return reasons;
}

function ageDaysLabel(days: number) {
  if (days < 30) return `${days}d old`;
  if (days < 365) return `${Math.round(days / 30)}mo`;
  return `${(days / 365).toFixed(1)}yr`;
}

// ── small utility components ─────────────────────────────────────────────────

function ProductImage({ src, title }: { src?: string | null; title?: string }) {
  if (!src) {
    return (
      <div
        className="w-11 h-11 rounded-lg shrink-0 flex items-center justify-center"
        style={{ background: "var(--bg3)" }}
      >
        <Trophy className="w-4 h-4" style={{ color: "var(--muted)" }} />
      </div>
    );
  }
  // eslint-disable-next-line @next/next/no-img-element
  return (
    <img
      src={src}
      alt={title || ""}
      className="w-11 h-11 rounded-lg object-cover shrink-0"
      style={{ background: "var(--bg3)" }}
    />
  );
}

function CopyButton({ text }: { text: string }) {
  const [copied, setCopied] = useState(false);
  const handle = (e: React.MouseEvent) => {
    e.stopPropagation();
    navigator.clipboard.writeText(text).catch(() => {});
    setCopied(true);
    setTimeout(() => setCopied(false), 1500);
  };
  return (
    <button
      onClick={handle}
      title="Copy product name"
      className="opacity-0 group-hover:opacity-60 hover:!opacity-100 shrink-0 transition-opacity p-0.5 rounded"
    >
      {copied
        ? <Check className="w-3 h-3" style={{ color: "#4CC38A" }} />
        : <Copy className="w-3 h-3" style={{ color: "var(--muted)" }} />}
    </button>
  );
}

// ── winner row ───────────────────────────────────────────────────────────────

interface WinnerRowProps {
  product: WinningProduct;
  rank: number;
  expanded: boolean;
  onToggle: () => void;
  isLast: boolean;
  pinned: boolean;
  onPin: () => void;
}

function WinnerRow({ product, rank, expanded, onToggle, isLast, pinned, onPin }: WinnerRowProps) {
  const verdict = product.locked ? null : getVerdict(product.score);
  const reasons = product.locked ? [] : getReasons(product);

  return (
    <div
      className="group cursor-pointer transition-colors hover:bg-white/[0.015]"
      style={!isLast ? { borderBottom: "1px solid var(--border)" } : undefined}
      onClick={onToggle}
    >
      {/* Main row */}
      <div className="flex items-center gap-3 px-4 py-3">
        <span
          className="text-xs font-mono w-4 text-center shrink-0"
          style={{ color: "var(--muted)" }}
        >
          {rank}
        </span>

        <ProductImage src={product.image} title={product.title} />

        <div className="flex-1 min-w-0">
          <div className="flex items-center gap-1.5">
            <p className="text-sm font-medium truncate" style={{ color: "var(--text)" }}>
              {product.title || "Untitled product"}
            </p>
            <CopyButton text={product.title || ""} />
            {product.product_url && (
              <a
                href={product.product_url}
                target="_blank"
                rel="noopener noreferrer"
                className="shrink-0 opacity-40 hover:opacity-100 transition-opacity"
                onClick={(e) => e.stopPropagation()}
                title="View on their store"
              >
                <ExternalLink className="w-3 h-3" style={{ color: "var(--muted)" }} />
              </a>
            )}
            <button
              onClick={(e) => { e.stopPropagation(); onPin(); }}
              title={pinned ? "Stop watching" : "Watch this product"}
              className={`shrink-0 p-0.5 rounded transition-opacity ${pinned ? "opacity-100" : "opacity-0 group-hover:opacity-60 hover:!opacity-100"}`}
            >
              <Bookmark
                className="w-3 h-3"
                style={{ color: pinned ? "var(--accent)" : "var(--muted)", fill: pinned ? "var(--accent)" : "none" }}
              />
            </button>
          </div>

          <div className="flex items-center gap-2 mt-0.5 flex-wrap">
            <span className="text-xs" style={{ color: "var(--muted)" }}>
              {formatPrice(product.price_min)}
            </span>

            {!product.locked && (
              <>
                {product.discounted && product.discount_pct ? (
                  <span
                    className="text-[10px] px-1.5 py-0.5 rounded-md font-medium"
                    style={{ background: "rgba(242,85,90,0.12)", color: "#F2555A" }}
                  >
                    {Math.round(product.discount_pct)}% off
                  </span>
                ) : (
                  <span
                    className="text-[10px] px-1.5 py-0.5 rounded-md font-medium"
                    style={{ background: "rgba(76,195,138,0.10)", color: "var(--emerald)" }}
                  >
                    Full price
                  </span>
                )}

                {product.age_days != null && (
                  <span className="text-[10px]" style={{ color: "var(--muted)" }}>
                    {ageDaysLabel(product.age_days)}
                  </span>
                )}

                {!product.available && (
                  <span
                    className="text-[10px] px-1.5 py-0.5 rounded-md"
                    style={{ background: "rgba(242,85,90,0.08)", color: "#F2555A" }}
                  >
                    OOS
                  </span>
                )}
              </>
            )}

            {product.locked && (
              <span
                className="text-[10px] px-1.5 py-0.5 rounded-md"
                style={{ background: "rgba(255,178,36,0.08)", color: "var(--accent)" }}
              >
                Upgrade to see verdict
              </span>
            )}
          </div>
        </div>

        {/* Verdict badge + chevron */}
        <div className="flex items-center gap-2 shrink-0">
          {verdict && (
            <span
              className="text-[10px] font-bold px-2 py-1 rounded-lg whitespace-nowrap"
              style={{
                background: verdict.bg,
                color: verdict.color,
                border: `1px solid ${verdict.border}`,
              }}
            >
              {verdict.label}
            </span>
          )}
          {!product.locked && (
            expanded
              ? <ChevronUp className="w-3.5 h-3.5" style={{ color: "var(--muted)" }} />
              : <ChevronDown
                  className="w-3.5 h-3.5 opacity-0 group-hover:opacity-100 transition-opacity"
                  style={{ color: "var(--muted)" }}
                />
          )}
        </div>
      </div>

      {/* Reasoning — shown when expanded */}
      {expanded && !product.locked && (
        <div
          className="px-4 pb-4 pt-0"
          style={{ borderTop: "1px solid rgba(255,255,255,0.05)", marginLeft: 52 }}
        >
          <p
            className="text-[10px] font-semibold uppercase tracking-wider pt-3 pb-2"
            style={{ color: "var(--muted)" }}
          >
            Why {verdict?.label}
          </p>
          <ul className="space-y-1.5 mb-3">
            {reasons.map((r, i) => (
              <li key={i} className="flex items-start gap-2">
                <span className="mt-1 w-1 h-1 rounded-full shrink-0" style={{ background: verdict?.color }} />
                <span className="text-xs leading-relaxed" style={{ color: "var(--text-2, var(--muted))" }}>
                  {r}
                </span>
              </li>
            ))}
          </ul>
          {product.reason && (
            <p className="text-xs leading-relaxed pt-2" style={{
              color: "var(--muted)",
              borderTop: "1px solid rgba(255,255,255,0.05)",
            }}>
              {product.reason}
            </p>
          )}
        </div>
      )}
    </div>
  );
}

// ── filter / sort types ──────────────────────────────────────────────────────

type FilterKey = "worth_testing" | "watch_first" | "full_price" | "in_stock" | "new_launch";
type SortKey   = "score" | "newest" | "price_asc" | "price_desc";

const FILTERS: { key: FilterKey; label: string }[] = [
  { key: "worth_testing", label: "Worth Testing" },
  { key: "watch_first",   label: "Watch First" },
  { key: "full_price",    label: "Full price" },
  { key: "in_stock",      label: "In stock" },
  { key: "new_launch",    label: "New (<30d)" },
];

const SORTS: { key: SortKey; label: string }[] = [
  { key: "score",     label: "Score" },
  { key: "newest",    label: "Newest" },
  { key: "price_asc", label: "Price ↑" },
  { key: "price_desc",label: "Price ↓" },
];

// ── launch row ───────────────────────────────────────────────────────────────

function LaunchRow({ p, isLast }: { p: NewestProduct; isLast: boolean }) {
  const isVeryNew = (p.age_days ?? 99) <= 7;
  const isNew     = (p.age_days ?? 99) <= 30;
  const deepVars  = (p.variants_count ?? 0) >= 8;

  let ageBadgeStyle: React.CSSProperties;
  if (isVeryNew)   ageBadgeStyle = { background: "rgba(47,159,201,0.15)", color: "#2F9FC9" };
  else if (isNew)  ageBadgeStyle = { background: "rgba(255,178,36,0.10)", color: "var(--amber)" };
  else             ageBadgeStyle = { background: "transparent", color: "var(--muted)" };

  return (
    <div
      className="flex items-center gap-3 px-4 py-3"
      style={!isLast ? { borderBottom: "1px solid var(--border)" } : undefined}
    >
      <ProductImage src={p.image} title={p.title} />

      <div className="flex-1 min-w-0">
        <div className="flex items-center gap-1.5">
          <p className="text-sm font-medium truncate" style={{ color: "var(--text)" }}>
            {p.title || "Untitled"}
          </p>
          {p.product_url && (
            <a
              href={p.product_url}
              target="_blank"
              rel="noopener noreferrer"
              className="shrink-0 opacity-40 hover:opacity-100 transition-opacity"
            >
              <ExternalLink className="w-3 h-3" style={{ color: "var(--muted)" }} />
            </a>
          )}
        </div>

        <div className="flex items-center gap-2 mt-0.5 flex-wrap">
          <span className="text-xs" style={{ color: "var(--muted)" }}>
            {formatPrice(p.price_min)}
          </span>
          {deepVars && (
            <span
              className="text-[10px] px-1.5 py-0.5 rounded-md font-medium"
              style={{ background: "rgba(255,178,36,0.12)", color: "var(--accent)" }}
            >
              {p.variants_count} variants
            </span>
          )}
          {!p.available && (
            <span
              className="text-[10px] px-1.5 py-0.5 rounded-md"
              style={{ background: "rgba(242,85,90,0.08)", color: "#F2555A" }}
            >
              OOS
            </span>
          )}
        </div>
      </div>

      <span
        className="text-[10px] font-medium px-2 py-1 rounded-full shrink-0"
        style={ageBadgeStyle}
      >
        {p.age_days != null ? `${p.age_days}d ago` : "—"}
      </span>
    </div>
  );
}

// ── main component ───────────────────────────────────────────────────────────

export default function WinningProductsTab({ competitorId }: { competitorId: string }) {
  const [data,        setData]        = useState<WinningProductsResponse | null>(null);
  const [loading,     setLoading]     = useState(true);
  const [upgradeOpen, setUpgradeOpen] = useState(false);
  const [view,        setView]        = useState<"winners" | "launches">("winners");
  const [activeFilters, setActiveFilters] = useState<Set<FilterKey>>(new Set());
  const [sort,        setSort]        = useState<SortKey>("score");
  const [expandedHandle, setExpandedHandle] = useState<string | null>(null);
  const [pinnedMap, setPinnedMap] = useState<Record<string, string>>({}); // handle -> watch id

  useEffect(() => {
    api.winningProducts(competitorId)
      .then((r) => setData(r.data))
      .catch(() => {})
      .finally(() => setLoading(false));
  }, [competitorId]);

  const loadPins = useCallback(() => {
    watchlistApi.list()
      .then((r) => {
        const m: Record<string, string> = {};
        (r.data || [])
          .filter((w) => w.competitor_id === competitorId)
          .forEach((w) => { m[w.handle] = w.id; });
        setPinnedMap(m);
      })
      .catch(() => {});
  }, [competitorId]);

  useEffect(() => { loadPins(); }, [loadPins]);

  async function togglePin(p: WinningProduct) {
    const handle = p.handle;
    if (!handle) return;
    const existingId = pinnedMap[handle];
    if (existingId) {
      setPinnedMap((prev) => { const n = { ...prev }; delete n[handle]; return n; });
      await watchlistApi.remove(existingId).catch(() => loadPins());
      return;
    }
    try {
      await watchlistApi.add({
        competitor_id: competitorId,
        product_handle: handle,
        product_title: p.title,
        product_url: p.product_url,
        pinned_price: p.price_min ?? null,
      });
      loadPins();
    } catch (e: unknown) {
      const detail = (e as { data?: { detail?: { code?: string } } })?.data?.detail;
      if (detail?.code === "watchlist_limit_reached") setUpgradeOpen(true);
    }
  }

  const toggleFilter = (key: FilterKey) => {
    setActiveFilters((prev) => {
      const next = new Set(prev);
      next.has(key) ? next.delete(key) : next.add(key);
      return next;
    });
    setExpandedHandle(null);
  };

  const filteredProducts = useMemo(() => {
    if (!data) return [];
    let list = [...data.products];

    if (activeFilters.has("worth_testing")) list = list.filter((p) => p.score >= 75);
    if (activeFilters.has("watch_first"))   list = list.filter((p) => p.score >= 50 && p.score < 75);
    if (activeFilters.has("full_price"))    list = list.filter((p) => !p.discounted);
    if (activeFilters.has("in_stock"))      list = list.filter((p) => p.available);
    if (activeFilters.has("new_launch"))    list = list.filter((p) => (p.age_days ?? 999) <= 30);

    if (sort === "newest")    list.sort((a, b) => (a.age_days ?? 9999) - (b.age_days ?? 9999));
    if (sort === "price_asc") list.sort((a, b) => (a.price_min ?? 0) - (b.price_min ?? 0));
    if (sort === "price_desc")list.sort((a, b) => (b.price_min ?? 0) - (a.price_min ?? 0));

    return list;
  }, [data, activeFilters, sort]);

  if (loading) {
    return (
      <div className="space-y-3">
        {[1, 2, 3, 4].map((i) => (
          <div key={i} className="h-14 rounded-md animate-pulse" style={{ background: "var(--bg-card)" }} />
        ))}
      </div>
    );
  }

  if (!data || data.products.length === 0) {
    return (
      <div
        className="rounded-md p-8 text-center"
        style={{ background: "var(--bg-card)", border: "1px solid var(--border)" }}
      >
        <p style={{ color: "var(--muted)" }}>
          No products to score yet — check back after the next scan.
        </p>
      </div>
    );
  }

  const launches = data.newest || [];

  // Verdict summary counts for the header
  const worthCount = data.products.filter((p) => !p.locked && p.score >= 75).length;
  const watchCount = data.products.filter((p) => !p.locked && p.score >= 50 && p.score < 75).length;

  return (
    <div className="space-y-4">

      {/* ── Header + view switcher ─────────────────────────────────────────── */}
      <div className="flex items-start justify-between gap-3">
        <div>
          <h3 className="font-semibold" style={{ color: "var(--text)" }}>
            Should you test these products?
          </h3>
          <p className="text-xs mt-0.5" style={{ color: "var(--muted)" }}>
            {worthCount > 0 && (
              <span style={{ color: "#FFB224" }}>{worthCount} worth testing</span>
            )}
            {worthCount > 0 && watchCount > 0 && <span> · </span>}
            {watchCount > 0 && (
              <span style={{ color: "var(--amber)" }}>{watchCount} to watch</span>
            )}
            {worthCount === 0 && watchCount === 0 && (
              <span>{data.products.length} products scored</span>
            )}
            {" · "}click a row for reasoning
          </p>
        </div>

        <div
          className="flex items-center rounded-md p-0.5 shrink-0"
          style={{ background: "var(--bg3)" }}
        >
          <button
            onClick={() => setView("winners")}
            className="flex items-center gap-1.5 px-3 py-1.5 rounded-lg text-xs font-medium transition-all"
            style={{
              background: view === "winners" ? "var(--bg-card)" : undefined,
              color: view === "winners" ? "var(--text)" : "var(--muted)",
            }}
          >
            <Trophy className="w-3.5 h-3.5" />
            Winners
          </button>
          <button
            onClick={() => setView("launches")}
            className="flex items-center gap-1.5 px-3 py-1.5 rounded-lg text-xs font-medium transition-all"
            style={{
              background: view === "launches" ? "var(--bg-card)" : undefined,
              color: view === "launches" ? "var(--text)" : "var(--muted)",
            }}
          >
            <Flame className="w-3.5 h-3.5" />
            Launches
            {launches.length > 0 && (
              <span
                className="text-[9px] px-1 py-0.5 rounded-full font-bold leading-none"
                style={{ background: "rgba(255,178,36,0.15)", color: "var(--accent)" }}
              >
                {launches.length}
              </span>
            )}
          </button>
        </div>
      </div>

      {/* ── Winners view ───────────────────────────────────────────────────── */}
      {view === "winners" && (
        <>
          {/* Filter + sort bar */}
          <div className="flex items-center gap-1.5 flex-wrap">
            {FILTERS.map((f) => {
              const on = activeFilters.has(f.key);
              return (
                <button
                  key={f.key}
                  onClick={() => toggleFilter(f.key)}
                  className="text-[11px] px-2.5 py-1 rounded-lg font-medium transition-all"
                  style={{
                    background: on ? "rgba(255,178,36,0.12)" : "var(--bg3)",
                    color: on ? "var(--accent)" : "var(--muted)",
                    border: on ? "1px solid rgba(255,178,36,0.22)" : "1px solid transparent",
                  }}
                >
                  {f.label}
                </button>
              );
            })}

            <div
              className="ml-auto flex items-center rounded-lg overflow-hidden"
              style={{ background: "var(--bg3)" }}
            >
              {SORTS.map((s) => (
                <button
                  key={s.key}
                  onClick={() => setSort(s.key)}
                  className="text-[11px] px-2.5 py-1 transition-colors"
                  style={{
                    color: sort === s.key ? "var(--text)" : "var(--muted)",
                    background: sort === s.key ? "rgba(255,255,255,0.06)" : undefined,
                  }}
                >
                  {s.label}
                </button>
              ))}
            </div>
          </div>

          {activeFilters.size > 0 && (
            <p className="text-xs" style={{ color: "var(--muted)" }}>
              {filteredProducts.length} of {data.products.length} products match
              {" "}
              <button
                onClick={() => setActiveFilters(new Set())}
                className="underline hover:no-underline"
                style={{ color: "var(--accent)" }}
              >
                clear
              </button>
            </p>
          )}

          <div
            className="rounded-md overflow-hidden"
            style={{ background: "var(--bg-card)", border: "1px solid var(--border)" }}
          >
            {filteredProducts.length === 0 ? (
              <div className="p-8 text-center">
                <p className="text-sm" style={{ color: "var(--muted)" }}>
                  No products match these filters.
                </p>
              </div>
            ) : (
              filteredProducts.map((p, i) => {
                const handle = p.handle || String(i);
                return (
                  <WinnerRow
                    key={handle}
                    product={p}
                    rank={i + 1}
                    isLast={i === filteredProducts.length - 1 && !data.locked}
                    expanded={expandedHandle === handle}
                    onToggle={() =>
                      setExpandedHandle(expandedHandle === handle ? null : handle)
                    }
                    pinned={!!p.handle && !!pinnedMap[p.handle]}
                    onPin={() => togglePin(p)}
                  />
                );
              })
            )}

            {data.locked && data.locked_count > 0 && (
              <div className="p-4" style={{ borderTop: "1px solid var(--border)" }}>
                <LockedValueCard
                  title={`${data.locked_count} more products scored`}
                  teaser="Unlock the full ranking with Worth Testing / Watch First verdicts across every product."
                  plan="pro"
                />
              </div>
            )}
          </div>

          {/* Verdict legend */}
          <div className="flex items-center gap-4 text-[11px]" style={{ color: "var(--muted)" }}>
            <span className="flex items-center gap-1.5">
              <span className="w-2 h-2 rounded-full inline-block" style={{ background: "#FFB224" }} />
              Worth Testing — score ≥ 75
            </span>
            <span className="flex items-center gap-1.5">
              <span className="w-2 h-2 rounded-full inline-block" style={{ background: "var(--amber)" }} />
              Watch First — score 50–74
            </span>
            <span className="flex items-center gap-1.5">
              <span className="w-2 h-2 rounded-full inline-block" style={{ background: "#A8AC9E" }} />
              Skip — score &lt; 50
            </span>
          </div>
        </>
      )}

      {/* ── Launches view ──────────────────────────────────────────────────── */}
      {view === "launches" && (
        <div className="space-y-3">
          <div
            className="rounded-md px-4 py-3 flex items-start gap-3"
            style={{ background: "var(--bg3)", border: "1px solid var(--border)" }}
          >
            <Sparkles className="w-4 h-4 mt-0.5 shrink-0" style={{ color: "var(--muted)" }} />
            <p className="text-xs leading-relaxed" style={{ color: "var(--muted)" }}>
              <span style={{ color: "var(--text-2)" }}>A recent launch with deep variants signals real conviction.</span>
              {" "}If it stays listed past 30 days, the category has demand. New launches from established brands
              are worth adding to your product research list before they build momentum.
            </p>
          </div>

          <div
            className="rounded-md overflow-hidden"
            style={{ background: "var(--bg-card)", border: "1px solid var(--border)" }}
          >
            {launches.length === 0 ? (
              <div className="p-8 text-center">
                <p className="text-sm" style={{ color: "var(--muted)" }}>
                  No recent launches detected yet.
                </p>
              </div>
            ) : (
              launches.map((p, i) => (
                <LaunchRow key={i} p={p} isLast={i === launches.length - 1} />
              ))
            )}
          </div>

          <div className="flex items-center gap-4 text-[11px]" style={{ color: "var(--muted)" }}>
            <span className="flex items-center gap-1.5">
              <span className="w-2 h-2 rounded-full inline-block" style={{ background: "#FFB224" }} />
              ≤ 7 days
            </span>
            <span className="flex items-center gap-1.5">
              <span className="w-2 h-2 rounded-full inline-block" style={{ background: "var(--amber)" }} />
              8–30 days
            </span>
            <span className="flex items-center gap-1.5">
              <span className="w-2 h-2 rounded-full inline-block" style={{ background: "var(--muted)" }} />
              30+ days
            </span>
          </div>
        </div>
      )}

      <UpgradeModal open={upgradeOpen} onClose={() => setUpgradeOpen(false)} trigger="general" />
    </div>
  );
}
