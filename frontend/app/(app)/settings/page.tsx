"use client";

import { Suspense, useEffect, useState } from "react";
import { useSearchParams } from "next/navigation";
import { user as userApi, billing, myStore as myStoreApi, team as teamApi, apiKeys as apiKeysApi, type UserSubscription, type NotificationPrefs, type Competitor, type TeamMember, type ApiKey } from "@/lib/api";
import { cn } from "@/lib/utils";
import UpgradeModal from "@/components/UpgradeModal";
import { Store, Hash, Globe, Users, X, Loader2, Key, Copy, Check, Terminal } from "lucide-react";

// Inner component uses useSearchParams — must be inside <Suspense>
function SettingsContent() {
  const [subscription, setSubscription] = useState<UserSubscription | null>(null);
  const [prefs, setPrefs] = useState<NotificationPrefs | null>(null);
  const [saving, setSaving] = useState(false);
  const [saved, setSaved] = useState(false);
  const [upgradeOpen, setUpgradeOpen] = useState(false);
  const [portalLoading, setPortalLoading] = useState(false);
  const [store, setStore] = useState<Competitor | null>(null);
  const [storeUrl, setStoreUrl] = useState("");
  const [storeSaving, setStoreSaving] = useState(false);
  const [storeError, setStoreError] = useState("");
  const [slackUrl, setSlackUrl] = useState("");
  const [webhookUrl, setWebhookUrl] = useState("");
  const [testingSlack, setTestingSlack] = useState(false);
  const [testingWebhook, setTestingWebhook] = useState(false);
  const [slackTestResult, setSlackTestResult] = useState<"ok" | "error" | null>(null);
  const [webhookTestResult, setWebhookTestResult] = useState<"ok" | "error" | null>(null);
  const [teamMembers, setTeamMembers] = useState<TeamMember[]>([]);
  const [inviteEmail, setInviteEmail] = useState("");
  const [inviting, setInviting] = useState(false);
  const [inviteError, setInviteError] = useState("");
  const [inviteSent, setInviteSent] = useState(false);
  const [keys, setKeys] = useState<ApiKey[]>([]);
  const [newKeyName, setNewKeyName] = useState("");
  const [creatingKey, setCreatingKey] = useState(false);
  const [newKeyPlaintext, setNewKeyPlaintext] = useState("");
  const [copiedKey, setCopiedKey] = useState(false);
  const searchParams = useSearchParams();

  useEffect(() => {
    userApi.subscription().then((r) => {
      setSubscription(r.data);
      if (["pro", "agency", "developer"].includes(r.data.tier)) {
        apiKeysApi.list().then((kr) => setKeys(kr.data)).catch(() => {});
      }
    }).catch(() => {});
    userApi.prefs().then((r) => {
      setPrefs(r.data);
      setSlackUrl(r.data.slack_webhook_url || "");
      setWebhookUrl(r.data.webhook_url || "");
    }).catch(() => {});
    myStoreApi.get().then((r) => setStore(r.data)).catch(() => {});
    teamApi.members().then((r) => setTeamMembers(r.data)).catch(() => {});

    if (searchParams.get("upgraded") === "1") {
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
      // swallow — key creation failure is rare
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

  const tierBadgeStyle: Record<string, { bg: string; color: string }> = {
    free: { bg: "rgba(255,255,255,.06)", color: "var(--muted)" },
    pro: { bg: "rgba(163,240,0,.12)", color: "#a3f000" },
    agency: { bg: "rgba(59,130,246,.12)", color: "#60a5fa" },
    developer: { bg: "rgba(168,85,247,.12)", color: "#c084fc" },
  };

  const isPaidTier = ["pro", "agency", "developer"].includes(subscription?.tier ?? "");

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

        <section
          className="rounded-2xl p-6"
          style={{ background: "var(--bg-card)", border: "1px solid var(--border)" }}
        >
          <div className="flex items-center gap-2 mb-2">
            <Store className="w-4 h-4" style={{ color: "#a3f000" }} />
            <h2 className="font-semibold" style={{ color: "var(--text)" }}>Your store</h2>
          </div>
          <p className="text-sm mb-4" style={{ color: "var(--muted)" }}>
            Add your own Shopify store to unlock head-to-head comparisons on every competitor.
            It doesn&apos;t count against your tracking limit.
          </p>

          {store ? (
            <div className="flex items-center justify-between gap-4 flex-wrap">
              <div>
                <p className="text-sm font-medium" style={{ color: "var(--text)" }}>{store.hostname}</p>
                <p className="text-xs mt-0.5" style={{ color: "var(--muted)" }}>
                  {store.product_count != null ? `${store.product_count} products · ` : ""}
                  {store.scan_status === "done" ? "Scanned" : store.scan_status === "error" ? "Scan failed" : "Scanning…"}
                </p>
              </div>
              <button
                onClick={handleRemoveStore}
                className="font-semibold text-sm px-4 py-2 rounded-xl transition-all hover:opacity-80"
                style={{ background: "var(--bg3)", color: "#f87171", border: "1px solid var(--border)" }}
              >
                Remove
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
                {storeSaving ? "Adding…" : "Add store"}
              </button>
            </div>
          )}
          {storeError && <p className="text-xs mt-3" style={{ color: "#f87171" }}>{storeError}</p>}
        </section>

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

        {/* Integrations */}
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
              Create an incoming webhook in your Slack workspace and paste the URL below.{" "}
              Alerts will appear as rich messages in your chosen channel.
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
              POST JSON to any URL when a change alert fires. Works with Zapier, Make, Notion,
              or any custom endpoint.
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

        {/* Team seats — Agency only */}
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
              Invite up to 2 team members to access your competitor dashboards. They can view all data but cannot delete competitors or manage billing.
            </p>

            {/* Current members */}
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

            {/* Invite form */}
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
                    className="font-semibold text-sm px-5 py-2.5 rounded-xl transition-all hover:brightness-110 disabled:opacity-50 flex items-center gap-2"
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
        {/* API Keys — Pro / Agency / Developer */}
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
              Use API keys to access StoreScout data programmatically.
              Keys begin with <code className="text-xs font-mono px-1 py-0.5 rounded" style={{ background: "var(--bg3)" }}>sk_live_</code>.
              Copy your key immediately — it will not be shown again.
            </p>

            {/* Existing keys */}
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

            {/* New key revealed once */}
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
                    style={{ background: copiedKey ? "rgba(74,222,128,.15)" : "var(--bg3)", color: copiedKey ? "#4ade80" : "var(--muted)", border: "1px solid var(--border)" }}
                  >
                    {copiedKey ? <Check className="w-3.5 h-3.5" /> : <Copy className="w-3.5 h-3.5" />}
                    {copiedKey ? "Copied" : "Copy"}
                  </button>
                </div>
              </div>
            )}

            {/* Create form */}
            {keys.length < 5 && (
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
            )}
            {keys.length >= 5 && (
              <p className="text-xs" style={{ color: "var(--muted)" }}>
                Maximum of 5 active keys reached. Revoke one to create a new key.
              </p>
            )}
          </section>
        )}
      </div>

      <UpgradeModal open={upgradeOpen} onClose={() => setUpgradeOpen(false)} trigger="general" />
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
