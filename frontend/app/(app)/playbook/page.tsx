"use client";

import { useEffect, useState } from "react";
import Link from "next/link";
import {
  Zap, ArrowRight, Check, Clock, RefreshCw,
  TrendingUp, Package, Tag, LayoutGrid, AlertTriangle,
  Lock, X, ChevronRight, Users, Flame, Copy,
} from "lucide-react";
import { user as userApi, type PlaybookPlay, type PlaybookResponse, type DraftAsset } from "@/lib/api";
import UpgradeModal from "@/components/UpgradeModal";

// ── persistence ───────────────────────────────────────────────────────────────

const DONE_KEY       = "playbook_done_v1";
const TIMESTAMPS_KEY = "playbook_timestamps_v1";
const FEEDBACK_KEY   = "playbook_feedback_v1";

function getDone(): Set<string> {
  try { return new Set(JSON.parse(localStorage.getItem(DONE_KEY) || "[]")); }
  catch { return new Set(); }
}
function saveDone(ids: Set<string>) {
  try { localStorage.setItem(DONE_KEY, JSON.stringify([...ids])); } catch {}
}
function getTimestamps(): Record<string, string> {
  try { return JSON.parse(localStorage.getItem(TIMESTAMPS_KEY) || "{}"); }
  catch { return {}; }
}
function saveTimestamps(ts: Record<string, string>) {
  try { localStorage.setItem(TIMESTAMPS_KEY, JSON.stringify(ts)); } catch {}
}
function getFeedback(): Record<string, string> {
  try { return JSON.parse(localStorage.getItem(FEEDBACK_KEY) || "{}"); }
  catch { return {}; }
}
function saveFeedback(fb: Record<string, string>) {
  try { localStorage.setItem(FEEDBACK_KEY, JSON.stringify(fb)); } catch {}
}

function computeStreak(ts: Record<string, string>): number {
  const dates = new Set(Object.values(ts).map((iso) => iso.slice(0, 10)));
  if (dates.size === 0) return 0;
  const today = new Date().toISOString().slice(0, 10);
  // If nothing done today, start checking from yesterday (don't break streak mid-day)
  const startOffset = dates.has(today) ? 0 : 1;
  let streak = 0;
  for (let i = startOffset; i <= 90; i++) {
    const d = new Date();
    d.setDate(d.getDate() - i);
    const key = d.toISOString().slice(0, 10);
    if (dates.has(key)) {
      streak++;
    } else {
      break;
    }
  }
  return streak;
}

// ── section meta ──────────────────────────────────────────────────────────────

const SECTION_META = {
  act_now:   { label: "Act Now",                    desc: "Time-sensitive — competitor moves that need a response today",                                         color: "#f87171", dot: "#ef4444" },
  right_now: { label: "Your Position Right Now",    desc: "Derived from your competitors' current catalog — no new move needed to trigger these",                color: "#60a5fa", dot: "#3b82f6" },
  this_week: { label: "Moves to Make This Week",    desc: "Opportunities that are open now and compound the longer you wait",                                    color: "#a3f000", dot: "#a3f000" },
} as const;

const SECTION_ORDER = ["act_now", "right_now", "this_week"] as const;

const DEADLINE_STYLE: Record<string, { bg: string; color: string }> = {
  "right now":  { bg: "rgba(239,68,68,0.12)",  color: "#f87171" },
  "today":      { bg: "rgba(239,68,68,0.10)",  color: "#fb923c" },
  "within 48h": { bg: "rgba(251,146,60,0.10)", color: "#fb923c" },
  "this week":  { bg: "rgba(163,240,0,0.08)",  color: "#a3f000" },
};

function deadlineStyle(d: string) {
  return DEADLINE_STYLE[d] ?? { bg: "rgba(148,163,184,0.08)", color: "#94a3b8" };
}

function typeIcon(t: string): React.ElementType {
  switch (t) {
    case "availability": return Package;
    case "pricing":      return Tag;
    case "catalog":      return LayoutGrid;
    case "positioning":  return TrendingUp;
    case "change":       return AlertTriangle;
    default:             return Zap;
  }
}

// ── feedback ──────────────────────────────────────────────────────────────────

const FEEDBACK_OPTIONS = [
  { key: "worked",       label: "Worked",            emoji: "🔥" },
  { key: "too_early",    label: "Too early to tell", emoji: "⏳" },
  { key: "not_relevant", label: "Not relevant",      emoji: "👎" },
] as const;

function FeedbackRow({ playId, feedback, onFeedback }: {
  playId: string;
  feedback: Record<string, string>;
  onFeedback: (id: string, value: string) => void;
}) {
  if (feedback[playId]) return null;
  return (
    <div className="flex items-center gap-1.5 mt-2.5 flex-wrap">
      <span className="text-[11px] mr-0.5" style={{ color: "var(--muted)" }}>How did it go?</span>
      {FEEDBACK_OPTIONS.map((opt) => (
        <button
          key={opt.key}
          onClick={(e) => { e.stopPropagation(); onFeedback(playId, opt.key); }}
          className="text-[11px] font-medium px-2.5 py-1 rounded-lg transition-all hover:bg-white/[0.08]"
          style={{ background: "rgba(255,255,255,0.04)", color: "var(--muted)", border: "1px solid var(--border)" }}
        >
          {opt.emoji} {opt.label}
        </button>
      ))}
      <button
        onClick={(e) => { e.stopPropagation(); onFeedback(playId, "dismissed"); }}
        className="p-1 rounded transition-opacity hover:opacity-70"
        style={{ color: "var(--muted)" }}
      >
        <X className="w-3 h-3" />
      </button>
    </div>
  );
}

// ── draft asset section ───────────────────────────────────────────────────────

function DraftAssetSection({ asset }: { asset: DraftAsset }) {
  const [copied, setCopied] = useState<string | null>(null);

  function copy(text: string, key: string) {
    navigator.clipboard.writeText(text).then(() => {
      setCopied(key);
      setTimeout(() => setCopied(null), 1500);
    }).catch(() => {});
  }

  if (asset.type === "email") {
    return (
      <div className="space-y-2">
        {asset.subject && (
          <div
            className="flex items-start gap-2 p-3 rounded-xl"
            style={{ background: "var(--bg3)", border: "1px solid var(--border)" }}
          >
            <div className="flex-1 min-w-0">
              <p className="text-[10px] font-bold uppercase tracking-wider mb-1" style={{ color: "var(--muted)" }}>Subject line</p>
              <p className="text-sm font-medium" style={{ color: "var(--text)" }}>{asset.subject}</p>
            </div>
            <button
              onClick={() => copy(asset.subject!, "subject")}
              className="shrink-0 p-1.5 rounded-lg transition-all hover:bg-white/[0.06] mt-0.5"
              style={{ color: copied === "subject" ? "#a3f000" : "var(--muted)" }}
              title="Copy to clipboard"
            >
              {copied === "subject" ? <Check className="w-3.5 h-3.5" /> : <Copy className="w-3.5 h-3.5" />}
            </button>
          </div>
        )}
        {asset.body_opening && (
          <div
            className="flex items-start gap-2 p-3 rounded-xl"
            style={{ background: "var(--bg3)", border: "1px solid var(--border)" }}
          >
            <div className="flex-1 min-w-0">
              <p className="text-[10px] font-bold uppercase tracking-wider mb-1.5" style={{ color: "var(--muted)" }}>Email opening</p>
              <p className="text-sm leading-relaxed" style={{ color: "var(--text)" }}>{asset.body_opening}</p>
            </div>
            <button
              onClick={() => copy(asset.body_opening!, "body")}
              className="shrink-0 p-1.5 rounded-lg transition-all hover:bg-white/[0.06] mt-0.5"
              style={{ color: copied === "body" ? "#a3f000" : "var(--muted)" }}
              title="Copy to clipboard"
            >
              {copied === "body" ? <Check className="w-3.5 h-3.5" /> : <Copy className="w-3.5 h-3.5" />}
            </button>
          </div>
        )}
      </div>
    );
  }

  if (asset.type === "ad") {
    return (
      <div className="space-y-2">
        {asset.headlines && asset.headlines.length > 0 && (
          <div
            className="p-3 rounded-xl"
            style={{ background: "var(--bg3)", border: "1px solid var(--border)" }}
          >
            <div className="flex items-center justify-between mb-2">
              <p className="text-[10px] font-bold uppercase tracking-wider" style={{ color: "var(--muted)" }}>Headlines</p>
              <button
                onClick={() => copy(asset.headlines!.join("\n"), "headlines")}
                className="flex items-center gap-1 text-[10px] font-medium px-2 py-1 rounded-md transition-all hover:bg-white/[0.06]"
                style={{ color: copied === "headlines" ? "#a3f000" : "var(--muted)" }}
              >
                {copied === "headlines" ? <Check className="w-3 h-3" /> : <Copy className="w-3 h-3" />}
                {copied === "headlines" ? "Copied" : "Copy all"}
              </button>
            </div>
            {asset.headlines.map((h, i) => (
              <p
                key={i}
                className="text-sm py-1.5"
                style={{
                  color: "var(--text)",
                  borderBottom: i < asset.headlines!.length - 1 ? "1px solid var(--border)" : undefined,
                }}
              >
                {h}
              </p>
            ))}
          </div>
        )}
        {asset.ad_body && (
          <div
            className="flex items-start gap-2 p-3 rounded-xl"
            style={{ background: "var(--bg3)", border: "1px solid var(--border)" }}
          >
            <div className="flex-1 min-w-0">
              <p className="text-[10px] font-bold uppercase tracking-wider mb-1.5" style={{ color: "var(--muted)" }}>Ad description</p>
              <p className="text-sm leading-relaxed" style={{ color: "var(--text)" }}>{asset.ad_body}</p>
            </div>
            <button
              onClick={() => copy(asset.ad_body!, "ad_body")}
              className="shrink-0 p-1.5 rounded-lg transition-all hover:bg-white/[0.06] mt-0.5"
              style={{ color: copied === "ad_body" ? "#a3f000" : "var(--muted)" }}
              title="Copy to clipboard"
            >
              {copied === "ad_body" ? <Check className="w-3.5 h-3.5" /> : <Copy className="w-3.5 h-3.5" />}
            </button>
          </div>
        )}
      </div>
    );
  }

  return null;
}

// ── detail modal ──────────────────────────────────────────────────────────────

function DetailModal({ play, onClose, onDone, isDone, feedback, onFeedback }: {
  play: PlaybookPlay;
  onClose: () => void;
  onDone: () => void;
  isDone: boolean;
  feedback: Record<string, string>;
  onFeedback: (id: string, value: string) => void;
}) {
  const sectionColor = SECTION_META[play.section as keyof typeof SECTION_META]?.color ?? "#94a3b8";
  const dlStyle = deadlineStyle(play.deadline);
  const Icon = typeIcon(play.type);
  const detail = play.detail;

  return (
    <>
      {/* Backdrop */}
      <div
        className="fixed inset-0 z-40 bg-black/60 backdrop-blur-sm"
        onClick={onClose}
      />

      {/* Centered modal */}
      <div
        className="fixed inset-0 z-50 flex items-center justify-center p-4"
        onClick={onClose}
      >
        <div
          className="w-full max-w-xl max-h-[90vh] overflow-y-auto flex flex-col rounded-2xl"
          style={{ background: "var(--bg2)", border: "1px solid var(--border)" }}
          onClick={(e) => e.stopPropagation()}
        >

        {/* Header */}
        <div
          className="flex items-start gap-3 p-5 sticky top-0 rounded-t-2xl"
          style={{ background: "var(--bg2)", borderBottom: "1px solid var(--border)" }}
        >
          <div
            className="w-9 h-9 rounded-xl flex items-center justify-center shrink-0 mt-0.5"
            style={{ background: `${sectionColor}14` }}
          >
            <Icon className="w-4 h-4" style={{ color: sectionColor }} />
          </div>
          <div className="flex-1 min-w-0">
            <div className="flex items-center gap-2 mb-1 flex-wrap">
              <span
                className="text-[10px] font-bold px-2 py-1 rounded-md"
                style={{ background: dlStyle.bg, color: dlStyle.color }}
              >
                {play.deadline}
              </span>
              <span
                className="text-[10px] font-medium px-1.5 py-0.5 rounded-md"
                style={{ background: "rgba(255,255,255,0.05)", color: "var(--muted)" }}
              >
                {play.hostname}
              </span>
            </div>
            <h2 className="text-sm font-semibold leading-snug" style={{ color: "var(--text)" }}>
              {play.headline}
            </h2>
          </div>
          <button
            onClick={onClose}
            className="shrink-0 p-1.5 rounded-lg hover:bg-white/[0.06] transition-colors"
            style={{ color: "var(--muted)" }}
          >
            <X className="w-4 h-4" />
          </button>
        </div>

        {/* Body */}
        <div className="flex-1 p-5 space-y-6">

          {/* Competitor data table */}
          {detail?.competitors && detail.competitors.length > 0 && (
            <div>
              <div className="flex items-center gap-2 mb-2.5">
                <Users className="w-3.5 h-3.5" style={{ color: "var(--muted)" }} />
                <p className="text-[11px] font-bold uppercase tracking-wider" style={{ color: "var(--muted)" }}>
                  Competitor data
                </p>
              </div>
              <div
                className="rounded-xl overflow-hidden"
                style={{ border: "1px solid var(--border)" }}
              >
                {detail.competitors.map((c, i) => (
                  <div
                    key={i}
                    className="flex items-center justify-between gap-3 px-4 py-2.5"
                    style={i < detail.competitors!.length - 1 ? { borderBottom: "1px solid var(--border)" } : undefined}
                  >
                    <span className="text-xs font-medium" style={{ color: "var(--text)" }}>
                      {c.hostname}
                    </span>
                    <span className="text-xs font-mono" style={{ color: sectionColor }}>
                      {c.metric}
                    </span>
                  </div>
                ))}
              </div>
            </div>
          )}

          {/* Why now */}
          {detail?.why && (
            <div
              className="rounded-xl p-4"
              style={{ background: `${sectionColor}08`, border: `1px solid ${sectionColor}20` }}
            >
              <p className="text-[10px] font-bold uppercase tracking-wider mb-1.5" style={{ color: sectionColor }}>
                Why now
              </p>
              <p className="text-sm leading-relaxed" style={{ color: "var(--muted)" }}>
                {detail.why}
              </p>
            </div>
          )}

          {/* Step-by-step */}
          {detail?.steps && detail.steps.length > 0 && (
            <div>
              <p className="text-[11px] font-bold uppercase tracking-wider mb-3" style={{ color: "var(--muted)" }}>
                How to execute — step by step
              </p>
              <ol className="space-y-3">
                {detail.steps.map((step, i) => (
                  <li key={i} className="flex items-start gap-3">
                    <span
                      className="text-[10px] font-bold w-5 h-5 rounded-full flex items-center justify-center shrink-0 mt-0.5"
                      style={{ background: `${sectionColor}18`, color: sectionColor }}
                    >
                      {i + 1}
                    </span>
                    <span className="text-sm leading-relaxed" style={{ color: "var(--text-2, var(--muted))" }}>
                      {step}
                    </span>
                  </li>
                ))}
              </ol>
            </div>
          )}

          {/* Ready-to-use asset (Evolution 4) */}
          {play.draft_asset && play.draft_asset.type !== "none" && (
            <div
              className="p-4 rounded-xl"
              style={{ background: "rgba(96,165,250,0.04)", border: "1px solid rgba(96,165,250,0.15)" }}
            >
              <p className="text-[10px] font-bold uppercase tracking-wider mb-3" style={{ color: "#60a5fa" }}>
                ▶ {play.draft_asset.label || (play.draft_asset.type === "email" ? "Ready-to-send email" : "Ad copy options")}
              </p>
              <DraftAssetSection asset={play.draft_asset} />
            </div>
          )}

          {/* Expected outcome */}
          {detail?.outcome && (
            <div
              className="rounded-xl p-4"
              style={{ background: "rgba(163,240,0,0.05)", border: "1px solid rgba(163,240,0,0.15)" }}
            >
              <p className="text-[10px] font-bold uppercase tracking-wider mb-1.5" style={{ color: "#a3f000" }}>
                Expected outcome
              </p>
              <p className="text-sm leading-relaxed" style={{ color: "var(--muted)" }}>
                {detail.outcome}
              </p>
            </div>
          )}

          {/* Fallback: show action text if no detail */}
          {!detail && (
            <div>
              <p className="text-[11px] font-bold uppercase tracking-wider mb-2" style={{ color: "var(--muted)" }}>
                What to do
              </p>
              <p className="text-sm leading-relaxed" style={{ color: "var(--muted)" }}>
                {play.action}
              </p>
            </div>
          )}
        </div>

        {/* Footer */}
        <div
          className="p-5 flex flex-col gap-3"
          style={{ borderTop: "1px solid var(--border)" }}
        >
          <div className="flex items-center gap-3">
            <button
              onClick={() => { onDone(); onClose(); }}
              className="flex items-center gap-1.5 text-sm font-semibold px-4 py-2 rounded-xl transition-all hover:brightness-110 flex-1 justify-center"
              style={{
                background: isDone ? "rgba(163,240,0,0.12)" : "rgba(163,240,0,0.15)",
                color: "#a3f000",
                border: "1px solid rgba(163,240,0,0.25)",
              }}
            >
              <Check className="w-4 h-4" />
              {isDone ? "Mark as not done" : "Mark as done"}
            </button>

            {play.competitor_id && play.tab && (
              <Link
                href={`/dashboard/${play.competitor_id}?tab=${play.tab}`}
                onClick={onClose}
                className="flex items-center gap-1.5 text-sm font-medium px-4 py-2 rounded-xl transition-all hover:bg-white/[0.06]"
                style={{ color: "var(--muted)", border: "1px solid var(--border)" }}
              >
                View in dashboard <ChevronRight className="w-3.5 h-3.5" />
              </Link>
            )}
          </div>

          {/* Feedback prompt when play is already done (Evolution 2) */}
          {isDone && (
            <FeedbackRow playId={play.id} feedback={feedback} onFeedback={onFeedback} />
          )}
        </div>

        </div>{/* end modal inner */}
      </div>{/* end centering container */}
    </>
  );
}

// ── play card ─────────────────────────────────────────────────────────────────

function PlayCard({ play, done, onDone, onOpen, isLast }: {
  play: PlaybookPlay;
  done: boolean;
  onDone: () => void;
  onOpen: () => void;
  isLast: boolean;
}) {
  const Icon = typeIcon(play.type);
  const dlStyle = deadlineStyle(play.deadline);
  const sectionColor = SECTION_META[play.section as keyof typeof SECTION_META]?.color ?? "#94a3b8";

  return (
    <div
      className="transition-opacity"
      style={{
        opacity: done ? 0.5 : 1,
        ...(!isLast ? { borderBottom: "1px solid var(--border)" } : {}),
      }}
    >
      <div className="px-4 py-4">
        <div className="flex items-start gap-3">
          <div
            className="w-8 h-8 rounded-lg flex items-center justify-center shrink-0 mt-0.5"
            style={{ background: `${sectionColor}12` }}
          >
            <Icon className="w-4 h-4" style={{ color: sectionColor }} />
          </div>

          <div className="flex-1 min-w-0">
            <div className="flex items-start justify-between gap-2 mb-1">
              <p className="text-sm font-semibold leading-snug" style={{ color: "var(--text)" }}>
                {play.headline}
              </p>
              <span
                className="text-[10px] font-bold px-2 py-1 rounded-md whitespace-nowrap shrink-0"
                style={{ background: dlStyle.bg, color: dlStyle.color }}
              >
                {play.deadline}
              </span>
            </div>

            <span
              className="text-[10px] font-medium px-1.5 py-0.5 rounded-md"
              style={{ background: "rgba(255,255,255,0.05)", color: "var(--muted)" }}
            >
              {play.hostname}
            </span>

            <p className="text-sm leading-relaxed mt-2.5 line-clamp-2" style={{ color: "var(--muted)" }}>
              {play.action}
            </p>

            <div className="flex items-center gap-3 mt-3">
              <button
                onClick={onDone}
                className="flex items-center gap-1.5 text-xs font-semibold px-3 py-1.5 rounded-lg transition-all"
                style={{
                  background: done ? "rgba(163,240,0,0.12)" : "rgba(255,255,255,0.06)",
                  color: done ? "#a3f000" : "var(--muted)",
                  border: done ? "1px solid rgba(163,240,0,0.2)" : "1px solid transparent",
                }}
              >
                <Check className="w-3 h-3" />
                {done ? "Done" : "Mark done"}
              </button>

              <button
                onClick={onOpen}
                className="flex items-center gap-1 text-xs font-semibold ml-auto transition-opacity hover:opacity-70"
                style={{ color: sectionColor }}
              >
                See more <ArrowRight className="w-3 h-3" />
              </button>
            </div>
          </div>
        </div>
      </div>
    </div>
  );
}

// ── section ───────────────────────────────────────────────────────────────────

function PlaySection({ section, plays, done, onDone, onOpen }: {
  section: keyof typeof SECTION_META;
  plays: PlaybookPlay[];
  done: Set<string>;
  onDone: (id: string) => void;
  onOpen: (play: PlaybookPlay) => void;
}) {
  const meta = SECTION_META[section];
  if (plays.length === 0) return null;

  return (
    <div className="fade-up">
      <div className="flex items-center gap-2 mb-2">
        <span className="w-2 h-2 rounded-full shrink-0" style={{ background: meta.dot }} />
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
      <p className="text-xs mb-3" style={{ color: "var(--muted)" }}>{meta.desc}</p>

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
            onOpen={() => onOpen(p)}
            isLast={i === plays.length - 1}
          />
        ))}
      </div>
    </div>
  );
}

// ── skeleton ──────────────────────────────────────────────────────────────────

function Skeleton() {
  return (
    <div className="space-y-8">
      {[1, 2].map((s) => (
        <div key={s}>
          <div className="h-3 w-36 rounded-full animate-pulse mb-3" style={{ background: "var(--bg3)" }} />
          <div className="rounded-2xl overflow-hidden" style={{ background: "var(--bg-card)", border: "1px solid var(--border)" }}>
            {[1, 2].map((i) => (
              <div key={i} className="p-4 animate-pulse" style={i === 1 ? { borderBottom: "1px solid var(--border)" } : undefined}>
                <div className="flex gap-3">
                  <div className="w-8 h-8 rounded-lg shrink-0" style={{ background: "var(--bg3)" }} />
                  <div className="flex-1 space-y-2">
                    <div className="h-4 rounded-full w-3/4" style={{ background: "var(--bg3)" }} />
                    <div className="h-3 rounded-full w-full" style={{ background: "var(--bg3)" }} />
                    <div className="h-3 rounded-full w-1/2" style={{ background: "var(--bg3)" }} />
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

// ── main ──────────────────────────────────────────────────────────────────────

export default function PlaybookPage() {
  const [data,        setData]        = useState<PlaybookResponse | null>(null);
  const [loading,     setLoading]     = useState(true);
  const [refreshing,  setRefreshing]  = useState(false);
  const [done,        setDone]        = useState<Set<string>>(new Set());
  const [feedback,    setFeedback]    = useState<Record<string, string>>({});
  const [tab,         setTab]         = useState<"active" | "done">("active");
  const [detailPlay,  setDetailPlay]  = useState<PlaybookPlay | null>(null);
  const [upgradeOpen, setUpgradeOpen] = useState(false);

  function load(isRefresh = false) {
    if (isRefresh) setRefreshing(true); else setLoading(true);
    userApi.playbook()
      .then(setData)
      .catch(() => setData(null))
      .finally(() => { setLoading(false); setRefreshing(false); });
  }

  useEffect(() => {
    setDone(getDone());
    setFeedback(getFeedback());
    load();
  }, []);

  function markDone(id: string) {
    setDone((prev) => {
      const next = new Set(prev);
      if (next.has(id)) {
        next.delete(id);
      } else {
        next.add(id);
        // Record first-completion timestamp for streak tracking (don't overwrite if re-done)
        const ts = getTimestamps();
        if (!ts[id]) {
          ts[id] = new Date().toISOString();
          saveTimestamps(ts);
        }
      }
      saveDone(next);
      return next;
    });
  }

  function handleFeedback(id: string, value: string) {
    setFeedback((prev) => {
      const next = { ...prev, [id]: value };
      saveFeedback(next);
      return next;
    });
  }

  const streak = computeStreak(getTimestamps());

  if (loading) {
    return (
      <div className="space-y-6">
        <div>
          <div className="h-7 w-48 rounded-full animate-pulse mb-2" style={{ background: "var(--bg3)" }} />
          <div className="h-4 w-64 rounded-full animate-pulse" style={{ background: "var(--bg3)" }} />
        </div>
        <Skeleton />
      </div>
    );
  }

  if (!data || data.competitor_count === 0) {
    return (
      <div className="space-y-6">
        <h1 className="text-2xl font-bold" style={{ color: "var(--text)" }}>Your Playbook</h1>
        <div className="rounded-2xl p-10 text-center" style={{ background: "var(--bg-card)", border: "1px solid var(--border)" }}>
          <Zap className="w-8 h-8 mx-auto mb-3" style={{ color: "var(--accent)" }} />
          <p className="font-semibold mb-1" style={{ color: "var(--text)" }}>No competitors tracked yet</p>
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

  const plays       = data.plays || [];
  const activePlays = plays.filter((p) => !done.has(p.id));
  const donePlays   = plays.filter((p) => done.has(p.id));

  const bySection = (list: PlaybookPlay[]) => ({
    act_now:   list.filter((p) => p.section === "act_now"),
    right_now: list.filter((p) => p.section === "right_now"),
    this_week: list.filter((p) => p.section === "this_week"),
  });

  const activeSections = bySection(activePlays);

  return (
    <>
      <div className="space-y-6">

        {/* ── Header ─────────────────────────────────────────────────────── */}
        <div className="flex items-start justify-between gap-4">
          <div>
            <div className="flex items-center gap-2 mb-1 flex-wrap">
              <h1 className="text-2xl font-bold" style={{ color: "var(--text)" }}>Your Playbook</h1>
              {activePlays.length > 0 && (
                <span
                  className="text-xs font-bold px-2 py-1 rounded-full"
                  style={{ background: "rgba(163,240,0,0.12)", color: "#a3f000" }}
                >
                  {activePlays.length} open
                </span>
              )}
              {streak > 0 && (
                <span
                  className="text-[10px] font-bold px-2 py-1 rounded-full flex items-center gap-1"
                  style={{ background: "rgba(251,146,60,0.12)", color: "#fb923c" }}
                  title="Consecutive days you've executed at least one play"
                >
                  <Flame className="w-3 h-3" />
                  {streak}-day streak
                </span>
              )}
              {data.ai_source && (
                <span
                  className="text-[10px] font-bold px-2 py-1 rounded-full flex items-center gap-1"
                  style={{ background: "rgba(96,165,250,0.12)", color: "#60a5fa" }}
                >
                  <Zap className="w-3 h-3" />
                  AI-powered
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

        {/* ── AI generating banner ────────────────────────────────────────── */}
        {data.ai_generating && !data.ai_source && (
          <div
            className="flex items-center gap-2.5 px-4 py-3 rounded-xl text-xs"
            style={{
              background: "rgba(96,165,250,0.06)",
              border: "1px solid rgba(96,165,250,0.18)",
              color: "#60a5fa",
            }}
          >
            <RefreshCw className="w-3.5 h-3.5 animate-spin shrink-0" />
            <span>
              <span className="font-bold">AI analysis in progress</span>
              <span style={{ color: "var(--muted)" }}> — Claude is reviewing your competitors. Refresh in ~30 seconds for AI-powered plays.</span>
            </span>
          </div>
        )}

        {/* ── Tabs ───────────────────────────────────────────────────────── */}
        <div
          className="flex items-center rounded-xl p-0.5 w-fit"
          style={{ background: "var(--bg3)" }}
        >
          {(["active", "done"] as const).map((t) => {
            const count = t === "active" ? activePlays.length : donePlays.length;
            return (
              <button
                key={t}
                onClick={() => setTab(t)}
                className="flex items-center gap-2 px-4 py-1.5 rounded-lg text-sm font-medium transition-all"
                style={{
                  background: tab === t ? "var(--bg-card)" : undefined,
                  color: tab === t ? "var(--text)" : "var(--muted)",
                }}
              >
                {t === "active" ? "Active" : "Done"}
                {count > 0 && (
                  <span
                    className="text-[10px] font-bold px-1.5 py-0.5 rounded-full min-w-[18px] text-center"
                    style={{
                      background: tab === t ? "rgba(163,240,0,0.15)" : "rgba(255,255,255,0.08)",
                      color: tab === t ? "#a3f000" : "var(--muted)",
                    }}
                  >
                    {count}
                  </span>
                )}
              </button>
            );
          })}
        </div>

        {/* ── Active tab ─────────────────────────────────────────────────── */}
        {tab === "active" && (
          <>
            {activePlays.length === 0 ? (
              plays.length === 0 && data.ai_generating ? (
                <div className="rounded-2xl p-8 text-center" style={{ background: "var(--bg-card)", border: "1px solid var(--border)" }}>
                  <RefreshCw className="w-6 h-6 mx-auto mb-3 animate-spin" style={{ color: "#60a5fa" }} />
                  <p className="font-semibold mb-1" style={{ color: "var(--text)" }}>Generating your first AI-powered plays</p>
                  <p className="text-sm" style={{ color: "var(--muted)" }}>
                    Claude is reviewing your {data.competitor_count} competitor{data.competitor_count !== 1 ? "s" : ""}. Refresh in ~30 seconds.
                  </p>
                </div>
              ) : (
                <div className="rounded-2xl p-8 text-center" style={{ background: "var(--bg-card)", border: "1px solid var(--border)" }}>
                  <Check className="w-6 h-6 mx-auto mb-2" style={{ color: "#a3f000" }} />
                  <p className="font-semibold mb-1" style={{ color: "var(--text)" }}>All caught up</p>
                  <p className="text-sm" style={{ color: "var(--muted)" }}>
                    Everything&apos;s marked done. Your playbook refreshes after each competitor scan.
                  </p>
                </div>
              )
            ) : (
              <div className="space-y-8">
                {SECTION_ORDER.map((section) => (
                  <PlaySection
                    key={section}
                    section={section}
                    plays={activeSections[section]}
                    done={done}
                    onDone={markDone}
                    onOpen={setDetailPlay}
                  />
                ))}
              </div>
            )}

            {/* Locked CTA */}
            {data.locked && (
              <div
                className="rounded-2xl px-5 py-5 flex items-center justify-between gap-4"
                style={{ background: "rgba(163,240,0,.06)", border: "1px dashed rgba(163,240,0,.3)" }}
              >
                <div className="flex items-center gap-3">
                  <div className="w-9 h-9 rounded-xl flex items-center justify-center shrink-0" style={{ background: "rgba(168,255,0,.08)", border: "1px solid rgba(168,255,0,.14)" }}>
                    <Lock className="w-4 h-4" style={{ color: "var(--accent)" }} />
                  </div>
                  <div>
                    <p className="text-sm font-semibold" style={{ color: "var(--text)" }}>
                      {data.locked_count ?? "More"} plays locked
                    </p>
                    <p className="text-xs" style={{ color: "var(--muted)" }}>
                      Upgrade to Pro to see every move across all your competitors.
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
          </>
        )}

        {/* ── Done tab ───────────────────────────────────────────────────── */}
        {tab === "done" && (
          <div>
            {donePlays.length === 0 ? (
              <div className="rounded-2xl p-8 text-center" style={{ background: "var(--bg-card)", border: "1px solid var(--border)" }}>
                <Clock className="w-6 h-6 mx-auto mb-2" style={{ color: "var(--muted)" }} />
                <p className="font-semibold mb-1" style={{ color: "var(--text)" }}>Nothing done yet</p>
                <p className="text-sm" style={{ color: "var(--muted)" }}>
                  Mark plays as done and they&apos;ll appear here so you can track what you&apos;ve acted on.
                </p>
              </div>
            ) : (
              <div
                className="rounded-2xl overflow-hidden"
                style={{ background: "var(--bg-card)", border: "1px solid var(--border)" }}
              >
                {donePlays.map((p, i) => (
                  <div
                    key={p.id}
                    className="px-4 py-3"
                    style={i < donePlays.length - 1 ? { borderBottom: "1px solid var(--border)" } : undefined}
                  >
                    <div className="flex items-center gap-3">
                      <Check className="w-3.5 h-3.5 shrink-0" style={{ color: "#a3f000" }} />
                      <p className="text-sm flex-1 truncate" style={{ color: "var(--muted)" }}>
                        {p.headline}
                      </p>
                      <div className="flex items-center gap-2 shrink-0">
                        {feedback[p.id] && feedback[p.id] !== "dismissed" && (
                          <span className="text-sm">
                            {FEEDBACK_OPTIONS.find((f) => f.key === feedback[p.id])?.emoji}
                          </span>
                        )}
                        <button
                          onClick={() => setDetailPlay(p)}
                          className="text-[11px] font-medium transition-opacity hover:opacity-70"
                          style={{ color: "var(--muted)" }}
                        >
                          Details
                        </button>
                        <button
                          onClick={() => markDone(p.id)}
                          className="text-[11px] font-medium transition-opacity hover:opacity-70"
                          style={{ color: "var(--accent)" }}
                        >
                          Undo
                        </button>
                      </div>
                    </div>
                    {/* Feedback prompt (Evolution 2) */}
                    <FeedbackRow playId={p.id} feedback={feedback} onFeedback={handleFeedback} />
                  </div>
                ))}
              </div>
            )}
          </div>
        )}

      </div>

      {/* ── Detail modal ───────────────────────────────────────────────────── */}
      {detailPlay && (
        <DetailModal
          play={detailPlay}
          onClose={() => setDetailPlay(null)}
          onDone={() => markDone(detailPlay.id)}
          isDone={done.has(detailPlay.id)}
          feedback={feedback}
          onFeedback={handleFeedback}
        />
      )}

      <UpgradeModal open={upgradeOpen} onClose={() => setUpgradeOpen(false)} trigger="general" />
    </>
  );
}
