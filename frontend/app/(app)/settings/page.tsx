"use client";

import { useEffect, useState } from "react";
import { useSearchParams } from "next/navigation";
import { user as userApi, billing, type UserSubscription, type NotificationPrefs } from "@/lib/api";
import { cn } from "@/lib/utils";
import UpgradeModal from "@/components/UpgradeModal";

export default function SettingsPage() {
  const [subscription, setSubscription] = useState<UserSubscription | null>(null);
  const [prefs, setPrefs] = useState<NotificationPrefs | null>(null);
  const [saving, setSaving] = useState(false);
  const [saved, setSaved] = useState(false);
  const [upgradeOpen, setUpgradeOpen] = useState(false);
  const [portalLoading, setPortalLoading] = useState(false);
  const searchParams = useSearchParams();

  useEffect(() => {
    userApi.subscription().then((r) => setSubscription(r.data)).catch(() => {});
    userApi.prefs().then((r) => setPrefs(r.data)).catch(() => {});

    // Show success banner if returning from Stripe checkout
    if (searchParams.get("upgraded") === "1") {
      // Reload subscription data after a short delay for webhook to process
      setTimeout(() => {
        userApi.subscription().then((r) => setSubscription(r.data)).catch(() => {});
      }, 2000);
    }
  }, [searchParams]);

  async function handleSavePrefs() {
    if (!prefs) return;
    setSaving(true);
    await userApi.updatePrefs(prefs).catch(() => {});
    setSaving(false);
    setSaved(true);
    setTimeout(() => setSaved(false), 2000);
  }

  async function handleManageBilling() {
    setPortalLoading(true);
    try {
      const { url } = await billing.portal();
      window.location.href = url;
    } catch {
      setPortalLoading(false);
    }
  }

  function toggle(key: keyof NotificationPrefs) {
    if (!prefs) return;
    setPrefs({ ...prefs, [key]: !prefs[key] });
  }

  const tierBadgeStyle: Record<string, { bg: string; color: string }> = {
    free: { bg: "rgba(255,255,255,.06)", color: "var(--muted)" },
    pro: { bg: "rgba(163,240,0,.12)", color: "#a3f000" },
    agency: { bg: "rgba(59,130,246,.12)", color: "#60a5fa" },
  };

  const upgraded = searchParams.get("upgraded") === "1";

  return (
    <div>
      <h1 className="text-2xl font-bold mb-6" style={{ color: "var(--text)" }}>Settings</h1>

      {upgraded && (
        <div
          className="mb-6 px-4 py-3 rounded-xl text-sm font-medium"
          style={{ background: "rgba(163,240,0,.12)", border: "1px solid rgba(163,240,0,.25)", color: "#a3f000" }}
        >
          Your plan has been upgraded. Welcome to Pro!
        </div>
      )}

      <div className="space-y-6 max-w-2xl">
        {/* Subscription */}
        {subscription && (
          <section
            className="rounded-2xl p-6"
            style={{ background: "var(--bg-card)", border: "1px solid var(--border)" }}
          >
            <h2 className="font-semibold mb-4" style={{ color: "var(--text)" }}>Your plan</h2>
            <div className="flex items-center justify-between gap-4 flex-wrap">
              <div>
                <div className="flex items-center gap-2 mb-1">
                  <span
                    className="text-xs font-bold uppercase px-2 py-1 rounded-lg"
                    style={tierBadgeStyle[subscription.tier] || tierBadgeStyle.free}
                  >
                    {subscription.tier}
                  </span>
                  {subscription.subscription_status && subscription.subscription_status !== "inactive" && (
                    <span className="text-sm" style={{ color: "var(--muted)" }}>
                      {subscription.subscription_status}
                    </span>
                  )}
                </div>
                <p className="text-sm" style={{ color: "var(--muted)" }}>
                  {subscription.limits.max_competitors} competitor{subscription.limits.max_competitors !== 1 ? "s" : ""} ·{" "}
                  {subscription.tier === "free" ? "Manual rescan (weekly)" : `Auto-scan every ${subscription.limits.scan_hours}h`} ·{" "}
                  {subscription.limits.history_days === 0 ? "No history" : `${subscription.limits.history_days}d history`}
                </p>
              </div>
              <div className="flex gap-2">
                {subscription.tier === "free" ? (
                  <button
                    onClick={() => setUpgradeOpen(true)}
                    className="font-semibold text-sm px-4 py-2 rounded-xl transition-all hover:brightness-110"
                    style={{ background: "#a3f000", color: "#060d18" }}
                  >
                    Upgrade
                  </button>
                ) : (
                  <button
                    onClick={handleManageBilling}
                    disabled={portalLoading}
                    className="font-semibold text-sm px-4 py-2 rounded-xl transition-all hover:opacity-80 disabled:opacity-50"
                    style={{ background: "var(--bg3)", color: "var(--text)", border: "1px solid var(--border)" }}
                  >
                    {portalLoading ? "Loading…" : "Manage billing"}
                  </button>
                )}
              </div>
            </div>
          </section>
        )}

        {/* Notification preferences */}
        {prefs && (
          <section
            className="rounded-2xl p-6"
            style={{ background: "var(--bg-card)", border: "1px solid var(--border)" }}
          >
            <h2 className="font-semibold mb-4" style={{ color: "var(--text)" }}>Email notifications</h2>

            <div className="space-y-3">
              {[
                { key: "email_price_changes" as const, label: "Price changes", desc: "Alert when a product price changes ≥10%" },
                { key: "email_new_products" as const, label: "New product launches", desc: "Alert when a new product is published" },
                { key: "email_discount_changes" as const, label: "Discount campaigns", desc: "Alert when a sale starts or ends" },
                { key: "email_weekly_digest" as const, label: "Weekly digest", desc: "Monday morning summary with AI insights (Pro+)" },
              ].map(({ key, label, desc }) => (
                <div key={key} className="flex items-start justify-between gap-4 py-3 border-b" style={{ borderColor: "var(--border)" }}>
                  <div>
                    <p className="text-sm font-medium" style={{ color: "var(--text)" }}>{label}</p>
                    <p className="text-xs mt-0.5" style={{ color: "var(--muted)" }}>{desc}</p>
                  </div>
                  <button
                    onClick={() => toggle(key)}
                    className={cn(
                      "relative inline-flex h-6 w-11 shrink-0 items-center rounded-full transition-colors focus:outline-none"
                    )}
                    style={{ background: prefs[key] ? "#a3f000" : "rgba(255,255,255,.12)" }}
                  >
                    <span
                      className="pointer-events-none inline-block h-4 w-4 rounded-full bg-white shadow-lg transition-transform"
                      style={{ transform: prefs[key] ? "translateX(1.375rem)" : "translateX(0.25rem)" }}
                    />
                  </button>
                </div>
              ))}
            </div>

            <button
              onClick={handleSavePrefs}
              disabled={saving}
              className="mt-4 font-semibold text-sm px-5 py-2.5 rounded-xl transition-all hover:brightness-110 disabled:opacity-50"
              style={{ background: "#a3f000", color: "#060d18" }}
            >
              {saved ? "Saved ✓" : saving ? "Saving…" : "Save preferences"}
            </button>
          </section>
        )}
      </div>

      <UpgradeModal open={upgradeOpen} onClose={() => setUpgradeOpen(false)} trigger="general" />
    </div>
  );
}
