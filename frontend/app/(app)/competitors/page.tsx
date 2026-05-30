"use client";

import { Suspense, useEffect, useState } from "react";
import { useSearchParams } from "next/navigation";
import Link from "next/link";
import {
  competitors as competitorsApi, user as userApi, myStore as myStoreApi, shopify as shopifyApi,
  type Competitor, type UserSubscription, type ShopifyConnection,
} from "@/lib/api";
import { cn, formatPrice } from "@/lib/utils";
import { AddCompetitorModal } from "@/components/competitors/AddCompetitorModal";
import UpgradeModal from "@/components/UpgradeModal";
import {
  Store, X, Loader2, Check, Plus, RefreshCw, Target, Zap, ArrowRight,
  Package, Tag,
} from "lucide-react";

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
  // The /competitors list endpoint enriches each row with the latest snapshot's
  // product_count, promo_rate, median_price and new_30d.
  const promoHigh = c.promo_rate != null && c.promo_rate >= 20;
  const showNew = c.new_30d != null && c.new_30d > 0;

  return (
    <div
      className="rounded-2xl p-5 flex flex-col transition-all hover:border-white/15"
      style={{ background: "var(--bg-card)", border: "1px solid var(--border)" }}
    >
      {/* Top: name + status + remove */}
      <div className="flex items-start justify-between gap-3 mb-4">
        <div className="flex items-start gap-2.5 min-w-0">
          <span
            className={cn("w-2 h-2 rounded-full shrink-0 mt-1.5", c.scan_status === "scanning" && "animate-pulse")}
            style={{ background: statusColor }}
          />
          <div className="min-w-0">
            <p className="text-base font-bold truncate" style={{ color: "var(--text)" }}>
              {c.display_name || c.hostname}
            </p>
            <div className="flex items-center gap-2 mt-1">
              <span
                className="text-[10px] font-bold px-1.5 py-0.5 rounded"
                style={{
                  background: c.scan_status === "error"
                    ? "rgba(239,68,68,.1)"
                    : c.scan_status === "done"
                    ? "rgba(34,197,94,.1)"
                    : "rgba(255,255,255,.06)",
                  color: statusColor,
                }}
              >
                {statusLabel}
              </span>
              <span className="text-[11px]" style={{ color: "var(--muted)" }}>{lastScanned}</span>
            </div>
          </div>
        </div>
        <button
          onClick={onRemove}
          title="Remove competitor"
          className="p-1.5 rounded-lg transition-colors hover:bg-red-500/10 shrink-0"
          style={{ color: "#f87171" }}
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
        className="flex items-center justify-between gap-3 px-3 py-2.5 rounded-xl mb-4 text-[11px]"
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
          className="flex-1 flex items-center justify-center gap-1.5 text-xs font-semibold py-2 rounded-lg transition-all hover:brightness-110"
          style={{ background: "var(--accent)", color: "#ffffff" }}
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
  const [myCompetitors, setMyCompetitors] = useState<Competitor[]>([]);
  const [rescanning, setRescanning] = useState<Set<string>>(new Set());
  const [addCompetitorOpen, setAddCompetitorOpen] = useState(false);
  const [loading, setLoading] = useState(true);

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
      .then((r) => { setMyCompetitors(r.data || []); })
      .catch(() => {})
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
          <h1 className="text-xl font-bold" style={{ color: "var(--text)" }}>Competitors</h1>
          {subscription && (
            <p className="text-sm mt-0.5" style={{ color: "var(--muted)" }}>
              {myCompetitors.length} / {subscription.limits.max_competitors} tracked
            </p>
          )}
        </div>
        {atCompetitorLimit ? (
          <button
            onClick={() => setUpgradeOpen(true)}
            className="flex items-center gap-2 font-bold text-sm px-4 py-2.5 rounded-xl transition-all hover:brightness-110"
            style={{ background: "rgba(59,130,246,.1)", color: "var(--accent)", border: "1px solid rgba(59,130,246,.2)" }}
          >
            <Zap className="w-4 h-4" />
            Upgrade for more
          </button>
        ) : (
          <button
            onClick={() => setAddCompetitorOpen(true)}
            className="flex items-center gap-2 font-bold text-sm px-4 py-2.5 rounded-xl transition-all hover:brightness-110"
            style={{ background: "var(--accent)", color: "#ffffff" }}
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
              className="rounded-xl px-4 py-3"
              style={{
                background: highlight ? "rgba(59,130,246,.05)" : "var(--bg3)",
                border: highlight ? "1px solid rgba(59,130,246,.2)" : "1px solid var(--border)",
              }}
            >
              <p className="text-[11px] font-medium mb-1" style={{ color: "var(--muted)" }}>{label}</p>
              <p className="text-sm font-bold" style={{ color: highlight ? "var(--accent)" : "var(--text)" }}>{value}</p>
            </div>
          ))}
        </div>
      )}

      {/* Competitor cards */}
      <div className="mb-8">
        <div className="flex items-center gap-2 mb-4">
          <Target className="w-4 h-4" style={{ color: "var(--accent)" }} />
          <p className="text-sm font-semibold" style={{ color: "var(--text)" }}>Tracked stores</p>
        </div>

        {loading ? (
          <div className="grid grid-cols-1 lg:grid-cols-2 gap-4">
            {[1, 2, 3, 4].map((i) => (
              <div key={i} className="h-44 rounded-2xl animate-pulse" style={{ background: "var(--bg3)" }} />
            ))}
          </div>
        ) : myCompetitors.length === 0 ? (
          <div
            className="p-10 text-center rounded-2xl"
            style={{ background: "var(--bg-card)", border: "1px solid var(--border)" }}
          >
            <Target className="w-8 h-8 mx-auto mb-3" style={{ color: "var(--muted)", opacity: 0.4 }} />
            <p className="text-sm font-semibold mb-1" style={{ color: "var(--text)" }}>No competitors tracked yet</p>
            <p className="text-xs mb-5" style={{ color: "var(--muted)" }}>
              Add a Shopify store URL to start monitoring prices, launches, and discounts.
            </p>
            <button
              onClick={() => setAddCompetitorOpen(true)}
              className="flex items-center gap-2 font-bold text-sm px-5 py-2.5 rounded-xl mx-auto transition-all hover:brightness-110"
              style={{ background: "var(--accent)", color: "#ffffff" }}
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

      {/* Your store */}
      <section
        className="rounded-2xl p-6 max-w-3xl"
        style={{ background: "var(--bg-card)", border: "1px solid var(--border)" }}
      >
        <div className="flex items-center gap-2 mb-2">
          <Store className="w-4 h-4" style={{ color: "#3b82f6" }} />
          <h2 className="font-semibold" style={{ color: "var(--text)" }}>Your store</h2>
        </div>
        <p className="text-sm mb-4" style={{ color: "var(--muted)" }}>
          Connect via Shopify OAuth to verify ownership and unlock personalised playbook recommendations.
          Doesn&apos;t count against your tracking limit.
        </p>

        {shopifyConnectedBanner && (
          <div
            className="flex items-center gap-2 px-4 py-3 rounded-xl mb-4 text-sm font-medium"
            style={{ background: "rgba(34,197,94,0.08)", border: "1px solid rgba(34,197,94,0.2)", color: "var(--emerald)" }}
          >
            <Check className="w-4 h-4 shrink-0" />
            Shopify store connected successfully.
          </div>
        )}

        {shopifyConnection ? (
          <div
            className="flex items-center justify-between gap-4 px-4 py-3 rounded-xl"
            style={{ background: "rgba(34,197,94,0.05)", border: "1px solid rgba(34,197,94,0.18)" }}
          >
            <div className="flex items-center gap-3 min-w-0">
              <div
                className="w-8 h-8 rounded-lg flex items-center justify-center shrink-0"
                style={{ background: "rgba(34,197,94,0.12)" }}
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
              className="shrink-0 text-sm font-semibold px-4 py-2 rounded-xl transition-all hover:opacity-80"
              style={{ background: "var(--bg3)", color: "#f87171", border: "1px solid var(--border)" }}
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
                className="flex-1 px-4 py-2.5 rounded-xl text-sm outline-none"
                style={{ background: "var(--bg3)", border: "1px solid var(--border)", color: "var(--text)" }}
              />
              <button
                onClick={handleShopifyConnect}
                disabled={shopifyConnecting}
                className="font-semibold text-sm px-5 py-2.5 rounded-xl transition-all hover:brightness-110 disabled:opacity-60 flex items-center gap-2"
                style={{ background: "#3b82f6", color: "#ffffff" }}
              >
                {shopifyConnecting ? <Loader2 className="w-4 h-4 animate-spin" /> : null}
                {shopifyConnecting ? "Connecting…" : "Connect via Shopify"}
              </button>
            </div>

            {store ? (
              <div
                className="flex items-center justify-between gap-4 px-4 py-2.5 rounded-xl"
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
                  style={{ color: "#f87171" }}
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
                  className="flex-1 px-4 py-2.5 rounded-xl text-sm outline-none"
                  style={{ background: "var(--bg3)", border: "1px solid var(--border)", color: "var(--text)" }}
                  autoFocus
                />
                <button
                  onClick={handleSaveStore}
                  disabled={storeSaving}
                  className="font-semibold text-sm px-4 py-2.5 rounded-xl transition-all hover:brightness-105 disabled:opacity-60"
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
        {storeError && <p className="text-xs mt-3" style={{ color: "#f87171" }}>{storeError}</p>}
      </section>

      {addCompetitorOpen && (
        <AddCompetitorModal
          onClose={() => setAddCompetitorOpen(false)}
          onAdded={(c) => {
            setMyCompetitors((prev) => [...prev, c]);
            setAddCompetitorOpen(false);
          }}
        />
      )}
      <UpgradeModal open={upgradeOpen} onClose={() => setUpgradeOpen(false)} trigger="competitor_limit" />
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
