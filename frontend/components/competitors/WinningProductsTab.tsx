"use client";

import { useEffect, useState, useMemo } from "react";
import {
  Lock, Trophy, Sparkles, ExternalLink, Copy, Check,
  ChevronDown, ChevronUp, Flame, Clock, Layers, Tag,
  ShoppingBag, Image as ImageIcon,
} from "lucide-react";
import {
  competitors as api,
  type WinningProductsResponse,
  type WinningProduct,
  type NewestProduct,
} from "@/lib/api";
import { formatPrice } from "@/lib/utils";
import UpgradeModal from "@/components/UpgradeModal";

// ── signal config ────────────────────────────────────────────────────────────

const SIGNALS: {
  key: string;
  label: string;
  icon: React.ElementType;
  color: string;
  desc: string;
}[] = [
  { key: "longevity",            label: "Longevity",    icon: Clock,      color: "#60a5fa", desc: "Still in catalog — survived market test" },
  { key: "variant_depth",        label: "Variants",     icon: Layers,     color: "#a78bfa", desc: "Option depth = seller's investment signal" },
  { key: "full_price_confidence",label: "Full price",   icon: Tag,        color: "#34d399", desc: "Sells without relying on markdowns" },
  { key: "availability",         label: "In stock",     icon: ShoppingBag,color: "#a3f000", desc: "Active inventory = still reordering it" },
  { key: "image_investment",     label: "Imagery",      icon: ImageIcon,  color: "#fb923c", desc: "Merchandising effort on the listing" },
];

function scoreColor(score: number) {
  if (score >= 75) return "#a3f000";
  if (score >= 50) return "#facc15";
  return "#94a3b8";
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
        ? <Check className="w-3 h-3" style={{ color: "#a3f000" }} />
        : <Copy className="w-3 h-3" style={{ color: "var(--muted)" }} />}
    </button>
  );
}

function SignalBar({ value, color }: { value: number; color: string }) {
  return (
    <div
      className="flex-1 h-1.5 rounded-full overflow-hidden"
      style={{ background: "rgba(255,255,255,0.07)" }}
    >
      <div
        className="h-full rounded-full"
        style={{ width: `${Math.round(value * 100)}%`, background: color }}
      />
    </div>
  );
}

// ── winner row ───────────────────────────────────────────────────────────────

interface WinnerRowProps {
  product: WinningProduct;
  rank: number;
  expanded: boolean;
  onToggle: () => void;
  isLast: boolean;
}

function WinnerRow({ product, rank, expanded, onToggle, isLast }: WinnerRowProps) {
  const color = scoreColor(product.score);

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
          {/* Title line */}
          <div className="flex items-center gap-1.5">
            <p
              className="text-sm font-medium truncate"
              style={{ color: "var(--text)" }}
            >
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
          </div>

          {/* Meta chips */}
          <div className="flex items-center gap-2 mt-0.5 flex-wrap">
            <span className="text-xs" style={{ color: "var(--muted)" }}>
              {formatPrice(product.price_min)}
            </span>

            {product.locked ? (
              <span
                className="text-[10px] px-1.5 py-0.5 rounded-md"
                style={{ background: "rgba(168,255,0,0.08)", color: "var(--accent)" }}
              >
                Upgrade to see signals
              </span>
            ) : (
              <>
                {product.discounted && product.discount_pct ? (
                  <span
                    className="text-[10px] px-1.5 py-0.5 rounded-md font-medium"
                    style={{ background: "rgba(239,68,68,0.12)", color: "#f87171" }}
                  >
                    {Math.round(product.discount_pct)}% off
                  </span>
                ) : (
                  <span
                    className="text-[10px] px-1.5 py-0.5 rounded-md font-medium"
                    style={{ background: "rgba(52,211,153,0.10)", color: "#34d399" }}
                  >
                    Full price
                  </span>
                )}

                {product.age_days != null && (
                  <span className="text-[10px]" style={{ color: "var(--muted)" }}>
                    {ageDaysLabel(product.age_days)}
                  </span>
                )}

                {(product.variants_count ?? 0) > 1 && (
                  <span className="text-[10px]" style={{ color: "var(--muted)" }}>
                    {product.variants_count}v
                  </span>
                )}

                {!product.available && (
                  <span
                    className="text-[10px] px-1.5 py-0.5 rounded-md"
                    style={{ background: "rgba(239,68,68,0.08)", color: "#f87171" }}
                  >
                    OOS
                  </span>
                )}
              </>
            )}
          </div>
        </div>

        {/* Score + expand toggle */}
        <div className="flex items-center gap-1.5 shrink-0">
          <span className="text-base font-bold font-mono" style={{ color }}>
            {product.score}
          </span>
          <span className="text-[10px]" style={{ color: "var(--muted)" }}>/100</span>
          {!product.locked && (
            expanded
              ? <ChevronUp className="w-3.5 h-3.5 ml-0.5" style={{ color: "var(--muted)" }} />
              : <ChevronDown
                  className="w-3.5 h-3.5 ml-0.5 opacity-0 group-hover:opacity-100 transition-opacity"
                  style={{ color: "var(--muted)" }}
                />
          )}
        </div>
      </div>

      {/* Signal breakdown — shown when expanded */}
      {expanded && !product.locked && (
        <div
          className="px-4 pb-4 pt-0"
          style={{ borderTop: "1px solid rgba(255,255,255,0.05)", marginLeft: 52 }}
        >
          <p
            className="text-[10px] font-semibold uppercase tracking-wider pt-3 pb-2.5"
            style={{ color: "var(--muted)" }}
          >
            Signal breakdown — why it scored {product.score}
          </p>
          <div className="space-y-2">
            {SIGNALS.map((sig) => {
              const value = product.signals?.[sig.key] ?? 0;
              const Icon = sig.icon;
              return (
                <div key={sig.key} className="flex items-center gap-2.5" title={sig.desc}>
                  <Icon className="w-3 h-3 shrink-0" style={{ color: sig.color, opacity: 0.7 }} />
                  <span
                    className="text-[11px] w-20 shrink-0"
                    style={{ color: "var(--muted)" }}
                  >
                    {sig.label}
                  </span>
                  <SignalBar value={value} color={sig.color} />
                  <span
                    className="text-[11px] w-5 text-right font-mono shrink-0"
                    style={{ color: sig.color }}
                  >
                    {Math.round(value * 10)}
                  </span>
                </div>
              );
            })}
          </div>
          {product.reason && (
            <p className="text-xs mt-3 leading-relaxed" style={{ color: "var(--muted)" }}>
              {product.reason}
            </p>
          )}
        </div>
      )}
    </div>
  );
}

// ── filter / sort types ──────────────────────────────────────────────────────

type FilterKey = "full_price" | "in_stock" | "deep_variants" | "long_running" | "new_launch";
type SortKey   = "score" | "newest" | "price_asc" | "price_desc";

const FILTERS: { key: FilterKey; label: string }[] = [
  { key: "full_price",    label: "Full price" },
  { key: "in_stock",     label: "In stock" },
  { key: "deep_variants",label: "10+ variants" },
  { key: "long_running", label: "6mo+ catalog" },
  { key: "new_launch",   label: "New (<30d)" },
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
  if (isVeryNew)   ageBadgeStyle = { background: "rgba(168,255,0,0.15)", color: "#a3f000" };
  else if (isNew)  ageBadgeStyle = { background: "rgba(251,191,36,0.10)", color: "#fbbf24" };
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
              style={{ background: "rgba(167,139,250,0.12)", color: "#a78bfa" }}
            >
              {p.variants_count} variants
            </span>
          )}
          {!p.available && (
            <span
              className="text-[10px] px-1.5 py-0.5 rounded-md"
              style={{ background: "rgba(239,68,68,0.08)", color: "#f87171" }}
            >
              OOS
            </span>
          )}
        </div>
      </div>

      {/* Age badge */}
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

  useEffect(() => {
    api.winningProducts(competitorId)
      .then((r) => setData(r.data))
      .catch(() => {})
      .finally(() => setLoading(false));
  }, [competitorId]);

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

    if (activeFilters.has("full_price"))    list = list.filter((p) => !p.discounted);
    if (activeFilters.has("in_stock"))      list = list.filter((p) => p.available);
    if (activeFilters.has("deep_variants")) list = list.filter((p) => (p.variants_count ?? 0) >= 10);
    if (activeFilters.has("long_running"))  list = list.filter((p) => (p.age_days ?? 0) >= 180);
    if (activeFilters.has("new_launch"))    list = list.filter((p) => (p.age_days ?? 999) <= 30);

    if (sort === "newest")    list.sort((a, b) => (a.age_days ?? 9999) - (b.age_days ?? 9999));
    if (sort === "price_asc") list.sort((a, b) => (a.price_min ?? 0) - (b.price_min ?? 0));
    if (sort === "price_desc")list.sort((a, b) => (b.price_min ?? 0) - (a.price_min ?? 0));
    // "score" keeps backend order

    return list;
  }, [data, activeFilters, sort]);

  // ── loading ──
  if (loading) {
    return (
      <div className="space-y-3">
        {[1, 2, 3, 4].map((i) => (
          <div key={i} className="h-14 rounded-xl animate-pulse" style={{ background: "var(--bg-card)" }} />
        ))}
      </div>
    );
  }

  if (!data || data.products.length === 0) {
    return (
      <div
        className="rounded-2xl p-8 text-center"
        style={{ background: "var(--bg-card)", border: "1px solid var(--border)" }}
      >
        <p style={{ color: "var(--muted)" }}>
          No products to score yet — check back after the next scan.
        </p>
      </div>
    );
  }

  const launches = data.newest || [];

  return (
    <div className="space-y-4">

      {/* ── Header + view switcher ─────────────────────────────────────────── */}
      <div className="flex items-start justify-between gap-3">
        <div>
          <h3 className="font-semibold" style={{ color: "var(--text)" }}>
            Product Intelligence
          </h3>
          <p className="text-xs mt-0.5" style={{ color: "var(--muted)" }}>
            {data.products.length} products scored · click a row to see signal breakdown
          </p>
        </div>

        <div
          className="flex items-center rounded-xl p-0.5 shrink-0"
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
                style={{ background: "rgba(168,255,0,0.15)", color: "var(--accent)" }}
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
                    background: on ? "rgba(168,255,0,0.12)" : "var(--bg3)",
                    color: on ? "var(--accent)" : "var(--muted)",
                    border: on ? "1px solid rgba(168,255,0,0.22)" : "1px solid transparent",
                  }}
                >
                  {f.label}
                </button>
              );
            })}

            {/* Sort */}
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

          {/* Result count when filters active */}
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

          {/* Product list */}
          <div
            className="rounded-2xl overflow-hidden"
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
                  />
                );
              })
            )}

            {/* Locked CTA */}
            {data.locked && data.locked_count > 0 && (
              <div
                className="px-5 py-5 text-center"
                style={{
                  background: "rgba(163,240,0,.04)",
                  borderTop: "1px dashed rgba(163,240,0,.2)",
                }}
              >
                <Lock className="w-4 h-4 mx-auto mb-2" style={{ color: "#a3f000" }} />
                <p className="text-sm font-medium mb-0.5" style={{ color: "var(--text)" }}>
                  {data.locked_count} more products scored
                </p>
                <p className="text-xs mb-3" style={{ color: "var(--muted)" }}>
                  Unlock the full ranking, signal breakdown, and filter controls.
                </p>
                <button
                  onClick={() => setUpgradeOpen(true)}
                  className="font-semibold text-sm px-5 py-2 rounded-xl transition-all hover:brightness-110"
                  style={{ background: "#a3f000", color: "#060d18" }}
                >
                  Unlock all products
                </button>
              </div>
            )}
          </div>

          {/* Signal legend */}
          {!data.locked && (
            <div className="flex flex-wrap gap-3 pt-1">
              {SIGNALS.map((sig) => {
                const Icon = sig.icon;
                return (
                  <span
                    key={sig.key}
                    className="flex items-center gap-1.5 text-[11px]"
                    style={{ color: "var(--muted)" }}
                    title={sig.desc}
                  >
                    <Icon className="w-3 h-3" style={{ color: sig.color }} />
                    {sig.label}
                  </span>
                );
              })}
            </div>
          )}
        </>
      )}

      {/* ── Launches view ──────────────────────────────────────────────────── */}
      {view === "launches" && (
        <div className="space-y-3">
          {/* Context callout */}
          <div
            className="rounded-xl px-4 py-3 flex items-start gap-3"
            style={{ background: "rgba(96,165,250,0.07)", border: "1px solid rgba(96,165,250,0.15)" }}
          >
            <Sparkles className="w-4 h-4 mt-0.5 shrink-0" style={{ color: "#60a5fa" }} />
            <p className="text-xs leading-relaxed" style={{ color: "var(--muted)" }}>
              <span style={{ color: "#e2e8f0" }}>Established brands validate products before listing.</span>
              {" "}A recent launch with high variant depth or full-price confidence signals they have conviction —
              watch whether it sticks or disappears. New products from a fast-growing competitor are a category
              move worth noting.
            </p>
          </div>

          {/* Launch list */}
          <div
            className="rounded-2xl overflow-hidden"
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

          {/* Age legend */}
          <div className="flex items-center gap-4 text-[11px]" style={{ color: "var(--muted)" }}>
            <span className="flex items-center gap-1.5">
              <span className="w-2 h-2 rounded-full inline-block" style={{ background: "#a3f000" }} />
              ≤ 7 days
            </span>
            <span className="flex items-center gap-1.5">
              <span className="w-2 h-2 rounded-full inline-block" style={{ background: "#fbbf24" }} />
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
