"use client";

import { useEffect, useState, useCallback, useMemo, useRef } from "react";
import { Bell, RefreshCw, CheckCheck } from "lucide-react";
import { alerts as alertsApi, type AlertEvent } from "@/lib/api";
import { groupAlertEvents, generateNarrative } from "@/lib/signals";
import { SignalFeed } from "@/components/signals/SignalFeed";

const FILTERS = [
  { value: "",               label: "All" },
  { value: "price_change",   label: "Price changes" },
  { value: "new_product",    label: "New products" },
  { value: "discount_start", label: "Discounts" },
] as const;

const REFRESH_INTERVAL_MS = 30_000;

function countByType(list: AlertEvent[], value: string): number {
  if (!value) return list.length;
  return list.filter((a) => a.change_type === value).length;
}

export default function AlertsPage() {
  const [alertList,    setAlertList]    = useState<AlertEvent[]>([]);
  const [loading,      setLoading]      = useState(true);
  const [refreshing,   setRefreshing]   = useState(false);
  const [filter,       setFilter]       = useState("");
  const [unreadCount,  setUnreadCount]  = useState(0);
  const [markingRead,  setMarkingRead]  = useState(false);
  const markedReadRef = useRef(false);

  const load = useCallback(async (silent = false) => {
    if (!silent) setLoading(true);
    else setRefreshing(true);
    try {
      const { data } = await alertsApi.list(200);
      setAlertList(data);
      // Count unread in the freshly fetched list
      setUnreadCount(data.filter((a) => !a.read_at).length);
    } catch {
      // ignore network errors silently
    } finally {
      setLoading(false);
      setRefreshing(false);
    }
  }, []);

  // Initial load + auto-mark-all-read in one shot
  useEffect(() => {
    load().then(() => {
      // Mark all as read once per page visit, non-blocking
      if (!markedReadRef.current) {
        markedReadRef.current = true;
        alertsApi.markAllRead().catch(() => {});
      }
    });
  }, [load]);

  // 30-second silent refresh
  useEffect(() => {
    const timer = setInterval(() => load(true), REFRESH_INTERVAL_MS);
    return () => clearInterval(timer);
  }, [load]);

  async function handleMarkAllRead() {
    setMarkingRead(true);
    await alertsApi.markAllRead().catch(() => {});
    setUnreadCount(0);
    setAlertList((prev) => prev.map((a) => ({ ...a, read_at: new Date().toISOString() })));
    setMarkingRead(false);
  }

  const filtered = useMemo(
    () => filter ? alertList.filter((a) => a.change_type === filter) : alertList,
    [alertList, filter],
  );

  const signalGroups   = useMemo(() => groupAlertEvents(filtered), [filtered]);
  const narrative      = useMemo(() => generateNarrative(signalGroups), [signalGroups]);
  const strategicCount = signalGroups.filter((g) => g.tier === "strategic").length;

  return (
    <div className="fade-up">
      {/* ── Header ──────────────────────────────────────────────────────────── */}
      <div className="flex items-center justify-between mb-6">
        <div className="flex items-center gap-3">
          <h1 className="text-xl font-bold" style={{ color: "var(--text)" }}>
            Alerts
          </h1>
          {!loading && strategicCount > 0 && (
            <span
              className="px-2.5 py-0.5 rounded-full text-xs font-semibold"
              style={{ background: "rgba(255,178,36,.12)", color: "var(--accent)" }}
            >
              {strategicCount} strategic signal{strategicCount !== 1 ? "s" : ""}
            </span>
          )}
          {!loading && strategicCount === 0 && alertList.length > 0 && (
            <span
              className="px-2.5 py-0.5 rounded-full text-xs font-semibold"
              style={{ background: "rgba(255,178,36,.12)", color: "var(--accent)" }}
            >
              {alertList.length} change{alertList.length !== 1 ? "s" : ""}
            </span>
          )}
        </div>

        <div className="flex items-center gap-2">
          {/* Mark all read — only when there are unread items */}
          {unreadCount > 0 && (
            <button
              onClick={handleMarkAllRead}
              disabled={markingRead}
              className="flex items-center gap-1.5 text-xs font-medium px-3 py-1.5 rounded-xl transition-all hover:opacity-80 disabled:opacity-50"
              style={{ background: "var(--bg3)", color: "var(--muted)", border: "1px solid var(--border)" }}
              title={`Mark all ${unreadCount} as read`}
            >
              <CheckCheck className="w-3.5 h-3.5" />
              Mark all read
              <span
                className="px-1.5 py-0.5 rounded-full text-[10px] font-bold"
                style={{ background: "rgba(255,178,36,.15)", color: "var(--accent)" }}
              >
                {unreadCount}
              </span>
            </button>
          )}

          {/* Manual refresh */}
          <button
            onClick={() => load(true)}
            disabled={refreshing || loading}
            className="p-1.5 rounded-xl transition-all hover:bg-white/5 disabled:opacity-40"
            style={{ color: "var(--muted)" }}
            title="Refresh"
          >
            <RefreshCw className={`w-4 h-4 ${refreshing ? "animate-spin" : ""}`} />
          </button>

          {/* Live indicator */}
          <div className="flex items-center gap-2">
            <span className="relative flex h-2 w-2" aria-hidden="true">
              <span
                className="animate-ping absolute inline-flex h-full w-full rounded-full opacity-60"
                style={{ background: "var(--accent)" }}
              />
              <span
                className="relative inline-flex rounded-full h-2 w-2"
                style={{ background: "var(--accent)" }}
              />
            </span>
            <span className="text-xs font-medium" style={{ color: "var(--muted)" }}>
              Live
            </span>
          </div>
        </div>
      </div>

      {/* ── Narrative bar ────────────────────────────────────────────────────── */}
      {!loading && narrative && (
        <div
          className="flex items-center gap-2 px-4 py-2.5 rounded-xl mb-5 text-xs font-medium fade-up-1"
          style={{
            background: "var(--bg3)",
            border: "1px solid var(--border)",
            color: "var(--text-2)",
          }}
        >
          {narrative}
        </div>
      )}

      {/* ── Filter pills ─────────────────────────────────────────────────────── */}
      <div className="flex gap-2 mb-6 flex-wrap fade-up-1">
        {FILTERS.map(({ value, label }) => {
          const active = filter === value;
          const count  = countByType(alertList, value);
          return (
            <button
              key={value}
              onClick={() => setFilter(value)}
              className="flex items-center gap-1.5 px-3 py-1.5 rounded-full text-xs font-medium transition-all"
              style={
                active
                  ? { background: "var(--accent)", color: "var(--ink)" }
                  : { background: "var(--bg4)", color: "var(--muted)", border: "1px solid var(--border)" }
              }
            >
              {label}
              <span
                className="px-1.5 py-0.5 rounded-full text-[10px] font-bold tabular-nums"
                style={
                  active
                    ? { background: "rgba(0,0,0,.22)", color: "var(--ink)" }
                    : { background: "rgba(255,255,255,.06)", color: "var(--muted)" }
                }
              >
                {count}
              </span>
            </button>
          );
        })}
      </div>

      {/* ── Body ─────────────────────────────────────────────────────────────── */}
      {loading ? (
        <div className="space-y-3 fade-in">
          {[1, 2, 3, 4, 5].map((i) => (
            <div key={i} className="h-16 rounded-xl animate-pulse" style={{ background: "var(--bg3)" }} />
          ))}
        </div>

      ) : alertList.length === 0 ? (
        <div className="rounded-2xl overflow-hidden fade-in" style={{ border: "1px solid var(--border)" }}>
          {/* Header */}
          <div className="flex flex-col items-center text-center px-6 pt-10 pb-6" style={{ background: "var(--bg3)" }}>
            <div className="w-12 h-12 rounded-2xl mb-4 flex items-center justify-center" style={{ background: "rgba(255,178,36,.06)", border: "1px solid rgba(255,178,36,.14)" }}>
              <Bell className="w-6 h-6" style={{ color: "var(--accent)" }} />
            </div>
            <p className="text-base font-bold mb-2" style={{ color: "var(--text)" }}>All clear</p>
            <p className="text-sm max-w-sm leading-relaxed" style={{ color: "var(--muted)" }}>
              StoreScout is monitoring your competitors. You&apos;ll see signals here when they change prices, launch products, run discounts, or remove catalog items.
            </p>
          </div>

          {/* Ghost example rows */}
          <div className="px-4 pb-6 space-y-2 opacity-40 pointer-events-none" style={{ background: "var(--bg-card)" }}>
            <p className="text-[10px] font-bold uppercase tracking-wider pt-4 pb-1" style={{ color: "var(--muted)" }}>
              What alerts look like
            </p>
            {[
              { icon: "↓", label: "Price drop detected", desc: "Oversized T-Shirt dropped 22% — $45 → $35", time: "2h ago", color: "#4CC38A" },
              { icon: "+", label: "New product launched", desc: "Summer Pump Cover added to catalog", time: "Yesterday", color: "#FFB224" },
              { icon: "%", label: "Discount campaign started", desc: "17 products now showing sale pricing", time: "3 days ago", color: "#FFB224" },
            ].map((ex) => (
              <div key={ex.label} className="flex items-start gap-3 px-4 py-3 rounded-xl" style={{ background: "var(--bg3)", border: "1px solid var(--border)" }}>
                <div className="w-8 h-8 rounded-lg flex items-center justify-center shrink-0 text-sm font-bold" style={{ background: `${ex.color}15`, color: ex.color }}>
                  {ex.icon}
                </div>
                <div className="min-w-0 flex-1">
                  <p className="text-sm font-semibold leading-none mb-1" style={{ color: "var(--text)" }}>{ex.label}</p>
                  <p className="text-xs" style={{ color: "var(--muted)" }}>{ex.desc}</p>
                </div>
                <span className="text-xs shrink-0 mt-0.5" style={{ color: "var(--muted)" }}>{ex.time}</span>
              </div>
            ))}
          </div>
        </div>

      ) : filtered.length === 0 ? (
        <div
          className="flex flex-col items-center justify-center min-h-[200px] text-center rounded-2xl fade-in"
          style={{ background: "var(--bg3)", border: "1px solid var(--border)" }}
        >
          <p className="text-sm font-semibold" style={{ color: "var(--text)" }}>
            No {FILTERS.find((f) => f.value === filter)?.label.toLowerCase()} detected
          </p>
          <button
            onClick={() => setFilter("")}
            className="mt-3 text-xs font-medium underline"
            style={{ color: "var(--muted)" }}
          >
            Clear filter
          </button>
        </div>

      ) : (
        <div className="fade-up-2">
          <SignalFeed groups={signalGroups} maxRaw={20} />
        </div>
      )}
    </div>
  );
}
