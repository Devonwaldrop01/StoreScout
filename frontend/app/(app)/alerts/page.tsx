"use client";

import { useEffect, useState, useCallback } from "react";
import Link from "next/link";
import { Bell, ArrowRight } from "lucide-react";
import { alerts as alertsApi, type AlertEvent } from "@/lib/api";
import { cn, formatRelativeTime, formatPrice, formatDelta, changeTypeIcon, severityColor } from "@/lib/utils";

// ── Filter definitions ────────────────────────────────────────────────────────
const FILTERS = [
  { value: "",               label: "All" },
  { value: "price_change",   label: "Price changes" },
  { value: "new_product",    label: "New products" },
  { value: "discount_start", label: "Discounts" },
] as const;

// ── Date grouping ─────────────────────────────────────────────────────────────
function getDateBucket(isoString: string): string {
  const now  = new Date();
  const date = new Date(isoString);

  const startOfToday     = new Date(now.getFullYear(), now.getMonth(), now.getDate());
  const startOfYesterday = new Date(startOfToday.getTime() - 86_400_000);
  const startOfWeek      = new Date(startOfToday.getTime() - 6 * 86_400_000);

  if (date >= startOfToday)     return "Today";
  if (date >= startOfYesterday) return "Yesterday";
  if (date >= startOfWeek)      return "This week";
  return "Older";
}

const BUCKET_ORDER = ["Today", "Yesterday", "This week", "Older"] as const;

function groupAlerts(list: AlertEvent[]): { bucket: string; items: AlertEvent[] }[] {
  const map: Record<string, AlertEvent[]> = {};
  for (const a of list) {
    const b = getDateBucket(a.detected_at);
    if (!map[b]) map[b] = [];
    map[b].push(a);
  }
  return BUCKET_ORDER.filter((b) => map[b]?.length).map((b) => ({ bucket: b, items: map[b] }));
}

// ── Severity accent bar color ─────────────────────────────────────────────────
function severityBarColor(severity: string): string {
  if (severity === "critical") return "var(--red)";
  if (severity === "warning")  return "var(--amber)";
  return "transparent";
}

// ── Count helper ──────────────────────────────────────────────────────────────
function countByType(list: AlertEvent[], value: string): number {
  if (!value) return list.length;
  return list.filter((a) => a.change_type === value).length;
}

// ── Component ─────────────────────────────────────────────────────────────────
export default function AlertsPage() {
  const [alertList, setAlertList] = useState<AlertEvent[]>([]);
  const [loading,   setLoading]   = useState(true);
  const [filter,    setFilter]    = useState("");

  // Always load all 100; filter client-side for counts, API-side for display
  const load = useCallback(async () => {
    try {
      const { data } = await alertsApi.list(100, filter || undefined);
      setAlertList(data);
    } catch {
      // ignore
    } finally {
      setLoading(false);
    }
  }, [filter]);

  useEffect(() => {
    load();
  }, [load]);

  // Pre-load all alerts once for count badges (always unfiltered)
  const [allAlerts, setAllAlerts] = useState<AlertEvent[]>([]);
  useEffect(() => {
    alertsApi.list(100).then(({ data }) => setAllAlerts(data)).catch(() => {});
  }, []);

  const groups = groupAlerts(alertList);

  return (
    <div className="fade-up">
      {/* ── Header ─────────────────────────────────────────────────────────── */}
      <div className="flex items-center justify-between mb-7">
        <div className="flex items-center gap-3">
          <h1 className="text-2xl font-bold tracking-tight" style={{ color: "var(--text)" }}>
            Alerts
          </h1>
          {!loading && (
            <span
              className="px-2.5 py-0.5 rounded-full text-xs font-semibold"
              style={{ background: "rgba(168,255,0,.12)", color: "var(--accent)" }}
            >
              {alertList.length} change{alertList.length !== 1 ? "s" : ""} detected
            </span>
          )}
        </div>

        {/* Live indicator */}
        <div className="flex items-center gap-2">
          <span
            className="relative flex h-2 w-2"
            aria-hidden="true"
          >
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

      {/* ── Filter pills ───────────────────────────────────────────────────── */}
      <div className="flex gap-2 mb-7 flex-wrap fade-up-1">
        {FILTERS.map(({ value, label }) => {
          const active = filter === value;
          const count  = countByType(allAlerts.length ? allAlerts : alertList, value);
          return (
            <button
              key={value}
              onClick={() => { setFilter(value); setLoading(true); }}
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

      {/* ── Loading skeleton ────────────────────────────────────────────────── */}
      {loading ? (
        <div className="space-y-3 fade-in">
          {[1, 2, 3, 4, 5].map((i) => (
            <div
              key={i}
              className="h-20 rounded-2xl animate-pulse"
              style={{ background: "var(--bg3)" }}
            />
          ))}
        </div>

      ) : alertList.length === 0 ? (
        /* ── Empty state ─────────────────────────────────────────────────── */
        <div
          className="flex flex-col items-center justify-center min-h-[320px] text-center rounded-2xl fade-in"
          style={{ background: "var(--bg3)", border: "1px solid var(--border)" }}
        >
          <Bell
            size={48}
            className="mb-4"
            style={{ color: "var(--muted)", opacity: 0.3 }}
          />
          <p className="text-base font-semibold mb-1" style={{ color: "var(--text)" }}>
            All clear
          </p>
          <p className="text-sm max-w-xs" style={{ color: "var(--muted)" }}>
            We&apos;ll notify you here the moment a competitor makes a move.
          </p>
        </div>

      ) : (
        /* ── Grouped alert feed ──────────────────────────────────────────── */
        <div className="space-y-6 fade-up-2">
          {groups.map(({ bucket, items }) => (
            <section key={bucket}>
              {/* Sticky section header */}
              <div
                className="sticky top-0 z-10 flex items-center gap-3 py-2 mb-3"
                style={{ background: "var(--bg)" }}
              >
                <span className="text-[11px] font-semibold uppercase tracking-widest" style={{ color: "var(--muted)" }}>
                  {bucket}
                </span>
                <span className="text-[11px]" style={{ color: "var(--muted)", opacity: 0.5 }}>
                  {items.length}
                </span>
                <div className="flex-1 h-px" style={{ background: "var(--border)" }} />
              </div>

              {/* Alert rows */}
              <div className="space-y-2">
                {items.map((alert) => {
                  const icon      = changeTypeIcon(alert.change_type);
                  const old_v     = alert.old_value || {};
                  const new_v     = alert.new_value || {};
                  const barColor  = severityBarColor(alert.severity);

                  let detail = "";
                  if (alert.change_type === "price_change" && alert.delta_pct != null) {
                    detail = `${formatPrice(old_v.price as number)} → ${formatPrice(new_v.price as number)} (${formatDelta(alert.delta_pct)})`;
                  } else if (alert.change_type === "new_product" && new_v.price_min) {
                    detail = `$${new_v.price_min}`;
                  } else if (
                    alert.change_type === "discount_start" ||
                    alert.change_type === "discount_end"
                  ) {
                    detail = `${formatDelta(alert.delta_pct || 0)} catalog promo rate`;
                  }

                  return (
                    <Link
                      key={alert.id}
                      href={`/dashboard/${alert.competitor_id}`}
                      className="group flex items-stretch gap-0 rounded-2xl overflow-hidden transition-colors hover:bg-white/[0.03]"
                      style={{
                        background: "var(--bg3)",
                        border: "1px solid var(--border)",
                      }}
                    >
                      {/* Severity accent bar */}
                      <div
                        className="w-[3px] shrink-0 rounded-full my-2 ml-2"
                        style={{ background: barColor }}
                      />

                      {/* Content */}
                      <div className="flex flex-1 items-center gap-3 px-4 py-3 min-w-0">
                        {/* Icon */}
                        <span className="text-xl leading-none shrink-0">{icon}</span>

                        {/* Text block */}
                        <div className="flex-1 min-w-0">
                          <div className="flex items-center gap-2 mb-0.5">
                            {/* Hostname chip */}
                            <span
                              className="text-[10px] font-semibold px-1.5 py-0.5 rounded-md shrink-0"
                              style={{
                                background: "rgba(255,255,255,.06)",
                                color: "var(--muted)",
                                border: "1px solid var(--border)",
                              }}
                            >
                              {alert.hostname}
                            </span>
                          </div>
                          <p className="text-sm font-medium truncate" style={{ color: "var(--text)" }}>
                            {alert.product_title ||
                              alert.change_type
                                .replace(/_/g, " ")
                                .replace(/\b\w/g, (c) => c.toUpperCase())}
                          </p>
                          {detail && (
                            <p
                              className={cn(
                                "text-xs font-mono mt-0.5",
                                severityColor(alert.severity)
                              )}
                            >
                              {detail}
                            </p>
                          )}
                        </div>

                        {/* Time + arrow */}
                        <div className="flex items-center gap-2 shrink-0">
                          <p className="text-xs" style={{ color: "var(--muted)" }}>
                            {formatRelativeTime(alert.detected_at)}
                          </p>
                          <ArrowRight
                            size={14}
                            className="opacity-0 group-hover:opacity-40 transition-opacity"
                            style={{ color: "var(--muted)" }}
                          />
                        </div>
                      </div>
                    </Link>
                  );
                })}
              </div>
            </section>
          ))}
        </div>
      )}
    </div>
  );
}
