"use client";

import { useEffect, useState } from "react";
import { Zap } from "lucide-react";
import Link from "next/link";
import { user as userApi, type ActionItem } from "@/lib/api";
import { ActionCard } from "@/components/ui";

const DISMISSED_KEY = "playbook_dismissed";

function getDismissed(): Set<string> {
  try {
    const raw = localStorage.getItem(DISMISSED_KEY);
    return raw ? new Set(JSON.parse(raw)) : new Set();
  } catch {
    return new Set();
  }
}

function saveDismissed(ids: Set<string>) {
  try {
    localStorage.setItem(DISMISSED_KEY, JSON.stringify([...ids]));
  } catch {}
}

interface Props {
  competitorCount: number;
}

export function ActionPlaybook({ competitorCount }: Props) {
  const [items, setItems] = useState<ActionItem[]>([]);
  const [locked, setLocked] = useState(false);
  const [loading, setLoading] = useState(true);
  const [dismissed, setDismissed] = useState<Set<string>>(new Set());

  useEffect(() => {
    setDismissed(getDismissed());
    userApi.actionItems()
      .then((r) => {
        setItems(r.data || []);
        setLocked(r.locked ?? false);
      })
      .catch(() => {})
      .finally(() => setLoading(false));
  }, []);

  function dismiss(id: string) {
    setDismissed((prev) => {
      const next = new Set(prev);
      next.add(id);
      saveDismissed(next);
      return next;
    });
  }

  if (competitorCount === 0) return null;

  const visibleRaw = items.filter((item) => !dismissed.has(item.id));

  // Deduplicate: if two items share the same instructional text (same template applied to
  // different competitors), show only the highest-priority one — prevents "X has stock gaps /
  // Y has stock gaps" repeating side-by-side.
  const seenHeadlineKeys = new Set<string>();
  const visible = visibleRaw.filter((item) => {
    const key = item.headline.replace(/^[\w.-]+\.[\w]+\s+/, "").toLowerCase().substring(0, 50);
    if (seenHeadlineKeys.has(key)) return false;
    seenHeadlineKeys.add(key);
    return true;
  });

  if (loading) {
    return (
      <div className="mb-6 fade-in">
        <div className="flex items-center gap-2 mb-3">
          <Zap className="w-4 h-4" style={{ color: "var(--accent)" }} />
          <h2 className="text-base font-bold" style={{ color: "var(--text)" }}>Your Move</h2>
        </div>
        <div className="grid grid-cols-1 sm:grid-cols-3 gap-3">
          {[1, 2, 3].map((i) => (
            <div key={i} className="h-36 rounded-xl animate-pulse" style={{ background: "var(--bg3)" }} />
          ))}
        </div>
      </div>
    );
  }

  if (!loading && visible.length === 0 && !locked) {
    return (
      <div
        className="mb-6 rounded-xl px-5 py-3 fade-in flex items-center gap-3"
        style={{ background: "var(--bg3)", border: "1px solid var(--border)" }}
      >
        <Zap className="w-3.5 h-3.5 shrink-0" style={{ color: "var(--muted)" }} />
        <p className="text-xs" style={{ color: "var(--muted)" }}>
          <span className="font-medium" style={{ color: "var(--text-2)" }}>Your Move</span>
          {" · "}No urgent competitive moves detected in the last 7 days. You&apos;ll see action recommendations here when a competitor makes a significant pricing or catalog change.
        </p>
      </div>
    );
  }

  if (locked) {
    return (
      <div
        className="mb-6 rounded-xl px-5 py-4 fade-in flex items-center justify-between gap-4"
        style={{ background: "var(--bg3)", border: "1px solid var(--border)" }}
      >
        <div className="flex items-center gap-3">
          <div
            className="w-8 h-8 rounded-lg flex items-center justify-center shrink-0"
            style={{ background: "rgba(59,130,246,.08)", border: "1px solid rgba(59,130,246,.14)" }}
          >
            <Zap className="w-4 h-4" style={{ color: "var(--accent)" }} />
          </div>
          <div>
            <p className="text-sm font-semibold" style={{ color: "var(--text)" }}>
              Unlock "Your Move" recommendations
            </p>
            <p className="text-xs" style={{ color: "var(--muted)" }}>
              Pro plan analyses your competitors and tells you exactly what to do next.
            </p>
          </div>
        </div>
        <Link
          href="/settings?tab=billing"
          className="shrink-0 text-xs font-bold px-3 py-1.5 rounded-lg transition-all hover:brightness-110"
          style={{ background: "var(--accent)", color: "#ffffff" }}
        >
          Upgrade
        </Link>
      </div>
    );
  }

  if (!loading && visible.length === 0) {
    return (
      <div
        className="mb-6 rounded-xl px-5 py-3 fade-in flex items-center justify-between gap-3"
        style={{ background: "var(--bg3)", border: "1px solid var(--border)" }}
      >
        <div className="flex items-center gap-3 min-w-0">
          <Zap className="w-3.5 h-3.5 shrink-0" style={{ color: "var(--muted)" }} />
          <p className="text-xs" style={{ color: "var(--muted)" }}>
            <span className="font-medium" style={{ color: "var(--text-2)" }}>Your Move</span>
            {" · "}All recommendations reviewed.
          </p>
        </div>
        <button
          onClick={() => {
            try { localStorage.removeItem(DISMISSED_KEY); } catch {}
            setDismissed(new Set());
          }}
          className="shrink-0 text-[11px] font-medium px-2.5 py-1 rounded-lg transition-all hover:bg-white/[0.06]"
          style={{ color: "var(--muted)", border: "1px solid var(--border)" }}
        >
          Show again
        </button>
      </div>
    );
  }

  const shown = visible.slice(0, 3);
  // Size the grid to the item count so 1 or 2 items fill the row — no empty columns
  const gridCols = shown.length === 1 ? "sm:grid-cols-1" : shown.length === 2 ? "sm:grid-cols-2" : "sm:grid-cols-3";

  return (
    <div className="mb-6 fade-up">
      <div className="flex items-center gap-2 mb-1">
        <Zap className="w-4 h-4" style={{ color: "var(--accent)" }} />
        <h2 className="text-base font-bold" style={{ color: "var(--text)" }}>Your Move</h2>
      </div>
      <p className="text-xs mb-3" style={{ color: "var(--muted)" }}>
        What to do about the most important competitor activity right now.
      </p>

      <div className={`grid grid-cols-1 ${gridCols} gap-3`}>
        {shown.map((item) => (
          <ActionCard
            key={item.id}
            type={item.type as "threat" | "opportunity" | "gap"}
            headline={item.headline}
            action_text={item.action_text}
            context={item.context}
            hostname={item.hostname}
            competitor_id={item.competitor_id}
            tab={item.tab}
            onDismiss={() => dismiss(item.id)}
          />
        ))}
      </div>
    </div>
  );
}
