"use client";

import { Suspense, useEffect, useState } from "react";
import { useSearchParams } from "next/navigation";
import {
  user as userApi, billing, myStore as myStoreApi, team as teamApi,
  apiKeys as apiKeysApi, competitors as competitorsApi,
  type UserSubscription, type NotificationPrefs, type Competitor,
  type TeamMember, type ApiKey,
} from "@/lib/api";
import { cn } from "@/lib/utils";
import UpgradeModal from "@/components/UpgradeModal";
import { AddCompetitorModal } from "@/components/competitors/AddCompetitorModal";
import { createClient } from "@/lib/supabase/client";
import {
  Store, Hash, Globe, Users, X, Loader2, Key, Copy, Check, Terminal,
  Plus, RefreshCw, Target, User, Zap,
} from "lucide-react";

function SettingsContent() {
  const supabase = createClient();
  const searchParams = useSearchParams();

  // Plan + prefs
  const [subscription, setSubscription] = useState<UserSubscription | null>(null);
  const [prefs, setPrefs] = useState<NotificationPrefs | null>(null);
  const [saving, setSaving] = useState(false);
  const [saved, setSaved] = useState(false);
  const [upgradeOpen, setUpgradeOpen] = useState(false);
  const [portalLoading, setPortalLoading] = useState(false);

  // Competitors
  const [myCompetitors, setMyCompetitors] = useState<Competitor[]>([]);
  const [rescanning, setRescanning] = useState<Set<string>>(new Set());
  const [addCompetitorOpen, setAddCompetitorOpen] = useState(false);

  // Your store
  const [store, setStore] = useState<Competitor | null>(null);
  const [storeUrl, setStoreUrl] = useState("");
  const [storeSaving, setStoreSaving] = useState(false);
  const [storeError, setStoreError] = useState("");

  // Integrations
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
    // Open upgrade modal if sidebar or onboarding sent ?upgrade=1
    if (searchParams.get("upgrade") === "1") {
      setUpgradeOpen(true);
    }

    userApi.subscription().then((r) => {
      setSubscription(r.data);
      if (["pro", "agency", "developer"].includes(r.data.tier)) {
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

    competitorsApi.list().then((r) => setMyCompetitors(r.data || [])).catch(() => {});
    myStoreApi.get().then((r) => setStore(r.data)).catch(() => {});

    supabase.auth.getUser().then(({ data }) => {
      if (data.user?.email) setUserEmail(data.user.email);
    });

    // Poll for tier update after Stripe redirect (webhook may take a few seconds)
    if (searchParams.get("upgraded") === "1") {
      let attempts = 0;
      const poll = () => {
        attempts++;
        userApi.subscription()
          .then((r) => {
            setSubscription(r.data);
            const isPaid = ["pro", "agency", "developer"].includes(r.data.tier ?? "");
            if (!isPaid && attempts < 6) setTimeout(poll, 2000);
          })
          .catch(() => { if (attempts < 6) setTimeout(poll, 2000); });
      };
      setTimeout(poll, 1500);
    }
  }, [searchParams, supabase]);

  // ── Prefs ──────────────────────────────────────────────────────────────────
  async function handleSavePrefs() {
    if (!prefs) return;
    setSaving(true);
    await userApi.updatePrefs(prefs).catch(() => {});
    setSaving(false);
    setSaved(true);
    setTimeout(() => setSaved(false), 2000);
  }

  function toggle(key: keyof NotificationPrefs) {
    if (!prefs) return;
    setPrefs({ ...prefs, [key]: !prefs[key] });
  }

  // ── Billing ────────────────────────────────────────────────────────────────
  async function handleManageBilling() {
    setPortalLoading(true);
    try {
      const { url } = await billing.portal();
      window.location.href = url;
    } catch {
      setPortalLoading(false);
    }
  }

  // ── Competitors ────────────────────────────────────────────────────────────
  async function handleRescanCompetitor(id: string) {
    setRescanning((prev) => new Set(prev).add(id));
    try {
      await competitorsApi.rescan(id);
      // Refresh list after a moment to pick up the new status
      setTimeout(async () => {
        const { data } = await competitorsApi.list();
        setMyCompetitors(data || []);
        setRescanning((prev) => { const s = new Set(prev); s.delete(id); return s; });
      }, 2000);
    } catch {
      setRescanning((prev) => { const s = new Set(prev); s.delete(id); return s; });
    }
  }

  async function handleRemoveCompetitor(id: string) {
    if (!confirm("Remove this competitor? All scan history will be deleted.")) return;
    await competitorsApi.remove(id).catch(() => {});
    setMyCompetitors((prev) => prev.filter((c) => c.id !== id));
  }

  // ── Your store ─────────────────────────────────────────────────────────────
  async function handleSaveStore() {
    if (!storeUrl.trim()) return;
    setStoreSaving(true);
    setStoreError("");
    try {
      const { data } = await myStoreApi.set(storeUrl.trim());
      setStore(data);
      setStoreUrl("");
    } catch {
      setStoreError("Could not add that store. Check the URL and try again.");
    }
    setStoreSaving(false);
  }

  async function handleRemoveStore() {
    await myStoreApi.remove().catch(() => {});
    setStore(null);
  }

  // ── Integrations ───────────────────────────────────────────────────────────
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

  // ── Team ───────────────────────────────────────────────────────────────────
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

  // ── API keys ───────────────────────────────────────────────────────────────
  async function handleCreateKey() {
    setCreatingKey(true);
    setNewKeyPlaintext("");
    try {
      const { data } = await apiKeysApi.create(newKeyName.trim() || "API key");
      setNewKeyPlaintext(data.key);
      setNewKeyName("");
      const kr = await apiKeysApi.list();
      setKeys(kr.data);
    } catch {
      // key creation failure is rare
    } finally {
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

  // ── Account ────────────────────────────────────────────────────────────────
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
    // Call delete endpoint if it exists, then sign out
    await supabase.auth.signOut().catch(() => {});
    window.location.href = "/";
  }

  // ── UI helpers ─────────────────────────────────────────────────────────────
  const tierBadgeStyle: Record<string, { bg: string; color: string }> = {
    free:      { bg: "rgba(255,255,255,.06)",   color: "var(--muted)" },
    pro:       { bg: "rgba(163,240,0,.12)",      color: "#a3f000" },
    agency:    { bg: "rgba(59,130,246,.12)",     color: "#60a5fa" },
    developer: { bg: "rgba(168,85,247,.12)",     color: "#c084fc" },
  };

  const isPaidTier = ["pro", "agency", "developer"].includes(subscription?.tier ?? "");
  const atCompetitorLimit = subscription
    ? myCompetitors.length >= subscription.limits.max_competitors
    : false;
  const upgraded = searchParams.get("upgraded") === "1";

  function formatLastScanned(c: Competitor) {
    if (c.scan_status === "scanning") return "Scanning now…";
    if (c.scan_status === "error") return "Scan failed";
    if (c.last_scanned_at) {
      return `Last scanned ${new Date(c.last_scanned_at).toLocaleDateString("en-US", { month: "short", day: "numeric" })}`;
    }
    return "Pending first scan";
  }

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

        {/* ── Plan ── */}
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
                    <span className="text-sm capitalize" style={{ color: "var(--muted)" }}>
                      {subscription.subscription_status}
                    </span>
                  )}
                </div>
                <p className="text-sm" style={{ color: "var(--muted)" }}>
                  {subscription.limits.max_competitors} competitor{subscription.limits.max_competitors !== 1 ? "s" : ""} ·{" "}
                  {subscription.tier === "free"
                    ? "Manual rescan (weekly)"
                    : `Auto-scan every ${subscription.limits.scan_hours}h`} ·{" "}
                  {subscription.limits.history_days === 0
                    ? "No history"
                    : `${subscription.limits.history_days}d history`}
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

        {/* ── Tracked competitors ── */}
        <section
          className="rounded-2xl p-6"
          style={{ background: "var(--bg-card)", border: "1px solid var(--border)" }}
        >
          <div className="flex items-center justify-between mb-2">
            <div className="flex items-center gap-2">
              <Target className="w-4 h-4" style={{ color: "#a3f000" }} />
              <h2 className="font-semibold" style={{ color: "var(--text)" }}>Tracked competitors</h2>
            </div>
            {subscription && (
              <span
                className="text-xs font-mono px-2 py-1 rounded-lg"
                style={{
                  background: atCompetitorLimit ? "rgba(163,240,0,.1)" : "var(--bg3)",
                  color: atCompetitorLimit ? "#a3f000" : "var(--muted)",
                  border: `1px solid ${atCompetitorLimit ? "rgba(163,240,0,.25)" : "var(--border)"}`,
                }}
              >
                {myCompetitors.length} / {subscription.limits.max_competitors}
              </span>
            )}
          </div>
          <p className="text-sm mb-5" style={{ color: "var(--muted)" }}>
            Remove competitors you no longer need to free up tracking slots.
          </p>

          {myCompetitors.length === 0 ? (
            <p className="text-sm mb-4" style={{ color: "var(--muted)" }}>
              No competitors tracked yet. Add one to get started.
            </p>
          ) : (
            <div className="space-y-2 mb-4">
              {myCompetitors.map((c) => (
                <div
                  key={c.id}
                  className="flex items-center justify-between gap-3 rounded-xl px-4 py-3"
                  style={{ background: "var(--bg3)", border: "1px solid var(--border)" }}
                >
                  <div className="min-w-0">
                    <p className="text-sm font-medium truncate" style={{ color: "var(--text)" }}>
                      {c.display_name || c.hostname}
                    </p>
                    <p className="text-xs mt-0.5" style={{ color: "var(--muted)" }}>
                      {c.product_count != null ? `${c.product_count} products · ` : ""}
                      {formatLastScanned(c)}
                    </p>
                  </div>
                  <div className="flex items-center gap-2 shrink-0">
                    <button
                      onClick={() => handleRescanCompetitor(c.id)}
                      disabled={rescanning.has(c.id) || c.scan_status === "scanning"}
                      title="Trigger manual rescan"
                      className="p-1.5 rounded-lg transition-colors hover:bg-white/5 disabled:opacity-40"
                      style={{ color: "var(--muted)" }}
                    >
                      <RefreshCw className={cn("w-4 h-4", rescanning.has(c.id) && "animate-spin")} />
                    </button>
                    <button
                      onClick={() => handleRemoveCompetitor(c.id)}
                      title="Remove competitor"
                      className="p-1.5 rounded-lg transition-colors hover:bg-red-500/10"
                      style={{ color: "#f87171" }}
                    >
                      <X className="w-4 h-4" />
                    </button>
                  </div>
                </div>
              ))}
            </div>
          )}

          {atCompetitorLimit ? (
            <button
              onClick={() => setUpgradeOpen(true)}
              className="flex items-center gap-2 text-sm font-semibold px-4 py-2.5 rounded-xl transition-all hover:brightness-110"
              style={{ background: "rgba(163,240,0,.1)", color: "#a3f000", border: "1px solid rgba(163,240,0,.2)" }}
            >
              <Zap className="w-4 h-4" />
              Upgrade to track more competitors
            </button>
          ) : (
            <button
              onClick={() => setAddCompetitorOpen(true)}
              className="flex items-center gap-2 text-sm font-semibold px-4 py-2.5 rounded-xl transition-all hover:opacity-80"
              style={{ background: "var(--bg3)", color: "var(--text)", border: "1px solid var(--border)" }}
            >
              <Plus className="w-4 h-4" />
              Add competitor
            </button>
          )}
        </section>

        {/* ── Your store ── */}
        <section
          className="rounded-2xl p-6"
          style={{ background: "var(--bg-card)", border: "1px solid var(--border)" }}
        >
          <div className="flex items-center gap-2 mb-2">
            <Store className="w-4 h-4" style={{ color: "#a3f000" }} />
            <h2 className="font-semibold" style={{ color: "var(--text)" }}>Your store</h2>
          </div>
          <p className="text-sm mb-4" style={{ color: "var(--muted)" }}>
            Connect your Shopify store to unlock head-to-head comparisons on every competitor.
            Doesn&apos;t count against your tracking limit.
          </p>

          {store ? (
            <div className="flex items-center justify-between gap-4 flex-wrap">
              <div>
                <p className="text-sm font-medium" style={{ color: "var(--text)" }}>{store.hostname}</p>
                <p className="text-xs mt-0.5" style={{ color: "var(--muted)" }}>
                  {store.product_count != null ? `${store.product_count} products · ` : ""}
                  {store.scan_status === "done" ? "Connected" : store.scan_status === "error" ? "Scan failed" : "Scanning…"}
                </p>
              </div>
              <button
                onClick={handleRemoveStore}
                className="font-semibold text-sm px-4 py-2 rounded-xl transition-all hover:opacity-80"
                style={{ background: "var(--bg3)", color: "#f87171", border: "1px solid var(--border)" }}
              >
                Disconnect
              </button>
            </div>
          ) : (
            <div className="flex gap-2">
              <input
                value={storeUrl}
                onChange={(e) => setStoreUrl(e.target.value)}
                onKeyDown={(e) => e.key === "Enter" && handleSaveStore()}
                placeholder="yourstore.com"
                className="flex-1 px-4 py-2.5 rounded-xl text-sm outline-none"
                style={{ background: "var(--bg3)", border: "1px solid var(--border)", color: "var(--text)" }}
              />
              <button
                onClick={handleSaveStore}
                disabled={storeSaving}
                className="font-semibold text-sm px-5 py-2.5 rounded-xl transition-all hover:brightness-110 disabled:opacity-60"
                style={{ background: "#a3f000", color: "#060d18" }}
              >
                {storeSaving ? "Adding…" : "Connect"}
              </button>
            </div>
          )}
          {storeError && <p className="text-xs mt-3" style={{ color: "#f87171" }}>{storeError}</p>}
        </section>

        {/* ── Email notifications ── */}
        {prefs && (
          <section
            className="rounded-2xl p-6"
            style={{ background: "var(--bg-card)", border: "1px solid var(--border)" }}
          >
            <h2 className="font-semibold mb-4" style={{ color: "var(--text)" }}>Email notifications</h2>
            <div className="space-y-3">
              {[
                { key: "email_price_changes" as const,   label: "Price changes",        desc: "Alert when a product price changes ≥10%" },
                { key: "email_new_products" as const,    label: "New product launches", desc: "Alert when a new product is published" },
                { key: "email_discount_changes" as const,label: "Discount campaigns",   desc: "Alert when a sale starts or ends" },
                { key: "email_weekly_digest" as const,   label: "Weekly digest",        desc: "Monday morning summary with AI insights (Pro+)" },
              ].map(({ key, label, desc }) => (
                <div key={key} className="flex items-start justify-between gap-4 py-3 border-b last:border-0" style={{ borderColor: "var(--border)" }}>
                  <div>
                    <p className="text-sm font-medium" style={{ color: "var(--text)" }}>{label}</p>
                    <p className="text-xs mt-0.5" style={{ color: "var(--muted)" }}>{desc}</p>
                  </div>
                  <button
                    onClick={() => toggle(key)}
                    className="relative inline-flex h-6 w-11 shrink-0 items-center rounded-full transition-colors focus:outline-none"
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

        {/* ── Integrations ── */}
        <section
          className="rounded-2xl p-6"
          style={{ background: "var(--bg-card)", border: "1px solid var(--border)" }}
        >
          <h2 className="font-semibold mb-1" style={{ color: "var(--text)" }}>Integrations</h2>
          <p className="text-sm mb-5" style={{ color: "var(--muted)" }}>
            Receive alerts in Slack or any tool that accepts a webhook. Pro and Agency plans only.
          </p>

          {/* Slack */}
          <div className="mb-6">
            <div className="flex items-center gap-2 mb-2">
              <Hash className="w-4 h-4" style={{ color: "#a3f000" }} />
              <p className="text-sm font-semibold" style={{ color: "var(--text)" }}>Slack incoming webhook</p>
              {prefs && (
                <button
                  onClick={() => {
                    const next = !prefs.slack_enabled;
                    setPrefs({ ...prefs, slack_enabled: next });
                    userApi.updatePrefs({ slack_enabled: next }).catch(() => {});
                  }}
                  className="ml-auto relative inline-flex h-6 w-11 shrink-0 items-center rounded-full transition-colors"
                  style={{ background: prefs.slack_enabled ? "#a3f000" : "rgba(255,255,255,.12)" }}
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
              Alerts appear as rich messages in your chosen channel.
            </p>
            <div className="flex gap-2">
              <input
                value={slackUrl}
                onChange={(e) => setSlackUrl(e.target.value)}
                onBlur={handleSaveSlack}
                placeholder="https://hooks.slack.com/services/..."
                className="flex-1 px-4 py-2.5 rounded-xl text-sm font-mono outline-none"
                style={{ background: "var(--bg3)", border: "1px solid var(--border)", color: "var(--text)" }}
              />
              <button
                onClick={handleTestSlack}
                disabled={testingSlack || !slackUrl}
                className="font-semibold text-sm px-4 py-2.5 rounded-xl transition-all hover:opacity-80 disabled:opacity-40 shrink-0"
                style={{ background: "var(--bg3)", color: "var(--text)", border: "1px solid var(--border)" }}
              >
                {testingSlack ? "Sending…" : "Test"}
              </button>
            </div>
            {slackTestResult && (
              <p className="text-xs mt-2" style={{ color: slackTestResult === "ok" ? "#4ade80" : "#f87171" }}>
                {slackTestResult === "ok" ? "✓ Test message sent to Slack" : "✗ Failed — check the webhook URL"}
              </p>
            )}
          </div>

          {/* Generic webhook */}
          <div>
            <div className="flex items-center gap-2 mb-2">
              <Globe className="w-4 h-4" style={{ color: "#60a5fa" }} />
              <p className="text-sm font-semibold" style={{ color: "var(--text)" }}>Webhook (Zapier, Make, custom)</p>
              {prefs && (
                <button
                  onClick={() => {
                    const next = !prefs.webhook_enabled;
                    setPrefs({ ...prefs, webhook_enabled: next });
                    userApi.updatePrefs({ webhook_enabled: next }).catch(() => {});
                  }}
                  className="ml-auto relative inline-flex h-6 w-11 shrink-0 items-center rounded-full transition-colors"
                  style={{ background: prefs.webhook_enabled ? "#a3f000" : "rgba(255,255,255,.12)" }}
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
                className="flex-1 px-4 py-2.5 rounded-xl text-sm font-mono outline-none"
                style={{ background: "var(--bg3)", border: "1px solid var(--border)", color: "var(--text)" }}
              />
              <button
                onClick={handleTestWebhook}
                disabled={testingWebhook || !webhookUrl}
                className="font-semibold text-sm px-4 py-2.5 rounded-xl transition-all hover:opacity-80 disabled:opacity-40 shrink-0"
                style={{ background: "var(--bg3)", color: "var(--text)", border: "1px solid var(--border)" }}
              >
                {testingWebhook ? "Sending…" : "Test"}
              </button>
            </div>
            {webhookTestResult && (
              <p className="text-xs mt-2" style={{ color: webhookTestResult === "ok" ? "#4ade80" : "#f87171" }}>
                {webhookTestResult === "ok" ? "✓ Test payload delivered" : "✗ Failed — check the URL and try again"}
              </p>
            )}
          </div>
        </section>

        {/* ── Team seats — Agency only ── */}
        {subscription?.tier === "agency" && (
          <section
            className="rounded-2xl p-6"
            style={{ background: "var(--bg-card)", border: "1px solid var(--border)" }}
          >
            <div className="flex items-center justify-between mb-2">
              <div className="flex items-center gap-2">
                <Users className="w-4 h-4" style={{ color: "#60a5fa" }} />
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
                    className="flex items-center justify-between gap-3 rounded-xl px-4 py-3"
                    style={{ background: "var(--bg3)", border: "1px solid var(--border)" }}
                  >
                    <div>
                      <p className="text-sm font-medium" style={{ color: "var(--text)" }}>{m.invited_email}</p>
                      <p className="text-xs mt-0.5 capitalize" style={{ color: m.status === "active" ? "#4ade80" : "var(--muted)" }}>
                        {m.status === "active" ? "Active" : "Invite pending"}
                      </p>
                    </div>
                    <button
                      onClick={() => handleRemoveMember(m.id)}
                      className="p-1.5 rounded-lg transition-colors hover:bg-red-500/10"
                      style={{ color: "#f87171" }}
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
                    className="flex-1 px-4 py-2.5 rounded-xl text-sm outline-none"
                    style={{ background: "var(--bg3)", border: "1px solid var(--border)", color: "var(--text)" }}
                  />
                  <button
                    onClick={handleInvite}
                    disabled={inviting || !inviteEmail.trim()}
                    className="font-semibold text-sm px-5 py-2.5 rounded-xl transition-all hover:brightness-110 disabled:opacity-50 flex items-center gap-2 shrink-0"
                    style={{ background: "#60a5fa", color: "#060d18" }}
                  >
                    {inviting ? <Loader2 className="w-4 h-4 animate-spin" /> : null}
                    {inviting ? "Sending…" : "Invite"}
                  </button>
                </div>
                {inviteError && <p className="text-xs mt-2" style={{ color: "#f87171" }}>{inviteError}</p>}
                {inviteSent && <p className="text-xs mt-2" style={{ color: "#4ade80" }}>✓ Invite sent</p>}
              </div>
            )}
          </section>
        )}

        {/* ── API keys — Pro / Agency / Developer ── */}
        {isPaidTier && (
          <section
            className="rounded-2xl p-6"
            style={{ background: "var(--bg-card)", border: "1px solid var(--border)" }}
          >
            <div className="flex items-center justify-between mb-2">
              <div className="flex items-center gap-2">
                <Key className="w-4 h-4" style={{ color: "#c084fc" }} />
                <h2 className="font-semibold" style={{ color: "var(--text)" }}>API keys</h2>
              </div>
              <a
                href="/api-docs"
                className="flex items-center gap-1 text-xs font-medium hover:underline"
                style={{ color: "#c084fc" }}
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
                    className="flex items-center justify-between gap-3 rounded-xl px-4 py-3"
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
                      style={{ color: "#f87171" }}
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
                className="mb-5 rounded-xl p-4"
                style={{ background: "rgba(168,85,247,.08)", border: "1px solid rgba(168,85,247,.25)" }}
              >
                <p className="text-xs font-semibold mb-2" style={{ color: "#c084fc" }}>
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
                      background: copiedKey ? "rgba(74,222,128,.15)" : "var(--bg3)",
                      color: copiedKey ? "#4ade80" : "var(--muted)",
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
                  className="flex-1 px-4 py-2.5 rounded-xl text-sm outline-none"
                  style={{ background: "var(--bg3)", border: "1px solid var(--border)", color: "var(--text)" }}
                />
                <button
                  onClick={handleCreateKey}
                  disabled={creatingKey}
                  className="font-semibold text-sm px-5 py-2.5 rounded-xl transition-all hover:brightness-110 disabled:opacity-50 flex items-center gap-2 shrink-0"
                  style={{ background: "#c084fc", color: "#060d18" }}
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

        {/* ── Account ── */}
        <section
          className="rounded-2xl p-6"
          style={{ background: "var(--bg-card)", border: "1px solid var(--border)" }}
        >
          <div className="flex items-center gap-2 mb-5">
            <User className="w-4 h-4" style={{ color: "var(--muted)" }} />
            <h2 className="font-semibold" style={{ color: "var(--text)" }}>Account</h2>
          </div>

          <div className="space-y-0">
            <div className="flex items-center justify-between py-3 border-b" style={{ borderColor: "var(--border)" }}>
              <div>
                <p className="text-sm font-medium" style={{ color: "var(--text)" }}>Email address</p>
                <p className="text-xs mt-0.5 font-mono" style={{ color: "var(--muted)" }}>
                  {userEmail || "—"}
                </p>
              </div>
            </div>

            <div className="flex items-center justify-between py-3 border-b" style={{ borderColor: "var(--border)" }}>
              <div>
                <p className="text-sm font-medium" style={{ color: "var(--text)" }}>Password</p>
                <p className="text-xs mt-0.5" style={{ color: "var(--muted)" }}>
                  {passwordResetSent ? "Reset link sent — check your email" : "We'll send a reset link to your email address"}
                </p>
              </div>
              <button
                onClick={handleResetPassword}
                disabled={passwordResetSent || !userEmail}
                className="shrink-0 text-sm font-semibold px-4 py-2 rounded-xl transition-all hover:opacity-80 disabled:opacity-50"
                style={{ background: "var(--bg3)", color: "var(--text)", border: "1px solid var(--border)" }}
              >
                {passwordResetSent ? "Sent ✓" : "Reset password"}
              </button>
            </div>
          </div>

          {/* Danger zone */}
          <div className="mt-5 pt-5 border-t" style={{ borderColor: "var(--border)" }}>
            <p className="text-xs font-bold uppercase tracking-wider mb-3" style={{ color: "#f87171" }}>
              Danger zone
            </p>
            <button
              onClick={handleDeleteAccount}
              disabled={deletingAccount}
              className="text-sm font-semibold px-4 py-2.5 rounded-xl transition-all hover:opacity-80 disabled:opacity-60"
              style={{ background: "rgba(248,113,113,.1)", color: "#f87171", border: "1px solid rgba(248,113,113,.25)" }}
            >
              {deletingAccount ? "Deleting…" : "Delete account"}
            </button>
            <p className="text-xs mt-2" style={{ color: "var(--muted)" }}>
              Permanently deletes your account, all tracked competitors, and scan history. This cannot be undone.
            </p>
          </div>
        </section>

      </div>

      <UpgradeModal open={upgradeOpen} onClose={() => setUpgradeOpen(false)} trigger="general" />

      {addCompetitorOpen && (
        <AddCompetitorModal
          onClose={() => setAddCompetitorOpen(false)}
          onAdded={(c) => {
            setMyCompetitors((prev) => [...prev, c]);
            setAddCompetitorOpen(false);
          }}
        />
      )}
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
