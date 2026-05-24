"use client";

import { useEffect, useState, useCallback, useMemo } from "react";
import { Bell } from "lucide-react";
import { alerts as alertsApi, type AlertEvent } from "@/lib/api";
import { groupAlertEvents, generateNarrative } from "@/lib/signals";
import { SignalFeed } from "@/components/signals/SignalFeed";

// ── Filter definitions ────────────────────────────────────────────────────────
const FILTERS = [
  { value: "",               label: "All" },
  { value: "price_change",   label: "Price changes" },
  { value: "new_product",    label: "New products" },
  { value: "discount_start", label: "Discounts" },
] as const;

function countByType(list: AlertEvent[], value: string): number {
  if (!value) return list.length;
  return list.filter((a) => a.change_type === value).length;
}

// ── Component ─────────────────────────────────────────────────────────────────
export default function AlertsPage() {
  const [alertList, setAlertList] = useState<AlertEvent[]>([]);
  const [loading,   setLoading]   = useState(true);
  const [filter,    setFilter]    = useState("");

  const load = useCallback(async () => {
    setLoading(true);
    try {
      const { data } = await alertsApi.list(200);
      setAlertList(data);
    } catch {
      // ignore
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => { load(); }, [load]);

  const filtered = useMemo(
    () => filter ? alertList.filter((a) => a.change_type === filter) : alertList,
    [alertList, filter],
  );

  const signalGroups = useMemo(() => groupAlertEvents(filtered), [filtered]);
  const narrative    = useMemo(() => generateNarrative(signalGroups), [signalGroups]);

  const strategicCount = signalGroups.filter((g) => g.tier === "strategic").length;

  return (
    <div className="fade-up">
      {/* ── Header ─────────────────────────────────────────────────────────── */}
      <div className="flex items-center justify-between mb-6">
        <div className="flex items-center gap-3">
          <h1 className="text-2xl font-bold tracking-tight" style={{ color: "var(--text)" }}>
            Alerts
          </h1>
          {!loading && strategicCount > 0 && (
            <span
              className="px-2.5 py-0.5 rounded-full text-xs font-semibold"
              style={{ background: "rgba(239,68,68,.15)", color: "var(--red)" }}
            >
              {strategicCount} strategic signal{strategicCount !== 1 ? "s" : ""}
            </span>
          )}
          {!loading && strategicCount === 0 && alertList.length > 0 && (
            <span
              className="px-2.5 py-0.5 rounded-full text-xs font-semibold"
              style={{ background: "rgba(168,255,0,.12)", color: "var(--accent)" }}
            >
              {alertList.length} change{alertList.length !== 1 ? "s" : ""}
            </span>
          )}
        </div>

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

      {/* ── Narrative bar ──────────────────────────────────────────────────── */}
      {!loading && narrative && (
        <div
          className="flex items-center gap-2 px-4 py-2.5 rounded-xl mb-5 text-xs font-medium fade-up-1"
          style={{
            background: strategicCount > 0 ? "rgba(239,68,68,.08)" : "var(--bg3)",
            border: `1px solid ${strategicCount > 0 ? "rgba(239,68,68,.2)" : "var(--border)"}`,
            color: strategicCount > 0 ? "var(--red)" : "var(--text-2)",
          }}
        >
          <span>{narrative}</span>
        </div>
      )}

      {/* ── Filter pills ───────────────────────────────────────────────────── */}
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
                  ? { background: "var(--accent)", color: "#0a0a0f" }
                  : {
                      background: "var(--bg4)",
                      color: "var(--muted)",
                      border: "1px solid var(--border)",
                    }
              }
            >
              {label}
              <span
                className="px-1.5 py-0.5 rounded-full text-[10px] font-bold tabular-nums"
                style={
                  active
                    ? { background: "rgba(0,0,0,.18)", color: "#0a0a0f" }
                    : { background: "rgba(255,255,255,.06)", color: "var(--muted)" }
                }
              >
                {count}
              </span>
            </button>
          );
        })}
      </div>

      {/* ── Body ───────────────────────────────────────────────────────────── */}
      {loading ? (
        <div className="space-y-3 fade-in">
          {[1, 2, 3, 4, 5].map((i) => (
            <div key={i} className="h-16 rounded-xl animate-pulse" style={{ background: "var(--bg3)" }} />
          ))}
        </div>

      ) : alertList.length === 0 ? (
        <div
          className="flex flex-col items-center justify-center min-h-[320px] text-center rounded-2xl fade-in"
          style={{ background: "var(--bg3)", border: "1px solid var(--border)" }}
        >
          <Bell size={48} className="mb-4" style={{ color: "var(--muted)", opacity: 0.3 }} />
          <p className="text-base font-semibold mb-1" style={{ color: "var(--text)" }}>
            All clear
          </p>
          <p className="text-sm max-w-xs" style={{ color: "var(--muted)" }}>
            We&apos;ll notify you here the moment a competitor makes a move.
          </p>
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
