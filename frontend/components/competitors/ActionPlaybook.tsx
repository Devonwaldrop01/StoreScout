"use client";

import { useEffect, useState } from "react";
import { X, ArrowRight, Zap, Shield, TrendingUp } from "lucide-react";
import Link from "next/link";
import { user as userApi, type ActionItem } from "@/lib/api";

const TYPE_CONFIG = {
  threat: {
    Icon: Shield,
    color: "var(--red)",
    bg: "rgba(239,68,68,.07)",
    border: "rgba(239,68,68,.2)",
    label: "Threat",
  },
  opportunity: {
    Icon: TrendingUp,
    color: "var(--accent)",
    bg: "rgba(168,255,0,.07)",
    border: "rgba(168,255,0,.18)",
    label: "Opportunity",
  },
  gap: {
    Icon: Zap,
    color: "var(--blue)",
    bg: "rgba(96,165,250,.07)",
    border: "rgba(96,165,250,.18)",
    label: "Gap",
  },
} as const;

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

  const visible = items.filter((item) => !dismissed.has(item.id));

  if (loading) {
    return (
      <div className="mb-6 fade-in">
        <div className="flex items-center gap-2 mb-3">
          <Zap className="w-4 h-4" style={{ color: "var(--accent)" }} />
          <span className="text-xs font-bold uppercase tracking-wider" style={{ color: "var(--muted)" }}>
            Your Move
          </span>
        </div>
        <div className="grid grid-cols-1 sm:grid-cols-3 gap-3">
          {[1, 2, 3].map((i) => (
            <div key={i} className="h-28 rounded-xl animate-pulse" style={{ background: "var(--bg3)" }} />
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
            style={{ background: "rgba(168,255,0,.08)", border: "1px solid rgba(168,255,0,.14)" }}
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
          style={{ background: "var(--accent)", color: "#0a0a0f" }}
        >
          Upgrade
        </Link>
      </div>
    );
  }

  if (!loading && visible.length === 0) return null;

  return (
    <div className="mb-6 fade-up">
      <div className="flex items-center gap-2 mb-3">
        <Zap className="w-4 h-4" style={{ color: "var(--accent)" }} />
        <span className="text-xs font-bold uppercase tracking-wider" style={{ color: "var(--muted)" }}>
          Your Move
        </span>
      </div>

      <div className="grid grid-cols-1 sm:grid-cols-3 gap-3">
        {visible.slice(0, 3).map((item) => {
          const cfg = TYPE_CONFIG[item.type] ?? TYPE_CONFIG.opportunity;
          const { Icon } = cfg;
          return (
            <div
              key={item.id}
              className="relative rounded-xl p-4 fade-in"
              style={{ background: cfg.bg, border: `1px solid ${cfg.border}` }}
            >
              {/* Dismiss */}
              <button
                onClick={() => dismiss(item.id)}
                className="absolute top-3 right-3 p-0.5 rounded opacity-40 hover:opacity-80 transition-opacity"
                style={{ color: "var(--muted)" }}
                aria-label="Dismiss"
              >
                <X className="w-3.5 h-3.5" />
              </button>

              {/* Header */}
              <div className="flex items-center gap-2 mb-2.5 pr-5">
                <div
                  className="w-6 h-6 rounded-md flex items-center justify-center shrink-0"
                  style={{ background: `${cfg.color}18` }}
                >
                  <Icon className="w-3.5 h-3.5" style={{ color: cfg.color }} />
                </div>
                <div className="flex items-center gap-1.5 min-w-0">
                  <span
                    className="text-[10px] font-bold uppercase tracking-wider"
                    style={{ color: cfg.color }}
                  >
                    {cfg.label}
                  </span>
                  <span className="text-[10px]" style={{ color: "var(--muted)" }}>·</span>
                  <span
                    className="text-[10px] truncate"
                    style={{ color: "var(--muted)" }}
                  >
                    {item.hostname}
                  </span>
                </div>
              </div>

              {/* Headline */}
              <p className="text-xs font-semibold leading-snug mb-1.5" style={{ color: "var(--text)" }}>
                {item.headline}
              </p>

              {/* Action text */}
              <p className="text-[11px] leading-relaxed mb-3" style={{ color: "var(--muted)" }}>
                {item.action_text}
              </p>

              {/* Footer */}
              <div className="flex items-center justify-between">
                <span className="text-[10px]" style={{ color: "var(--muted)" }}>
                  {item.context}
                </span>
                <Link
                  href={`/dashboard/${item.competitor_id}?tab=${item.tab}`}
                  className="flex items-center gap-1 text-[10px] font-semibold transition-opacity hover:opacity-70"
                  style={{ color: cfg.color }}
                >
                  View <ArrowRight className="w-2.5 h-2.5" />
                </Link>
              </div>
            </div>
          );
        })}
      </div>
    </div>
  );
}
