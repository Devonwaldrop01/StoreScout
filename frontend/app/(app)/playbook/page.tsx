"use client";

import { useEffect, useState } from "react";
import Link from "next/link";
import {
  Zap, ArrowRight, Check, Clock, RefreshCw,
  TrendingUp, Package, Tag, LayoutGrid, AlertTriangle,
  Lock, X, ChevronRight, Users, Flame, Copy,
} from "lucide-react";
import {
  user as userApi, playbookItems as itemsApi,
  type PlaybookPlay, type PlaybookResponse, type DraftAsset, type PlaybookItem,
} from "@/lib/api";
import UpgradeModal from "@/components/UpgradeModal";
import { EmptyStateCard, LockedValueCard } from "@/components/ui";
import { RecommendationCard } from "@/components/playbook/RecommendationCard";

// A play is a Playbook-2.0 strategic recommendation when it carries the rich
// strategy-first fields (vs a legacy template/change play).
const isRichRec = (p: PlaybookPlay) => !!(p.objective || (p.execution_paths && p.execution_paths.length > 0));

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

// Per-play step checklist progress — the unit of "actually doing it"
const STEPS_KEY = "playbook_steps_v1";
function getSteps(): Record<string, boolean[]> {
  try { return JSON.parse(localStorage.getItem(STEPS_KEY) || "{}"); }
  catch { return {}; }
}
function saveSteps(steps: Record<string, boolean[]>) {
  try { localStorage.setItem(STEPS_KEY, JSON.stringify(steps)); } catch {}
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
  act_now:   { label: "Act Now",      desc: "Time-sensitive — competitor moves that need a response today",                           color: "#F2555A", dot: "#F2555A" },
  right_now: { label: "Right Now",    desc: "Derived from your competitors' current catalog — no new move needed to trigger these",   color: "#A8AC9E", dot: "#A8AC9E" },
  this_week: { label: "This Week",    desc: "Opportunities that are open now and compound the longer you wait",                      color: "#6C7164", dot: "#6C7164" },
} as const;

const SECTION_ORDER = ["act_now", "right_now", "this_week"] as const;

const DEADLINE_STYLE: Record<string, { bg: string; color: string }> = {
  "right now":  { bg: "rgba(242,85,90,0.12)",  color: "#F2555A" },
  "today":      { bg: "rgba(255,178,36,0.10)",  color: "var(--amber)" },
  "within 48h": { bg: "rgba(255,178,36,0.10)", color: "var(--amber)" },
  "this week":  { bg: "rgba(236,238,230,.06)",  color: "var(--text-2)" },
};

function deadlineStyle(d: string) {
  return DEADLINE_STYLE[d] ?? { bg: "rgba(148,163,184,0.08)", color: "#A8AC9E" };
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
            className="flex items-start gap-2 p-3 rounded-md"
            style={{ background: "var(--bg3)", border: "1px solid var(--border)" }}
          >
            <div className="flex-1 min-w-0">
              <p className="text-[10px] font-bold uppercase tracking-wider mb-1" style={{ color: "var(--muted)" }}>Subject line</p>
              <p className="text-sm font-medium" style={{ color: "var(--text)" }}>{asset.subject}</p>
            </div>
            <button
              onClick={() => copy(asset.subject!, "subject")}
              className="shrink-0 p-1.5 rounded-lg transition-all hover:bg-white/[0.06] mt-0.5"
              style={{ color: copied === "subject" ? "#4CC38A" : "var(--muted)" }}
              title="Copy to clipboard"
            >
              {copied === "subject" ? <Check className="w-3.5 h-3.5" /> : <Copy className="w-3.5 h-3.5" />}
            </button>
          </div>
        )}
        {asset.body_opening && (
          <div
            className="flex items-start gap-2 p-3 rounded-md"
            style={{ background: "var(--bg3)", border: "1px solid var(--border)" }}
          >
            <div className="flex-1 min-w-0">
              <p className="text-[10px] font-bold uppercase tracking-wider mb-1.5" style={{ color: "var(--muted)" }}>Email opening</p>
              <p className="text-sm leading-relaxed" style={{ color: "var(--text)" }}>{asset.body_opening}</p>
            </div>
            <button
              onClick={() => copy(asset.body_opening!, "body")}
              className="shrink-0 p-1.5 rounded-lg transition-all hover:bg-white/[0.06] mt-0.5"
              style={{ color: copied === "body" ? "#4CC38A" : "var(--muted)" }}
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
            className="p-3 rounded-md"
            style={{ background: "var(--bg3)", border: "1px solid var(--border)" }}
          >
            <div className="flex items-center justify-between mb-2">
              <p className="text-[10px] font-bold uppercase tracking-wider" style={{ color: "var(--muted)" }}>Headlines</p>
              <button
                onClick={() => copy(asset.headlines!.join("\n"), "headlines")}
                className="flex items-center gap-1 text-[10px] font-medium px-2 py-1 rounded-md transition-all hover:bg-white/[0.06]"
                style={{ color: copied === "headlines" ? "#4CC38A" : "var(--muted)" }}
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
            className="flex items-start gap-2 p-3 rounded-md"
            style={{ background: "var(--bg3)", border: "1px solid var(--border)" }}
          >
            <div className="flex-1 min-w-0">
              <p className="text-[10px] font-bold uppercase tracking-wider mb-1.5" style={{ color: "var(--muted)" }}>Ad description</p>
              <p className="text-sm leading-relaxed" style={{ color: "var(--text)" }}>{asset.ad_body}</p>
            </div>
            <button
              onClick={() => copy(asset.ad_body!, "ad_body")}
              className="shrink-0 p-1.5 rounded-lg transition-all hover:bg-white/[0.06] mt-0.5"
              style={{ color: copied === "ad_body" ? "#4CC38A" : "var(--muted)" }}
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
  const sectionColor = SECTION_META[play.section as keyof typeof SECTION_META]?.color ?? "#A8AC9E";
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
          className="w-full max-w-xl max-h-[90vh] overflow-y-auto flex flex-col rounded-md"
          style={{ background: "var(--bg2)", border: "1px solid var(--border)" }}
          onClick={(e) => e.stopPropagation()}
        >

        {/* Header */}
        <div
          className="flex items-start gap-3 p-5 sticky top-0 rounded-t-2xl"
          style={{ background: "var(--bg2)", borderBottom: "1px solid var(--border)" }}
        >
          <div
            className="w-9 h-9 rounded-md flex items-center justify-center shrink-0 mt-0.5"
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
                className="rounded-md overflow-hidden"
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
              className="rounded-md p-4"
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
              className="p-4 rounded-md"
              style={{ background: "var(--bg3)", border: "1px solid var(--border)" }}
            >
              <p className="text-[10px] font-bold uppercase tracking-wider mb-3" style={{ color: "var(--text-2)" }}>
                ▶ {play.draft_asset.label || (play.draft_asset.type === "email" ? "Ready-to-send email" : "Ad copy options")}
              </p>
              <DraftAssetSection asset={play.draft_asset} />
            </div>
          )}

          {/* Expected outcome */}
          {detail?.outcome && (
            <div
              className="rounded-md p-4"
              style={{ background: "var(--bg3)", border: "1px solid var(--border)" }}
            >
              <p className="text-[10px] font-bold uppercase tracking-wider mb-1.5" style={{ color: "var(--text-2)" }}>
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
              className="flex items-center gap-1.5 text-sm font-semibold px-4 py-2 rounded-md transition-all hover:brightness-110 flex-1 justify-center"
              style={{
                background: isDone ? "rgba(76,195,138,.12)" : "var(--accent)",
                color: isDone ? "var(--emerald)" : "var(--ink)",
                border: isDone ? "1px solid rgba(76,195,138,.25)" : "1px solid transparent",
              }}
            >
              <Check className="w-4 h-4" />
              {isDone ? "Mark as not done" : "Mark as done"}
            </button>

            {play.competitor_id && play.tab && (
              <Link
                href={`/dashboard/${play.competitor_id}?tab=${play.tab}`}
                onClick={onClose}
                className="flex items-center gap-1.5 text-sm font-medium px-4 py-2 rounded-md transition-all hover:bg-white/[0.06]"
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

// ── interactive step checklist ────────────────────────────────────────────────

function StepChecklist({ steps, checked, onToggle }: {
  steps: string[];
  checked: boolean[];
  onToggle: (idx: number) => void;
}) {
  if (steps.length === 0) return null;
  const doneCount = checked.filter(Boolean).length;
  return (
    <div>
      <div className="flex items-center justify-between mb-2">
        <p className="label-caps">Steps</p>
        <span className="num text-[10px]" style={{ color: doneCount > 0 ? "var(--emerald)" : "var(--muted)" }}>
          {doneCount}/{steps.length}
        </span>
      </div>
      <div className="space-y-1">
        {steps.map((step, i) => {
          const isChecked = !!checked[i];
          return (
            <button
              key={i}
              onClick={(e) => { e.stopPropagation(); onToggle(i); }}
              className="w-full flex items-start gap-2.5 px-3 py-2 rounded text-left transition-colors hover:bg-white/[.03]"
              style={{ background: "var(--bg3)", border: "1px solid var(--border)" }}
            >
              <span
                className="w-4 h-4 rounded-sm flex items-center justify-center shrink-0 mt-px transition-colors"
                style={{
                  background: isChecked ? "var(--emerald)" : "transparent",
                  border: isChecked ? "1px solid var(--emerald)" : "1px solid var(--muted)",
                }}
              >
                {isChecked && <Check className="w-3 h-3" style={{ color: "var(--ink)" }} />}
              </span>
              <span
                className="text-xs leading-relaxed flex-1"
                style={{ color: isChecked ? "var(--muted)" : "var(--text-2)", textDecoration: isChecked ? "line-through" : "none" }}
              >
                {step}
              </span>
            </button>
          );
        })}
      </div>
    </div>
  );
}

// ── focus card — the single play to do FIRST ──────────────────────────────────

function FocusCard({ play, onDone, onOpen, stepsChecked, onToggleStep }: {
  play: PlaybookPlay;
  onDone: () => void;
  onOpen: () => void;
  stepsChecked: boolean[];
  onToggleStep: (idx: number) => void;
}) {
  const sectionMeta = SECTION_META[play.section as keyof typeof SECTION_META];
  const sectionColor = sectionMeta?.color ?? "#A8AC9E";
  const steps = play.detail?.steps ?? [];
  const why = play.detail?.why;
  const outcome = play.detail?.outcome;
  const dl = deadlineStyle(play.deadline);

  return (
    <div className="panel panel-tick overflow-hidden fade-up">
      <div className="px-5 pt-4 pb-5">
        <div className="flex items-center gap-2 flex-wrap mb-2">
          <p className="tick-label tick-label--live">Up next</p>
          <span className="label-caps" style={{ color: sectionColor }}>{sectionMeta?.label ?? play.section}</span>
          <span className="num text-[10px] px-1.5 py-0.5 rounded" style={{ background: dl.bg, color: dl.color }}>{play.deadline}</span>
          <span className="num text-[10px] ml-auto" style={{ color: "var(--muted)" }}>{play.hostname}</span>
        </div>

        <p className="text-lg font-bold leading-snug mb-1" style={{ color: "var(--text)" }}>
          {play.headline}
        </p>
        {why && (
          <p className="text-xs leading-relaxed mb-3" style={{ color: "var(--text-2)" }}>
            <span className="font-semibold" style={{ color: "var(--muted)" }}>Why now · </span>{why}
          </p>
        )}

        <div className="space-y-4">
          <StepChecklist steps={steps} checked={stepsChecked} onToggle={onToggleStep} />

          {play.draft_asset && (
            <div>
              <p className="label-caps mb-2">Ready to paste</p>
              <DraftAssetSection asset={play.draft_asset} />
            </div>
          )}

          {outcome && (
            <p className="text-xs leading-relaxed px-3 py-2 rounded" style={{ background: "var(--bg3)", color: "var(--muted)" }}>
              <span className="font-semibold" style={{ color: "var(--emerald)" }}>Expected outcome · </span>{outcome}
            </p>
          )}
        </div>

        <div className="flex items-center gap-3 mt-4">
          <button
            onClick={onDone}
            className="flex items-center gap-1.5 text-xs font-bold px-4 py-2 rounded transition-all hover:brightness-110"
            style={{ background: "var(--accent)", color: "var(--ink)" }}
          >
            <Check className="w-3.5 h-3.5" />
            Mark done
          </button>
          <button
            onClick={onOpen}
            className="flex items-center gap-1 text-xs font-medium ml-auto transition-opacity hover:opacity-70"
            style={{ color: "var(--muted)" }}
          >
            Full detail <ArrowRight className="w-3 h-3" />
          </button>
        </div>
      </div>
    </div>
  );
}

// ── queue row — compact, expands in place ─────────────────────────────────────

function PlayCard({ play, done, onDone, onOpen, isLast, stepsChecked, onToggleStep }: {
  play: PlaybookPlay;
  done: boolean;
  onDone: () => void;
  onOpen: () => void;
  isLast: boolean;
  stepsChecked: boolean[];
  onToggleStep: (idx: number) => void;
}) {
  const [expanded, setExpanded] = useState(false);
  const sectionMeta = SECTION_META[play.section as keyof typeof SECTION_META];
  const sectionColor = sectionMeta?.color ?? "#A8AC9E";
  const steps = play.detail?.steps ?? [];
  const startedCount = stepsChecked.filter(Boolean).length;
  const why = play.detail?.why;
  const dl = deadlineStyle(play.deadline);

  return (
    <div
      className="transition-opacity"
      style={{
        opacity: done ? 0.5 : 1,
        ...(!isLast ? { borderBottom: "1px solid var(--border)" } : {}),
        borderLeft: `3px solid ${sectionColor}`,
      }}
    >
      {/* Compact row — click to expand in place */}
      <button
        onClick={() => setExpanded((v) => !v)}
        className="w-full text-left px-4 py-3 transition-colors hover:bg-white/[.015]"
      >
        <div className="flex items-center gap-2 flex-wrap">
          <p className="text-sm font-semibold leading-snug flex-1 min-w-[200px]" style={{ color: "var(--text)" }}>
            {play.headline}
          </p>
          {startedCount > 0 && steps.length > 0 && (
            <span className="num text-[10px] px-1.5 py-0.5 rounded" style={{ background: "rgba(76,195,138,.12)", color: "var(--emerald)" }}>
              {startedCount}/{steps.length}
            </span>
          )}
          <span className="num text-[10px] px-1.5 py-0.5 rounded shrink-0" style={{ background: dl.bg, color: dl.color }}>{play.deadline}</span>
          <span className="num text-[10px] shrink-0" style={{ color: "var(--muted)" }}>{play.hostname}</span>
          {expanded
            ? <ChevronRight className="w-3.5 h-3.5 shrink-0 rotate-90 transition-transform" style={{ color: "var(--muted)" }} />
            : <ChevronRight className="w-3.5 h-3.5 shrink-0 transition-transform" style={{ color: "var(--muted)" }} />}
        </div>
        {!expanded && (
          <p className="text-xs leading-relaxed mt-1 line-clamp-1" style={{ color: "var(--muted)" }}>
            {play.action}
          </p>
        )}
      </button>

      {/* Expanded working area */}
      {expanded && (
        <div className="px-4 pb-4 space-y-4">
          {why && (
            <p className="text-xs leading-relaxed" style={{ color: "var(--text-2)" }}>
              <span className="font-semibold" style={{ color: "var(--muted)" }}>Why now · </span>{why}
            </p>
          )}
          <StepChecklist steps={steps} checked={stepsChecked} onToggle={onToggleStep} />
          {play.draft_asset && (
            <div>
              <p className="label-caps mb-2">Ready to paste</p>
              <DraftAssetSection asset={play.draft_asset} />
            </div>
          )}
          <div className="flex items-center gap-3">
            <button
              onClick={(e) => { e.stopPropagation(); onDone(); }}
              className="flex items-center gap-1.5 text-xs font-semibold px-3 py-1.5 rounded transition-all"
              style={{
                background: done ? "rgba(76,195,138,0.10)" : "rgba(255,255,255,0.06)",
                color: done ? "var(--emerald)" : "var(--text-2)",
                border: done ? "1px solid rgba(76,195,138,0.2)" : "1px solid var(--border)",
              }}
            >
              <Check className="w-3 h-3" />
              {done ? "Done" : "Mark done"}
            </button>
            <button
              onClick={(e) => { e.stopPropagation(); onOpen(); }}
              className="flex items-center gap-1 text-xs font-medium ml-auto transition-opacity hover:opacity-70"
              style={{ color: "var(--muted)" }}
            >
              Full detail <ArrowRight className="w-3 h-3" />
            </button>
          </div>
        </div>
      )}
    </div>
  );
}

// ── section ───────────────────────────────────────────────────────────────────

function PlaySection({ section, plays, done, onDone, onOpen, steps, onToggleStep }: {
  section: keyof typeof SECTION_META;
  plays: PlaybookPlay[];
  done: Set<string>;
  onDone: (id: string) => void;
  onOpen: (play: PlaybookPlay) => void;
  steps: Record<string, boolean[]>;
  onToggleStep: (playId: string, idx: number) => void;
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

      {plays.every(isRichRec) ? (
        // Playbook 2.0 — strategy-first recommendation cards (each self-contained)
        <div className="space-y-3">
          {plays.map((p) => (
            <RecommendationCard key={p.id} play={p} done={done.has(p.id)} onDone={() => onDone(p.id)} />
          ))}
        </div>
      ) : (
        // Legacy template/change plays — the boxed step-list card
        <div className="rounded-md overflow-hidden" style={{ background: "var(--bg-card)", border: "1px solid var(--border)" }}>
          {plays.map((p, i) => (
            isRichRec(p) ? (
              <RecommendationCard key={p.id} play={p} done={done.has(p.id)} onDone={() => onDone(p.id)} />
            ) : (
              <PlayCard
                key={p.id}
                play={p}
                done={done.has(p.id)}
                onDone={() => onDone(p.id)}
                onOpen={() => onOpen(p)}
                isLast={i === plays.length - 1}
                stepsChecked={steps[p.id] ?? []}
                onToggleStep={(idx) => onToggleStep(p.id, idx)}
              />
            )
          ))}
        </div>
      )}
    </div>
  );
}

// ── saved moves (persisted playbook items — the action loop) ──────────────────

const SAVED_PRIORITY: Record<string, { color: string; label: string }> = {
  high:   { color: "#F2555A", label: "High" },
  medium: { color: "#A8AC9E", label: "Medium" },
  low:    { color: "#6C7164", label: "Low" },
};

const OUTCOME_OPTIONS = [
  { key: "worked" as const,       label: "Worked",            emoji: "🔥" },
  { key: "too_early" as const,    label: "Too early to tell", emoji: "⏳" },
  { key: "not_relevant" as const, label: "Not relevant",      emoji: "👎" },
];

const SOURCE_LABEL: Record<string, string> = {
  signal: "Signal",
  gap: "Market opening",
  winning_product: "Winning product",
  pricing: "Pricing",
  brief: "Scout Brief",
  pro_analysis: "Intelligence Pro",
  manual: "Manual",
};

function SavedItemRow({ item, onUpdate, isLast }: {
  item: PlaybookItem;
  onUpdate: (id: string, patch: { status?: PlaybookItem["status"]; outcome?: PlaybookItem["outcome"] }) => void;
  isLast: boolean;
}) {
  const [expanded, setExpanded] = useState(false);
  const [askOutcome, setAskOutcome] = useState(false);
  const pr = SAVED_PRIORITY[item.priority] ?? SAVED_PRIORITY.medium;

  return (
    <div style={!isLast ? { borderBottom: "1px solid var(--border)" } : undefined}>
      <button
        onClick={() => setExpanded(!expanded)}
        className="w-full flex items-start gap-3 px-4 py-3 text-left transition-colors hover:bg-white/[.02]"
      >
        <span className="w-2 h-2 rounded-full shrink-0 mt-1.5" style={{ background: pr.color }} title={`${pr.label} priority`} />
        <div className="flex-1 min-w-0">
          <p className="text-sm font-semibold leading-snug" style={{ color: "var(--text)" }}>{item.title}</p>
          <div className="flex items-center gap-2 flex-wrap mt-1">
            <span className="label-caps" style={{ color: "var(--muted)" }}>{SOURCE_LABEL[item.source_type] ?? item.source_type}</span>
            {item.hostname && <span className="num text-[10px]" style={{ color: "var(--muted)" }}>{item.hostname}</span>}
          </div>
        </div>
        <ChevronRight className={`w-4 h-4 shrink-0 mt-0.5 transition-transform ${expanded ? "rotate-90" : ""}`} style={{ color: "var(--muted)" }} />
      </button>

      {expanded && (
        <div className="px-4 pb-4 pl-9 space-y-3">
          {item.reason && (
            <p className="text-xs leading-relaxed" style={{ color: "var(--text-2)" }}>
              <span className="font-semibold" style={{ color: "var(--muted)" }}>Why · </span>{item.reason}
            </p>
          )}
          {item.evidence && (
            <p className="num text-[11px] leading-relaxed px-3 py-2 rounded" style={{ background: "var(--bg3)", color: "var(--muted)" }}>
              {item.evidence}
            </p>
          )}

          {askOutcome ? (
            <div className="flex items-center gap-1.5 flex-wrap">
              <span className="text-[11px]" style={{ color: "var(--muted)" }}>Did it work?</span>
              {OUTCOME_OPTIONS.map((o) => (
                <button
                  key={o.key}
                  onClick={() => { onUpdate(item.id, { outcome: o.key }); setAskOutcome(false); }}
                  className="text-[11px] font-medium px-2.5 py-1 rounded-full transition-all hover:bg-white/[.06]"
                  style={{ border: "1px solid var(--border)", color: "var(--text-2)" }}
                >
                  {o.emoji} {o.label}
                </button>
              ))}
            </div>
          ) : (
            <div className="flex items-center gap-2 flex-wrap">
              <button
                onClick={() => { onUpdate(item.id, { status: "done" }); setAskOutcome(true); }}
                className="flex items-center gap-1.5 text-xs font-bold px-3 py-1.5 rounded transition-all hover:brightness-110"
                style={{ background: "var(--accent)", color: "var(--ink)" }}
              >
                <Check className="w-3.5 h-3.5" /> Mark done
              </button>
              <button
                onClick={() => onUpdate(item.id, { status: "dismissed" })}
                className="flex items-center gap-1 text-xs font-medium px-3 py-1.5 rounded transition-all hover:bg-white/[.06]"
                style={{ color: "var(--muted)", border: "1px solid var(--border)" }}
              >
                <X className="w-3 h-3" /> Dismiss
              </button>
              {item.competitor_id && (
                <Link
                  href={`/dashboard/${item.competitor_id}`}
                  className="flex items-center gap-1 text-xs font-medium ml-auto transition-opacity hover:opacity-70"
                  style={{ color: "var(--muted)" }}
                >
                  View source <ArrowRight className="w-3 h-3" />
                </Link>
              )}
            </div>
          )}
        </div>
      )}
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
          <div className="rounded-md overflow-hidden" style={{ background: "var(--bg-card)", border: "1px solid var(--border)" }}>
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
  const [userTier,    setUserTier]    = useState<string>("free");
  const [steps,       setSteps]       = useState<Record<string, boolean[]>>({});
  const [loadError,   setLoadError]   = useState(false);
  const [savedItems,  setSavedItems]  = useState<PlaybookItem[]>([]);

  function load(isRefresh = false) {
    if (isRefresh) setRefreshing(true); else setLoading(true);
    userApi.playbook()
      .then((d) => { setData(d); setLoadError(false); })
      // A failed fetch is NOT an empty playbook — keep whatever we have and
      // surface a retry instead of the misleading "no competitors" state.
      .catch(() => setLoadError(true))
      .finally(() => { setLoading(false); setRefreshing(false); });
    itemsApi.list().then((r) => setSavedItems(r.data)).catch(() => {});
  }

  function updateSavedItem(id: string, patch: { status?: PlaybookItem["status"]; outcome?: PlaybookItem["outcome"] }) {
    // Optimistic — the row moves immediately; the server write follows
    setSavedItems((prev) => prev.map((it) => (it.id === id ? { ...it, ...patch } : it)));
    itemsApi.update(id, patch).catch(() => {
      itemsApi.list().then((r) => setSavedItems(r.data)).catch(() => {});
    });
  }

  useEffect(() => {
    setDone(getDone());
    setFeedback(getFeedback());
    setSteps(getSteps());
    load();
    userApi.subscription().then((r) => setUserTier(r.data.tier ?? "free")).catch(() => {});
  }, []);

  function toggleStep(playId: string, idx: number) {
    setSteps((prev) => {
      const arr = [...(prev[playId] ?? [])];
      arr[idx] = !arr[idx];
      const next = { ...prev, [playId]: arr };
      saveSteps(next);
      return next;
    });
  }

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

  if (!data && loadError) {
    return (
      <div className="space-y-6">
        <p className="tick-label mb-1.5">Intel · your moves</p>
        <h1 className="text-xl font-bold tracking-tight" style={{ color: "var(--text)" }}>Playbook</h1>
        <div className="rounded-md p-10 text-center" style={{ background: "var(--bg-card)", border: "1px solid var(--border)" }}>
          <RefreshCw className="w-8 h-8 mx-auto mb-3" style={{ color: "var(--muted)" }} />
          <p className="font-semibold mb-1" style={{ color: "var(--text)" }}>Couldn&apos;t load your playbook</p>
          <p className="text-sm mb-4" style={{ color: "var(--muted)" }}>
            Connection hiccup — your plays are safe. Try again in a moment.
          </p>
          <button
            onClick={() => load()}
            className="inline-flex items-center gap-2 text-sm font-semibold px-4 py-2 rounded-md transition-all hover:brightness-110"
            style={{ background: "var(--accent)", color: "var(--ink)" }}
          >
            <RefreshCw className="w-4 h-4" /> Retry
          </button>
        </div>
      </div>
    );
  }

  if (!data || data.competitor_count === 0) {
    return (
      <div className="space-y-6">
        <p className="tick-label mb-1.5">Intel · your moves</p>
        <h1 className="text-xl font-bold tracking-tight" style={{ color: "var(--text)" }}>Playbook</h1>
        <div className="rounded-md p-10 text-center" style={{ background: "var(--bg-card)", border: "1px solid var(--border)" }}>
          <Zap className="w-8 h-8 mx-auto mb-3" style={{ color: "var(--accent)" }} />
          <p className="font-semibold mb-1" style={{ color: "var(--text)" }}>No competitors tracked yet</p>
          <p className="text-sm mb-4" style={{ color: "var(--muted)" }}>
            Add a Shopify competitor and your playbook will be ready after the first scan — usually within 2 minutes.
          </p>
          <Link
            href="/dashboard"
            className="inline-flex items-center gap-2 text-sm font-semibold px-4 py-2 rounded-md transition-all hover:brightness-110"
            style={{ background: "var(--accent)", color: "var(--ink)" }}
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
  const pendingSaved = savedItems.filter((s) => s.status === "pending");
  const doneSaved    = savedItems.filter((s) => s.status === "done");

  const bySection = (list: PlaybookPlay[]) => ({
    act_now:   list.filter((p) => p.section === "act_now"),
    right_now: list.filter((p) => p.section === "right_now"),
    this_week: list.filter((p) => p.section === "this_week"),
  });

  const focusPlay = activePlays[0] ?? null;
  const queuePlays = activePlays.slice(1);
  const activeSections = bySection(queuePlays);

  return (
    <>
      <div className="space-y-6">

        {/* ── Header ─────────────────────────────────────────────────────── */}
        <div className="flex items-start justify-between gap-4">
          <div>
            <p className="tick-label mb-1.5">Intel · your moves</p>
            <div className="flex items-center gap-2 mb-1 flex-wrap">
              <h1 className="text-xl font-bold tracking-tight" style={{ color: "var(--text)" }}>Playbook</h1>
              {activePlays.length + pendingSaved.length > 0 && (
                <span
                  className="text-xs font-bold px-2 py-1 rounded-full"
                  style={{ background: "var(--bg3)", color: "var(--text-2)", border: "1px solid var(--border)" }}
                >
                  {activePlays.length + pendingSaved.length} open
                </span>
              )}
              {streak > 0 && (
                <span
                  className="text-[10px] font-bold px-2 py-1 rounded-full flex items-center gap-1"
                  style={{ background: "var(--bg3)", color: "var(--text-2)", border: "1px solid var(--border)" }}
                  title="Consecutive days you've executed at least one play"
                >
                  <Flame className="w-3 h-3" />
                  {streak}-day streak
                </span>
              )}
              {data.ai_source && (
                <span
                  className="label-caps px-2 py-1 rounded-full flex items-center gap-1"
                  style={{ background: "var(--bg3)", color: "var(--text-2)", border: "1px solid var(--border)" }}
                >
                  <Zap className="w-3 h-3" />
                  Scout AI
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

        {/* ── AI analysis: FINITE states only ─────────────────────────────── */}
        {/* Generating — a real job is in flight. Never shown indefinitely: the
            backend resolves to timed_out after a real timeout. */}
        {!data.ai_source && (data.ai_state === "generating" || data.ai_state === "queued"
          || (data.ai_state == null && data.ai_generating)) && (
          <div
            className="flex items-center gap-2.5 px-4 py-3 rounded-md text-xs"
            style={{ background: "var(--bg3)", border: "1px solid var(--border)", color: "var(--text-2)" }}
          >
            <RefreshCw className="w-3.5 h-3.5 animate-spin shrink-0" />
            <span>
              <span className="font-bold">AI analysis in progress</span>
              <span style={{ color: "var(--muted)" }}> — Claude is reviewing your competitors. These deterministic plays are ready now; AI-tailored plays will replace them shortly.</span>
            </span>
          </div>
        )}
        {/* Failed / timed out / unavailable — a finite terminal state with Retry.
            The deterministic plays below remain fully usable. */}
        {!data.ai_source && (data.ai_state === "timed_out" || data.ai_state === "failed" || data.ai_state === "unavailable") && (
          <div
            className="flex items-center justify-between gap-2.5 px-4 py-3 rounded-md text-xs"
            style={{ background: "var(--bg3)", border: "1px solid var(--border)", color: "var(--text-2)" }}
          >
            <span>
              <span className="font-bold">AI-tailored plays aren&apos;t available right now</span>
              <span style={{ color: "var(--muted)" }}> — the plays below are ready to use. You can retry the AI pass.</span>
            </span>
            <button
              onClick={async () => { try { await userApi.regeneratePlaybook(); load(); } catch { /* noop */ } }}
              className="shrink-0 text-xs font-semibold px-3 py-1.5 rounded-md"
              style={{ background: "var(--accent)", color: "var(--ink)" }}
            >
              Retry
            </button>
          </div>
        )}

        {/* ── Tabs ───────────────────────────────────────────────────────── */}
        <div
          className="flex items-center rounded-md p-0.5 w-fit"
          style={{ background: "var(--bg3)" }}
        >
          {(["active", "done"] as const).map((t) => {
            const count = t === "active" ? activePlays.length + pendingSaved.length : donePlays.length + doneSaved.length;
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
                      background: tab === t ? "rgba(236,238,230,.10)" : "transparent",
                      color: tab === t ? "var(--text)" : "var(--muted)",
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
            {activePlays.length === 0 && pendingSaved.length === 0 ? (
              plays.length === 0 && data.ai_generating ? (
                <EmptyStateCard
                  icon={RefreshCw}
                  headline="Building your playbook"
                  body={`Scout AI is reviewing your ${data.competitor_count} competitor${data.competitor_count !== 1 ? "s" : ""}. This takes ~30 seconds.`}
                />
              ) : (
                <EmptyStateCard
                  icon={Check}
                  headline="All caught up"
                  body="Everything's marked done. Your playbook refreshes after each competitor scan — and anything you save from a competitor page lands here too."
                />
              )
            ) : (
              <div className="space-y-8">
                {focusPlay && (
                  <FocusCard
                    play={focusPlay}
                    onDone={() => markDone(focusPlay.id)}
                    onOpen={() => setDetailPlay(focusPlay)}
                    stepsChecked={steps[focusPlay.id] ?? []}
                    onToggleStep={(idx) => toggleStep(focusPlay.id, idx)}
                  />
                )}

                {/* Saved by you — persisted items from anywhere in the app */}
                {pendingSaved.length > 0 && (
                  <div>
                    <p className="tick-label mb-4 pb-2" style={{ borderBottom: "1px solid var(--border)" }}>
                      Saved by you · {pendingSaved.length}
                    </p>
                    <div className="rounded-md overflow-hidden" style={{ background: "var(--bg-card)", border: "1px solid var(--border)" }}>
                      {pendingSaved.map((it, i) => (
                        <SavedItemRow key={it.id} item={it} onUpdate={updateSavedItem} isLast={i === pendingSaved.length - 1} />
                      ))}
                    </div>
                  </div>
                )}

                {queuePlays.length > 0 && (
                  <div>
                    <p className="tick-label mb-4 pb-2" style={{ borderBottom: "1px solid var(--border)" }}>
                      Queue · {queuePlays.length}
                    </p>
                    <div className="space-y-8">
                      {SECTION_ORDER.map((section) => (
                        <PlaySection
                          key={section}
                          section={section}
                          plays={activeSections[section]}
                          done={done}
                          onDone={markDone}
                          onOpen={setDetailPlay}
                          steps={steps}
                          onToggleStep={toggleStep}
                        />
                      ))}
                    </div>
                  </div>
                )}
              </div>
            )}

            {/* Locked CTA */}
            {data.locked && (
              <LockedValueCard
                title={`${data.locked_count ?? "More"} plays locked`}
                teaser="Pro subscribers see every move across all competitors, updated after each scan."
                plan="pro"
              />
            )}
          </>
        )}

        {/* ── Done tab ───────────────────────────────────────────────────── */}
        {tab === "done" && (
          <div className="space-y-4">
            {donePlays.length === 0 && doneSaved.length === 0 ? (
              <div className="rounded-md p-8 text-center" style={{ background: "var(--bg-card)", border: "1px solid var(--border)" }}>
                <Clock className="w-6 h-6 mx-auto mb-2" style={{ color: "var(--muted)" }} />
                <p className="font-semibold mb-1" style={{ color: "var(--text)" }}>Nothing done yet</p>
                <p className="text-sm" style={{ color: "var(--muted)" }}>
                  Mark plays as done and they&apos;ll appear here so you can track what you&apos;ve acted on.
                </p>
              </div>
            ) : donePlays.length === 0 ? null : (
              <div
                className="rounded-md overflow-hidden"
                style={{ background: "var(--bg-card)", border: "1px solid var(--border)" }}
              >
                {donePlays.map((p, i) => (
                  <div
                    key={p.id}
                    className="px-4 py-3"
                    style={i < donePlays.length - 1 ? { borderBottom: "1px solid var(--border)" } : undefined}
                  >
                    <div className="flex items-center gap-3">
                      <Check className="w-3.5 h-3.5 shrink-0" style={{ color: "#4CC38A" }} />
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

            {/* Completed saved moves — with their tracked outcomes */}
            {doneSaved.length > 0 && (
              <div>
                <p className="tick-label mb-2">Saved moves · done</p>
                <div className="rounded-md overflow-hidden" style={{ background: "var(--bg-card)", border: "1px solid var(--border)" }}>
                  {doneSaved.map((it, i) => (
                    <div
                      key={it.id}
                      className="px-4 py-3 flex items-center gap-3"
                      style={i < doneSaved.length - 1 ? { borderBottom: "1px solid var(--border)" } : undefined}
                    >
                      <Check className="w-3.5 h-3.5 shrink-0" style={{ color: "#4CC38A" }} />
                      <p className="text-sm flex-1 truncate" style={{ color: "var(--muted)" }}>{it.title}</p>
                      <div className="flex items-center gap-2 shrink-0">
                        {it.outcome && (
                          <span className="text-sm" title={OUTCOME_OPTIONS.find((o) => o.key === it.outcome)?.label}>
                            {OUTCOME_OPTIONS.find((o) => o.key === it.outcome)?.emoji}
                          </span>
                        )}
                        {!it.outcome && (
                          <div className="flex items-center gap-1">
                            {OUTCOME_OPTIONS.map((o) => (
                              <button
                                key={o.key}
                                onClick={() => updateSavedItem(it.id, { outcome: o.key })}
                                title={o.label}
                                className="text-sm p-0.5 rounded transition-all opacity-50 hover:opacity-100"
                              >
                                {o.emoji}
                              </button>
                            ))}
                          </div>
                        )}
                        <button
                          onClick={() => updateSavedItem(it.id, { status: "pending" })}
                          className="text-[11px] font-medium transition-opacity hover:opacity-70"
                          style={{ color: "var(--accent)" }}
                        >
                          Undo
                        </button>
                      </div>
                    </div>
                  ))}
                </div>
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

      <UpgradeModal open={upgradeOpen} onClose={() => setUpgradeOpen(false)} trigger="general" currentTier={userTier} />
    </>
  );
}
