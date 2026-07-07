"use client";

import { Suspense, useEffect, useState } from "react";
import { useSearchParams } from "next/navigation";
import Link from "next/link";
import {
  competitors as competitorsApi, user as userApi, myStore as myStoreApi, shopify as shopifyApi,
  getCachedCompetitors,
  type Competitor, type UserSubscription, type ShopifyConnection, type AIDiscoverySuggestion,
} from "@/lib/api";
import { cn, formatPrice } from "@/lib/utils";
import { AddCompetitorModal } from "@/components/competitors/AddCompetitorModal";
import UpgradeModal from "@/components/UpgradeModal";
import {
  Store, X, Loader2, Check, Plus, RefreshCw, Target, Zap, ArrowRight,
  Package, Tag, Search, Sparkles,
} from "lucide-react";

// ── Discovery pipeline progress ───────────────────────────────────────────
// Honest stage narration for the discover-ai request: the backend really does
// these three things in order (business context → Claude ecosystem mapping →
// per-domain Shopify verification with refill batches).

const DISCOVERY_STAGES = [
  { label: "Analyzing your business", after: 0 },
  { label: "Mapping your competitor ecosystem", after: 2500 },
  { label: "Verifying Shopify storefronts", after: 7000 },
];

function DiscoveryProgress() {
  const [elapsed, setElapsed] = useState(0);
  useEffect(() => {
    const start = Date.now();
    const t = setInterval(() => setElapsed(Date.now() - start), 500);
    return () => clearInterval(t);
  }, []);

  return (
    <div
      className="mt-4 px-4 py-3 rounded-md space-y-2 analyzing-sweep"
      style={{ background: "var(--bg3)", border: "1px solid var(--border)" }}
    >
      {DISCOVERY_STAGES.map((s, i) => {
        const active = elapsed >= s.after && (i === DISCOVERY_STAGES.length - 1 || elapsed < DISCOVERY_STAGES[i + 1].after);
        const done = i < DISCOVERY_STAGES.length - 1 && elapsed >= DISCOVERY_STAGES[i + 1].after;
        const pending = elapsed < s.after;
        return (
          <div key={s.label} className="flex items-center gap-2.5 text-xs" style={{ opacity: pending ? 0.4 : 1 }}>
            {done ? (
              <Check className="w-3.5 h-3.5 shrink-0" style={{ color: "var(--emerald)" }} />
            ) : active ? (
              <Loader2 className="w-3.5 h-3.5 shrink-0 animate-spin" style={{ color: "var(--accent)" }} />
            ) : (
              <span className="w-3.5 h-3.5 shrink-0 rounded-full" style={{ border: "1px solid var(--border)" }} />
            )}
            <span style={{ color: done ? "var(--muted)" : "var(--text-2)" }}>{s.label}</span>
            {active && i === 2 && (
              <span style={{ color: "var(--muted)" }}>— checking each candidate, this can take up to a minute</span>
            )}
          </div>
        );
      })}
    </div>
  );
}

// ── Favicon logo ──────────────────────────────────────────────────────────

function FaviconLogo({ hostname, size = 44 }: { hostname: string; size?: number }) {
  const [imgError, setImgError] = useState(false);
  const initials = hostname.replace(/\..*/, "").slice(0, 2).toUpperCase();
  const hue = hostname.split("").reduce((a, c) => a + c.charCodeAt(0), 0) % 360;

  if (imgError) {
    return (
      <div
        className="rounded-md flex items-center justify-center font-bold shrink-0"
        style={{
          width: size,
          height: size,
          fontSize: Math.round(size * 0.35),
          background: `hsl(${hue},35%,18%)`,
          color: `hsl(${hue},60%,65%)`,
          border: "1px solid var(--border)",
        }}
      >
        {initials}
      </div>
    );
  }

  return (
    <img
      src={`https://www.google.com/s2/favicons?domain=${hostname}&sz=64`}
      onError={() => setImgError(true)}
      alt=""
      className="rounded-md object-contain shrink-0"
      style={{
        width: size,
        height: size,
        background: "var(--bg3)",
        border: "1px solid var(--border)",
        padding: 6,
      }}
    />
  );
}

// ── Stat cell ──────────────────────────────────────────────────────────────

function StatCell({ label, value }: { label: string; value: string }) {
  return (
    <div>
      <p className="text-[10px] font-medium uppercase tracking-wide mb-1" style={{ color: "var(--muted)" }}>{label}</p>
      <p className="text-lg font-bold num" style={{ color: "var(--text)" }}>{value}</p>
    </div>
  );
}

// ── Competitor card ──────────────────────────────────────────────────────────

function CompetitorCard({
  c, rescanning, onRescan, onRemove, statusColor, statusLabel, lastScanned,
}: {
  c: Competitor;
  rescanning: boolean;
  onRescan: () => void;
  onRemove: () => void;
  statusColor: string;
  statusLabel: string;
  lastScanned: string;
}) {
  const promoHigh = c.promo_rate != null && c.promo_rate >= 20;
  const showNew = c.new_30d != null && c.new_30d > 0;

  const statusBg =
    c.scan_status === "error"
      ? "rgba(242,85,90,.1)"
      : c.scan_status === "done"
      ? "rgba(76,195,138,.1)"
      : "rgba(255,255,255,.06)";

  return (
    <div
      className="rounded-md p-5 flex flex-col transition-all hover:border-white/15"
      style={{ background: "var(--bg-card)", border: "1px solid var(--border)" }}
    >
      {/* Identity header */}
      <div className="flex items-start gap-3 mb-4">
        <FaviconLogo hostname={c.hostname} size={44} />
        <div className="flex-1 min-w-0">
          <p className="text-base font-bold truncate leading-tight" style={{ color: "var(--text)" }}>
            {c.display_name || c.hostname}
          </p>
          {c.display_name && (
            <p className="text-xs truncate mt-0.5" style={{ color: "var(--muted)" }}>{c.hostname}</p>
          )}
          <div className="flex items-center gap-2 mt-1.5">
            <span
              className="inline-flex items-center gap-1.5 text-[10px] font-bold px-1.5 py-0.5 rounded"
              style={{ background: statusBg, color: statusColor }}
            >
              <span
                className={cn("w-1.5 h-1.5 rounded-full", c.scan_status === "scanning" && "animate-pulse")}
                style={{ background: statusColor }}
              />
              {statusLabel}
            </span>
            <span className="text-[11px]" style={{ color: "var(--muted)" }}>{lastScanned}</span>
          </div>
        </div>
        <button
          onClick={onRemove}
          title="Remove competitor"
          className="p-1.5 rounded-lg transition-colors hover:bg-red-500/10 shrink-0"
          style={{ color: "#F2555A" }}
        >
          <X className="w-4 h-4" />
        </button>
      </div>

      {/* Stats grid */}
      <div className="grid grid-cols-3 gap-3 mb-4">
        <StatCell
          label="Products"
          value={c.product_count != null ? c.product_count.toLocaleString() : "—"}
        />
        <StatCell label="Median price" value={formatPrice(c.median_price)} />
        <StatCell
          label="On sale"
          value={c.promo_rate != null ? `${c.promo_rate.toFixed(0)}%` : "—"}
        />
      </div>

      {/* Secondary metrics */}
      <div
        className="flex items-center justify-between gap-3 px-3 py-2.5 rounded-md mb-4 text-[11px]"
        style={{ background: "var(--bg3)" }}
      >
        <span className="flex items-center gap-1.5" style={{ color: "var(--muted)" }}>
          <Package className="w-3 h-3" />
          {showNew ? (
            <>
              <span className="num font-semibold" style={{ color: "var(--emerald)" }}>+{c.new_30d}</span> new in 30d
            </>
          ) : (
            "No new products (30d)"
          )}
        </span>
        {promoHigh && (
          <span className="flex items-center gap-1 font-semibold" style={{ color: "var(--amber)" }}>
            <Tag className="w-3 h-3" />
            Heavy promo
          </span>
        )}
      </div>

      {/* Footer actions */}
      <div className="flex items-center gap-2 mt-auto">
        <Link
          href={`/dashboard/${c.id}`}
          className="flex-1 flex items-center justify-center gap-1.5 text-xs font-semibold py-2 rounded transition-colors hover:bg-white/[.06]"
          style={{ background: "var(--bg3)", color: "var(--text)", border: "1px solid var(--border)" }}
        >
          View details <ArrowRight className="w-3.5 h-3.5" />
        </Link>
        <button
          onClick={onRescan}
          disabled={rescanning || c.scan_status === "scanning"}
          title="Trigger manual rescan"
          className="flex items-center gap-1.5 text-xs font-medium px-3 py-2 rounded-lg transition-colors hover:bg-white/5 disabled:opacity-40"
          style={{ color: "var(--muted)", border: "1px solid var(--border)" }}
        >
          <RefreshCw className={cn("w-3.5 h-3.5", rescanning && "animate-spin")} />
          Rescan
        </button>
      </div>
    </div>
  );
}

function CompetitorsContent() {
  const searchParams = useSearchParams();

  const [subscription, setSubscription] = useState<UserSubscription | null>(null);
  const [upgradeOpen, setUpgradeOpen] = useState(false);
  const [myCompetitors, setMyCompetitors] = useState<Competitor[]>(() => getCachedCompetitors() ?? []);
  // Success-confirmed flag: the "no competitors yet" empty state must never
  // render off a failed fetch (loading state ≠ empty state).
  const [confirmedLoad, setConfirmedLoad] = useState(() => getCachedCompetitors() !== null);
  const [listError, setListError] = useState(false);
  const [rescanning, setRescanning] = useState<Set<string>>(new Set());
  const [addCompetitorOpen, setAddCompetitorOpen] = useState(false);
  const [addCompetitorInitialUrl, setAddCompetitorInitialUrl] = useState("");
  const [loading, setLoading] = useState(true);

  // Competitor discovery
  const [discoverDescription, setDiscoverDescription] = useState("");
  const [discovering, setDiscovering] = useState(false);
  const [discoverResult, setDiscoverResult] = useState<AIDiscoverySuggestion | null>(null);
  const [discoverError, setDiscoverError] = useState("");

  // Your store
  const [store, setStore] = useState<Competitor | null>(null);
  const [storeUrl, setStoreUrl] = useState("");
  const [storeSaving, setStoreSaving] = useState(false);
  const [storeError, setStoreError] = useState("");
  const [shopifyConnection, setShopifyConnection] = useState<ShopifyConnection | null>(null);
  const [shopifyShop, setShopifyShop] = useState("");
  const [shopifyConnecting, setShopifyConnecting] = useState(false);
  const [shopifyConnectedBanner, setShopifyConnectedBanner] = useState(false);
  const [showManualStore, setShowManualStore] = useState(false);

  useEffect(() => {
    userApi.subscription().then((r) => setSubscription(r.data)).catch(() => {});
    competitorsApi.list()
      .then((r) => { setMyCompetitors(r.data || []); setConfirmedLoad(true); setListError(false); })
      .catch(() => { setListError(true); })
      .finally(() => setLoading(false));
    myStoreApi.get().then((r) => setStore(r.data)).catch(() => {});
    shopifyApi.connection().then((r) => setShopifyConnection(r.data)).catch(() => {});

    if (searchParams.get("connected") === "true") {
      setShopifyConnectedBanner(true);
      setTimeout(() => setShopifyConnectedBanner(false), 5000);
      myStoreApi.get().then((r) => setStore(r.data)).catch(() => {});
      shopifyApi.connection().then((r) => setShopifyConnection(r.data)).catch(() => {});
    }
  }, [searchParams]);

  async function handleRescanCompetitor(id: string) {
    setRescanning((prev) => new Set(prev).add(id));
    try {
      await competitorsApi.rescan(id);
      setTimeout(async () => {
        const { data } = await competitorsApi.list();
        setMyCompetitors(data || []);
        setRescanning((prev) => { const s = new Set(prev); s.delete(id); return s; });
      }, 2000);
    } catch {
      setRescanning((prev) => { const s = new Set(prev); s.delete(id); return s; });
    }
  }

  async function handleRemoveCompetitor(id: string) {
    if (!confirm("Remove this competitor? All scan history will be deleted.")) return;
    await competitorsApi.remove(id).catch(() => {});
    setMyCompetitors((prev) => prev.filter((c) => c.id !== id));
  }

  async function handleSaveStore() {
    if (!storeUrl.trim()) return;
    setStoreSaving(true);
    setStoreError("");
    try {
      const { data } = await myStoreApi.set(storeUrl.trim());
      setStore(data);
      setStoreUrl("");
    } catch {
      setStoreError("Could not add that store. Check the URL and try again.");
    }
    setStoreSaving(false);
  }

  async function handleRemoveStore() {
    await myStoreApi.remove().catch(() => {});
    setStore(null);
  }

  async function handleShopifyConnect() {
    const shop = shopifyShop.trim().toLowerCase().replace(/^https?:\/\//, "").replace(/\/$/, "");
    if (!shop) { setStoreError("Enter your myshopify.com domain."); return; }
    const normalized = shop.includes(".myshopify.com") ? shop : `${shop}.myshopify.com`;
    setShopifyConnecting(true);
    setStoreError("");
    try {
      const { url } = await shopifyApi.connectUrl(normalized);
      window.location.href = url;
    } catch {
      setStoreError("Could not start Shopify connection. Check the domain and try again.");
      setShopifyConnecting(false);
    }
  }

  async function handleShopifyDisconnect() {
    await shopifyApi.disconnect().catch(() => {});
    setShopifyConnection(null);
    setStore(null);
  }

  async function handleDiscover() {
    if (!discoverDescription.trim() || discovering) return;
    setDiscovering(true);
    setDiscoverError("");
    setDiscoverResult(null);
    try {
      const r = await competitorsApi.discoverAI(discoverDescription.trim());
      setDiscoverResult(r.data);
    } catch (err: unknown) {
      const apiErr = err as { data?: { detail?: { code?: string } | string } };
      const detail = apiErr?.data?.detail;
      if (typeof detail === "object" && detail?.code === "discovery_limit_reached") {
        setDiscoverError("You've used your 1 free discovery search this month. Upgrade to Pro for unlimited searches.");
      } else {
        setDiscoverError("Something went wrong generating suggestions. Please try again.");
      }
    } finally {
      setDiscovering(false);
    }
  }

  const atCompetitorLimit = subscription
    ? myCompetitors.length >= subscription.limits.max_competitors
    : false;

  function formatLastScanned(c: Competitor) {
    if (c.scan_status === "scanning") return "Scanning now…";
    if (c.scan_status === "error") return "Scan failed";
    if (c.last_scanned_at) {
      return `Scanned ${new Date(c.last_scanned_at).toLocaleDateString("en-US", { month: "short", day: "numeric" })}`;
    }
    return "Pending first scan";
  }

  function scanStatusColor(status: string | undefined) {
    if (status === "scanning") return "var(--accent)";
    if (status === "error") return "var(--red)";
    if (status === "done") return "var(--emerald)";
    return "var(--muted)";
  }

  function scanStatusLabel(status: string | undefined) {
    if (status === "scanning") return "Scanning";
    if (status === "error") return "Error";
    if (status === "done") return "Done";
    return "Pending";
  }

  return (
    <div>
      {/* Header */}
      <div className="flex items-center justify-between mb-6">
        <div>
          <p className="tick-label mb-1.5">Operate · tracked stores</p>
          <h1 className="text-xl font-bold tracking-tight" style={{ color: "var(--text)" }}>Competitors</h1>
          {subscription && (
            <p className="text-sm mt-0.5" style={{ color: "var(--muted)" }}>
              {myCompetitors.length} / {subscription.limits.max_competitors} tracked
            </p>
          )}
        </div>
        {atCompetitorLimit ? (
          <button
            onClick={() => setUpgradeOpen(true)}
            className="flex items-center gap-2 font-bold text-sm px-4 py-2.5 rounded-md transition-all hover:brightness-110"
            style={{ background: "rgba(255,178,36,.1)", color: "var(--accent)", border: "1px solid rgba(255,178,36,.2)" }}
          >
            <Zap className="w-4 h-4" />
            Upgrade for more
          </button>
        ) : (
          <button
            onClick={() => setAddCompetitorOpen(true)}
            className="flex items-center gap-2 font-bold text-sm px-4 py-2.5 rounded-md transition-all hover:brightness-110"
            style={{ background: "var(--accent)", color: "var(--ink)" }}
          >
            <Plus className="w-4 h-4" />
            Add competitor
          </button>
        )}
      </div>

      {/* Stats strip */}
      {subscription && (
        <div className="grid grid-cols-3 gap-3 mb-6">
          {[
            {
              label: "Tracked",
              value: `${myCompetitors.length} / ${subscription.limits.max_competitors}`,
              highlight: atCompetitorLimit,
            },
            {
              label: "Rescan",
              value: subscription.tier === "free" ? "Manual" : `Every ${subscription.limits.scan_hours}h`,
              highlight: false,
            },
            {
              label: "History",
              value: subscription.limits.history_days === 0 ? "Current only" : `${subscription.limits.history_days}d`,
              highlight: false,
            },
          ].map(({ label, value, highlight }) => (
            <div
              key={label}
              className="rounded-md px-4 py-3"
              style={{
                background: "var(--bg3)",
                border: "1px solid var(--border)",
              }}
            >
              <p className="text-[11px] font-medium mb-1" style={{ color: "var(--muted)" }}>{label}</p>
              <p className="text-sm font-bold num" style={{ color: "var(--text)" }}>{value}</p>
            </div>
          ))}
        </div>
      )}

      {/* Competitor cards */}
      <div className="mb-8">
        <div className="flex items-center gap-2 mb-4">
          <Target className="w-4 h-4" style={{ color: "var(--text-2)" }} />
          <p className="text-sm font-semibold" style={{ color: "var(--text)" }}>Tracked stores</p>
        </div>

        {listError && myCompetitors.length > 0 && (
          <div
            className="mb-3 px-3 py-2 rounded-md text-xs flex items-center gap-2"
            style={{ background: "var(--bg3)", border: "1px solid var(--border)", color: "var(--text-2)" }}
          >
            <RefreshCw className="w-3.5 h-3.5 shrink-0" style={{ color: "var(--muted)" }} />
            Connection hiccup — showing your latest data.
          </div>
        )}

        {loading ? (
          <div className="grid grid-cols-1 lg:grid-cols-2 gap-4">
            {[1, 2, 3, 4].map((i) => (
              <div key={i} className="h-44 rounded-md animate-pulse" style={{ background: "var(--bg3)" }} />
            ))}
          </div>
        ) : myCompetitors.length === 0 && !confirmedLoad ? (
          <div
            className="p-10 text-center rounded-md"
            style={{ background: "var(--bg-card)", border: "1px solid var(--border)" }}
          >
            <RefreshCw className="w-8 h-8 mx-auto mb-3" style={{ color: "var(--muted)", opacity: 0.4 }} />
            <p className="text-sm font-semibold mb-1" style={{ color: "var(--text)" }}>Couldn&apos;t reach StoreScout</p>
            <p className="text-xs mb-5" style={{ color: "var(--muted)" }}>
              Your tracked stores are safe — this is a connection hiccup. Try again in a moment.
            </p>
            <button
              onClick={() => window.location.reload()}
              className="flex items-center gap-2 font-bold text-sm px-5 py-2.5 rounded-md mx-auto transition-all hover:brightness-110"
              style={{ background: "var(--accent)", color: "var(--ink)" }}
            >
              <RefreshCw className="w-4 h-4" />
              Retry
            </button>
          </div>
        ) : myCompetitors.length === 0 ? (
          <div
            className="p-10 text-center rounded-md"
            style={{ background: "var(--bg-card)", border: "1px solid var(--border)" }}
          >
            <Target className="w-8 h-8 mx-auto mb-3" style={{ color: "var(--muted)", opacity: 0.4 }} />
            <p className="text-sm font-semibold mb-1" style={{ color: "var(--text)" }}>No competitors tracked yet</p>
            <p className="text-xs mb-5" style={{ color: "var(--muted)" }}>
              Add a Shopify store URL to start monitoring prices, launches, and discounts.
            </p>
            <button
              onClick={() => setAddCompetitorOpen(true)}
              className="flex items-center gap-2 font-bold text-sm px-5 py-2.5 rounded-md mx-auto transition-all hover:brightness-110"
              style={{ background: "var(--accent)", color: "var(--ink)" }}
            >
              <Plus className="w-4 h-4" />
              Add your first competitor
            </button>
          </div>
        ) : (
          <div className="grid grid-cols-1 lg:grid-cols-2 gap-4">
            {myCompetitors.map((c) => (
              <CompetitorCard
                key={c.id}
                c={c}
                rescanning={rescanning.has(c.id)}
                onRescan={() => handleRescanCompetitor(c.id)}
                onRemove={() => handleRemoveCompetitor(c.id)}
                statusColor={scanStatusColor(c.scan_status)}
                statusLabel={scanStatusLabel(c.scan_status)}
                lastScanned={formatLastScanned(c)}
              />
            ))}
          </div>
        )}
      </div>

      {/* Find competitors */}
      <section className="mb-8">
        <div
          className="rounded-md overflow-hidden"
          style={{ border: "1px solid var(--border)" }}
        >
          {/* Header */}
          <div
            className="px-5 py-4 flex items-center justify-between"
            style={{ background: "var(--bg3)", borderBottom: "1px solid var(--border)" }}
          >
            <div className="flex items-center gap-2">
              <Sparkles className="w-4 h-4" style={{ color: "var(--text-2)" }} />
              <p className="text-sm font-semibold" style={{ color: "var(--text)" }}>Find competitors</p>
              <span className="text-xs" style={{ color: "var(--muted)" }}>— AI-powered</span>
            </div>
            {subscription?.tier === "free" && (
              <span className="text-[11px] font-medium" style={{ color: "var(--muted)" }}>
                {discoverResult && discoverResult.searches_limit !== null
                  ? `${Math.max(0, (discoverResult.searches_limit ?? 0) - (discoverResult.searches_used ?? 0))} of ${discoverResult.searches_limit} searches left this month`
                  : "1 free search / month"}
              </span>
            )}
          </div>

          {/* Body */}
          <div className="p-5" style={{ background: "var(--bg-card)" }}>
            <textarea
              value={discoverDescription}
              onChange={(e) => setDiscoverDescription(e.target.value)}
              onKeyDown={(e) => { if (e.key === "Enter" && (e.metaKey || e.ctrlKey)) handleDiscover(); }}
              rows={3}
              placeholder={
                shopifyConnection
                  ? "Your connected store data is used automatically. Add any extra context — target customer, product focus, price range, brand positioning…"
                  : "Describe your store — what do you sell, who's your customer, what's your price range? e.g. \"Women's activewear, $40-80, targeting fitness enthusiasts\""
              }
              className="w-full text-sm rounded-md px-4 py-3 resize-none outline-none transition-all"
              style={{
                background: "var(--bg3)",
                border: "1px solid var(--border)",
                color: "var(--text)",
              }}
              onFocus={(e) => { e.currentTarget.style.borderColor = "rgba(255,178,36,.4)"; }}
              onBlur={(e) => { e.currentTarget.style.borderColor = "var(--border)"; }}
            />
            <div className="flex items-center justify-between mt-3">
              <p className="text-xs" style={{ color: "var(--muted)" }}>
                {subscription?.tier === "free" ? "Free plan: 1 search per month" : "Unlimited searches"}
              </p>
              <button
                onClick={handleDiscover}
                disabled={discovering || !discoverDescription.trim()}
                className="flex items-center gap-2 text-sm font-semibold px-4 py-2 rounded-md transition-all hover:brightness-110 disabled:opacity-40 disabled:cursor-not-allowed"
                style={{ background: "var(--accent)", color: "var(--ink)" }}
              >
                {discovering ? (
                  <><Loader2 className="w-3.5 h-3.5 animate-spin" />Finding…</>
                ) : (
                  <><Search className="w-3.5 h-3.5" />Find competitors</>
                )}
              </button>
            </div>

            {discovering && <DiscoveryProgress />}

            {discoverError && (
              <div
                className="mt-4 px-4 py-3 rounded-md text-sm"
                style={{ background: "rgba(242,85,90,.08)", border: "1px solid rgba(242,85,90,.2)", color: "#F7999C" }}
              >
                {discoverError}
                {discoverError.includes("Upgrade") && (
                  <button
                    onClick={() => setUpgradeOpen(true)}
                    className="ml-2 underline font-semibold"
                    style={{ color: "var(--accent)" }}
                  >
                    Upgrade →
                  </button>
                )}
              </div>
            )}

            {/* Verified Shopify — trackable now */}
            {discoverResult && discoverResult.suggestions.length > 0 && (
              <div className="mt-4">
                <p className="tick-label mb-2">
                  Verified Shopify · trackable — {discoverResult.suggestions.length}
                </p>
                <div className="space-y-2">
                  {discoverResult.suggestions.map((s) => {
                    const alreadyTracked = myCompetitors.some((c) => c.hostname === s.domain);
                    return (
                      <div
                        key={s.domain}
                        className="flex items-center justify-between gap-4 px-4 py-3 rounded-md"
                        style={{ background: "var(--bg3)", border: "1px solid var(--border)" }}
                      >
                        <div className="flex items-center gap-3 min-w-0">
                          <FaviconLogo hostname={s.domain} size={32} />
                          <div className="min-w-0">
                            <div className="flex items-center gap-2">
                              <p className="text-sm font-semibold truncate" style={{ color: "var(--text)" }}>{s.domain}</p>
                              {typeof s.confidence === "number" && (
                                <span
                                  className="num text-[10px] font-bold px-1.5 py-0.5 rounded shrink-0"
                                  style={{ background: "rgba(76,195,138,.1)", color: "var(--emerald)", border: "1px solid rgba(76,195,138,.2)" }}
                                  title={s.signals?.length ? `Verification signals: ${s.signals.join(" · ")}` : undefined}
                                >
                                  {s.confidence}% Shopify
                                </span>
                              )}
                            </div>
                            <p className="text-xs truncate" style={{ color: "var(--muted)" }}>{s.reason}</p>
                          </div>
                        </div>
                        {alreadyTracked ? (
                          <span className="text-xs font-medium shrink-0 flex items-center gap-1" style={{ color: "var(--emerald)" }}>
                            <Check className="w-3.5 h-3.5" /> Tracking
                          </span>
                        ) : (
                          <button
                            onClick={() => { setAddCompetitorInitialUrl(s.domain); setAddCompetitorOpen(true); }}
                            className="text-xs font-semibold px-3 py-1.5 rounded-lg shrink-0 transition-all hover:brightness-110"
                            style={{ background: "rgba(255,178,36,.1)", color: "var(--accent)", border: "1px solid rgba(255,178,36,.2)" }}
                          >
                            Track →
                          </button>
                        )}
                      </div>
                    );
                  })}
                </div>
              </div>
            )}

            {/* Real competitors we can't monitor — shown honestly, never dropped */}
            {discoverResult && (discoverResult.relevant_non_shopify?.length ?? 0) > 0 && (
              <div className="mt-5">
                <p className="tick-label mb-1">
                  Direct competitors we can&apos;t monitor yet — {discoverResult.relevant_non_shopify!.length}
                </p>
                <p className="text-xs mb-2" style={{ color: "var(--muted)" }}>
                  These brands compete with you but don&apos;t run a scannable Shopify storefront, so StoreScout can&apos;t track them yet. Worth watching manually.
                </p>
                <div className="space-y-1.5">
                  {discoverResult.relevant_non_shopify!.map((s) => (
                    <div
                      key={s.domain}
                      className="flex items-center justify-between gap-4 px-4 py-2.5 rounded-md"
                      style={{ background: "var(--bg-card)", border: "1px dashed var(--border)", opacity: 0.85 }}
                    >
                      <div className="flex items-center gap-3 min-w-0">
                        <FaviconLogo hostname={s.domain} size={26} />
                        <div className="min-w-0">
                          <p className="text-sm font-medium truncate" style={{ color: "var(--text-2)" }}>{s.domain}</p>
                          <p className="text-xs truncate" style={{ color: "var(--muted)" }}>{s.reason}</p>
                        </div>
                      </div>
                      <span className="text-[11px] shrink-0" style={{ color: "var(--muted)" }}>
                        {s.note?.includes("private") ? "Catalog private" : "Not Shopify"}
                      </span>
                    </div>
                  ))}
                </div>
              </div>
            )}

            {/* Search ran but nothing verified — say so, never a silent blank */}
            {discoverResult && discoverResult.suggestions.length === 0 && (discoverResult.relevant_non_shopify?.length ?? 0) === 0 && (
              <div
                className="mt-4 px-4 py-3 rounded-md text-sm"
                style={{ background: "var(--bg3)", border: "1px solid var(--border)", color: "var(--text-2)" }}
              >
                We couldn&apos;t verify any trackable Shopify competitors from that description. Try adding more detail — product type, price range, and target customer help the most.
              </div>
            )}
          </div>
        </div>
      </section>

      {/* Your store */}
      <section
        className="rounded-md p-6 max-w-3xl"
        style={{ background: "var(--bg-card)", border: "1px solid var(--border)" }}
      >
        <div className="flex items-center gap-2 mb-2">
          <Store className="w-4 h-4" style={{ color: "#FFB224" }} />
          <h2 className="font-semibold" style={{ color: "var(--text)" }}>Your store</h2>
        </div>
        <p className="text-sm mb-4" style={{ color: "var(--muted)" }}>
          Connect via Shopify OAuth to verify ownership and unlock personalised playbook recommendations.
          Doesn&apos;t count against your tracking limit.
        </p>

        {shopifyConnectedBanner && (
          <div
            className="flex items-center gap-2 px-4 py-3 rounded-md mb-4 text-sm font-medium"
            style={{ background: "rgba(76,195,138,0.08)", border: "1px solid rgba(76,195,138,0.2)", color: "var(--emerald)" }}
          >
            <Check className="w-4 h-4 shrink-0" />
            Shopify store connected successfully.
          </div>
        )}

        {shopifyConnection ? (
          <div
            className="flex items-center justify-between gap-4 px-4 py-3 rounded-md"
            style={{ background: "rgba(76,195,138,0.05)", border: "1px solid rgba(76,195,138,0.18)" }}
          >
            <div className="flex items-center gap-3 min-w-0">
              <div
                className="w-8 h-8 rounded-lg flex items-center justify-center shrink-0"
                style={{ background: "rgba(76,195,138,0.12)" }}
              >
                <Store className="w-4 h-4" style={{ color: "var(--emerald)" }} />
              </div>
              <div className="min-w-0">
                <p className="text-sm font-semibold truncate" style={{ color: "var(--text)" }}>
                  {shopifyConnection.shop_name || shopifyConnection.shop}
                </p>
                <p className="text-xs mt-0.5" style={{ color: "var(--muted)" }}>
                  {shopifyConnection.shop} · Verified via Shopify OAuth
                  {store?.product_count != null ? ` · ${store.product_count} products` : ""}
                </p>
              </div>
            </div>
            <button
              onClick={handleShopifyDisconnect}
              className="shrink-0 text-sm font-semibold px-4 py-2 rounded-md transition-all hover:opacity-80"
              style={{ background: "var(--bg3)", color: "#F2555A", border: "1px solid var(--border)" }}
            >
              Disconnect
            </button>
          </div>
        ) : (
          <div className="space-y-3">
            <div className="flex gap-2">
              <input
                value={shopifyShop}
                onChange={(e) => setShopifyShop(e.target.value)}
                onKeyDown={(e) => e.key === "Enter" && handleShopifyConnect()}
                placeholder="yourstore.myshopify.com"
                className="flex-1 px-4 py-2.5 rounded-md text-sm outline-none"
                style={{ background: "var(--bg3)", border: "1px solid var(--border)", color: "var(--text)" }}
              />
              <button
                onClick={handleShopifyConnect}
                disabled={shopifyConnecting}
                className="font-semibold text-sm px-5 py-2.5 rounded-md transition-all hover:brightness-110 disabled:opacity-60 flex items-center gap-2"
                style={{ background: "#FFB224", color: "var(--ink)" }}
              >
                {shopifyConnecting ? <Loader2 className="w-4 h-4 animate-spin" /> : null}
                {shopifyConnecting ? "Connecting…" : "Connect via Shopify"}
              </button>
            </div>

            {store ? (
              <div
                className="flex items-center justify-between gap-4 px-4 py-2.5 rounded-md"
                style={{ background: "var(--bg3)", border: "1px solid var(--border)" }}
              >
                <div>
                  <p className="text-xs font-medium" style={{ color: "var(--text)" }}>{store.hostname}</p>
                  <p className="text-[11px] mt-0.5" style={{ color: "var(--muted)" }}>
                    Manually connected{store.product_count != null ? ` · ${store.product_count} products` : ""}
                  </p>
                </div>
                <button
                  onClick={handleRemoveStore}
                  className="text-[11px] font-medium px-3 py-1.5 rounded-lg transition-all hover:opacity-70"
                  style={{ color: "#F2555A" }}
                >
                  Remove
                </button>
              </div>
            ) : showManualStore ? (
              <div className="flex gap-2">
                <input
                  value={storeUrl}
                  onChange={(e) => setStoreUrl(e.target.value)}
                  onKeyDown={(e) => e.key === "Enter" && handleSaveStore()}
                  placeholder="yourstore.com"
                  className="flex-1 px-4 py-2.5 rounded-md text-sm outline-none"
                  style={{ background: "var(--bg3)", border: "1px solid var(--border)", color: "var(--text)" }}
                  autoFocus
                />
                <button
                  onClick={handleSaveStore}
                  disabled={storeSaving}
                  className="font-semibold text-sm px-4 py-2.5 rounded-md transition-all hover:brightness-105 disabled:opacity-60"
                  style={{ background: "var(--bg3)", color: "var(--text)", border: "1px solid var(--border)" }}
                >
                  {storeSaving ? "Adding…" : "Add"}
                </button>
              </div>
            ) : (
              <p className="text-xs" style={{ color: "var(--muted)" }}>
                Or{" "}
                <button
                  onClick={() => setShowManualStore(true)}
                  className="underline underline-offset-2 hover:opacity-70 transition-opacity"
                  style={{ color: "var(--muted)" }}
                >
                  add manually
                </button>
                {" "}with any store URL — ownership not verified.
              </p>
            )}
          </div>
        )}
        {storeError && <p className="text-xs mt-3" style={{ color: "#F2555A" }}>{storeError}</p>}
      </section>

      {addCompetitorOpen && (
        <AddCompetitorModal
          initialUrl={addCompetitorInitialUrl}
          onClose={() => { setAddCompetitorOpen(false); setAddCompetitorInitialUrl(""); }}
          onAdded={(c) => {
            setMyCompetitors((prev) => [...prev, c]);
            setAddCompetitorOpen(false);
            setAddCompetitorInitialUrl("");
          }}
        />
      )}
      <UpgradeModal open={upgradeOpen} onClose={() => setUpgradeOpen(false)} trigger="competitor_limit" currentTier={subscription?.tier} />
    </div>
  );
}

export default function CompetitorsPage() {
  return (
    <Suspense fallback={<div style={{ color: "var(--muted)" }} className="p-6">Loading…</div>}>
      <CompetitorsContent />
    </Suspense>
  );
}
