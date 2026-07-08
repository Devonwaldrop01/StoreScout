"use client";

/**
 * First-scan reveal — the onboarding continuation that runs right after a
 * user's first successful scan. Day 1 shouldn't feel like waiting for
 * monitoring; it should feel like discovery. Five screens walk through what
 * StoreScout just learned, built ONLY from real scan data (no fake numbers,
 * no simulated changes — fallbacks are truthful facts from the snapshot).
 */

import { use, useEffect, useRef, useState } from "react";
import { useRouter, useSearchParams } from "next/navigation";
import {
  ArrowRight, Check, Tag, Package, TrendingUp, Zap,
  Sparkles, Layers, FileText,
} from "lucide-react";
import { competitors as api, type Snapshot, type BriefCard } from "@/lib/api";
import { track } from "@/lib/analytics";
import { InsightCard } from "@/components/ui/InsightCard";

// ── Parsed brief (digest fields shipped in Phase 1) ────────────────────────
interface ParsedBrief {
  threat_level?: string;
  highlights?: string[];
  one_move?: string;
  cards?: BriefCard[];
}

const MONITORS = [
  { icon: Tag,      title: "Price changes",     desc: "Every price move on every product, with the % delta" },
  { icon: Sparkles, title: "Product launches",  desc: "New products the moment they appear in the catalog" },
  { icon: TrendingUp, title: "Discount campaigns", desc: "Flash sales and discount waves as they start and end" },
  { icon: Package,  title: "Inventory shifts",  desc: "Products going out of stock or being removed" },
  { icon: Layers,   title: "Collection changes", desc: "New collections and merchandising moves" },
  { icon: FileText, title: "Brand & content",   desc: "Positioning, pages, and content investments" },
];

export default function RevealPage({ params }: { params: Promise<{ id: string }> }) {
  const { id } = use(params);
  const router = useRouter();
  const searchParams = useSearchParams();

  const [step, setStep] = useState(0);
  const [snapshot, setSnapshot] = useState<Snapshot | null>(null);
  const [snapshotMissing, setSnapshotMissing] = useState(false);
  const [hostname, setHostname] = useState("");
  const [nextScanLabel, setNextScanLabel] = useState<string | null>(null);
  const [brief, setBrief] = useState<ParsedBrief | null>(null);
  const briefTries = useRef(0);

  const plan = searchParams.get("plan");
  const dest = plan && plan !== "free" ? `/dashboard/${id}?upgrade=${plan}` : `/dashboard/${id}`;

  // Competitor record — hostname + next scan time
  useEffect(() => {
    api.get(id)
      .then((r) => {
        setHostname(r.data.display_name || r.data.hostname);
        if (r.data.next_scan_at) {
          const ms = new Date(r.data.next_scan_at).getTime() - Date.now();
          const h = Math.round(ms / 3_600_000);
          setNextScanLabel(ms <= 0 ? "soon" : h >= 24 ? `in ${Math.round(h / 24)}d` : `in ${h}h`);
        }
      })
      .catch(() => {});
  }, [id]);

  // Snapshot — poll briefly if the scan is still finishing
  useEffect(() => {
    let cancelled = false;
    let attempts = 0;
    const tryFetch = async () => {
      if (cancelled) return;
      attempts++;
      try {
        const r = await api.latestSnapshot(id);
        if (!cancelled) setSnapshot(r.data);
      } catch {
        if (attempts >= 15) { if (!cancelled) setSnapshotMissing(true); return; }
        setTimeout(tryFetch, 3000);
      }
    };
    tryFetch();
    return () => { cancelled = true; };
  }, [id]);

  // Brief — generates ~seconds after the snapshot; poll quietly, never block
  useEffect(() => {
    if (!snapshot || brief) return;
    let cancelled = false;
    const tryFetch = async () => {
      if (cancelled || briefTries.current >= 10) return;
      briefTries.current++;
      try {
        const r = await api.brief(id);
        if (cancelled) return;
        try { setBrief(JSON.parse(r.data.summary_text) as ParsedBrief); } catch { /* legacy format */ }
      } catch {
        setTimeout(tryFetch, 4000);
      }
    };
    tryFetch();
    return () => { cancelled = true; };
  }, [id, snapshot, brief]);

  function finish() {
    try { track("first_scan_reveal_completed", { competitor_id: id, steps_seen: step + 1 }); } catch { /* ignore */ }
    router.push(dest);
  }

  // ── Derivations — real data only ─────────────────────────────────────────
  const d = (snapshot?.snapshot_data ?? {}) as Record<string, Record<string, unknown>>;
  const catalog = (d.catalog ?? {}) as Record<string, unknown>;
  const pricing = (d.pricing ?? {}) as Record<string, unknown>;
  const discounts = (d.discounts ?? {}) as Record<string, unknown>;
  const positioning = (d.positioning ?? {}) as Record<string, Record<string, unknown>>;
  const launch = (d.launch_timeline ?? {}) as Record<string, Record<string, Record<string, Record<string, number>>>>;
  const gaps = (d.gap_analysis ?? {}) as Record<string, unknown>;
  const storeProfile = (d.store_profile ?? {}) as Record<string, Record<string, unknown>>;

  const products = catalog.total_products as number | undefined;
  const median = pricing.median as number | undefined;
  const priceMin = pricing.min as number | undefined;
  const priceMax = pricing.max as number | undefined;
  const promoRate = discounts.discounted_pct as number | undefined;
  const positionLabel = positioning.market_position?.label as string | undefined;
  const launches30 = launch.launch_counts?.["30d"]?.count as unknown as number | undefined;
  const gapsTotal = gaps.total as number | undefined;
  const collectionsCount = storeProfile.collections?.count as number | undefined;

  const fmt = (n?: number) => (n != null ? `$${n.toLocaleString(undefined, { maximumFractionDigits: 0 })}` : "—");

  // Screen 1 stats — only render what we truly have
  const analyzedStats = [
    products != null && { label: "Products analyzed", value: products.toLocaleString() },
    median != null && { label: "Median price", value: fmt(median), sub: priceMin != null && priceMax != null ? `${fmt(priceMin)} – ${fmt(priceMax)}` : undefined },
    promoRate != null && { label: "Catalog discounted", value: `${promoRate}%` },
    launches30 != null && { label: "Launches · 30d", value: String(launches30) },
    collectionsCount != null && { label: "Collections", value: String(collectionsCount) },
    positionLabel && { label: "Positioning", value: positionLabel },
  ].filter(Boolean) as { label: string; value: string; sub?: string }[];

  // Screen 2 findings — brief cards preferred; truthful snapshot facts otherwise
  const briefFindings = (brief?.cards ?? [])
    .filter((c) => c.type !== "action")
    .slice(0, 3)
    .map((c) => ({ type: c.type, headline: c.headline, why: c.body }));
  const fallbackFindings = [
    promoRate != null && {
      type: "signal",
      headline: `${promoRate}% of their catalog is discounted right now`,
      why: promoRate >= 25
        ? "Heavy discounting usually means pricing pressure or clearance cycles — margin they're giving up that you might not have to."
        : "Light discounting suggests they're holding margin — undercutting selectively could win price-sensitive customers.",
    },
    launches30 != null && {
      type: "watch",
      headline: `${launches30} product launch${launches30 === 1 ? "" : "es"} in the last 30 days`,
      why: (launches30 as number) >= 5
        ? "That's an aggressive release pace — they're testing the market fast, and each launch is a signal about where demand is."
        : "A slow release cadence can mean focus on best-sellers — or an opening for you to out-ship them.",
    },
    median != null && {
      type: "opportunity",
      headline: `Median price ${fmt(median)} — ${positionLabel ?? "their pricing position"}`,
      why: "Knowing exactly where they sit lets you position deliberately above or below instead of guessing.",
    },
  ].filter(Boolean) as { type: string; headline: string; why: string }[];
  const findings = briefFindings.length >= 2 ? briefFindings : fallbackFindings;

  // Screen 3 — the biggest opening + one move
  const opportunityCard = brief?.cards?.find((c) => c.type === "opportunity");
  const actionCard = brief?.cards?.find((c) => c.type === "action");
  const oneMove = brief?.one_move || actionCard?.headline;
  const evidence = [
    products != null && `${products.toLocaleString()} products scanned`,
    promoRate != null && `${promoRate}% of catalog discounted`,
    launches30 != null && `${launches30} launches in 30 days`,
    median != null && `median price ${fmt(median)}`,
  ].filter(Boolean) as string[];

  // ── Waiting / failure states ─────────────────────────────────────────────
  if (snapshotMissing) {
    return (
      <Shell>
        <div className="text-center max-w-sm mx-auto">
          <p className="text-lg font-bold mb-2" style={{ color: "var(--text)" }}>Still analyzing {hostname || "your competitor"}…</p>
          <p className="text-sm mb-6" style={{ color: "var(--muted)" }}>
            This store is taking longer than usual. The full analysis will be waiting on your dashboard.
          </p>
          <button onClick={finish} className="text-sm font-semibold px-5 py-2.5 rounded-md" style={{ background: "var(--accent)", color: "var(--ink)" }}>
            Go to dashboard <ArrowRight className="w-4 h-4 inline -mt-0.5 ml-1" />
          </button>
        </div>
      </Shell>
    );
  }

  if (!snapshot) {
    return (
      <Shell>
        <div className="text-center rounded-md px-10 py-8 analyzing-sweep" style={{ background: "var(--bg-card)", border: "1px solid var(--border)" }}>
          <div className="flex items-center justify-center gap-1.5 mb-4">
            {[0, 1, 2].map((i) => (
              <div key={i} className="w-2 h-2 rounded-full animate-bounce" style={{ background: "var(--accent)", animationDelay: `${i * 0.15}s` }} />
            ))}
          </div>
          <p className="text-sm font-semibold" style={{ color: "var(--text)" }}>Finishing the analysis…</p>
        </div>
      </Shell>
    );
  }

  // ── The five screens ─────────────────────────────────────────────────────
  const screens = [
    // 1 — Analyzed
    <div key="s1" className="fade-up">
      <p className="tick-label tick-label--live mb-3">First scan complete</p>
      <h1 className="text-2xl sm:text-3xl font-bold tracking-tight mb-2" style={{ color: "var(--text)" }}>
        {hostname || "Your competitor"} has been analyzed.
      </h1>
      <p className="text-sm mb-8 max-w-md" style={{ color: "var(--muted)" }}>
        Here&apos;s what StoreScout pulled from their live storefront just now.
      </p>
      <div className="grid grid-cols-2 sm:grid-cols-3 gap-3 mb-2">
        {analyzedStats.map((s, i) => (
          <div
            key={s.label}
            className="rounded-md px-4 py-4 fade-up"
            style={{ background: "var(--bg-card)", border: "1px solid var(--border)", animationDelay: `${i * 90}ms` }}
          >
            <p className="num text-xl font-bold" style={{ color: "var(--text)" }}>{s.value}</p>
            <p className="label-caps mt-1">{s.label}</p>
            {s.sub && <p className="num text-[10px] mt-0.5" style={{ color: "var(--muted)" }}>{s.sub}</p>}
          </div>
        ))}
      </div>
    </div>,

    // 2 — Most notable findings
    <div key="s2" className="fade-up">
      <p className="tick-label mb-3">What stood out</p>
      <h1 className="text-2xl sm:text-3xl font-bold tracking-tight mb-2" style={{ color: "var(--text)" }}>
        The {findings.length === 1 ? "most notable thing" : `${findings.length} most notable things`} we found.
      </h1>
      <p className="text-sm mb-8 max-w-md" style={{ color: "var(--muted)" }}>
        Not every metric — just the ones that matter, and why.
      </p>
      <div className="space-y-3">
        {findings.map((f, i) => (
          <div key={i} className="fade-up" style={{ animationDelay: `${i * 120}ms` }}>
            <InsightCard type={f.type} headline={f.headline}>
              <p className="text-sm leading-relaxed" style={{ color: "var(--text-2)" }}>
                <span className="font-semibold" style={{ color: "var(--muted)" }}>Why it matters · </span>{f.why}
              </p>
            </InsightCard>
          </div>
        ))}
      </div>
    </div>,

    // 3 — Biggest opportunity
    <div key="s3" className="fade-up">
      <p className="tick-label mb-3">Your opening</p>
      <h1 className="text-2xl sm:text-3xl font-bold tracking-tight mb-2" style={{ color: "var(--text)" }}>
        {gapsTotal ? `${gapsTotal} market opening${gapsTotal === 1 ? "" : "s"} detected.` : "Your biggest opportunity."}
      </h1>
      <p className="text-sm mb-8 max-w-md" style={{ color: "var(--muted)" }}>
        {gapsTotal ? "The clearest one, and what to do about it:" : "Based on this first scan:"}
      </p>

      <div className="rounded-md p-5 mb-4" style={{ background: "var(--bg-card)", border: "1px solid var(--border)", borderLeft: "3px solid #4CC38A" }}>
        <p className="label-caps mb-2" style={{ color: "#4CC38A" }}>Opportunity</p>
        <p className="text-base font-semibold leading-snug mb-1.5" style={{ color: "var(--text)" }}>
          {opportunityCard?.headline ?? "Their catalog is now fully mapped — every gap is visible."}
        </p>
        <p className="text-sm leading-relaxed" style={{ color: "var(--text-2)" }}>
          {opportunityCard?.body ?? "Open the Catalog tab on your dashboard to see the market openings StoreScout found in their range, pricing, and merchandising."}
        </p>
      </div>

      {oneMove && (
        <div className="rounded-md p-4 mb-4 flex items-start gap-3" style={{ background: "var(--bg3)", border: "1px solid var(--border)" }}>
          <Zap className="w-4 h-4 mt-0.5 shrink-0" style={{ color: "var(--accent)" }} />
          <div>
            <p className="label-caps mb-1" style={{ color: "var(--accent)" }}>Your move</p>
            <p className="text-sm font-semibold leading-snug" style={{ color: "var(--text)" }}>{oneMove}</p>
          </div>
        </div>
      )}

      {evidence.length > 0 && (
        <p className="num text-[11px]" style={{ color: "var(--muted)" }}>
          Based on: {evidence.join(" · ")}
        </p>
      )}
    </div>,

    // 4 — What we monitor from here
    <div key="s4" className="fade-up">
      <p className="tick-label mb-3">From today onward</p>
      <h1 className="text-2xl sm:text-3xl font-bold tracking-tight mb-2" style={{ color: "var(--text)" }}>
        Here&apos;s what StoreScout watches for you now.
      </h1>
      <p className="text-sm mb-8 max-w-md" style={{ color: "var(--muted)" }}>
        Today was the baseline. Every scan from here compares against it — and you get told the moment something moves{nextScanLabel ? ` (next scan ${nextScanLabel})` : ""}.
      </p>
      <div className="grid sm:grid-cols-2 gap-3">
        {MONITORS.map(({ icon: Icon, title, desc }, i) => (
          <div
            key={title}
            className="rounded-md p-4 flex items-start gap-3 fade-up"
            style={{ background: "var(--bg-card)", border: "1px solid var(--border)", animationDelay: `${i * 70}ms` }}
          >
            <div className="w-8 h-8 rounded-md flex items-center justify-center shrink-0" style={{ background: "var(--bg3)", border: "1px solid var(--border)" }}>
              <Icon className="w-4 h-4" style={{ color: "var(--text-2)" }} />
            </div>
            <div>
              <p className="text-sm font-semibold" style={{ color: "var(--text)" }}>{title}</p>
              <p className="text-xs leading-snug mt-0.5" style={{ color: "var(--muted)" }}>{desc}</p>
            </div>
          </div>
        ))}
      </div>
    </div>,

    // 5 — Done
    <div key="s5" className="fade-up text-center">
      <div className="w-14 h-14 rounded-full mx-auto mb-5 flex items-center justify-center" style={{ background: "rgba(76,195,138,.12)", border: "1px solid rgba(76,195,138,.3)" }}>
        <Check className="w-7 h-7" style={{ color: "#4CC38A" }} />
      </div>
      <h1 className="text-2xl sm:text-3xl font-bold tracking-tight mb-3" style={{ color: "var(--text)" }}>
        You&apos;re all set.
      </h1>
      <p className="text-sm mb-8 max-w-sm mx-auto leading-relaxed" style={{ color: "var(--muted)" }}>
        {hostname || "Your competitor"} is under watch. Your dashboard has the full dossier — catalog, pricing, openings, and your playbook.
      </p>
      <button
        onClick={finish}
        className="text-sm font-bold px-7 py-3 rounded-md transition-all hover:brightness-110"
        style={{ background: "var(--accent)", color: "var(--ink)" }}
      >
        Open your dashboard <ArrowRight className="w-4 h-4 inline -mt-0.5 ml-1" />
      </button>
    </div>,
  ];

  return (
    <Shell>
      <div className="w-full max-w-2xl mx-auto">
        {screens[step]}

        {/* Footer nav */}
        <div className="flex items-center justify-between mt-10">
          <div className="flex items-center gap-1.5">
            {screens.map((_, i) => (
              <button
                key={i}
                onClick={() => setStep(i)}
                aria-label={`Step ${i + 1}`}
                className="h-1.5 rounded-full transition-all"
                style={{ width: i === step ? 20 : 6, background: i === step ? "var(--accent)" : i < step ? "var(--text-2)" : "var(--border)" }}
              />
            ))}
          </div>
          <div className="flex items-center gap-4">
            {step < screens.length - 1 && (
              <>
                <button onClick={finish} className="text-xs transition-opacity hover:opacity-70" style={{ color: "var(--muted)" }}>
                  Skip to dashboard
                </button>
                <button
                  onClick={() => setStep(step + 1)}
                  className="flex items-center gap-1.5 text-sm font-semibold px-5 py-2.5 rounded-md transition-all hover:brightness-110"
                  style={{ background: "var(--accent)", color: "var(--ink)" }}
                >
                  Continue <ArrowRight className="w-4 h-4" />
                </button>
              </>
            )}
          </div>
        </div>
      </div>
    </Shell>
  );
}

function Shell({ children }: { children: React.ReactNode }) {
  return (
    <div className="min-h-screen flex items-center justify-center px-5 py-12" style={{ background: "var(--bg)" }}>
      {children}
    </div>
  );
}
