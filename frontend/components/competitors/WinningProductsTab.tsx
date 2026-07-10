"use client";

/**
 * Product Intelligence — the question this tab answers:
 * "Which of their products actually matter, and should I respond?"
 *
 * The tier system is deliberately scarce (backend-capped): a couple of Hero
 * Products, a handful of Strong Performers, a few Emerging Winners — and the
 * rest explicitly de-emphasized. Every act-on tier explains WHY it earned its
 * standing, what it reveals about the competitor's business, and how to
 * respond. Scarcity is what makes the intelligence trustworthy.
 */

import { useEffect, useState, useCallback } from "react";
import {
  Crown, TrendingUp, Sparkles, Eye, ExternalLink, Copy, Check,
  ChevronDown, ChevronUp, Bookmark, Trophy,
} from "lucide-react";
import { LockedValueCard } from "@/components/ui";
import {
  competitors as api,
  watchlist as watchlistApi,
  type WinningProductsResponse,
  type WinningProduct,
  type MarketContext,
} from "@/lib/api";
import { formatPrice } from "@/lib/utils";
import UpgradeModal from "@/components/UpgradeModal";
import { SaveToPlaybook } from "@/components/SaveToPlaybook";

// ── Tier language ────────────────────────────────────────────────────────────

type Tier = "hero" | "strong" | "emerging" | "monitor" | "ignore";

const TIER_META: Record<Tier, { label: string; color: string; Icon: React.ElementType; desc: string }> = {
  hero:     { label: "Hero Products",     color: "#FFB224", Icon: Crown,      desc: "Load-bearing revenue — proven, defended, built around" },
  strong:   { label: "Strong Performers", color: "#4CC38A", Icon: TrendingUp, desc: "Dependable sellers — real revenue, but not their identity" },
  emerging: { label: "Emerging Winners",  color: "#7DB8C9", Icon: Sparkles,   desc: "Fresh launches they're backing — let them pay for the market test" },
  monitor:  { label: "Monitor",           color: "#A8AC9E", Icon: Eye,        desc: "Nothing decisive yet — signals haven't separated these from the pack" },
  ignore:   { label: "Filtered out",      color: "#6C7164", Icon: Eye,        desc: "Structurally weak — discounted, shallow, or unstocked" },
};

const TIER_ORDER: Tier[] = ["hero", "strong", "emerging", "monitor", "ignore"];

/**
 * Legacy fallback for snapshots scanned before the tier system: derive a
 * CONSERVATIVE tier from the score. Deliberately never assigns "hero" —
 * heroes require gates the client can't verify, and over-promoting is
 * exactly the trust bug this redesign kills.
 */
function fallbackTier(p: WinningProduct, rank: number): Tier {
  if (p.score >= 78 && rank < 5) return "strong";
  if (p.score >= 55) return "monitor";
  return "ignore";
}

function ageDaysLabel(days: number) {
  if (days < 30) return `${days}d`;
  if (days < 365) return `${Math.round(days / 30)}mo`;
  return `${(days / 365).toFixed(1)}yr`;
}

// ── Small pieces ─────────────────────────────────────────────────────────────

function ProductImage({ src, title, size = 44 }: { src?: string | null; title?: string; size?: number }) {
  if (!src) {
    return (
      <div className="rounded-lg shrink-0 flex items-center justify-center" style={{ width: size, height: size, background: "var(--bg3)" }}>
        <Trophy className="w-4 h-4" style={{ color: "var(--muted)" }} />
      </div>
    );
  }
  // eslint-disable-next-line @next/next/no-img-element
  return (
    <img src={src} alt={title || ""} className="rounded-lg object-cover shrink-0" style={{ width: size, height: size, background: "var(--bg3)" }} />
  );
}

function CopyButton({ text }: { text: string }) {
  const [copied, setCopied] = useState(false);
  return (
    <button
      onClick={(e) => {
        e.stopPropagation();
        navigator.clipboard.writeText(text).catch(() => {});
        setCopied(true);
        setTimeout(() => setCopied(false), 1500);
      }}
      title="Copy product name"
      className="opacity-0 group-hover:opacity-60 hover:!opacity-100 shrink-0 transition-opacity p-0.5 rounded"
    >
      {copied ? <Check className="w-3 h-3" style={{ color: "#4CC38A" }} /> : <Copy className="w-3 h-3" style={{ color: "var(--muted)" }} />}
    </button>
  );
}

// ── Product row (all tiers share it; heroes get the rich treatment) ─────────

function ProductRow({
  product, tier, competitorId, expanded, onToggle, isLast, pinned, onPin, market,
}: {
  product: WinningProduct;
  tier: Tier;
  competitorId: string;
  expanded: boolean;
  onToggle: () => void;
  isLast: boolean;
  pinned: boolean;
  onPin: () => void;
  market?: MarketContext | null;
}) {
  const meta = TIER_META[tier];
  const why = product.why?.length ? product.why : (product.reason ? [product.reason] : []);

  return (
    <div
      className="group cursor-pointer transition-colors hover:bg-white/[0.015]"
      style={!isLast ? { borderBottom: "1px solid var(--border)" } : undefined}
      onClick={onToggle}
    >
      <div className="flex items-center gap-3 px-4 py-3">
        <ProductImage src={product.image} title={product.title} size={tier === "hero" ? 48 : 40} />
        <div className="flex-1 min-w-0">
          <div className="flex items-center gap-1.5">
            <p className={`${tier === "hero" ? "text-sm font-semibold" : "text-sm font-medium"} truncate`} style={{ color: "var(--text)" }}>
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
              title={pinned ? "Stop watching" : "Watch this product for price/stock changes"}
              className={`shrink-0 p-0.5 rounded transition-opacity ${pinned ? "opacity-100" : "opacity-0 group-hover:opacity-60 hover:!opacity-100"}`}
            >
              <Bookmark className="w-3 h-3" style={{ color: pinned ? "var(--accent)" : "var(--muted)", fill: pinned ? "var(--accent)" : "none" }} />
            </button>
          </div>
          <p className="num text-[11px] mt-0.5" style={{ color: "var(--muted)" }}>
            {[
              product.price_min != null && formatPrice(product.price_min),
              product.age_days != null && ageDaysLabel(product.age_days),
              (product.variants_count ?? 0) > 1 && `${product.variants_count} variants`,
              product.discounted ? `${Math.round(product.discount_pct ?? 0)}% off` : "full price",
              product.premium_position && "premium-priced",
              product.cross_sell && "bundle",
            ].filter(Boolean).join(" · ")}
          </p>
        </div>
        <span className="num text-xs font-bold shrink-0" style={{ color: meta.color }}>{product.score}</span>
        {expanded
          ? <ChevronUp className="w-3.5 h-3.5 shrink-0" style={{ color: "var(--muted)" }} />
          : <ChevronDown className="w-3.5 h-3.5 shrink-0 opacity-0 group-hover:opacity-100 transition-opacity" style={{ color: "var(--muted)" }} />}
      </div>

      {expanded && (
        <div className="px-4 pb-4 space-y-3" style={{ marginLeft: 56 }} onClick={(e) => e.stopPropagation()}>
          {/* Why it earned this tier */}
          {why.length > 0 && (
            <div>
              <p className="label-caps mb-1.5" style={{ color: meta.color }}>Why it&apos;s a {meta.label.replace(/s$/, "").toLowerCase()}</p>
              <ul className="space-y-1">
                {why.map((r, i) => (
                  <li key={i} className="flex items-start gap-2">
                    <span className="mt-1.5 w-1 h-1 rounded-full shrink-0" style={{ background: meta.color }} />
                    <span className="text-xs leading-relaxed" style={{ color: "var(--text-2)" }}>{r}</span>
                  </li>
                ))}
              </ul>
            </div>
          )}

          {/* What it reveals about their business */}
          {product.reveals && (
            <div>
              <p className="label-caps mb-1">What this reveals</p>
              <p className="text-xs leading-relaxed" style={{ color: "var(--text-2)" }}>{product.reveals}</p>
            </div>
          )}

          {/* Should you respond, and how */}
          {product.respond && (
            <div className="rounded-md px-3 py-2.5" style={{ background: "var(--bg3)", border: "1px solid var(--border)" }}>
              <p className="label-caps mb-1" style={{ color: "var(--accent)" }}>Should you respond?</p>
              <p className="text-xs leading-relaxed" style={{ color: "var(--text)" }}>{product.respond}</p>
            </div>
          )}

          {/* Market research — verified index facts + clearly-labeled estimates */}
          {(tier === "hero" || tier === "strong" || tier === "emerging") && market?.category && (
            <div className="rounded-md px-3 py-2.5" style={{ background: "var(--bg3)", border: "1px solid var(--border)" }}>
              <p className="label-caps mb-1.5">Market research · {market.category}</p>
              <div className="space-y-1">
                <p className="text-xs leading-snug" style={{ color: "var(--text-2)" }}>
                  <span className="text-[10px] font-bold px-1 py-px rounded mr-1.5" style={{ background: "rgba(76,195,138,.12)", color: "#4CC38A" }}>VERIFIED</span>
                  {market.saturation} verified {market.category.toLowerCase()} store{market.saturation === 1 ? "" : "s"} in StoreScout&apos;s index
                  {market.peers.length > 0 && <> — closest peers: {market.peers.slice(0, 3).map((pr) => pr.brand_name || pr.domain).join(", ")}</>}
                </p>
                {product.price_min != null && (
                  <p className="text-xs leading-snug" style={{ color: "var(--text-2)" }}>
                    <span className="text-[10px] font-bold px-1 py-px rounded mr-1.5" style={{ background: "rgba(255,178,36,.12)", color: "var(--accent)" }}>ESTIMATED</span>
                    Typical wholesale for a {formatPrice(product.price_min)} retail product runs {formatPrice(product.price_min * 0.25)}–{formatPrice(product.price_min * 0.5)} (industry-standard 2–4× markup — verify with suppliers)
                  </p>
                )}
                <p className="text-xs leading-snug" style={{ color: "var(--muted)" }}>
                  <span className="text-[10px] font-bold px-1 py-px rounded mr-1.5" style={{ background: "rgba(125,184,201,.12)", color: "#7DB8C9" }}>GUIDANCE</span>
                  {market.saturation >= 15
                    ? "Crowded category — a me-too version won't cut through. Differentiate on audience, bundle, or service."
                    : "Sparse category in our index so far — early positioning is still winnable here."}
                </p>
              </div>
            </div>
          )}

          <div className="flex justify-end">
            <SaveToPlaybook
              size="xs"
              item={{
                source_type: "winning_product",
                source_ref: `${competitorId}:${product.handle ?? product.title ?? ""}`,
                competitor_id: competitorId,
                title: tier === "emerging"
                  ? `Re-check "${product.title || "this launch"}" in 60–90 days`
                  : `Respond to their ${tier} product "${product.title || ""}"`,
                reason: product.respond || product.reveals || `${TIER_META[tier].label} in their catalog`,
                evidence: why.slice(0, 3).join(" · "),
                priority: tier === "hero" ? "high" : "medium",
              }}
            />
          </div>
        </div>
      )}
    </div>
  );
}

// ── Tier section ─────────────────────────────────────────────────────────────

function TierSection({
  tier, products, competitorId, expandedHandle, onToggle, pinnedMap, onPin, collapsible, market,
}: {
  tier: Tier;
  products: WinningProduct[];
  competitorId: string;
  expandedHandle: string | null;
  onToggle: (h: string) => void;
  pinnedMap: Record<string, string>;
  onPin: (p: WinningProduct) => void;
  collapsible?: boolean;
  market?: MarketContext | null;
}) {
  const [open, setOpen] = useState(!collapsible);
  const meta = TIER_META[tier];
  const { Icon } = meta;
  if (products.length === 0) return null;

  return (
    <div>
      <button
        onClick={() => collapsible && setOpen(!open)}
        className={`w-full flex items-center gap-2 mb-2 text-left ${collapsible ? "cursor-pointer" : "cursor-default"}`}
      >
        <Icon className="w-3.5 h-3.5 shrink-0" style={{ color: meta.color }} />
        <span className="text-xs font-bold uppercase tracking-wider" style={{ color: meta.color }}>{meta.label}</span>
        <span className="num text-[10px] font-bold px-1.5 py-0.5 rounded-full" style={{ background: `${meta.color}18`, color: meta.color }}>
          {products.length}
        </span>
        <span className="text-[11px] flex-1 truncate" style={{ color: "var(--muted)" }}>— {meta.desc}</span>
        {collapsible && (open
          ? <ChevronUp className="w-3.5 h-3.5 shrink-0" style={{ color: "var(--muted)" }} />
          : <ChevronDown className="w-3.5 h-3.5 shrink-0" style={{ color: "var(--muted)" }} />)}
      </button>

      {open && (
        <div
          className="rounded-md overflow-hidden"
          style={{
            background: "var(--bg-card)",
            border: "1px solid var(--border)",
            borderLeft: tier === "hero" ? `3px solid ${meta.color}` : "1px solid var(--border)",
          }}
        >
          {products.map((p, i) => (
            <ProductRow
              key={p.handle || p.title || i}
              product={p}
              tier={tier}
              competitorId={competitorId}
              expanded={expandedHandle === (p.handle || p.title)}
              onToggle={() => onToggle(p.handle || p.title || "")}
              isLast={i === products.length - 1}
              pinned={!!p.handle && !!pinnedMap[p.handle]}
              onPin={() => onPin(p)}
              market={market}
            />
          ))}
        </div>
      )}
    </div>
  );
}

// ── Main tab ─────────────────────────────────────────────────────────────────

export default function WinningProductsTab({ competitorId }: { competitorId: string }) {
  const [data, setData] = useState<WinningProductsResponse | null>(null);
  const [loading, setLoading] = useState(true);
  const [upgradeOpen, setUpgradeOpen] = useState(false);
  const [expandedHandle, setExpandedHandle] = useState<string | null>(null);
  const [pinnedMap, setPinnedMap] = useState<Record<string, string>>({});
  const [market, setMarket] = useState<MarketContext | null>(null);

  useEffect(() => {
    api.winningProducts(competitorId)
      .then((r) => setData(r.data))
      .catch(() => {})
      .finally(() => setLoading(false));
    api.marketContext(competitorId)
      .then((r) => setMarket(r.data))
      .catch(() => {});
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
      <div className="rounded-md p-8 text-center" style={{ background: "var(--bg-card)", border: "1px solid var(--border)" }}>
        <p className="text-sm font-semibold mb-1" style={{ color: "var(--text)" }}>Scoring their catalog</p>
        <p className="text-sm max-w-sm mx-auto" style={{ color: "var(--muted)" }}>
          StoreScout ranks every product they sell into Hero / Strong / Emerging tiers — the ones worth
          responding to — as soon as the first full scan finishes. This fills in automatically; no need to refresh.
        </p>
      </div>
    );
  }

  // Group by tier. Snapshots from before the tier system get a conservative
  // client-side fallback (never "hero") and a notice that full tiers land
  // with the next scan.
  const hasServerTiers = data.products.some((p) => !!p.tier);
  const unlocked = data.products.filter((p) => !p.locked);
  const byTier: Record<Tier, WinningProduct[]> = { hero: [], strong: [], emerging: [], monitor: [], ignore: [] };
  unlocked.forEach((p, i) => {
    const t: Tier = (p.tier as Tier) || fallbackTier(p, i);
    byTier[t].push(p);
  });

  const actOnCount = byTier.hero.length + byTier.strong.length + byTier.emerging.length;

  return (
    <div className="space-y-5">

      {/* ── Header: the verdict, up front ──────────────────────────────────── */}
      <div>
        <h3 className="font-semibold" style={{ color: "var(--text)" }}>
          Which of their products actually matter?
        </h3>
        <p className="text-xs mt-0.5" style={{ color: "var(--muted)" }}>
          {actOnCount > 0 ? (
            <>
              <span style={{ color: "var(--text-2)" }}>
                {actOnCount} of {data.products.length} scored products earn attention
              </span>
              {" — the rest are deliberately filtered. Scarcity is the point: when everything is a winner, nothing is."}
            </>
          ) : (
            "Nothing in this catalog clears the bar right now — that itself is intelligence: no proven product to defend."
          )}
        </p>
        {!hasServerTiers && (
          <p className="text-[11px] mt-1.5 px-2.5 py-1.5 rounded inline-block" style={{ background: "var(--bg3)", color: "var(--muted)", border: "1px solid var(--border)" }}>
            Conservative provisional tiers — the full multi-signal tier analysis lands with the next scan.
          </p>
        )}
        {data.locked && (
          <p className="text-[11px] mt-1.5 px-2.5 py-1.5 rounded inline-block" style={{ background: "rgba(255,178,36,.08)", color: "var(--text-2)", border: "1px solid rgba(255,178,36,.2)" }}>
            Free preview — the top few products with live scores. Full Hero/Strong/Emerging tiering, the &ldquo;why&rdquo; behind each, and how to respond come with Pro (and sharpen as scan history builds).
          </p>
        )}
      </div>

      {/* ── Tiers, scarcest first ──────────────────────────────────────────── */}
      <div className="space-y-6">
        {TIER_ORDER.map((tier) => (
          <TierSection
            key={tier}
            tier={tier}
            products={byTier[tier]}
            competitorId={competitorId}
            expandedHandle={expandedHandle}
            onToggle={(h) => setExpandedHandle(expandedHandle === h ? null : h)}
            pinnedMap={pinnedMap}
            onPin={togglePin}
            collapsible={tier === "monitor" || tier === "ignore"}
            market={market}
          />
        ))}
      </div>

      {/* Free-tier gate — unchanged economics, honest count */}
      {data.locked && data.locked_count > 0 && (
        <LockedValueCard
          title={`${data.locked_count} more products analyzed`}
          teaser="Unlock the full tier analysis — Hero Products, Emerging Winners, and how to respond to each."
          plan="pro"
        />
      )}

      <UpgradeModal open={upgradeOpen} onClose={() => setUpgradeOpen(false)} />
    </div>
  );
}
