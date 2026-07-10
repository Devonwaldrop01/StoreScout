"use client";

/**
 * Dashboard insight sections that answer, in 10 seconds, "what did StoreScout
 * learn about my market?" — an executive Market-at-a-Glance strip aggregated
 * across tracked competitors, and an Intelligence-Network credibility bar that
 * grounds the analysis in the real verified index.
 */

import { useEffect, useState } from "react";
import Link from "next/link";
import { TrendingUp, Package, Tag, Rocket, ShieldAlert, DollarSign, Network } from "lucide-react";
import { storeIndex, type Competitor } from "@/lib/api";

function threatLevel(comps: Competitor[]): { label: string; color: string; note: string } {
  const hot = comps.filter((c) => (c.promo_rate ?? 0) >= 30 || (c.new_30d ?? 0) >= 8).length;
  if (hot >= 2) return { label: "Elevated", color: "#F2555A", note: `${hot} competitors are actively pushing` };
  if (hot === 1) return { label: "Moderate", color: "#FFB224", note: "1 competitor is making moves" };
  return { label: "Low", color: "#4CC38A", note: "no aggressive competitor activity right now" };
}

export function MarketAtAGlance({ competitors }: { competitors: Competitor[] }) {
  const scanned = competitors.filter((c) => c.scan_status === "done" || c.product_count != null);
  if (scanned.length === 0) return null;

  const products = scanned.reduce((s, c) => s + (c.product_count ?? 0), 0);
  const prices = scanned.map((c) => c.median_price).filter((v): v is number => v != null);
  const avgPrice = prices.length ? Math.round(prices.reduce((a, b) => a + b, 0) / prices.length) : null;
  const launches = scanned.reduce((s, c) => s + (c.new_30d ?? 0), 0);
  const promoting = scanned.filter((c) => (c.promo_rate ?? 0) >= 5).length;
  const avgPromo = scanned.length ? Math.round(scanned.reduce((s, c) => s + (c.promo_rate ?? 0), 0) / scanned.length) : 0;
  const threat = threatLevel(scanned);

  const tiles = [
    { icon: Package, label: "Competitors analyzed", value: scanned.length.toString(), href: "/competitors", color: "var(--text)" },
    { icon: TrendingUp, label: "Products analyzed", value: products.toLocaleString(), href: "/competitors", color: "var(--text)" },
    { icon: DollarSign, label: "Avg. market price", value: avgPrice != null ? `$${avgPrice}` : "—", href: "/competitors", color: "var(--text)" },
    { icon: Tag, label: "Now discounting", value: `${promoting}/${scanned.length}`, sub: `~${avgPromo}% of catalogs`, href: "/competitors", color: promoting ? "#FFB224" : "var(--text)" },
    { icon: Rocket, label: "New launches (30d)", value: launches.toLocaleString(), href: "/competitors", color: launches ? "#7DB8C9" : "var(--text)" },
    { icon: ShieldAlert, label: "Threat level", value: threat.label, sub: threat.note, href: "/alerts", color: threat.color },
  ];

  return (
    <div className="rounded-md p-4 sm:p-5" style={{ background: "var(--bg-card)", border: "1px solid var(--border)" }}>
      <div className="flex items-center gap-2 mb-3.5">
        <h2 className="text-sm font-bold uppercase tracking-wider" style={{ color: "var(--text-2)" }}>Market at a glance</h2>
        <span className="text-[11px]" style={{ color: "var(--muted)" }}>· what StoreScout learned across your landscape</span>
      </div>
      <div className="grid grid-cols-2 md:grid-cols-3 lg:grid-cols-6 gap-2.5">
        {tiles.map((t) => (
          <Link key={t.label} href={t.href} className="rounded-md px-3 py-2.5 transition-all hover:bg-white/[.03]" style={{ background: "var(--bg3)", border: "1px solid var(--border)" }}>
            <t.icon className="w-3.5 h-3.5 mb-1.5" style={{ color: "var(--muted)" }} />
            <p className="num text-lg font-bold leading-none" style={{ color: t.color }}>{t.value}</p>
            <p className="text-[10px] uppercase tracking-wide mt-1" style={{ color: "var(--muted)" }}>{t.label}</p>
            {t.sub && <p className="text-[10px] mt-0.5" style={{ color: "var(--muted)", opacity: .8 }}>{t.sub}</p>}
          </Link>
        ))}
      </div>
    </div>
  );
}

export function IntelligenceNetwork() {
  const [stats, setStats] = useState<{ verified_stores: number; discovered_universe: number; categories: number } | null>(null);
  useEffect(() => { storeIndex.networkStats().then((r) => setStats(r.data)).catch(() => {}); }, []);
  if (!stats || stats.verified_stores === 0) return null;

  const items = [
    { label: "verified Shopify stores", value: stats.verified_stores },
    { label: "in the discovery universe", value: stats.discovered_universe },
    { label: "categories benchmarked", value: stats.categories },
  ];
  return (
    <div className="rounded-md px-4 py-3 flex items-center gap-3 flex-wrap" style={{ background: "var(--bg-card)", border: "1px solid var(--border)" }}>
      <div className="flex items-center gap-2">
        <Network className="w-4 h-4" style={{ color: "var(--accent)" }} />
        <span className="text-xs font-semibold" style={{ color: "var(--text)" }}>Powered by the StoreScout Intelligence Network</span>
      </div>
      <div className="flex items-center gap-4 ml-auto">
        {items.map((it) => (
          <div key={it.label} className="flex items-baseline gap-1.5">
            <span className="num text-sm font-bold" style={{ color: "var(--accent)" }}>{it.value.toLocaleString()}</span>
            <span className="text-[11px]" style={{ color: "var(--muted)" }}>{it.label}</span>
          </div>
        ))}
      </div>
    </div>
  );
}
