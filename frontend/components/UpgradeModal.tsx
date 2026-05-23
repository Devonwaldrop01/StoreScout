"use client";

import { useState } from "react";
import { X, Zap, Building2, Check } from "lucide-react";
import { billing } from "@/lib/api";

interface Props {
  open: boolean;
  onClose: () => void;
  trigger?: "competitor_limit" | "history" | "alerts" | "general";
}

const PLANS = [
  {
    key: "pro",
    name: "Pro",
    price: 29,
    annualPrice: 23,
    icon: Zap,
    color: "#a3f000",
    colorBg: "rgba(163,240,0,.08)",
    colorBorder: "rgba(163,240,0,.25)",
    features: [
      "10 competitors",
      "Daily auto-scans",
      "90-day price history",
      "Email + in-app alerts",
      "Weekly AI digest",
    ],
  },
  {
    key: "agency",
    name: "Agency",
    price: 79,
    annualPrice: 63,
    icon: Building2,
    color: "#60a5fa",
    colorBg: "rgba(96,165,250,.08)",
    colorBorder: "rgba(96,165,250,.25)",
    features: [
      "50 competitors",
      "Daily auto-scans",
      "Unlimited history",
      "Email + in-app alerts",
      "Weekly AI digest",
      "Shareable report URLs",
    ],
  },
];

const TRIGGER_COPY: Record<string, string> = {
  competitor_limit: "You've reached your free plan limit of 1 competitor. Upgrade to track more.",
  history: "Price history is available on Pro and Agency plans.",
  alerts: "Email alerts are available on Pro and Agency plans.",
  general: "Unlock the full power of StoreScout.",
};

export default function UpgradeModal({ open, onClose, trigger = "general" }: Props) {
  const [annual, setAnnual] = useState(false);
  const [loading, setLoading] = useState<string | null>(null);
  const [error, setError] = useState("");

  if (!open) return null;

  async function handleUpgrade(plan: string) {
    setLoading(plan);
    setError("");
    try {
      const { url } = await billing.checkout(plan, annual ? "annual" : "monthly");
      window.location.href = url;
    } catch (e: unknown) {
      const msg = e instanceof Error ? e.message : "Something went wrong";
      setError(msg);
      setLoading(null);
    }
  }

  return (
    <div
      className="fixed inset-0 z-50 flex items-center justify-center p-4"
      style={{ background: "rgba(0,0,0,.7)", backdropFilter: "blur(4px)" }}
      onClick={(e) => e.target === e.currentTarget && onClose()}
    >
      <div
        className="relative w-full max-w-2xl rounded-2xl p-8"
        style={{ background: "var(--bg2)", border: "1px solid var(--border)" }}
      >
        <button
          onClick={onClose}
          className="absolute top-4 right-4 p-1 rounded-lg hover:opacity-70 transition-opacity"
          style={{ color: "var(--muted)" }}
        >
          <X className="w-5 h-5" />
        </button>

        <div className="text-center mb-8">
          <h2 className="text-2xl font-bold mb-2" style={{ color: "var(--text)" }}>
            Upgrade StoreScout
          </h2>
          <p className="text-sm" style={{ color: "var(--muted)" }}>
            {TRIGGER_COPY[trigger]}
          </p>

          {/* Monthly / Annual toggle */}
          <div className="inline-flex items-center gap-3 mt-5 p-1 rounded-xl" style={{ background: "var(--bg3)" }}>
            <button
              onClick={() => setAnnual(false)}
              className="px-4 py-1.5 rounded-lg text-sm font-medium transition-all"
              style={{
                background: !annual ? "#a3f000" : "transparent",
                color: !annual ? "#060d18" : "var(--muted)",
              }}
            >
              Monthly
            </button>
            <button
              onClick={() => setAnnual(true)}
              className="px-4 py-1.5 rounded-lg text-sm font-medium transition-all flex items-center gap-1.5"
              style={{
                background: annual ? "#a3f000" : "transparent",
                color: annual ? "#060d18" : "var(--muted)",
              }}
            >
              Annual
              <span
                className="text-xs font-bold px-1.5 py-0.5 rounded-md"
                style={{ background: annual ? "rgba(0,0,0,.15)" : "rgba(163,240,0,.15)", color: annual ? "#060d18" : "#a3f000" }}
              >
                20% off
              </span>
            </button>
          </div>
        </div>

        <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
          {PLANS.map((plan) => {
            const Icon = plan.icon;
            const price = annual ? plan.annualPrice : plan.price;
            return (
              <div
                key={plan.key}
                className="rounded-2xl p-6 flex flex-col"
                style={{ background: plan.colorBg, border: `1px solid ${plan.colorBorder}` }}
              >
                <div className="flex items-center gap-2 mb-4">
                  <Icon className="w-5 h-5" style={{ color: plan.color }} />
                  <span className="font-bold" style={{ color: plan.color }}>{plan.name}</span>
                </div>

                <div className="mb-5">
                  <span className="text-3xl font-bold" style={{ color: "var(--text)" }}>${price}</span>
                  <span className="text-sm ml-1" style={{ color: "var(--muted)" }}>/mo</span>
                  {annual && (
                    <p className="text-xs mt-0.5" style={{ color: "var(--muted)" }}>
                      billed annually (${price * 12}/yr)
                    </p>
                  )}
                </div>

                <ul className="space-y-2 mb-6 flex-1">
                  {plan.features.map((f) => (
                    <li key={f} className="flex items-center gap-2 text-sm" style={{ color: "var(--muted)" }}>
                      <Check className="w-4 h-4 shrink-0" style={{ color: plan.color }} />
                      {f}
                    </li>
                  ))}
                </ul>

                <button
                  onClick={() => handleUpgrade(plan.key)}
                  disabled={!!loading}
                  className="w-full py-3 rounded-xl font-semibold text-sm transition-all hover:brightness-110 disabled:opacity-50"
                  style={{ background: plan.color, color: "#060d18" }}
                >
                  {loading === plan.key ? "Redirecting…" : `Upgrade to ${plan.name}`}
                </button>
              </div>
            );
          })}
        </div>

        {error && (
          <p className="text-sm text-red-400 text-center mt-4">{error}</p>
        )}

        <p className="text-xs text-center mt-4" style={{ color: "var(--muted)" }}>
          Secure checkout via Stripe · Cancel anytime · No hidden fees
        </p>
      </div>
    </div>
  );
}
