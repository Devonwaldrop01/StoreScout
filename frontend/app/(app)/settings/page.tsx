"use client";

import { Suspense, useEffect, useState } from "react";
import { useSearchParams } from "next/navigation";
import {
  user as userApi, billing, team as teamApi,
  apiKeys as apiKeysApi, integrations as integrationsApi,
  type UserSubscription, type NotificationPrefs,
  type TeamMember, type ApiKey, type KlaviyoStatus, type KlaviyoTestResult,
  type GoogleProperties,
} from "@/lib/api";
import UpgradeModal from "@/components/UpgradeModal";
import { IntelligenceSources } from "@/components/settings/IntelligenceSources";
import { IntegrationHub } from "@/components/integrations/IntegrationHub";
import { track } from "@/lib/analytics";
import { scanCadenceLabel, historyLabel, subscriptionNotice } from "@/lib/entitlements";
import { createClient } from "@/lib/supabase/client";
import {
  Hash, Globe, Users, X, Loader2, Key, Copy, Check, Terminal,
  Plus, User, Zap, Bell,
} from "lucide-react";

const PLANS = [
  {
    tier: "free",
    label: "Free",
    price: "$0",
    popular: false,
    features: ["1 competitor", "Weekly auto-scan + on-demand", "Current state only", "No real-time alerts"],
  },
  {
    tier: "pro",
    label: "Pro",
    price: "$29",
    popular: true,
    features: ["10 competitors", "Daily auto-rescan", "90-day history", "Email alerts", "Weekly AI digest"],
  },
  {
    tier: "agency",
    label: "Agency",
    price: "$79",
    popular: false,
    features: ["50 competitors", "Daily auto-rescan", "Unlimited history", "Email alerts", "Shareable reports"],
  },
];

function SettingsContent() {
  const supabase = createClient();
  const searchParams = useSearchParams();

  const [activeTab, setActiveTab] = useState("account");

  // Plan + prefs
  const [subscription, setSubscription] = useState<UserSubscription | null>(null);
  const [prefs, setPrefs] = useState<NotificationPrefs | null>(null);
  const [saving, setSaving] = useState(false);
  const [saved, setSaved] = useState(false);
  const [upgradeOpen, setUpgradeOpen] = useState(false);
  const [portalLoading, setPortalLoading] = useState(false);

  // Google
  const [googleConnected, setGoogleConnected] = useState(false);
  const [googleEnabled, setGoogleEnabled] = useState(false);
  const [googleGA4, setGoogleGA4] = useState("");
  const [googleGSC, setGoogleGSC] = useState("");
  const [googleProperties, setGoogleProperties] = useState<GoogleProperties | null>(null);
  const [googleConnecting, setGoogleConnecting] = useState(false);
  const [googleConnectedBanner, setGoogleConnectedBanner] = useState(false);
  const [googleSavingProperty, setGoogleSavingProperty] = useState(false);

  // Klaviyo
  const [klaviyoStatus, setKlaviyoStatus] = useState<KlaviyoStatus | null>(null);
  const [klaviyoKey, setKlaviyoKey] = useState("");
  const [klaviyoSaving, setKlaviyoSaving] = useState(false);
  const [klaviyoTesting, setKlaviyoTesting] = useState(false);
  const [klaviyoTestResult, setKlaviyoTestResult] = useState<KlaviyoTestResult | null>(null);
  const [klaviyoError, setKlaviyoError] = useState("");

  // Integrations (Slack/webhook)
  const [slackUrl, setSlackUrl] = useState("");
  const [webhookUrl, setWebhookUrl] = useState("");
  const [testingSlack, setTestingSlack] = useState(false);
  const [testingWebhook, setTestingWebhook] = useState(false);
  const [slackTestResult, setSlackTestResult] = useState<"ok" | "error" | null>(null);
  const [webhookTestResult, setWebhookTestResult] = useState<"ok" | "error" | null>(null);

  // Team
  const [teamMembers, setTeamMembers] = useState<TeamMember[]>([]);
  const [inviteEmail, setInviteEmail] = useState("");
  const [inviting, setInviting] = useState(false);
  const [inviteError, setInviteError] = useState("");
  const [inviteSent, setInviteSent] = useState(false);

  // API keys
  const [keys, setKeys] = useState<ApiKey[]>([]);
  const [newKeyName, setNewKeyName] = useState("");
  const [creatingKey, setCreatingKey] = useState(false);
  const [newKeyPlaintext, setNewKeyPlaintext] = useState("");
  const [copiedKey, setCopiedKey] = useState(false);

  // Account
  const [userEmail, setUserEmail] = useState("");
  const [passwordResetSent, setPasswordResetSent] = useState(false);
  const [deletingAccount, setDeletingAccount] = useState(false);

  useEffect(() => {
    if (searchParams.get("upgrade") === "1") setUpgradeOpen(true);
    if (searchParams.get("tab")) setActiveTab(searchParams.get("tab")!);

    userApi.subscription().then((r) => {
      setSubscription(r.data);
      if (r.data.tier === "developer") {
        apiKeysApi.list().then((kr) => setKeys(kr.data)).catch(() => {});
      }
      if (r.data.tier === "agency") {
        teamApi.members().then((tr) => setTeamMembers(tr.data)).catch(() => {});
      }
    }).catch(() => {});

    userApi.prefs().then((r) => {
      setPrefs(r.data);
      setSlackUrl(r.data.slack_webhook_url || "");
      setWebhookUrl(r.data.webhook_url || "");
    }).catch(() => {});

    integrationsApi.get().then((r) => { setKlaviyoStatus(r.data.klaviyo); setGoogleEnabled(!!r.data.google_enabled); }).catch(() => {});
    integrationsApi.google.properties()
      .then((r) => { setGoogleConnected(true); setGoogleProperties(r); })
      .catch(() => {});

    if (searchParams.get("google_connected") === "true") {
      setGoogleConnectedBanner(true);
      setActiveTab("integrations");
      setTimeout(() => setGoogleConnectedBanner(false), 5000);
      integrationsApi.google.properties()
        .then((r) => { setGoogleConnected(true); setGoogleProperties(r); })
        .catch(() => {});
    }

    supabase.auth.getUser().then(({ data }) => {
      if (data.user?.email) setUserEmail(data.user.email);
    });

    if (searchParams.get("upgraded") === "1") {
      let attempts = 0;
      const poll = () => {
        attempts++;
        userApi.subscription()
          .then((r) => {
            setSubscription(r.data);
            const isPaid = ["pro", "agency", "developer"].includes(r.data.tier ?? "");
            if (isPaid) {
              // Fire once per checkout return — the subscription is confirmed active.
              try {
                if (!sessionStorage.getItem("ss_sub_tracked")) {
                  track("subscription_started", { tier: r.data.tier });
                  sessionStorage.setItem("ss_sub_tracked", "1");
                }
              } catch {}
            } else if (attempts < 6) setTimeout(poll, 2000);
          })
          .catch(() => { if (attempts < 6) setTimeout(poll, 2000); });
      };
      setTimeout(poll, 1500);
    }
  }, [searchParams, supabase]);

  // ── Handlers ──────────────────────────────────────────────────────────────

  async function savePrefs(patch: Partial<NotificationPrefs>) {
    setPrefs((prev) => (prev ? { ...prev, ...patch } : prev));
    try {
      await userApi.updatePrefs(patch);
      setSaved(true);
      setTimeout(() => setSaved(false), 2000);
    } catch { /* optimistic value stays; next load corrects */ }
  }

  async function handleTogglePref(key: keyof NotificationPrefs) {
    if (!prefs) return;
    const newValue = !prefs[key];
    const newPrefs = { ...prefs, [key]: newValue };
    setPrefs(newPrefs);
    setSaving(true);
    try {
      await userApi.updatePrefs({ [key]: newValue });
      setSaved(true);
      setTimeout(() => setSaved(false), 2000);
    } catch {
      setPrefs(prefs);
    } finally {
      setSaving(false);
    }
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

  async function handleGoogleConnect() {
    setGoogleConnecting(true);
    try {
      const { url } = await integrationsApi.google.connectUrl();
      window.location.href = url;
    } catch {
      setGoogleConnecting(false);
    }
  }

  async function handleGoogleSaveProperty() {
    setGoogleSavingProperty(true);
    try {
      await integrationsApi.google.saveProperty(googleGA4 || null, googleGSC || null);
    } catch {}
    setGoogleSavingProperty(false);
  }

  async function handleGoogleDisconnect() {
    await integrationsApi.google.disconnect().catch(() => {});
    setGoogleConnected(false);
    setGoogleProperties(null);
    setGoogleGA4("");
    setGoogleGSC("");
  }

  async function handleSaveKlaviyo() {
    if (!klaviyoKey.trim()) return;
    setKlaviyoSaving(true);
    setKlaviyoError("");
    try {
      const { data } = await integrationsApi.klaviyo.save(klaviyoKey.trim());
      setKlaviyoStatus(data);
      setKlaviyoKey("");
    } catch {
      setKlaviyoError("Could not save key. Make sure it's a valid Klaviyo private API key.");
    }
    setKlaviyoSaving(false);
  }

  async function handleTestKlaviyo() {
    setKlaviyoTesting(true);
    setKlaviyoTestResult(null);
    setKlaviyoError("");
    try {
      const result = await integrationsApi.klaviyo.test();
      setKlaviyoTestResult(result);
    } catch (err: unknown) {
      const msg = (err as { data?: { detail?: string } })?.data?.detail || "Test failed — check your API key.";
      setKlaviyoError(msg);
    }
    setKlaviyoTesting(false);
  }

  async function handleRemoveKlaviyo() {
    await integrationsApi.klaviyo.remove().catch(() => {});
    setKlaviyoStatus(null);
    setKlaviyoTestResult(null);
  }

  async function handleSaveSlack() {
    await userApi.updatePrefs({ slack_webhook_url: slackUrl || undefined }).catch(() => {});
    setPrefs((p) => p ? { ...p, slack_webhook_url: slackUrl } : p);
  }

  async function handleSaveWebhook() {
    await userApi.updatePrefs({ webhook_url: webhookUrl || undefined }).catch(() => {});
    setPrefs((p) => p ? { ...p, webhook_url: webhookUrl } : p);
  }

  async function handleTestSlack() {
    if (!slackUrl) return;
    await handleSaveSlack();
    setTestingSlack(true);
    setSlackTestResult(null);
    try {
      const r = await userApi.testWebhook("slack");
      setSlackTestResult(r.status === "ok" ? "ok" : "error");
    } catch {
      setSlackTestResult("error");
    } finally {
      setTestingSlack(false);
      setTimeout(() => setSlackTestResult(null), 4000);
    }
  }

  async function handleTestWebhook() {
    if (!webhookUrl) return;
    await handleSaveWebhook();
    setTestingWebhook(true);
    setWebhookTestResult(null);
    try {
      const r = await userApi.testWebhook("generic");
      setWebhookTestResult(r.status === "ok" ? "ok" : "error");
    } catch {
      setWebhookTestResult("error");
    } finally {
      setTestingWebhook(false);
      setTimeout(() => setWebhookTestResult(null), 4000);
    }
  }

  async function handleInvite() {
    if (!inviteEmail.trim()) return;
    setInviting(true);
    setInviteError("");
    setInviteSent(false);
    try {
      await teamApi.invite(inviteEmail.trim());
      setInviteSent(true);
      setInviteEmail("");
      const { data } = await teamApi.members();
      setTeamMembers(data);
      setTimeout(() => setInviteSent(false), 4000);
    } catch (err: unknown) {
      const e = err as { data?: { detail?: string } };
      setInviteError(e?.data?.detail || "Could not send invite.");
    } finally {
      setInviting(false);
    }
  }

  async function handleRemoveMember(id: string) {
    if (!confirm("Remove this team member? They will lose access immediately.")) return;
    await teamApi.remove(id).catch(() => {});
    setTeamMembers((prev) => prev.filter((m) => m.id !== id));
  }

  async function handleCreateKey() {
    setCreatingKey(true);
    setNewKeyPlaintext("");
    try {
      const { data } = await apiKeysApi.create(newKeyName.trim() || "API key");
      setNewKeyPlaintext(data.key);
      setNewKeyName("");
      const kr = await apiKeysApi.list();
      setKeys(kr.data);
    } catch {} finally {
      setCreatingKey(false);
    }
  }

  async function handleRevokeKey(keyId: string) {
    if (!confirm("Revoke this API key? Any integrations using it will stop working immediately.")) return;
    await apiKeysApi.revoke(keyId).catch(() => {});
    setKeys((prev) => prev.filter((k) => k.id !== keyId));
  }

  function handleCopyKey() {
    navigator.clipboard.writeText(newKeyPlaintext).then(() => {
      setCopiedKey(true);
      setTimeout(() => setCopiedKey(false), 2000);
    });
  }

  async function handleResetPassword() {
    if (!userEmail) return;
    await supabase.auth.resetPasswordForEmail(userEmail, {
      redirectTo: `${window.location.origin}/auth/update-password`,
    });
    setPasswordResetSent(true);
    setTimeout(() => setPasswordResetSent(false), 5000);
  }

  async function handleDeleteAccount() {
    const confirmed = confirm(
      "Delete your account permanently?\n\nThis will remove all your tracked competitors, scan history, and billing data. This cannot be undone."
    );
    if (!confirmed) return;
    setDeletingAccount(true);
    await supabase.auth.signOut().catch(() => {});
    window.location.href = "/";
  }

  // ── UI helpers ─────────────────────────────────────────────────────────────

  const tierBadgeStyle: Record<string, { background: string; color: string }> = {
    free:      { background: "rgba(255,255,255,.06)",   color: "var(--muted)" },
    pro:       { background: "rgba(255,178,36,.12)",    color: "#FFB224" },
    agency:    { background: "rgba(255,178,36,.12)",    color: "#FFB224" },
    developer: { background: "rgba(168,85,247,.12)",    color: "#7DB8C9" },
  };

  const upgraded = searchParams.get("upgraded") === "1";
  const tier = subscription?.tier ?? "free";

  const tabs = [
    "account",
    "billing",
    "notifications",
    "integrations",
    ...(tier === "agency" ? ["team"] : []),
    ...(tier === "developer" ? ["api"] : []),
  ];

  const sectionClass = "rounded-md p-6";
  const sectionStyle = { background: "var(--bg-card)", border: "1px solid var(--border)" };
  const inputClass = "flex-1 px-4 py-2.5 rounded-md text-sm outline-none";
  const inputStyle = { background: "var(--bg3)", border: "1px solid var(--border)", color: "var(--text)" };

  return (
    <div className="max-w-2xl">
      <p className="tick-label mb-1.5">Configuration</p>
      <h1 className="text-xl font-bold tracking-tight mb-6" style={{ color: "var(--text)" }}>Settings</h1>

      {upgraded && (
        <div
          className="mb-6 px-4 py-3 rounded-md text-sm font-medium"
          style={{ background: "rgba(255,178,36,.12)", border: "1px solid rgba(255,178,36,.25)", color: "#FFB224" }}
        >
          Your plan has been upgraded. Welcome to Pro!
        </div>
      )}

      {/* Tab bar — underline rail */}
      <div className="flex items-center gap-1 mb-7 flex-wrap border-b" style={{ borderColor: "var(--border)" }}>
        {tabs.map((tab) => (
          <button
            key={tab}
            onClick={() => setActiveTab(tab)}
            className="relative px-4 py-2 text-sm font-medium capitalize transition-colors"
            style={{ color: activeTab === tab ? "var(--text)" : "var(--muted)" }}
          >
            {tab}
            {activeTab === tab && (
              <span className="absolute -bottom-px left-3 right-3 h-0.5" style={{ background: "var(--accent)" }} />
            )}
          </button>
        ))}
      </div>

      {/* ── Account tab ── */}
      {activeTab === "account" && (
        <div className="space-y-6">
          <section className={sectionClass} style={sectionStyle}>
            <div className="flex items-center gap-2 mb-5">
              <User className="w-4 h-4" style={{ color: "var(--muted)" }} />
              <h2 className="font-semibold" style={{ color: "var(--text)" }}>Account</h2>
            </div>

            <div className="space-y-0">
              <div
                className="flex items-center justify-between py-3 border-b"
                style={{ borderColor: "var(--border)" }}
              >
                <div>
                  <p className="text-sm font-medium" style={{ color: "var(--text)" }}>Email address</p>
                  <p className="text-xs mt-0.5 font-mono" style={{ color: "var(--muted)" }}>
                    {userEmail || "—"}
                  </p>
                </div>
              </div>

              <div
                className="flex items-center justify-between py-3"
                style={{ borderBottom: "1px solid var(--border)" }}
              >
                <div>
                  <p className="text-sm font-medium" style={{ color: "var(--text)" }}>Password</p>
                  <p className="text-xs mt-0.5" style={{ color: "var(--muted)" }}>
                    {passwordResetSent
                      ? "Reset link sent — check your email"
                      : "We'll send a reset link to your email address"}
                  </p>
                </div>
                <button
                  onClick={handleResetPassword}
                  disabled={passwordResetSent || !userEmail}
                  className="shrink-0 text-sm font-semibold px-4 py-2 rounded-md transition-all hover:opacity-80 disabled:opacity-50"
                  style={{ background: "var(--bg3)", color: "var(--text)", border: "1px solid var(--border)" }}
                >
                  {passwordResetSent ? "Sent ✓" : "Reset password"}
                </button>
              </div>
            </div>

            <div className="mt-5 pt-5 border-t" style={{ borderColor: "var(--border)" }}>
              <p className="text-xs font-bold uppercase tracking-wider mb-3" style={{ color: "#F2555A" }}>
                Danger zone
              </p>
              <button
                onClick={handleDeleteAccount}
                disabled={deletingAccount}
                className="text-sm font-semibold px-4 py-2.5 rounded-md transition-all hover:opacity-80 disabled:opacity-60"
                style={{ background: "rgba(242,85,90,.1)", color: "#F2555A", border: "1px solid rgba(242,85,90,.25)" }}
              >
                {deletingAccount ? "Deleting…" : "Delete account"}
              </button>
              <p className="text-xs mt-2" style={{ color: "var(--muted)" }}>
                Permanently deletes your account, all tracked competitors, and scan history. This cannot be undone.
              </p>
            </div>
          </section>
        </div>
      )}

      {/* ── Billing tab ── */}
      {activeTab === "billing" && (
        <div className="space-y-8">

          {/* Current plan + billing details (two-column) */}
          <div className="grid grid-cols-1 md:grid-cols-2 gap-5">
            {/* Left: plan card */}
            <section className={sectionClass} style={sectionStyle}>
              <p className="text-xs font-bold uppercase tracking-wider mb-4" style={{ color: "var(--muted)" }}>
                Current plan
              </p>
              {subscription ? (
                <>
                  <div className="flex items-center gap-2 mb-4">
                    <span
                      className="text-xs font-bold uppercase px-2 py-1 rounded-lg"
                      style={tierBadgeStyle[subscription.tier] || tierBadgeStyle.free}
                    >
                      {subscription.tier}
                    </span>
                    {subscription.subscription_status && subscription.subscription_status !== "inactive" && (
                      <span className="text-sm capitalize" style={{ color: "var(--muted)" }}>
                        {subscription.subscription_status}
                      </span>
                    )}
                  </div>
                  {(() => {
                    const notice = subscriptionNotice(subscription.subscription_state);
                    if (!notice) return null;
                    const warn = notice.tone === "warn";
                    return (
                      <div
                        className="text-xs rounded-md px-3 py-2 mb-4"
                        style={{
                          background: warn ? "rgba(242,85,90,.08)" : "var(--bg3)",
                          border: `1px solid ${warn ? "rgba(242,85,90,.2)" : "var(--border)"}`,
                          color: warn ? "#F2555A" : "var(--text-2)",
                        }}
                      >
                        {notice.text}
                      </div>
                    );
                  })()}
                  <div className="grid grid-cols-2 gap-x-4 gap-y-3 mb-5">
                    {[
                      { label: "Competitors", value: `Up to ${subscription.limits.max_competitors}` },
                      { label: "Auto-scan", value: scanCadenceLabel(subscription.limits.scan_hours) },
                      { label: "History", value: historyLabel(subscription.limits.history_days) },
                      { label: "AI digest", value: subscription.limits.ai_digest ? "Weekly" : "—" },
                    ].map(({ label, value }) => (
                      <div key={label}>
                        <p className="text-[11px]" style={{ color: "var(--muted)" }}>{label}</p>
                        <p className="text-sm font-semibold mt-0.5" style={{ color: "var(--text)" }}>{value}</p>
                      </div>
                    ))}
                  </div>
                  {subscription.tier === "free" ? (
                    <button
                      onClick={() => setUpgradeOpen(true)}
                      className="flex items-center gap-2 font-semibold text-sm px-4 py-2.5 rounded-md transition-all hover:brightness-110 w-full justify-center"
                      style={{ background: "var(--accent)", color: "var(--ink)" }}
                    >
                      <Zap className="w-4 h-4" />
                      Upgrade to Pro
                    </button>
                  ) : (
                    <button
                      onClick={handleManageBilling}
                      disabled={portalLoading}
                      className="font-semibold text-sm px-4 py-2.5 rounded-md transition-all hover:opacity-80 disabled:opacity-50 w-full"
                      style={{ background: "var(--bg3)", color: "var(--text)", border: "1px solid var(--border)" }}
                    >
                      {portalLoading ? "Loading…" : "Manage billing"}
                    </button>
                  )}
                </>
              ) : (
                <div className="space-y-2">
                  {[1, 2, 3].map((i) => <div key={i} className="h-4 rounded-lg animate-pulse" style={{ background: "var(--bg3)" }} />)}
                </div>
              )}
            </section>

            {/* Right: billing email + payment */}
            <section className={sectionClass} style={sectionStyle}>
              <div className="mb-5">
                <p className="text-xs font-bold uppercase tracking-wider mb-3" style={{ color: "var(--muted)" }}>
                  Billing email
                </p>
                <p
                  className="text-sm font-mono px-4 py-2.5 rounded-md"
                  style={{ background: "var(--bg3)", border: "1px solid var(--border)", color: "var(--text)" }}
                >
                  {userEmail || "—"}
                </p>
                <p className="text-xs mt-1.5" style={{ color: "var(--muted)" }}>
                  Receipts go to your account email.
                </p>
              </div>
              <div>
                <p className="text-xs font-bold uppercase tracking-wider mb-3" style={{ color: "var(--muted)" }}>
                  Payment method
                </p>
                <p className="text-sm mb-3" style={{ color: "var(--muted)" }}>
                  {subscription?.tier !== "free"
                    ? "Managed via Stripe billing portal."
                    : "No payment method on file."}
                </p>
                <button
                  onClick={handleManageBilling}
                  disabled={portalLoading}
                  className="text-sm font-semibold px-4 py-2 rounded-md transition-all hover:opacity-80 disabled:opacity-50"
                  style={{ background: "var(--bg3)", color: "var(--text)", border: "1px solid var(--border)" }}
                >
                  {portalLoading
                    ? "Loading…"
                    : subscription?.tier !== "free"
                    ? "Update payment"
                    : "Add card"}
                </button>
              </div>
            </section>
          </div>

          {/* Plan cards */}
          <div>
            <p className="text-xs font-bold uppercase tracking-wider mb-4" style={{ color: "var(--muted)" }}>
              Plans
            </p>
            <div className="grid grid-cols-1 sm:grid-cols-3 gap-4">
              {PLANS.map((plan) => {
                const isCurrent = tier === plan.tier;
                return (
                  <div
                    key={plan.tier}
                    className="rounded-md p-5 flex flex-col"
                    style={{
                      background: "var(--bg-card)",
                      border: isCurrent
                        ? "1px solid rgba(255,178,36,.45)"
                        : "1px solid var(--border)",
                    }}
                  >
                    <div className="flex items-center justify-between mb-1">
                      <span className="font-semibold" style={{ color: "var(--text)" }}>{plan.label}</span>
                      {isCurrent && (
                        <span
                          className="text-[10px] font-bold px-2 py-0.5 rounded-full"
                          style={{ background: "var(--bg3)", color: "var(--text-2)", border: "1px solid var(--border)" }}
                        >
                          Current
                        </span>
                      )}
                      {plan.popular && !isCurrent && (
                        <span
                          className="text-[10px] font-bold px-2 py-0.5 rounded-full"
                          style={{ background: "var(--bg3)", color: "var(--text-2)", border: "1px solid var(--border)" }}
                        >
                          Popular
                        </span>
                      )}
                    </div>
                    <p className="text-xl font-bold mt-2 mb-1" style={{ color: "var(--text)" }}>
                      {plan.price}
                      <span className="text-sm font-normal" style={{ color: "var(--muted)" }}>/mo</span>
                    </p>
                    <ul className="space-y-1.5 mb-5 mt-3 flex-1">
                      {plan.features.map((f) => (
                        <li key={f} className="flex items-center gap-2 text-sm">
                          <Check className="w-3.5 h-3.5 shrink-0" style={{ color: "var(--emerald)" }} />
                          <span style={{ color: "var(--muted)" }}>{f}</span>
                        </li>
                      ))}
                    </ul>
                    {isCurrent ? (
                      <button
                        disabled
                        className="w-full py-2 rounded-md text-sm font-medium"
                        style={{ background: "var(--bg3)", color: "var(--muted)" }}
                      >
                        Current Plan
                      </button>
                    ) : (
                      <button
                        onClick={() => setUpgradeOpen(true)}
                        className="w-full py-2 rounded-md text-sm font-semibold transition-all hover:brightness-110"
                        style={{
                          background: "rgba(255,178,36,.12)",
                          color: "#FFB224",
                          border: "1px solid rgba(255,178,36,.2)",
                        }}
                      >
                        Upgrade to {plan.label}
                      </button>
                    )}
                  </div>
                );
              })}
            </div>
          </div>
        </div>
      )}

      {/* ── Notifications tab ── */}
      {activeTab === "notifications" && prefs && (
        <section className={sectionClass} style={sectionStyle}>
          <div className="flex items-center justify-between mb-1">
            <div className="flex items-center gap-2">
              <Bell className="w-4 h-4" style={{ color: "var(--text-2)" }} />
              <h2 className="font-semibold" style={{ color: "var(--text)" }}>Email notifications</h2>
            </div>
            <span
              className="text-xs font-medium transition-opacity"
              style={{ color: "var(--emerald)", opacity: saved ? 1 : 0 }}
            >
              ✓ Saved
            </span>
          </div>
          <p className="text-sm mb-4" style={{ color: "var(--muted)" }}>
            Choose your cadence first, then which events matter. Changes save automatically.
          </p>

          {/* Cadence — the three-level notification system */}
          <div className="mb-5">
            <p className="text-xs font-semibold mb-2" style={{ color: "var(--text-2)" }}>How often should StoreScout email you?</p>
            <div className="grid sm:grid-cols-2 gap-2">
              {[
                { v: "critical_only" as const, label: "Critical only", desc: "Rare. Only major strategic events — flash sales, big price cuts." },
                { v: "daily" as const, label: "Daily Intelligence Brief", desc: "One email a day, ordered by impact — plus instant criticals. Recommended." },
                { v: "weekly" as const, label: "Weekly report only", desc: "The Monday market summary. Nothing in between." },
                { v: "quiet" as const, label: "Quiet", desc: "In-app only. No email at all." },
              ].map(({ v, label, desc }) => {
                const active = (prefs?.notification_level ?? "daily") === v;
                return (
                  <button
                    key={v}
                    onClick={() => savePrefs({ notification_level: v })}
                    className="text-left px-3 py-2.5 rounded-md transition-all"
                    style={{
                      background: active ? "var(--bg3)" : "transparent",
                      border: active ? "1px solid rgba(255,178,36,.35)" : "1px solid var(--border)",
                    }}
                  >
                    <p className="text-xs font-semibold" style={{ color: active ? "var(--text)" : "var(--text-2)" }}>{label}</p>
                    <p className="text-[11px] mt-0.5 leading-snug" style={{ color: "var(--muted)" }}>{desc}</p>
                  </button>
                );
              })}
            </div>
            {(prefs?.notification_level ?? "daily") === "daily" && (
              <div className="flex items-center gap-2 mt-2.5">
                <span className="text-xs" style={{ color: "var(--muted)" }}>Deliver the brief at</span>
                <select
                  value={String(prefs?.digest_hour ?? 8)}
                  onChange={(e) => savePrefs({ digest_hour: Number(e.target.value) })}
                  className="text-xs rounded px-2 py-1.5 outline-none"
                  style={{ background: "var(--bg3)", border: "1px solid var(--border)", color: "var(--text)" }}
                >
                  {Array.from({ length: 24 }, (_, h) => (
                    <option key={h} value={h}>{String(h).padStart(2, "0")}:00 UTC</option>
                  ))}
                </select>
              </div>
            )}
          </div>

          <div className="space-y-2">
            {[
              { key: "email_price_changes" as const, label: "Price changes", desc: "When a competitor changes prices by 10% or more" },
              { key: "email_new_products" as const, label: "New product launches", desc: "When a competitor publishes a new product" },
              { key: "email_discount_changes" as const, label: "Discount campaigns", desc: "When a sale starts or ends at a competitor" },
              { key: "email_weekly_digest" as const, label: "Weekly digest", desc: "Monday morning AI summary across all your competitors (Pro+)" },
            ].map(({ key, label, desc }) => (
              <button
                key={key}
                onClick={() => handleTogglePref(key)}
                disabled={saving}
                className="w-full flex items-center justify-between gap-4 px-4 py-3.5 rounded-md text-left transition-all"
                style={{
                  background: prefs[key] ? "rgba(76,195,138,.05)" : "var(--bg3)",
                  border: `1px solid ${prefs[key] ? "rgba(76,195,138,.2)" : "var(--border)"}`,
                }}
              >
                <div className="min-w-0">
                  <p className="text-sm font-medium" style={{ color: "var(--text)" }}>{label}</p>
                  <p className="text-xs mt-0.5" style={{ color: "var(--muted)" }}>{desc}</p>
                </div>
                <div
                  className="relative inline-flex h-6 w-11 shrink-0 items-center rounded-full transition-colors"
                  style={{ background: prefs[key] ? "#4CC38A" : "rgba(255,255,255,.12)" }}
                >
                  <span
                    className="pointer-events-none inline-block h-4 w-4 rounded-full bg-white shadow-lg transition-transform"
                    style={{ transform: prefs[key] ? "translateX(1.375rem)" : "translateX(0.25rem)" }}
                  />
                </div>
              </button>
            ))}
          </div>
        </section>
      )}

      {/* ── Integrations tab ── */}
      {activeTab === "integrations" && (
        <section className={sectionClass} style={sectionStyle}>
          <h2 className="font-semibold mb-1" style={{ color: "var(--text)" }}>Intelligence sources</h2>
          <p className="text-sm mb-5" style={{ color: "var(--muted)" }}>
            Every source teaches StoreScout more about your business — and every recommendation gets more personal.
          </p>

          <IntelligenceSources />

          {/* The ecosystem — intelligence map + value-story cards for every integration */}
          <div className="my-6 pt-6" style={{ borderTop: "1px solid var(--border)" }}>
            <IntegrationHub onConnect={(id) => {
              if ((id === "ga4" || id === "gsc") && googleEnabled) { handleGoogleConnect(); return; }
              // Klaviyo / Shopify / others: bring the real connect controls into view.
              try { document.getElementById("integration-controls")?.scrollIntoView({ behavior: "smooth" }); } catch { /* ignore */ }
            }} />
          </div>

          <div id="integration-controls" />

          {/* Google Analytics + Search Console — hidden until prod OAuth is verified */}
          {googleEnabled && (
          <div className="mb-6 pb-6" style={{ borderBottom: "1px solid var(--border)" }}>
            <div className="flex items-center gap-2 mb-2">
              <Globe className="w-4 h-4" style={{ color: "#4285f4" }} />
              <p className="text-sm font-semibold" style={{ color: "var(--text)" }}>Google Analytics + Search Console</p>
              {googleConnected && (
                <span className="text-[10px] font-bold px-2 py-0.5 rounded-full" style={{ background: "rgba(255,178,36,0.1)", color: "#FFB224" }}>
                  Connected
                </span>
              )}
            </div>
            <p className="text-xs mb-3" style={{ color: "var(--muted)" }}>
              Lets the AI know your traffic, top pages, and organic keyword rankings when generating plays.
            </p>

            {googleConnectedBanner && (
              <div className="flex items-center gap-2 px-4 py-3 rounded-md mb-3 text-sm font-medium" style={{ background: "rgba(76,195,138,0.08)", border: "1px solid rgba(76,195,138,0.2)", color: "var(--emerald)" }}>
                <Check className="w-4 h-4 shrink-0" /> Google account connected. Select your property below.
              </div>
            )}

            {googleConnected && googleProperties ? (
              <div className="space-y-3">
                {googleProperties.ga4_properties.length > 0 && (
                  <div>
                    <p className="text-xs font-medium mb-1.5" style={{ color: "var(--muted)" }}>GA4 property</p>
                    <select
                      value={googleGA4}
                      onChange={(e) => setGoogleGA4(e.target.value)}
                      className="w-full px-4 py-2.5 rounded-md text-sm outline-none"
                      style={inputStyle}
                    >
                      <option value="">— Select a property —</option>
                      {googleProperties.ga4_properties.map((p) => (
                        <option key={p.id} value={p.id}>{p.display_name} ({p.website_url || p.id})</option>
                      ))}
                    </select>
                  </div>
                )}
                {googleProperties.gsc_sites.length > 0 && (
                  <div>
                    <p className="text-xs font-medium mb-1.5" style={{ color: "var(--muted)" }}>Search Console site</p>
                    <select
                      value={googleGSC}
                      onChange={(e) => setGoogleGSC(e.target.value)}
                      className="w-full px-4 py-2.5 rounded-md text-sm outline-none"
                      style={inputStyle}
                    >
                      <option value="">— Select a site —</option>
                      {googleProperties.gsc_sites.map((s) => (
                        <option key={s.url} value={s.url}>{s.url}</option>
                      ))}
                    </select>
                  </div>
                )}
                <div className="flex items-center gap-2">
                  <button
                    onClick={handleGoogleSaveProperty}
                    disabled={googleSavingProperty || (!googleGA4 && !googleGSC)}
                    className="text-sm font-semibold px-4 py-2 rounded-md transition-all hover:brightness-110 disabled:opacity-50"
                    style={{ background: "#FFB224", color: "var(--ink)" }}
                  >
                    {googleSavingProperty ? "Saving…" : "Save"}
                  </button>
                  <button
                    onClick={handleGoogleDisconnect}
                    className="text-sm font-medium px-4 py-2 rounded-md transition-all hover:opacity-70"
                    style={{ color: "#F2555A" }}
                  >
                    Disconnect
                  </button>
                </div>
              </div>
            ) : (
              <button
                onClick={handleGoogleConnect}
                disabled={googleConnecting}
                className="flex items-center gap-2 font-semibold text-sm px-5 py-2.5 rounded-md transition-all hover:brightness-110 disabled:opacity-60"
                style={{ background: "var(--bg3)", color: "var(--text)", border: "1px solid var(--border)" }}
              >
                {googleConnecting ? <Loader2 className="w-4 h-4 animate-spin" /> : <Globe className="w-4 h-4" style={{ color: "#4285f4" }} />}
                {googleConnecting ? "Connecting…" : "Connect Google"}
              </button>
            )}
          </div>
          )}

          {/* Klaviyo */}
          <div className="mb-6 pb-6" style={{ borderBottom: "1px solid var(--border)" }}>
            <div className="flex items-center gap-2 mb-2">
              <Zap className="w-4 h-4" style={{ color: "var(--text-2)" }} />
              <p className="text-sm font-semibold" style={{ color: "var(--text)" }}>Klaviyo</p>
              {klaviyoStatus?.connected && (
                <span className="text-[10px] font-bold px-2 py-0.5 rounded-full" style={{ background: "rgba(255,178,36,0.1)", color: "#FFB224" }}>
                  Connected
                </span>
              )}
            </div>
            <p className="text-xs mb-3" style={{ color: "var(--muted)" }}>
              Connect your Klaviyo account so the AI knows your email list size when generating plays.
              Use a <strong style={{ color: "var(--text-2, var(--muted))" }}>Private API key</strong> from Klaviyo → Account → API Keys.
            </p>

            {klaviyoStatus?.connected ? (
              <div
                className="flex items-center justify-between gap-4 px-4 py-3 rounded-md"
                style={{ background: "var(--bg3)", border: "1px solid var(--border)" }}
              >
                <div>
                  <p className="text-xs font-mono font-medium" style={{ color: "var(--text)" }}>
                    {klaviyoStatus.key_preview}
                  </p>
                  {klaviyoTestResult && (
                    <p className="text-xs mt-0.5" style={{ color: "var(--text-2)" }}>
                      {klaviyoTestResult.total_profiles.toLocaleString()} subscribers
                      {" · "}{klaviyoTestResult.list_count} list{klaviyoTestResult.list_count !== 1 ? "s" : ""}
                    </p>
                  )}
                </div>
                <div className="flex items-center gap-2 shrink-0">
                  <button
                    onClick={handleTestKlaviyo}
                    disabled={klaviyoTesting}
                    className="text-xs font-medium px-3 py-1.5 rounded-lg transition-all hover:bg-white/[0.06] disabled:opacity-40"
                    style={{ color: "var(--muted)", border: "1px solid var(--border)" }}
                  >
                    {klaviyoTesting ? "Testing…" : "Test"}
                  </button>
                  <button
                    onClick={handleRemoveKlaviyo}
                    className="text-xs font-medium px-3 py-1.5 rounded-lg transition-all hover:opacity-70"
                    style={{ color: "#F2555A" }}
                  >
                    Remove
                  </button>
                </div>
              </div>
            ) : (
              <div className="flex gap-2">
                <input
                  value={klaviyoKey}
                  onChange={(e) => setKlaviyoKey(e.target.value)}
                  onKeyDown={(e) => e.key === "Enter" && handleSaveKlaviyo()}
                  placeholder="pk_••••••••••••••••••••••••••••••••"
                  className={inputClass}
                  style={inputStyle}
                />
                <button
                  onClick={handleSaveKlaviyo}
                  disabled={klaviyoSaving || !klaviyoKey.trim()}
                  className="font-semibold text-sm px-4 py-2.5 rounded-md transition-all hover:brightness-110 disabled:opacity-50"
                  style={{ background: "var(--bg3)", color: "var(--text)", border: "1px solid var(--border)" }}
                >
                  {klaviyoSaving ? "Saving…" : "Save"}
                </button>
              </div>
            )}
            {klaviyoError && <p className="text-xs mt-2" style={{ color: "#F2555A" }}>{klaviyoError}</p>}
          </div>

          {/* Slack */}
          <div className="mb-6">
            <div className="flex items-center gap-2 mb-2">
              <Hash className="w-4 h-4" style={{ color: "var(--text-2)" }} />
              <p className="text-sm font-semibold" style={{ color: "var(--text)" }}>Slack incoming webhook</p>
              {prefs && (
                <button
                  onClick={() => {
                    const next = !prefs.slack_enabled;
                    setPrefs({ ...prefs, slack_enabled: next });
                    userApi.updatePrefs({ slack_enabled: next }).catch(() => {});
                  }}
                  className="ml-auto relative inline-flex h-6 w-11 shrink-0 items-center rounded-full transition-colors"
                  style={{ background: prefs.slack_enabled ? "#4CC38A" : "rgba(255,255,255,.12)" }}
                >
                  <span
                    className="pointer-events-none inline-block h-4 w-4 rounded-full bg-white shadow-lg transition-transform"
                    style={{ transform: prefs.slack_enabled ? "translateX(1.375rem)" : "translateX(0.25rem)" }}
                  />
                </button>
              )}
            </div>
            <p className="text-xs mb-3" style={{ color: "var(--muted)" }}>
              Create an incoming webhook in your Slack workspace and paste the URL below.
            </p>
            <div className="flex gap-2">
              <input
                value={slackUrl}
                onChange={(e) => setSlackUrl(e.target.value)}
                onBlur={handleSaveSlack}
                placeholder="https://hooks.slack.com/services/..."
                className={inputClass}
                style={{ ...inputStyle, fontFamily: "monospace" }}
              />
              <button
                onClick={handleTestSlack}
                disabled={testingSlack || !slackUrl}
                className="font-semibold text-sm px-4 py-2.5 rounded-md transition-all hover:opacity-80 disabled:opacity-40 shrink-0"
                style={{ background: "var(--bg3)", color: "var(--text)", border: "1px solid var(--border)" }}
              >
                {testingSlack ? "Sending…" : "Test"}
              </button>
            </div>
            {slackTestResult && (
              <p className="text-xs mt-2" style={{ color: slackTestResult === "ok" ? "var(--emerald)" : "#F2555A" }}>
                {slackTestResult === "ok" ? "✓ Test message sent to Slack" : "✗ Failed — check the webhook URL"}
              </p>
            )}
          </div>

          {/* Generic webhook */}
          <div>
            <div className="flex items-center gap-2 mb-2">
              <Globe className="w-4 h-4" style={{ color: "var(--text-2)" }} />
              <p className="text-sm font-semibold" style={{ color: "var(--text)" }}>Webhook (Zapier, Make, custom)</p>
              {prefs && (
                <button
                  onClick={() => {
                    const next = !prefs.webhook_enabled;
                    setPrefs({ ...prefs, webhook_enabled: next });
                    userApi.updatePrefs({ webhook_enabled: next }).catch(() => {});
                  }}
                  className="ml-auto relative inline-flex h-6 w-11 shrink-0 items-center rounded-full transition-colors"
                  style={{ background: prefs.webhook_enabled ? "#4CC38A" : "rgba(255,255,255,.12)" }}
                >
                  <span
                    className="pointer-events-none inline-block h-4 w-4 rounded-full bg-white shadow-lg transition-transform"
                    style={{ transform: prefs.webhook_enabled ? "translateX(1.375rem)" : "translateX(0.25rem)" }}
                  />
                </button>
              )}
            </div>
            <p className="text-xs mb-3" style={{ color: "var(--muted)" }}>
              POST JSON to any URL when a change alert fires. Works with Zapier, Make, Notion, or any custom endpoint.
            </p>
            <div className="flex gap-2">
              <input
                value={webhookUrl}
                onChange={(e) => setWebhookUrl(e.target.value)}
                onBlur={handleSaveWebhook}
                placeholder="https://hooks.zapier.com/hooks/catch/..."
                className={inputClass}
                style={{ ...inputStyle, fontFamily: "monospace" }}
              />
              <button
                onClick={handleTestWebhook}
                disabled={testingWebhook || !webhookUrl}
                className="font-semibold text-sm px-4 py-2.5 rounded-md transition-all hover:opacity-80 disabled:opacity-40 shrink-0"
                style={{ background: "var(--bg3)", color: "var(--text)", border: "1px solid var(--border)" }}
              >
                {testingWebhook ? "Sending…" : "Test"}
              </button>
            </div>
            {webhookTestResult && (
              <p className="text-xs mt-2" style={{ color: webhookTestResult === "ok" ? "var(--emerald)" : "#F2555A" }}>
                {webhookTestResult === "ok" ? "✓ Test payload delivered" : "✗ Failed — check the URL and try again"}
              </p>
            )}
          </div>
        </section>
      )}

      {/* ── Team tab (agency) ── */}
      {activeTab === "team" && (
        <section className={sectionClass} style={sectionStyle}>
          <div className="flex items-center justify-between mb-2">
            <div className="flex items-center gap-2">
              <Users className="w-4 h-4" style={{ color: "var(--text-2)" }} />
              <h2 className="font-semibold" style={{ color: "var(--text)" }}>Team seats</h2>
            </div>
            <span className="text-xs font-mono" style={{ color: "var(--muted)" }}>
              {teamMembers.length} / 2 used
            </span>
          </div>
          <p className="text-sm mb-5" style={{ color: "var(--muted)" }}>
            Invite up to 2 team members. They can view all data but cannot delete competitors or manage billing.
          </p>

          {teamMembers.length > 0 && (
            <div className="space-y-2 mb-5">
              {teamMembers.map((m) => (
                <div
                  key={m.id}
                  className="flex items-center justify-between gap-3 rounded-md px-4 py-3"
                  style={{ background: "var(--bg3)", border: "1px solid var(--border)" }}
                >
                  <div>
                    <p className="text-sm font-medium" style={{ color: "var(--text)" }}>{m.invited_email}</p>
                    <p
                      className="text-xs mt-0.5 capitalize"
                      style={{ color: m.status === "active" ? "var(--emerald)" : "var(--muted)" }}
                    >
                      {m.status === "active" ? "Active" : "Invite pending"}
                    </p>
                  </div>
                  <button
                    onClick={() => handleRemoveMember(m.id)}
                    className="p-1.5 rounded-lg transition-colors hover:bg-red-500/10"
                    style={{ color: "#F2555A" }}
                  >
                    <X className="w-4 h-4" />
                  </button>
                </div>
              ))}
            </div>
          )}

          {teamMembers.length < 2 && (
            <div>
              <div className="flex gap-2">
                <input
                  value={inviteEmail}
                  onChange={(e) => setInviteEmail(e.target.value)}
                  onKeyDown={(e) => e.key === "Enter" && handleInvite()}
                  placeholder="teammate@company.com"
                  type="email"
                  className={inputClass}
                  style={inputStyle}
                />
                <button
                  onClick={handleInvite}
                  disabled={inviting || !inviteEmail.trim()}
                  className="font-semibold text-sm px-5 py-2.5 rounded-md transition-all hover:brightness-110 disabled:opacity-50 flex items-center gap-2 shrink-0"
                  style={{ background: "#FFB224", color: "#0B0C0A" }}
                >
                  {inviting ? <Loader2 className="w-4 h-4 animate-spin" /> : null}
                  {inviting ? "Sending…" : "Invite"}
                </button>
              </div>
              {inviteError && <p className="text-xs mt-2" style={{ color: "#F2555A" }}>{inviteError}</p>}
              {inviteSent && <p className="text-xs mt-2" style={{ color: "var(--emerald)" }}>✓ Invite sent</p>}
            </div>
          )}
        </section>
      )}

      {/* ── API tab (developer) ── */}
      {activeTab === "api" && (
        <section className={sectionClass} style={sectionStyle}>
          <div className="flex items-center justify-between mb-2">
            <div className="flex items-center gap-2">
              <Key className="w-4 h-4" style={{ color: "#7DB8C9" }} />
              <h2 className="font-semibold" style={{ color: "var(--text)" }}>API keys</h2>
            </div>
            <a
              href="/api-docs"
              className="flex items-center gap-1 text-xs font-medium hover:underline"
              style={{ color: "#7DB8C9" }}
            >
              <Terminal className="w-3 h-3" />
              API reference →
            </a>
          </div>
          <p className="text-sm mb-5" style={{ color: "var(--muted)" }}>
            Access StoreScout data programmatically. Keys begin with{" "}
            <code className="text-xs font-mono px-1 py-0.5 rounded" style={{ background: "var(--bg3)" }}>sk_live_</code>.
            Copy your key immediately — it will not be shown again.
          </p>

          {keys.length > 0 && (
            <div className="space-y-2 mb-5">
              {keys.map((k) => (
                <div
                  key={k.id}
                  className="flex items-center justify-between gap-3 rounded-md px-4 py-3"
                  style={{ background: "var(--bg3)", border: "1px solid var(--border)" }}
                >
                  <div className="min-w-0">
                    <p className="text-sm font-medium truncate" style={{ color: "var(--text)" }}>{k.name}</p>
                    <p className="text-xs font-mono mt-0.5" style={{ color: "var(--muted)" }}>
                      {k.key_prefix}••••••••
                      {k.last_used_at
                        ? ` · Last used ${new Date(k.last_used_at).toLocaleDateString()}`
                        : " · Never used"}
                    </p>
                  </div>
                  <button
                    onClick={() => handleRevokeKey(k.id)}
                    className="shrink-0 p-1.5 rounded-lg transition-colors hover:bg-red-500/10"
                    style={{ color: "#F2555A" }}
                    title="Revoke key"
                  >
                    <X className="w-4 h-4" />
                  </button>
                </div>
              ))}
            </div>
          )}

          {newKeyPlaintext && (
            <div
              className="mb-5 rounded-md p-4"
              style={{ background: "rgba(168,85,247,.08)", border: "1px solid rgba(168,85,247,.25)" }}
            >
              <p className="text-xs font-semibold mb-2" style={{ color: "#7DB8C9" }}>
                Your new API key — copy it now, it won&apos;t be shown again
              </p>
              <div className="flex items-center gap-2">
                <code
                  className="flex-1 text-xs font-mono px-3 py-2 rounded-lg overflow-x-auto"
                  style={{ background: "var(--bg3)", color: "var(--text)", display: "block" }}
                >
                  {newKeyPlaintext}
                </code>
                <button
                  onClick={handleCopyKey}
                  className="shrink-0 flex items-center gap-1.5 text-xs font-semibold px-3 py-2 rounded-lg transition-all"
                  style={{
                    background: copiedKey ? "rgba(76,195,138,.15)" : "var(--bg3)",
                    color: copiedKey ? "var(--emerald)" : "var(--muted)",
                    border: "1px solid var(--border)",
                  }}
                >
                  {copiedKey ? <Check className="w-3.5 h-3.5" /> : <Copy className="w-3.5 h-3.5" />}
                  {copiedKey ? "Copied" : "Copy"}
                </button>
              </div>
            </div>
          )}

          {keys.length < 5 ? (
            <div className="flex gap-2">
              <input
                value={newKeyName}
                onChange={(e) => setNewKeyName(e.target.value)}
                onKeyDown={(e) => e.key === "Enter" && handleCreateKey()}
                placeholder="Key name (e.g. Zapier integration)"
                className={inputClass}
                style={inputStyle}
              />
              <button
                onClick={handleCreateKey}
                disabled={creatingKey}
                className="font-semibold text-sm px-5 py-2.5 rounded-md transition-all hover:brightness-110 disabled:opacity-50 flex items-center gap-2 shrink-0"
                style={{ background: "#7DB8C9", color: "#0B0C0A" }}
              >
                {creatingKey ? <Loader2 className="w-4 h-4 animate-spin" /> : <Key className="w-4 h-4" />}
                Generate key
              </button>
            </div>
          ) : (
            <p className="text-xs" style={{ color: "var(--muted)" }}>
              Maximum of 5 active keys reached. Revoke one to create a new key.
            </p>
          )}
        </section>
      )}

      <UpgradeModal open={upgradeOpen} onClose={() => setUpgradeOpen(false)} trigger="general" currentTier={subscription?.tier} />
    </div>
  );
}

export default function SettingsPage() {
  return (
    <Suspense fallback={<div style={{ color: "var(--muted)" }} className="p-6">Loading…</div>}>
      <SettingsContent />
    </Suspense>
  );
}
