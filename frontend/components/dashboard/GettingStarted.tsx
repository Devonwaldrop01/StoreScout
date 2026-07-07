"use client";

import { useEffect, useState } from "react";
import Link from "next/link";
import { Check, ArrowRight, X, Rocket, Zap } from "lucide-react";
import { openFeedback, requestFeedbackOnce } from "@/lib/feedbackPrompt";

type Step = { id: string; label: string; auto?: boolean; href?: string; action?: boolean };

const DONE_KEY = "ss_getting_started";
const DISMISS_KEY = "ss_getting_started_dismissed";

function readSet(key: string): Set<string> {
  try {
    const raw = localStorage.getItem(key);
    return raw ? new Set(JSON.parse(raw)) : new Set();
  } catch {
    return new Set();
  }
}

interface Props {
  firstCompetitorId?: string;
  competitorAdded: boolean;
  firstScanDone?: boolean;
  isFree?: boolean;
  onUpgrade: () => void;
}

/**
 * Orientation checklist for ALL new accounts so day 1 rewards progress
 * instead of showing empty widgets. Every step links to a surface that
 * already exists; free users get an upgrade upsell as the final row, paid
 * users get "track another competitor" instead. Completion + dismissal
 * persist in localStorage.
 */
export function GettingStarted({ firstCompetitorId, competitorAdded, firstScanDone, isFree = true, onUpgrade }: Props) {
  const [done, setDone] = useState<Set<string>>(new Set());
  const [dismissed, setDismissed] = useState(false);
  const [playbookTried, setPlaybookTried] = useState(false);

  useEffect(() => {
    setDone(readSet(DONE_KEY));
    setDismissed(localStorage.getItem(DISMISS_KEY) === "1");
    // Step 4 auto-completes if they've marked any playbook play done
    try {
      const pb = localStorage.getItem("playbook_done_v1");
      setPlaybookTried(!!pb && JSON.parse(pb).length > 0);
    } catch { /* ignore */ }
  }, []);

  function markDone(id: string) {
    setDone((prev) => {
      const next = new Set(prev);
      next.add(id);
      try { localStorage.setItem(DONE_KEY, JSON.stringify([...next])); } catch {}
      return next;
    });
  }

  function dismiss() {
    setDismissed(true);
    try { localStorage.setItem(DISMISS_KEY, "1"); } catch {}
  }

  const detailHref = firstCompetitorId ? `/dashboard/${firstCompetitorId}` : "/competitors";

  const steps: Step[] = [
    { id: "add", label: "Add your first competitor", auto: competitorAdded },
    { id: "scan", label: "First scan completed", auto: firstScanDone },
    { id: "brief", label: "Read your competitor's Scout Brief", href: detailHref },
    { id: "pricing", label: "Explore their pricing & winning products", href: `${detailHref}?tab=pricing` },
    { id: "playbook", label: "Try a move from your Playbook", href: "/playbook", auto: playbookTried },
    { id: "connect", label: "Connect your store for personalized plays", href: "/settings?tab=integrations" },
    { id: "feedback", label: "Tell us what you think", action: true },
  ];

  const isDone = (s: { id: string; auto?: boolean }) => !!s.auto || done.has(s.id);
  const completed = steps.filter(isDone).length;

  // Once the core surfaces have been explored, ask for feedback once (gated).
  const CORE = ["add", "brief", "pricing", "playbook", "connect"];
  const coreComplete = CORE.every((id) => {
    const s = steps.find((x) => x.id === id);
    return s ? isDone(s) : false;
  });
  useEffect(() => {
    if (coreComplete) requestFeedbackOnce();
  }, [coreComplete]);

  if (dismissed || completed >= steps.length) return null;

  return (
    <div
      className="mb-6 rounded-md p-5 fade-up relative"
      style={{ background: "var(--bg-card)", border: "1px solid rgba(255,178,36,.18)" }}
    >
      <button
        onClick={dismiss}
        className="absolute top-4 right-4 p-1 rounded-lg transition-opacity hover:opacity-70"
        style={{ color: "var(--muted)" }}
        aria-label="Dismiss"
      >
        <X className="w-4 h-4" />
      </button>

      <div className="flex items-center gap-2 mb-1">
        <Rocket className="w-4 h-4" style={{ color: "var(--accent)" }} />
        <h2 className="text-base font-bold" style={{ color: "var(--text)" }}>Get started</h2>
      </div>
      <p className="text-xs mb-4" style={{ color: "var(--muted)" }}>
        {completed} of {steps.length} done — a few quick wins to get value from your competitor.
      </p>

      {/* Progress bar */}
      <div className="h-1.5 rounded-full mb-4 overflow-hidden" style={{ background: "var(--bg3)" }}>
        <div
          className="h-full rounded-full transition-all"
          style={{ width: `${(completed / steps.length) * 100}%`, background: "var(--accent)" }}
        />
      </div>

      <div className="space-y-1.5">
        {steps.map((s) => {
          const complete = isDone(s);
          const content = (
            <div
              className="flex items-center gap-3 px-3 py-2.5 rounded-md transition-all"
              style={{ background: complete ? "transparent" : "var(--bg3)" }}
            >
              <div
                className="w-5 h-5 rounded-full flex items-center justify-center shrink-0"
                style={{
                  background: complete ? "var(--emerald)" : "transparent",
                  border: complete ? "none" : "1.5px solid var(--border)",
                }}
              >
                {complete && <Check className="w-3 h-3" style={{ color: "var(--ink)" }} />}
              </div>
              <span
                className="text-sm flex-1"
                style={{ color: complete ? "var(--muted)" : "var(--text)", textDecoration: complete ? "line-through" : "none" }}
              >
                {s.label}
              </span>
              {!complete && (s.href || s.action) && <ArrowRight className="w-4 h-4 shrink-0" style={{ color: "var(--accent)" }} />}
            </div>
          );
          if (s.href) {
            return (
              <Link key={s.id} href={s.href} onClick={() => markDone(s.id)} className="block">
                {content}
              </Link>
            );
          }
          if (s.action) {
            return (
              <button
                key={s.id}
                onClick={() => { openFeedback("How's StoreScout so far?"); markDone(s.id); }}
                className="w-full text-left"
              >
                {content}
              </button>
            );
          }
          return <div key={s.id}>{content}</div>;
        })}

        {/* Final row — upgrade upsell for free users, next-competitor nudge for paid */}
        {isFree ? (
          <button onClick={onUpgrade} className="w-full text-left">
            <div
              className="flex items-center gap-3 px-3 py-2.5 rounded-md transition-all hover:brightness-110"
              style={{ background: "rgba(255,178,36,.06)", border: "1px solid rgba(255,178,36,.18)" }}
            >
              <div className="w-5 h-5 rounded-full flex items-center justify-center shrink-0" style={{ background: "rgba(255,178,36,.15)" }}>
                <Zap className="w-3 h-3" style={{ color: "var(--accent)" }} />
              </div>
              <span className="text-sm flex-1 font-medium" style={{ color: "var(--text)" }}>
                Track a 2nd competitor &amp; unlock alerts
              </span>
              <span className="text-xs font-bold shrink-0" style={{ color: "var(--accent)" }}>Upgrade</span>
            </div>
          </button>
        ) : (
          <Link href="/competitors" className="block">
            <div
              className="flex items-center gap-3 px-3 py-2.5 rounded-md transition-all hover:brightness-110"
              style={{ background: "var(--bg3)", border: "1px solid var(--border)" }}
            >
              <div className="w-5 h-5 rounded-full flex items-center justify-center shrink-0" style={{ border: "1.5px solid var(--border)" }}>
                <Zap className="w-3 h-3" style={{ color: "var(--text-2)" }} />
              </div>
              <span className="text-sm flex-1 font-medium" style={{ color: "var(--text)" }}>
                Track another competitor — coverage compounds
              </span>
              <ArrowRight className="w-4 h-4 shrink-0" style={{ color: "var(--muted)" }} />
            </div>
          </Link>
        )}
      </div>
    </div>
  );
}
