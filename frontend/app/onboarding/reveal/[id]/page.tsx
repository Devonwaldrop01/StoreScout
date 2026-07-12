"use client";

/**
 * First-scan reveal — the onboarding continuation that runs right after a
 * user's first successful scan. Day 1 shouldn't feel like waiting for
 * monitoring; it should feel like discovery. The screens walk through what
 * StoreScout just learned, built ONLY from persisted scan data (no fake
 * numbers, no simulated changes — fallbacks are truthful facts from the
 * snapshot). The flow adapts to how much data exists, survives a refresh, and
 * never blocks the dashboard on optional AI.
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
import {
  extractFacts, deriveStats, chooseFindings, deriveEvidence,
  revealScreenIds, isRevealComplete, markRevealComplete,
  readRevealStep, writeRevealStep, type RevealScreenId,
} from "@/lib/reveal";

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
  const [redirecting, setRedirecting] = useState(false);
  const briefTries = useRef(0);

  const plan = searchParams.get("plan");
  const dest = plan && plan !== "free" ? `/dashboard/${id}?upgrade=${plan}` : `/dashboard/${id}`;

  // A completed reveal must NOT replay on refresh or back-nav — send straight
  // to the dashboard. Otherwise resume at the step the user left off on.
  useEffect(() => {
    if (isRevealComplete(id)) {
      // One-shot mount guard: localStorage says done → leave immediately. Not a
      // render cascade (we navigate away), so the set-state-in-effect rule is
      // suppressed intentionally here.
      // eslint-disable-next-line react-hooks/set-state-in-effect
      setRedirecting(true);
      router.replace(dest);
      return;
    }
    const saved = readRevealStep(id);
    if (saved > 0) setStep(saved);
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [id]);

  // Persist progress so a mid-reveal refresh resumes instead of restarting.
  useEffect(() => {
    if (!redirecting) writeRevealStep(id, step);
  }, [id, step, redirecting]);

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
    if (redirecting) return;
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
  }, [id, redirecting]);

  // Brief — optional AI; generates ~seconds after the snapshot. Poll quietly
  // and NEVER block: if it never arrives the reveal falls back to snapshot data.
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
    markRevealComplete(id);
    try { track("first_scan_reveal_completed", { competitor_id: id, steps_seen: step + 1 }); } catch { /* ignore */ }
    router.push(dest);
  }

  // ── Derivations — persisted scan data only (see lib/reveal.ts) ────────────
  const facts = extractFacts(snapshot?.snapshot_data as Record<string, unknown> | undefined);
  const analyzedStats = deriveStats(facts);
  const findings = chooseFindings(brief?.cards, facts);
  const evidence = deriveEvidence(facts);

  const opportunityCard = brief?.cards?.find((c) => c.type === "opportunity");
  const actionCard = brief?.cards?.find((c) => c.type === "action");
  const oneMove = brief?.one_move || actionCard?.headline;
  const gapsTotal = facts.gapsTotal;
  const hasOpportunity = !!opportunityCard || gapsTotal != null || evidence.length > 0;

  // ── Waiting / failure states ─────────────────────────────────────────────
  if (redirecting) {
    return (
      <Shell>
        <div className="text-center" style={{ color: "var(--muted)" }}>
          <p className="text-sm font-semibold">Opening your dashboard…</p>
        </div>
      </Shell>
    );
  }

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

  // ── Screens, keyed so the order can adapt to available content ────────────
  const screenMap: Record<RevealScreenId, React.ReactNode> = {
    // Analyzed — observed/computed metrics
    analyzed: (
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
      </div>
    ),

    // Most notable findings — observed headline + framed interpretation
    findings: (
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
      </div>
    ),

    // Biggest opening + one move
    opportunity: (
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
            {opportunityCard?.headline ?? "Their full range, pricing, and merchandising are now mapped."}
          </p>
          <p className="text-sm leading-relaxed" style={{ color: "var(--text-2)" }}>
            {opportunityCard?.body ?? "Open the Catalog tab on your dashboard to see the market openings StoreScout found across their range, pricing, and merchandising."}
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
      </div>
    ),

    // What we monitor from here
    monitors: (
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
      </div>
    ),

    // Done
    done: (
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
      </div>
    ),
  };

  const order = revealScreenIds({ stats: analyzedStats, findings, hasOpportunity });
  const screens = order.map((k) => screenMap[k]);
  const safeStep = Math.min(step, screens.length - 1);

  return (
    <Shell>
      <div className="w-full max-w-2xl mx-auto">
        {screens[safeStep]}

        {/* Footer nav */}
        <div className="flex items-center justify-between mt-10">
          <div className="flex items-center gap-3">
            <div className="flex items-center gap-1.5">
              {screens.map((_, i) => (
                <button
                  key={i}
                  onClick={() => setStep(i)}
                  aria-label={`Step ${i + 1} of ${screens.length}`}
                  className="h-1.5 rounded-full transition-all"
                  style={{ width: i === safeStep ? 20 : 6, background: i === safeStep ? "var(--accent)" : i < safeStep ? "var(--text-2)" : "var(--border)" }}
                />
              ))}
            </div>
            <span className="num text-[11px]" style={{ color: "var(--muted)" }}>{safeStep + 1} of {screens.length}</span>
          </div>
          <div className="flex items-center gap-4">
            {safeStep < screens.length - 1 && (
              <>
                <button onClick={finish} className="text-xs transition-opacity hover:opacity-70" style={{ color: "var(--muted)" }}>
                  Skip to dashboard
                </button>
                <button
                  onClick={() => setStep(safeStep + 1)}
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
