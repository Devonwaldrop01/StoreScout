"use client";

import { useEffect, useState, useCallback } from "react";
import { Bell } from "lucide-react";
import { alerts as alertsApi, type AlertEvent } from "@/lib/api";
import { cn, formatRelativeTime, formatPrice, formatDelta, changeTypeIcon, severityColor } from "@/lib/utils";

const CHANGE_TYPES = [
  { value: "", label: "All types" },
  { value: "price_change", label: "Price changes" },
  { value: "new_product", label: "New products" },
  { value: "discount_start", label: "Discount started" },
  { value: "discount_end", label: "Discount ended" },
];

export default function AlertsPage() {
  const [alertList, setAlertList] = useState<AlertEvent[]>([]);
  const [loading, setLoading] = useState(true);
  const [filter, setFilter] = useState("");

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

  function getSeverityBorder(severity: string) {
    return { critical: "rgba(248,113,113,.3)", warning: "rgba(251,191,36,.3)", info: "var(--border)" }[severity] || "var(--border)";
  }

  return (
    <div>
      <div className="flex items-center justify-between mb-6">
        <div>
          <h1 className="text-2xl font-bold" style={{ color: "var(--text)" }}>Alerts</h1>
          <p className="text-sm mt-1" style={{ color: "var(--muted)" }}>
            Changes detected across all your tracked competitors
          </p>
        </div>
      </div>

      <div className="flex gap-2 mb-6 flex-wrap">
        {CHANGE_TYPES.map(({ value, label }) => (
          <button
            key={value}
            onClick={() => setFilter(value)}
            className={cn(
              "px-3 py-1.5 rounded-xl text-xs font-medium transition-colors",
              filter === value ? "text-white" : "hover:bg-white/5"
            )}
            style={
              filter === value
                ? { background: "rgba(163,240,0,.12)", color: "var(--green)" }
                : { color: "var(--muted)", border: "1px solid var(--border)" }
            }
          >
            {label}
          </button>
        ))}
      </div>

      {loading ? (
        <div className="space-y-3">
          {[1, 2, 3, 4].map((i) => (
            <div key={i} className="h-20 rounded-2xl animate-pulse" style={{ background: "var(--bg-card)" }} />
          ))}
        </div>
      ) : alertList.length === 0 ? (
        <div
          className="flex flex-col items-center justify-center min-h-[300px] text-center"
          style={{ background: "var(--bg-card)", border: "1px solid var(--border)", borderRadius: 16 }}
        >
          <Bell className="w-10 h-10 mb-4 opacity-30" style={{ color: "var(--muted)" }} />
          <p className="font-medium" style={{ color: "var(--text)" }}>No alerts yet</p>
          <p className="text-sm mt-1" style={{ color: "var(--muted)" }}>
            Alerts appear here when we detect changes in your tracked competitors
          </p>
        </div>
      ) : (
        <div className="space-y-2">
          {alertList.map((alert) => {
            const icon = changeTypeIcon(alert.change_type);
            const colorClass = severityColor(alert.severity);
            const old_v = alert.old_value || {};
            const new_v = alert.new_value || {};

            let detail = "";
            if (alert.change_type === "price_change" && alert.delta_pct != null) {
              detail = `${formatPrice(old_v.price as number)} → ${formatPrice(new_v.price as number)} (${formatDelta(alert.delta_pct)})`;
            } else if (alert.change_type === "new_product" && new_v.price_min) {
              detail = `$${new_v.price_min}`;
            } else if (alert.change_type === "discount_start" || alert.change_type === "discount_end") {
              detail = `${formatDelta((alert.delta_pct || 0))} catalog promo rate`;
            }

            return (
              <div
                key={alert.id}
                className="flex items-start gap-4 rounded-2xl p-4 transition-colors"
                style={{
                  background: "var(--bg-card)",
                  border: `1px solid ${getSeverityBorder(alert.severity)}`,
                }}
              >
                <span className="text-xl leading-none mt-0.5">{icon}</span>
                <div className="flex-1 min-w-0">
                  <div className="flex items-center gap-2 mb-0.5">
                    <span className="text-xs font-semibold px-2 py-0.5 rounded-lg" style={{ background: "rgba(255,255,255,.06)", color: "var(--muted)" }}>
                      {alert.hostname}
                    </span>
                    {alert.severity !== "info" && (
                      <span className={cn("text-xs font-bold uppercase", colorClass)}>
                        {alert.severity}
                      </span>
                    )}
                  </div>
                  <p className="text-sm font-medium truncate" style={{ color: "var(--text)" }}>
                    {alert.product_title || alert.change_type.replace(/_/g, " ").replace(/\b\w/g, (c) => c.toUpperCase())}
                  </p>
                  {detail && <p className={cn("text-xs font-mono mt-0.5", colorClass)}>{detail}</p>}
                </div>
                <p className="text-xs shrink-0" style={{ color: "var(--muted)" }}>
                  {formatRelativeTime(alert.detected_at)}
                </p>
              </div>
            );
          })}
        </div>
      )}
    </div>
  );
}
