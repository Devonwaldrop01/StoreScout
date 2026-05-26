"use client";

import { useEffect, useState } from "react";
import Link from "next/link";
import {
  Zap, ArrowRight, Check, Clock, RefreshCw,
  TrendingUp, Package, Tag, LayoutGrid, AlertTriangle,
  ChevronDown, ChevronUp, Lock,
} from "lucide-react";
import { user as userApi, type PlaybookPlay, type PlaybookResponse } from "@/lib/api";
import UpgradeModal from "@/components/UpgradeModal";

// ── constants ────────────────────────────────────────────────────────────────

const DONE_KEY = "playbook_done_v1";

function getDone(): Set<string> {
  try {
    const raw = localStorage.getItem(DONE_KEY);
    return raw ? new Set(JSON.parse(raw)) : new Set();
  } catch { return new Set(); }
}

function saveDone(ids: Set<string>) {
  try { localStorage.setItem(DONE_KEY, JSON.stringify([...ids])); } catch {}
}

const SECTION_META: Record<string, { label: string; description: string; color: string; dot: string }> = {
  act_now: {
    label: "Act Now",
    description: "Time-sensitive — competitor moves that need a response today",
    color: "#f87171",
    dot: "#ef4444",
  },
  right_now: {
    label: "Your Position Right Now",
    description: "Derived from your competitors' current catalog — no new move needed to trigger these",
    color: "#60a5fa",
    dot: "#3b82f6",
  },
  this_week: {
    label: "Moves to Make This Week",
    description: "Opportunities that are open now and compound the longer you wait",
    color: "#a3f000",
    dot: "#a3f000",
  },
};

const SECTION_ORDER: Array<"act_now" | "right_now" | "this_week"> = [
  "act_now",
  "right_now",
  "this_week",
];

const DEADLINE_STYLE: Record<string, { bg: string; color: string }> = {
  "right now":   { bg: "rgba(239,68,68,0.12)",   color: "#f87171" },
  "today":       { bg: "rgba(239,68,68,0.10)",    color: "#fb923c" },
  "within 48h":  { bg: "rgba(251,146,60,0.10)",   color: "#fb923c" },
  "this week":   { bg: "rgba(163,240,0,0.08)",    color: "#a3f000" },
  "this month":  { bg: "rgba(96,165,250,0.08)",   color: "#60a5fa" },
};

function deadlineStyle(deadline: string) {
  return DEADLINE_STYLE[deadline] ?? { bg: "rgba(148,163,184,0.08)", color: "#94a3b8" };
}

function typeIcon(type: string): React.ElementType {
  switch (type) {
    case "availability": return Package;
    case "pricing":      return Tag;
    case "catalog":      return LayoutGrid;
    case "positioning":  return TrendingUp;
    case "change":       return AlertTriangle;
    default:             return Zap;
  }
}

// ── play card ────────────────────────────────────────────────────────────────

interface PlayCardProps {
  play: PlaybookPlay;
  done: boolean;
  onDone: () => void;
  isLast: boolean;
}

function PlayCard({ play, done, onDone, isLast }: PlayCardProps) {
  const [expanded, setExpanded] = useState(true);
  const Icon = typeIcon(play.type);
  const dlStyle = deadlineStyle(play.deadline);
  const sectionColor = SECTION_META[play.section]?.color ?? "#94a3b8";

  if (done && !expanded) {
    return (
      <div
        className="flex items-center gap-3 px-4 py-2.5 opacity-40 cursor-pointer hover:opacity-60 transition-opacity"
        style={!isLast ? { borderBottom: "1px solid var(--border)" } : undefined}
        onClick={() => setExpanded(true)}
      >
        <Check className="w-3.5 h-3.5 shrink-0" style={{ color: "#a3f000" }} />
        <p className="text-xs line-through flex-1 truncate" style={{ color: "var(--muted)" }}>
          {play.headline}
        </p>
        <span className="text-[10px]" style={{ color: "var(--muted)" }}>undo</span>
      </div>
    );
  }

  return (
    <div
      className="transition-all"
      style={{
        opacity: done ? 0.55 : 1,
        ...(!isLast ? { borderBottom: "1px solid var(--border)" } : {}),
      }}
    >
      <div className="px-4 py-4">
        {/* Header */}
        <div className="flex items-start gap-3">
          {/* Icon */}
          <div
            className="w-8 h-8 rounded-lg flex items-center justify-center shrink-0 mt-0.5"
            style={{ background: `${sectionColor}12` }}
          >
            <Icon className="w-4 h-4" style={{ color: sectionColor }} />
          </div>

          <div className="flex-1 min-w-0">
            {/* Headline + deadline */}
            <div className="flex items-start justify-between gap-2 mb-1">
              <p
                className="text-sm font-semibold leading-snug"
                style={{
                  color: "var(--text)",
                  textDecoration: done ? "line-through" : undefined,
                }}
              >
                {play.headline}
              </p>
              <span
                className="text-[10px] font-bold px-2 py-1 rounded-md whitespace-nowrap shrink-0"
                style={{ background: dlStyle.bg, color: dlStyle.color }}
              >
                {play.deadline}
              </span>
            </div>

            {/* Hostname chip */}
            <span
              className="text-[10px] font-medium px-1.5 py-0.5 rounded-md"
              style={{ background: "rgba(255,255,255,0.05)", color: "var(--muted)" }}
            >
              {play.hostname}
            </span>

            {/* Action text */}
            <p className="text-sm leading-relaxed mt-2.5" style={{ color: "var(--muted)" }}>
              {play.action}
            </p>

            {/* Footer actions */}
            <div className="flex items-center gap-3 mt-3">
              <button
                onClick={onDone}
                className="flex items-center gap-1.5 text-xs font-semibold px-3 py-1.5 rounded-lg transition-all hover:brightness-110"
                style={{
                  background: done ? "rgba(163,240,0,0.12)" : "rgba(255,255,255,0.06)",
                  color: done ? "#a3f000" : "var(--muted)",
                  border: done ? "1px solid rgba(163,240,0,0.2)" : "1px solid transparent",
                }}
              >
                <Check className="w-3 h-3" />
                {done ? "Done" : "Mark done"}
              </button>

              {play.competitor_id && play.tab && (
                <Link
                  href={`/dashboard/${play.competitor_id}?tab=${play.tab}`}
                  className="flex items-center gap-1 text-xs font-medium transition-opacity hover:opacity-70 ml-auto"
                  style={{ color: sectionColor }}
                >
                  View <ArrowRight className="w-3 h-3" />
                </Link>
              )}
            </div>
          </div>

          {/* Collapse toggle for done items */}
          {done && (
            <button
              onClick={() => setExpanded(false)}
              className="shrink-0 opacity-40 hover:opacity-80 transition-opacity"
            >
              <ChevronUp className="w-4 h-4" style={{ color: "var(--muted)" }} />
            </button>
          )}
        </div>
      </div>
    </div>
  );
}

// ── section ───────────────────────────────────────────────────────────────────

function PlaySection({
  section,
  plays,
  done,
  onDone,
}: {
  section: "act_now" | "right_now" | "this_week";
  plays: PlaybookPlay[];
  done: Set<string>;
  onDone: (id: string) => void;
}) {
  const meta = SECTION_META[section];
  if (plays.length === 0) return null;

  return (
    <div className="fade-up">
      {/* Section header */}
      <div className="flex items-center gap-2 mb-3">
        <span
          className="w-2 h-2 rounded-full shrink-0"
          style={{ background: meta.dot }}
        />
        <h2 className="text-xs font-bold uppercase tracking-wider" style={{ color: meta.color }}>
          {meta.label}
        </h2>
        <span
          className="text-[10px] px-1.5 py-0.5 rounded-full font-bold"
          style={{ background: `${meta.color}18`, color: meta.color }}
        >
          {plays.length}
        </span>
      </div>
      <p className="text-xs mb-3" style={{ color: "var(--muted)" }}>
        {meta.description}
      </p>

      <div
        className="rounded-2xl overflow-hidden"
        style={{ background: "var(--bg-card)", border: "1px solid var(--border)" }}
      >
        {plays.map((p, i) => (
          <PlayCard
            key={p.id}
            play={p}
            done={done.has(p.id)}
            onDone={() => onDone(p.id)}
            isLast={i === plays.length - 1}
          />
        ))}
      </div>
    </div>
  );
}

// ── loading skeleton ──────────────────────────────────────────────────────────

function PlaybookSkeleton() {
  return (
    <div className="space-y-8">
      {[1, 2, 3].map((s) => (
        <div key={s}>
          <div className="h-3 w-32 rounded-full animate-pulse mb-3" style={{ background: "var(--bg3)" }} />
          <div className="rounded-2xl overflow-hidden" style={{ background: "var(--bg-card)", border: "1px solid var(--border)" }}>
            {[1, 2].map((i) => (
              <div
                key={i}
                className="p-4 animate-pulse"
                style={i === 1 ? { borderBottom: "1px solid var(--border)" } : undefined}
              >
                <div className="flex gap-3">
                  <div className="w-8 h-8 rounded-lg shrink-0" style={{ background: "var(--bg3)" }} />
                  <div className="flex-1 space-y-2">
                    <div className="h-4 rounded-full w-3/4" style={{ background: "var(--bg3)" }} />
                    <div className="h-3 rounded-full w-full" style={{ background: "var(--bg3)" }} />
                    <div className="h-3 rounded-full w-2/3" style={{ background: "var(--bg3)" }} />
                  </div>
                </div>
              </div>
            ))}
          </div>
        </div>
      ))}
    </div>
  );
}

// ── main page ─────────────────────────────────────────────────────────────────

export default function PlaybookPage() {
  const [data,        setData]        = useState<PlaybookResponse | null>(null);
  const [loading,     setLoading]     = useState(true);
  const [refreshing,  setRefreshing]  = useState(false);
  const [done,        setDone]        = useState<Set<string>>(new Set());
  const [upgradeOpen, setUpgradeOpen] = useState(false);
  const [showDone,    setShowDone]    = useState(false);

  function load(isRefresh = false) {
    if (isRefresh) setRefreshing(true);
    else setLoading(true);
    userApi.playbook()
      .then(setData)
      .catch(() => setData(null))
      .finally(() => { setLoading(false); setRefreshing(false); });
  }

  useEffect(() => {
    setDone(getDone());
    load();
  }, []);

  function markDone(id: string) {
    setDone((prev) => {
      const next = new Set(prev);
      next.has(id) ? next.delete(id) : next.add(id);
      saveDone(next);
      return next;
    });
  }

  // ── loading ──────────────────────────────────────────────────────────────
  if (loading) {
    return (
      <div className="space-y-6">
        <div>
          <div className="h-7 w-48 rounded-full animate-pulse mb-2" style={{ background: "var(--bg3)" }} />
          <div className="h-4 w-64 rounded-full animate-pulse" style={{ background: "var(--bg3)" }} />
        </div>
        <PlaybookSkeleton />
      </div>
    );
  }

  // ── no competitors ────────────────────────────────────────────────────────
  if (!data || data.competitor_count === 0) {
    return (
      <div className="space-y-6">
        <div>
          <h1 className="text-2xl font-bold" style={{ color: "var(--text)" }}>Your Playbook</h1>
          <p className="text-sm mt-1" style={{ color: "var(--muted)" }}>
            Track a competitor to unlock your competitive playbook.
          </p>
        </div>
        <div
          className="rounded-2xl p-10 text-center"
          style={{ background: "var(--bg-card)", border: "1px solid var(--border)" }}
        >
          <Zap className="w-8 h-8 mx-auto mb-3" style={{ color: "var(--accent)" }} />
          <p className="font-semibold mb-1" style={{ color: "var(--text)" }}>
            No competitors tracked yet
          </p>
          <p className="text-sm mb-4" style={{ color: "var(--muted)" }}>
            Add a Shopify competitor and your playbook will be ready after the first scan — usually within 2 minutes.
          </p>
          <Link
            href="/dashboard"
            className="inline-flex items-center gap-2 text-sm font-semibold px-4 py-2 rounded-xl transition-all hover:brightness-110"
            style={{ background: "var(--accent)", color: "#0a0a0f" }}
          >
            Add competitor <ArrowRight className="w-4 h-4" />
          </Link>
        </div>
      </div>
    );
  }

  const plays = data.plays || [];

  // Split into sections — done plays stay in their section (user can see/undo them)
  const bySection = {
    act_now:   plays.filter((p) => p.section === "act_now"),
    right_now: plays.filter((p) => p.section === "right_now"),
    this_week: plays.filter((p) => p.section === "this_week"),
  };

  const totalPlays = plays.length;
  const doneCount  = plays.filter((p) => done.has(p.id)).length;
  const activeCount = totalPlays - doneCount;

  return (
    <div className="space-y-8">

      {/* ── Page header ──────────────────────────────────────────────────── */}
      <div className="flex items-start justify-between gap-4">
        <div>
          <div className="flex items-center gap-2 mb-1">
            <h1 className="text-2xl font-bold" style={{ color: "var(--text)" }}>
              Your Playbook
            </h1>
            {activeCount > 0 && (
              <span
                className="text-xs font-bold px-2 py-1 rounded-full"
                style={{ background: "rgba(163,240,0,0.12)", color: "#a3f000" }}
              >
                {activeCount} open
              </span>
            )}
          </div>
          <p className="text-sm" style={{ color: "var(--muted)" }}>
            What to do right now, based on what your competitors are doing —{" "}
            <span style={{ color: "var(--text-2, var(--muted))" }}>
              {data.competitor_count} competitor{data.competitor_count !== 1 ? "s" : ""} analysed
            </span>
          </p>
        </div>

        <button
          onClick={() => load(true)}
          disabled={refreshing}
          className="flex items-center gap-1.5 text-xs font-medium px-3 py-2 rounded-lg transition-all hover:bg-white/[0.06] disabled:opacity-40"
          style={{ color: "var(--muted)", border: "1px solid var(--border)" }}
        >
          <RefreshCw className={`w-3.5 h-3.5 ${refreshing ? "animate-spin" : ""}`} />
          Refresh
        </button>
      </div>

      {/* ── How this works callout (first visit feel) ─────────────────────── */}
      {plays.length > 0 && (
        <div
          className="rounded-xl px-4 py-3 flex items-start gap-3"
          style={{ background: "rgba(168,255,0,0.04)", border: "1px solid rgba(168,255,0,0.10)" }}
        >
          <Zap className="w-4 h-4 mt-0.5 shrink-0" style={{ color: "var(--accent)" }} />
          <p className="text-xs leading-relaxed" style={{ color: "var(--muted)" }}>
            <span style={{ color: "var(--text)" }}>Two streams feed your playbook:</span>
            {" "}<span style={{ color: "#f87171" }}>Act Now</span> plays come from detected competitor moves.{" "}
            <span style={{ color: "#60a5fa" }}>Right Now</span> plays come from the current state of their catalog — always populated after your first scan, no waiting required.
          </p>
        </div>
      )}

      {/* ── Sections ─────────────────────────────────────────────────────── */}
      {SECTION_ORDER.map((section) => (
        <PlaySection
          key={section}
          section={section}
          plays={bySection[section]}
          done={done}
          onDone={markDone}
        />
      ))}

      {/* ── All done state ────────────────────────────────────────────────── */}
      {totalPlays > 0 && activeCount === 0 && (
        <div
          className="rounded-2xl p-8 text-center fade-in"
          style={{ background: "var(--bg-card)", border: "1px solid var(--border)" }}
        >
          <Check className="w-6 h-6 mx-auto mb-2" style={{ color: "#a3f000" }} />
          <p className="font-semibold mb-1" style={{ color: "var(--text)" }}>
            All caught up
          </p>
          <p className="text-sm" style={{ color: "var(--muted)" }}>
            You've worked through everything. Your playbook refreshes after each competitor scan.
          </p>
        </div>
      )}

      {/* ── Empty state (no plays generated yet) ─────────────────────────── */}
      {plays.length === 0 && !data.locked && (
        <div
          className="rounded-2xl p-8 text-center"
          style={{ background: "var(--bg-card)", border: "1px solid var(--border)" }}
        >
          <Clock className="w-6 h-6 mx-auto mb-2" style={{ color: "var(--muted)" }} />
          <p className="font-semibold mb-1" style={{ color: "var(--text)" }}>
            Building your playbook
          </p>
          <p className="text-sm" style={{ color: "var(--muted)" }}>
            Your competitor scans are still in progress. Check back in a few minutes — your first playbook will be ready once the scan completes.
          </p>
        </div>
      )}

      {/* ── Locked / upgrade CTA ─────────────────────────────────────────── */}
      {data.locked && (
        <div
          className="rounded-2xl px-5 py-5 flex items-center justify-between gap-4"
          style={{ background: "rgba(163,240,0,.06)", border: "1px dashed rgba(163,240,0,.3)" }}
        >
          <div className="flex items-center gap-3">
            <div
              className="w-9 h-9 rounded-xl flex items-center justify-center shrink-0"
              style={{ background: "rgba(168,255,0,.08)", border: "1px solid rgba(168,255,0,.14)" }}
            >
              <Lock className="w-4 h-4" style={{ color: "var(--accent)" }} />
            </div>
            <div>
              <p className="text-sm font-semibold" style={{ color: "var(--text)" }}>
                {data.locked_count ?? "More"} plays locked
              </p>
              <p className="text-xs" style={{ color: "var(--muted)" }}>
                Upgrade to Pro to see every competitive move across all your competitors.
              </p>
            </div>
          </div>
          <button
            onClick={() => setUpgradeOpen(true)}
            className="shrink-0 text-xs font-bold px-4 py-2 rounded-xl transition-all hover:brightness-110"
            style={{ background: "var(--accent)", color: "#0a0a0f" }}
          >
            Upgrade
          </button>
        </div>
      )}

      <UpgradeModal open={upgradeOpen} onClose={() => setUpgradeOpen(false)} trigger="general" />
    </div>
  );
}
