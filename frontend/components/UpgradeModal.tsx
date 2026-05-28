"use client";

import { useState } from "react";
import { X, Zap, Building2, Check, AlertCircle } from "lucide-react";
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
    color: "#3b82f6",
    colorBg: "rgba(59,130,246,.06)",
    colorBorder: "rgba(59,130,246,.3)",
    checkColor: "var(--accent)",
    glowShadow: "0 0 0 1px rgba(59,130,246,.3), 0 8px 32px rgba(59,130,246,.06)",
    popular: true,
    features: [
      "10 competitors",
      "Daily auto-rescan",
      "90-day history",
      "Email alerts",
      "Weekly AI digest",
      "In-app alert feed",
    ],
  },
  {
    key: "agency",
    name: "Agency",
    price: 79,
    annualPrice: 63,
    icon: Building2,
    color: "#60a5fa",
    colorBg: "rgba(96,165,250,.06)",
    colorBorder: "rgba(96,165,250,.25)",
    checkColor: "var(--blue)",
    glowShadow: "0 0 0 1px rgba(96,165,250,.25), 0 8px 32px rgba(96,165,250,.05)",
    popular: false,
    features: [
      "50 competitors",
      "Daily auto-rescan",
      "Unlimited history",
      "Email alerts",
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
      style={{ background: "rgba(0,0,0,.8)", backdropFilter: "blur(8px)" }}
      onClick={(e) => e.target === e.currentTarget && onClose()}
    >
      <div
        className="relative w-full max-w-xl rounded-2xl p-7"
        style={{
          background: "var(--bg2)",
          border: "1px solid var(--border)",
          boxShadow: "0 -1px 0 0 rgba(59,130,246,.15), 0 24px 80px rgba(0,0,0,.6)",
        }}
      >
        {/* Close button */}
        <button
          onClick={onClose}
          className="absolute top-4 right-4 p-1.5 rounded-lg transition-opacity hover:opacity-70"
          style={{ color: "var(--muted)" }}
        >
          <X className="w-4 h-4" />
        </button>

        {/* Header */}
        <div className="flex flex-col items-center text-center mb-6">
          {/* Icon */}
          <div
            className="flex items-center justify-center w-10 h-10 rounded-full mb-4"
            style={{
              background: "rgba(59,130,246,.12)",
              border: "1px solid rgba(59,130,246,.2)",
            }}
          >
            <Zap className="w-5 h-5" style={{ color: "var(--accent)" }} />
          </div>

          <h2 className="text-xl font-bold mb-1.5" style={{ color: "var(--text)" }}>
            Unlock StoreScout
          </h2>
          <p className="text-sm max-w-sm" style={{ color: "var(--muted)" }}>
            {TRIGGER_COPY[trigger]}
          </p>

          {/* Monthly / Annual toggle */}
          <div
            className="inline-flex items-center mt-5 p-1 rounded-xl"
            style={{ background: "var(--bg3)", border: "1px solid var(--border)" }}
          >
            <button
              onClick={() => setAnnual(false)}
              className="px-4 py-1.5 rounded-lg text-sm font-medium transition-all"
              style={{
                background: !annual ? "var(--accent)" : "transparent",
                color: !annual ? "#0a0a0f" : "var(--muted)",
              }}
            >
              Monthly
            </button>
            <button
              onClick={() => setAnnual(true)}
              className="px-4 py-1.5 rounded-lg text-sm font-medium transition-all flex items-center gap-2"
              style={{
                background: annual ? "var(--accent)" : "transparent",
                color: annual ? "#0a0a0f" : "var(--muted)",
              }}
            >
              Annual
              <span
                className="text-xs font-bold px-1.5 py-0.5 rounded-md"
                style={{
                  background: annual ? "rgba(0,0,0,.18)" : "rgba(59,130,246,.12)",
                  color: annual ? "#0a0a0f" : "var(--accent)",
                }}
              >
                20% off
              </span>
            </button>
          </div>
        </div>

        {/* Plan cards — stacked vertically */}
        <div className="flex flex-col gap-3">
          {PLANS.map((plan) => {
            const Icon = plan.icon;
            const price = annual ? plan.annualPrice : plan.price;
            return (
              <div
                key={plan.key}
                className="relative rounded-2xl p-5"
                style={{
                  background: plan.colorBg,
                  boxShadow: plan.glowShadow,
                  border: `1px solid ${plan.colorBorder}`,
                }}
              >
                {/* Most popular badge */}
                {plan.popular && (
                  <span
                    className="absolute top-4 right-4 text-xs font-bold px-2 py-0.5 rounded-full tracking-wide"
                    style={{
                      background: "rgba(59,130,246,.12)",
                      color: "var(--accent)",
                      border: "1px solid rgba(59,130,246,.2)",
                    }}
                  >
                    MOST POPULAR
                  </span>
                )}

                {/* Card header: name + price */}
                <div className="flex items-center justify-between mb-4 pr-28">
                  <div className="flex items-center gap-2">
                    <Icon className="w-4 h-4" style={{ color: plan.color }} />
                    <span className="font-bold text-sm" style={{ color: plan.color }}>
                      {plan.name}
                    </span>
                  </div>
                  <div className="flex items-baseline gap-0.5">
                    <span className="text-2xl font-bold" style={{ color: "var(--text)" }}>
                      ${price}
                    </span>
                    <span className="text-xs ml-0.5" style={{ color: "var(--muted)" }}>
                      /mo
                    </span>
                    {annual && (
                      <span className="text-xs ml-2" style={{ color: "var(--muted)" }}>
                        · ${price * 12}/yr
                      </span>
                    )}
                  </div>
                </div>

                {/* Features */}
                <ul className="grid grid-cols-2 gap-x-4 gap-y-1.5 mb-4">
                  {plan.features.map((f) => (
                    <li key={f} className="flex items-center gap-1.5 text-sm" style={{ color: "var(--text)" }}>
                      <Check className="w-3.5 h-3.5 shrink-0" style={{ color: plan.checkColor }} />
                      {f}
                    </li>
                  ))}
                </ul>

                {/* CTA */}
                <button
                  onClick={() => handleUpgrade(plan.key)}
                  disabled={!!loading}
                  className="w-full py-2.5 rounded-xl font-semibold text-sm transition-all hover:brightness-110 disabled:opacity-50"
                  style={{ background: plan.color, color: "#ffffff" }}
                >
                  {loading === plan.key ? "Redirecting…" : `Upgrade to ${plan.name}`}
                </button>
              </div>
            );
          })}
        </div>

        {error && (
          <div className="flex items-center gap-2 px-4 py-3 rounded-xl text-sm mt-4" style={{ background: "rgba(239,68,68,.1)", border: "1px solid rgba(239,68,68,.2)", color: "#f87171" }}>
            <AlertCircle className="w-4 h-4 flex-shrink-0" />
            {error}
          </div>
        )}

        {/* Footer */}
        <p className="text-xs text-center mt-5" style={{ color: "var(--muted)" }}>
          Secure checkout via Stripe · Cancel anytime
        </p>
      </div>
    </div>
  );
}
