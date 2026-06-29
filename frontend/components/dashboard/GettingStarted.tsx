"use client";

import { useEffect, useState } from "react";
import Link from "next/link";
import { Check, ArrowRight, X, Rocket, Zap } from "lucide-react";

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
  onUpgrade: () => void;
}

/**
 * Orientation checklist for new free users so they're never left at a dead end
 * after the first scan. Every step links to a surface that already exists; the
 * last step is the upgrade upsell. Completion + dismissal persist in localStorage.
 */
export function GettingStarted({ firstCompetitorId, competitorAdded, onUpgrade }: Props) {
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

  const steps = [
    { id: "add", label: "Add your first competitor", auto: competitorAdded, href: undefined as string | undefined },
    { id: "brief", label: "Read your competitor's Scout Brief", href: detailHref },
    { id: "pricing", label: "Explore their pricing & winning products", href: `${detailHref}?tab=pricing` },
    { id: "playbook", label: "Try a move from your Playbook", href: "/playbook", auto: playbookTried },
    { id: "connect", label: "Connect your store for personalized plays", href: "/settings?tab=integrations" },
  ];

  const isDone = (s: { id: string; auto?: boolean }) => !!s.auto || done.has(s.id);
  const completed = steps.filter(isDone).length;

  if (dismissed || completed >= steps.length) return null;

  return (
    <div
      className="mb-6 rounded-2xl p-5 fade-up relative"
      style={{ background: "var(--bg-card)", border: "1px solid rgba(59,130,246,.18)" }}
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
              className="flex items-center gap-3 px-3 py-2.5 rounded-xl transition-all"
              style={{ background: complete ? "transparent" : "var(--bg3)" }}
            >
              <div
                className="w-5 h-5 rounded-full flex items-center justify-center shrink-0"
                style={{
                  background: complete ? "var(--emerald)" : "transparent",
                  border: complete ? "none" : "1.5px solid var(--border)",
                }}
              >
                {complete && <Check className="w-3 h-3" style={{ color: "#fff" }} />}
              </div>
              <span
                className="text-sm flex-1"
                style={{ color: complete ? "var(--muted)" : "var(--text)", textDecoration: complete ? "line-through" : "none" }}
              >
                {s.label}
              </span>
              {!complete && s.href && <ArrowRight className="w-4 h-4 shrink-0" style={{ color: "var(--accent)" }} />}
            </div>
          );
          return s.href ? (
            <Link key={s.id} href={s.href} onClick={() => markDone(s.id)} className="block">
              {content}
            </Link>
          ) : (
            <div key={s.id}>{content}</div>
          );
        })}

        {/* Upsell step — always shown, doesn't count toward completion */}
        <button onClick={onUpgrade} className="w-full text-left">
          <div
            className="flex items-center gap-3 px-3 py-2.5 rounded-xl transition-all hover:brightness-110"
            style={{ background: "rgba(59,130,246,.06)", border: "1px solid rgba(59,130,246,.18)" }}
          >
            <div className="w-5 h-5 rounded-full flex items-center justify-center shrink-0" style={{ background: "rgba(59,130,246,.15)" }}>
              <Zap className="w-3 h-3" style={{ color: "var(--accent)" }} />
            </div>
            <span className="text-sm flex-1 font-medium" style={{ color: "var(--text)" }}>
              Track a 2nd competitor &amp; unlock alerts
            </span>
            <span className="text-xs font-bold shrink-0" style={{ color: "var(--accent)" }}>Upgrade</span>
          </div>
        </button>
      </div>
    </div>
  );
}
