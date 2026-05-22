"use client";

import { useEffect, useState, useCallback } from "react";
import { Plus, RefreshCw, TrendingUp, AlertTriangle } from "lucide-react";
import Link from "next/link";
import { competitors as api, type Competitor } from "@/lib/api";
import { cn, formatRelativeTime, formatPrice, formatPct } from "@/lib/utils";
import { AddCompetitorModal } from "@/components/competitors/AddCompetitorModal";

function ScanStatusDot({ status }: { status: Competitor["scan_status"] }) {
  const configs = {
    scanning: { color: "#a3f000", pulse: true, label: "Scanning…" },
    done: { color: "#22d3ee", pulse: false, label: "Up to date" },
    pending: { color: "#7d92aa", pulse: false, label: "Scheduled" },
    error: { color: "#f87171", pulse: false, label: "Error" },
  };
  const c = configs[status] || configs.pending;
  return (
    <span className="flex items-center gap-1.5 text-xs" style={{ color: c.color }}>
      <span
        className={cn("w-2 h-2 rounded-full inline-block", c.pulse && "animate-pulse")}
        style={{ background: c.color }}
      />
      {c.label}
    </span>
  );
}

function CompetitorCard({ competitor, onRemove }: { competitor: Competitor; onRemove: (id: string) => void }) {
  const [rescanning, setRescanning] = useState(false);

  async function handleRescan(e: React.MouseEvent) {
    e.preventDefault();
    setRescanning(true);
    await api.rescan(competitor.id).catch(() => {});
    setTimeout(() => setRescanning(false), 3000);
  }

  const isActive = competitor.scan_status === "scanning";

  return (
    <Link
      href={`/dashboard/${competitor.id}`}
      className="block rounded-2xl border p-5 transition-all hover:border-white/20 hover:-translate-y-0.5 group"
      style={{ background: "var(--bg-card)", borderColor: "var(--border)" }}
    >
      <div className="flex items-start justify-between mb-4">
        <div>
          <h3 className="font-semibold text-base" style={{ color: "var(--text)" }}>
            {competitor.display_name || competitor.hostname}
          </h3>
          <p className="text-xs mt-0.5" style={{ color: "var(--muted)" }}>
            {competitor.hostname}
          </p>
        </div>
        <ScanStatusDot status={competitor.scan_status} />
      </div>

      <div className="grid grid-cols-3 gap-3 mb-4">
        <MetricPill label="Products" value={competitor.product_count?.toLocaleString() ?? "—"} />
        <MetricPill label="Last scan" value={competitor.last_scanned_at ? formatRelativeTime(competitor.last_scanned_at) : "—"} />
        <MetricPill label="Status" value={competitor.is_active ? "Active" : "Paused"} />
      </div>

      <div className="flex items-center justify-between">
        <span className="text-xs" style={{ color: "var(--muted)" }}>
          Added {formatRelativeTime(competitor.created_at)}
        </span>
        <div className="flex items-center gap-2 opacity-0 group-hover:opacity-100 transition-opacity">
          <button
            onClick={handleRescan}
            className="flex items-center gap-1 text-xs px-2 py-1 rounded-lg transition-colors hover:bg-white/10"
            style={{ color: "var(--muted)" }}
          >
            <RefreshCw className={cn("w-3 h-3", (rescanning || isActive) && "animate-spin")} />
            Rescan
          </button>
        </div>
      </div>
    </Link>
  );
}

function MetricPill({ label, value }: { label: string; value: string }) {
  return (
    <div
      className="rounded-xl px-3 py-2 text-center"
      style={{ background: "rgba(255,255,255,.04)", border: "1px solid var(--border)" }}
    >
      <p className="text-xs mb-0.5" style={{ color: "var(--muted)" }}>{label}</p>
      <p className="text-sm font-semibold font-mono" style={{ color: "var(--text)" }}>{value}</p>
    </div>
  );
}

function EmptyState({ onAdd }: { onAdd: () => void }) {
  return (
    <div className="flex flex-col items-center justify-center min-h-[400px] text-center px-6">
      <div
        className="w-16 h-16 rounded-2xl flex items-center justify-center mb-6"
        style={{ background: "rgba(163,240,0,.1)", border: "1px solid rgba(163,240,0,.2)" }}
      >
        <TrendingUp className="w-8 h-8" style={{ color: "var(--green)" }} />
      </div>
      <h2 className="text-2xl font-bold mb-3" style={{ color: "var(--text)" }}>
        Add your first competitor
      </h2>
      <p className="text-base mb-8 max-w-sm" style={{ color: "var(--muted)" }}>
        Enter any Shopify store URL and we&apos;ll start monitoring their prices, launches, and discounts automatically.
      </p>
      <button
        onClick={onAdd}
        className="flex items-center gap-2 font-semibold px-6 py-3 rounded-xl transition-all hover:brightness-110"
        style={{ background: "var(--green)", color: "#060d18" }}
      >
        <Plus className="w-4 h-4" />
        Add competitor
      </button>
    </div>
  );
}

export default function DashboardPage() {
  const [competitorList, setCompetitorList] = useState<Competitor[]>([]);
  const [loading, setLoading] = useState(true);
  const [showModal, setShowModal] = useState(false);

  const load = useCallback(async () => {
    try {
      const { data } = await api.list();
      setCompetitorList(data);
    } catch {
      // ignore
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    load();
    // Poll every 10s to pick up scan completions
    const interval = setInterval(load, 10000);
    return () => clearInterval(interval);
  }, [load]);

  function handleAdded(competitor: Competitor) {
    setCompetitorList((prev) => [competitor, ...prev]);
    setShowModal(false);
  }

  function handleRemoved(id: string) {
    setCompetitorList((prev) => prev.filter((c) => c.id !== id));
  }

  if (loading) {
    return (
      <div>
        <div className="h-8 w-48 rounded-xl mb-2 animate-pulse" style={{ background: "var(--bg-card)" }} />
        <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-4 mt-6">
          {[1, 2, 3].map((i) => (
            <div key={i} className="h-40 rounded-2xl animate-pulse" style={{ background: "var(--bg-card)" }} />
          ))}
        </div>
      </div>
    );
  }

  return (
    <div>
      <div className="flex items-center justify-between mb-6">
        <div>
          <h1 className="text-2xl font-bold" style={{ color: "var(--text)" }}>Competitors</h1>
          <p className="text-sm mt-1" style={{ color: "var(--muted)" }}>
            {competitorList.length} store{competitorList.length !== 1 ? "s" : ""} tracked
          </p>
        </div>
        <button
          onClick={() => setShowModal(true)}
          className="flex items-center gap-2 font-semibold text-sm px-4 py-2.5 rounded-xl transition-all hover:brightness-110"
          style={{ background: "var(--green)", color: "#060d18" }}
        >
          <Plus className="w-4 h-4" />
          Add competitor
        </button>
      </div>

      {competitorList.length === 0 ? (
        <EmptyState onAdd={() => setShowModal(true)} />
      ) : (
        <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-4">
          {competitorList.map((c) => (
            <CompetitorCard key={c.id} competitor={c} onRemove={handleRemoved} />
          ))}
        </div>
      )}

      {showModal && (
        <AddCompetitorModal onClose={() => setShowModal(false)} onAdded={handleAdded} />
      )}
    </div>
  );
}
