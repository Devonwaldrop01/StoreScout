"use client";

import { useState } from "react";
import { X, Search, AlertCircle, CheckCircle2 } from "lucide-react";
import { competitors as api, type Competitor } from "@/lib/api";
import { cn } from "@/lib/utils";

interface Props {
  onClose: () => void;
  onAdded: (c: Competitor) => void;
}

export function AddCompetitorModal({ onClose, onAdded }: Props) {
  const [url, setUrl] = useState("");
  const [displayName, setDisplayName] = useState("");
  const [checking, setChecking] = useState(false);
  const [submitting, setSubmitting] = useState(false);
  const [storeStatus, setStoreStatus] = useState<"idle" | "ok" | "error">("idle");
  const [error, setError] = useState("");

  async function checkStore(value: string) {
    if (!value.trim()) return;
    setChecking(true);
    setStoreStatus("idle");
    try {
      const res = await fetch(
        `/check_store?store_url=${encodeURIComponent(value.trim())}`
      );
      const data = await res.json();
      setStoreStatus(data.ok ? "ok" : "error");
      setError(data.ok ? "" : (data.reason || "Store not accessible"));
    } catch {
      setStoreStatus("error");
      setError("Network error checking store");
    } finally {
      setChecking(false);
    }
  }

  let checkTimer: ReturnType<typeof setTimeout>;
  function handleUrlChange(e: React.ChangeEvent<HTMLInputElement>) {
    const value = e.target.value;
    setUrl(value);
    setStoreStatus("idle");
    clearTimeout(checkTimer);
    if (value.length > 5) {
      checkTimer = setTimeout(() => checkStore(value), 700);
    }
  }

  async function handleSubmit(e: React.FormEvent) {
    e.preventDefault();
    if (!url.trim()) return;
    setSubmitting(true);
    setError("");
    try {
      const { data } = await api.add(url.trim(), displayName || undefined);
      onAdded(data);
    } catch (err: unknown) {
      const apiErr = err as { data?: { detail?: string | { code?: string; limit?: number } } };
      const detail = apiErr?.data?.detail;
      if (typeof detail === "object" && detail?.code === "competitor_limit_reached") {
        setError(`You've reached your plan's limit of ${detail.limit} competitor${detail.limit === 1 ? "" : "s"}. Upgrade to track more.`);
      } else if (typeof detail === "string") {
        setError(detail);
      } else {
        setError("Failed to add competitor. Please try again.");
      }
    } finally {
      setSubmitting(false);
    }
  }

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center p-4">
      <div className="absolute inset-0 bg-black/60" onClick={onClose} />
      <div
        className="relative w-full max-w-md rounded-2xl p-6 shadow-2xl"
        style={{ background: "var(--bg2)", border: "1px solid var(--border)" }}
      >
        <div className="flex items-center justify-between mb-6">
          <h2 className="text-xl font-bold" style={{ color: "var(--text)" }}>Add competitor</h2>
          <button onClick={onClose} className="p-1 rounded-lg hover:bg-white/10 transition-colors">
            <X className="w-5 h-5" style={{ color: "var(--muted)" }} />
          </button>
        </div>

        <form onSubmit={handleSubmit} className="space-y-4">
          <div>
            <label className="block text-sm font-medium mb-2" style={{ color: "var(--muted)" }}>
              Shopify store URL
            </label>
            <div className="relative">
              <input
                type="text"
                value={url}
                onChange={handleUrlChange}
                placeholder="gymshark.com"
                className="w-full px-4 py-3 rounded-xl text-sm font-mono pr-10 outline-none transition-all"
                style={{
                  background: "var(--bg3)",
                  border: `1px solid ${storeStatus === "ok" ? "#22c55e" : storeStatus === "error" ? "#f87171" : "var(--border)"}`,
                  color: "var(--text)",
                }}
                autoFocus
              />
              <div className="absolute right-3 top-1/2 -translate-y-1/2">
                {checking && (
                  <div className="w-4 h-4 border-2 border-t-transparent rounded-full animate-spin" style={{ borderColor: "var(--blue)" }} />
                )}
                {!checking && storeStatus === "ok" && <CheckCircle2 className="w-4 h-4 text-green-400" />}
                {!checking && storeStatus === "error" && <AlertCircle className="w-4 h-4 text-red-400" />}
              </div>
            </div>
            {storeStatus === "ok" && (
              <p className="text-xs mt-1 text-green-400">✓ Shopify store detected — ready to scan</p>
            )}
            {storeStatus === "error" && (
              <p className="text-xs mt-1 text-red-400">{error || "Store not accessible"}</p>
            )}
          </div>

          <div>
            <label className="block text-sm font-medium mb-2" style={{ color: "var(--muted)" }}>
              Display name <span className="text-xs opacity-60">(optional)</span>
            </label>
            <input
              type="text"
              value={displayName}
              onChange={(e) => setDisplayName(e.target.value)}
              placeholder="e.g. Main competitor"
              className="w-full px-4 py-3 rounded-xl text-sm outline-none"
              style={{
                background: "var(--bg3)",
                border: "1px solid var(--border)",
                color: "var(--text)",
              }}
            />
          </div>

          {error && storeStatus !== "error" && (
            <div
              className="flex items-start gap-2 p-3 rounded-xl text-sm"
              style={{ background: "rgba(248,113,113,.1)", border: "1px solid rgba(248,113,113,.3)", color: "#fca5a5" }}
            >
              <AlertCircle className="w-4 h-4 mt-0.5 shrink-0" />
              {error}
            </div>
          )}

          <button
            type="submit"
            disabled={submitting || !url.trim() || storeStatus === "error"}
            className={cn(
              "w-full flex items-center justify-center gap-2 font-semibold py-3 rounded-xl transition-all",
              (submitting || !url.trim() || storeStatus === "error") ? "opacity-50 cursor-not-allowed" : "hover:brightness-110"
            )}
            style={{ background: "var(--green)", color: "#060d18" }}
          >
            {submitting ? (
              <>
                <div className="w-4 h-4 border-2 border-t-transparent rounded-full animate-spin border-black/40" />
                Adding…
              </>
            ) : (
              <>
                <Search className="w-4 h-4" />
                Start tracking
              </>
            )}
          </button>
        </form>
      </div>
    </div>
  );
}
