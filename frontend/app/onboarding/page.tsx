"use client";

import { useEffect, useRef, useState } from "react";
import { useRouter } from "next/navigation";
import { Zap, CheckCircle2, AlertCircle, AlertTriangle, ArrowRight, Search } from "lucide-react";
import { createClient } from "@/lib/supabase/client";
import { competitors as competitorsApi } from "@/lib/api";
import { cn } from "@/lib/utils";

// ── Survey option types ───────────────────────────────────────────────────────

const STORE_SIZES = ["Just starting out", "$100K–$500K", "$500K–$2M", "$2M+"] as const;
const CATEGORIES = ["Apparel", "Beauty & Health", "Home & Living", "Sports & Fitness", "Other"] as const;
const GOALS = ["Monitor pricing", "Track new launches", "Watch discount campaigns", "All of the above"] as const;

type StoreSize = (typeof STORE_SIZES)[number] | "";
type Category = (typeof CATEGORIES)[number] | "";
type Goal = (typeof GOALS)[number] | "";

// ── Main component ────────────────────────────────────────────────────────────

export default function OnboardingPage() {
  const router = useRouter();
  const supabase = createClient();

  const [authChecked, setAuthChecked] = useState(false);
  const [step, setStep] = useState<1 | 2>(1);

  // Step 1 state
  const [url, setUrl] = useState("");
  const [checking, setChecking] = useState(false);
  const [storeStatus, setStoreStatus] = useState<"idle" | "ok" | "restricted" | "error">("idle");
  const [storeError, setStoreError] = useState("");
  const [submitting, setSubmitting] = useState(false);
  const [addError, setAddError] = useState("");
  const [newCompetitorId, setNewCompetitorId] = useState("");

  // Step 2 state
  const [storeSize, setStoreSize] = useState<StoreSize>("");
  const [category, setCategory] = useState<Category>("");
  const [goal, setGoal] = useState<Goal>("");

  const checkTimerRef = useRef<ReturnType<typeof setTimeout> | null>(null);

  // ── Auth guard + skip if already onboarded ───────────────────────────────
  useEffect(() => {
    async function check() {
      const { data: { session } } = await supabase.auth.getSession();
      if (!session) {
        router.replace("/auth/login");
        return;
      }
      // If user already has competitors, skip onboarding
      try {
        const result = await competitorsApi.list();
        if ((result.data || []).length > 0) {
          router.replace("/dashboard");
          return;
        }
      } catch {
        // can't reach API — let them onboard anyway
      }
      setAuthChecked(true);
    }
    check();
  }, [router, supabase]);

  // ── Step 1: URL validation ───────────────────────────────────────────────
  async function checkStore(value: string) {
    if (!value.trim()) return;
    setChecking(true);
    setStoreStatus("idle");
    try {
      const res = await fetch(`/api/check_store?store_url=${encodeURIComponent(value.trim())}`);
      const data = await res.json();
      if (data.ok && data.restricted) {
        setStoreStatus("restricted");
        setStoreError("");
      } else if (data.ok) {
        setStoreStatus("ok");
        setStoreError("");
      } else {
        setStoreStatus("error");
        setStoreError("Doesn't look like a Shopify store");
      }
    } catch {
      setStoreStatus("error");
      setStoreError("Network error — check the URL and try again");
    } finally {
      setChecking(false);
    }
  }

  function handleUrlChange(e: React.ChangeEvent<HTMLInputElement>) {
    const value = e.target.value;
    setUrl(value);
    setStoreStatus("idle");
    setAddError("");
    if (checkTimerRef.current) clearTimeout(checkTimerRef.current);
    if (value.length > 5) {
      checkTimerRef.current = setTimeout(() => checkStore(value), 700);
    }
  }

  async function handleAddCompetitor(e: React.FormEvent) {
    e.preventDefault();
    if (!url.trim() || storeStatus === "error") return;
    setSubmitting(true);
    setAddError("");
    try {
      const { data } = await competitorsApi.add(url.trim());
      setNewCompetitorId(data.id);
      setStep(2);
    } catch (err: unknown) {
      const apiErr = err as { data?: { detail?: string | { code?: string; limit?: number } } };
      const detail = apiErr?.data?.detail;
      if (typeof detail === "object" && detail?.code === "competitor_limit_reached") {
        setAddError("Account error — try refreshing the page.");
      } else if (typeof detail === "string") {
        setAddError(detail);
      } else {
        setAddError("Something went wrong — please try again.");
      }
    } finally {
      setSubmitting(false);
    }
  }

  // ── Step 2: Survey submit + finish ──────────────────────────────────────
  function finish() {
    const dest = newCompetitorId ? `/dashboard/${newCompetitorId}` : "/dashboard";
    router.push(dest);
  }

  // ── Render ───────────────────────────────────────────────────────────────
  if (!authChecked) {
    return (
      <div className="min-h-screen flex items-center justify-center" style={{ background: "var(--bg)" }}>
        <div className="w-6 h-6 border-2 border-t-transparent rounded-full animate-spin" style={{ borderColor: "var(--green)" }} />
      </div>
    );
  }

  const borderColor =
    storeStatus === "ok" ? "#22c55e"
    : storeStatus === "restricted" ? "#facc15"
    : storeStatus === "error" ? "#f87171"
    : "var(--border)";

  return (
    <div className="min-h-screen flex flex-col items-center justify-center p-4" style={{ background: "var(--bg)" }}>
      {/* Logo */}
      <div className="flex items-center gap-2 mb-8">
        <Zap className="w-5 h-5" style={{ color: "var(--green)" }} />
        <span className="text-lg font-bold" style={{ color: "var(--text)" }}>StoreScout</span>
      </div>

      {/* Step indicator */}
      <div className="flex items-center gap-2 mb-6">
        {([1, 2] as const).map((s) => (
          <div key={s} className="flex items-center gap-2">
            <div
              className="w-7 h-7 rounded-full flex items-center justify-center text-xs font-bold transition-all"
              style={{
                background: step >= s ? "var(--green)" : "var(--bg3)",
                color: step >= s ? "#060d18" : "var(--muted)",
                border: `1px solid ${step >= s ? "var(--green)" : "var(--border)"}`,
              }}
            >
              {step > s ? <CheckCircle2 className="w-3.5 h-3.5" /> : s}
            </div>
            {s < 2 && (
              <div
                className="w-10 h-px"
                style={{ background: step > s ? "var(--green)" : "var(--border)" }}
              />
            )}
          </div>
        ))}
      </div>

      {/* Card */}
      <div
        className="w-full max-w-md rounded-2xl p-7"
        style={{ background: "var(--bg2)", border: "1px solid var(--border)" }}
      >
        {/* ── Step 1 ── */}
        {step === 1 && (
          <>
            <h1 className="text-xl font-bold mb-1" style={{ color: "var(--text)" }}>
              Add your first competitor
            </h1>
            <p className="text-sm mb-6" style={{ color: "var(--muted)" }}>
              Paste any Shopify store URL. We&apos;ll scan their full catalog and have data ready in about 20 seconds.
            </p>

            <form onSubmit={handleAddCompetitor} className="space-y-4">
              <div>
                <label className="block text-sm font-medium mb-1.5" style={{ color: "var(--muted)" }}>
                  Store URL
                </label>
                <div className="relative">
                  <input
                    type="text"
                    value={url}
                    onChange={handleUrlChange}
                    placeholder="gymshark.com"
                    autoFocus
                    className="w-full px-4 py-3 rounded-xl text-sm font-mono pr-10 outline-none transition-all"
                    style={{
                      background: "var(--bg3)",
                      border: `1px solid ${borderColor}`,
                      color: "var(--text)",
                    }}
                  />
                  <div className="absolute right-3 top-1/2 -translate-y-1/2">
                    {checking && (
                      <div className="w-4 h-4 border-2 border-t-transparent rounded-full animate-spin" style={{ borderColor: "var(--green)" }} />
                    )}
                    {!checking && storeStatus === "ok" && <CheckCircle2 className="w-4 h-4 text-green-400" />}
                    {!checking && storeStatus === "restricted" && <AlertTriangle className="w-4 h-4 text-yellow-400" />}
                    {!checking && storeStatus === "error" && <AlertCircle className="w-4 h-4 text-red-400" />}
                  </div>
                </div>

                {storeStatus === "ok" && (
                  <p className="text-xs mt-1.5 text-green-400">✓ Shopify store detected</p>
                )}
                {storeStatus === "restricted" && (
                  <p className="text-xs mt-1.5 text-yellow-400">This store restricts public access — we&apos;ll still attempt to scan it</p>
                )}
                {storeStatus === "error" && (
                  <p className="text-xs mt-1.5 text-red-400">{storeError}</p>
                )}
              </div>

              {addError && (
                <div
                  className="flex items-start gap-2 p-3 rounded-xl text-sm"
                  style={{ background: "rgba(248,113,113,.1)", border: "1px solid rgba(248,113,113,.3)", color: "#fca5a5" }}
                >
                  <AlertCircle className="w-4 h-4 mt-0.5 shrink-0" />
                  {addError}
                </div>
              )}

              <button
                type="submit"
                disabled={submitting || !url.trim() || storeStatus === "error" || checking}
                className={cn(
                  "w-full flex items-center justify-center gap-2 font-semibold py-3 rounded-xl transition-all",
                  submitting || !url.trim() || storeStatus === "error" || checking
                    ? "opacity-50 cursor-not-allowed"
                    : "hover:brightness-110"
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

            <p className="text-xs text-center mt-4" style={{ color: "var(--muted)" }}>
              You can add more competitors after signup.
            </p>
          </>
        )}

        {/* ── Step 2 ── */}
        {step === 2 && (
          <>
            <div className="flex items-center gap-2 mb-1">
              <CheckCircle2 className="w-5 h-5 text-green-400" />
              <h1 className="text-xl font-bold" style={{ color: "var(--text)" }}>
                Scan started!
              </h1>
            </div>
            <p className="text-sm mb-6" style={{ color: "var(--muted)" }}>
              While we scan your competitor, tell us a little about yourself so we can tailor your experience. Takes 10 seconds.
            </p>

            <div className="space-y-5">
              {/* Q1 */}
              <div>
                <p className="text-sm font-medium mb-2" style={{ color: "var(--text)" }}>How big is your store?</p>
                <div className="flex flex-wrap gap-2">
                  {STORE_SIZES.map((s) => (
                    <PillButton key={s} label={s} selected={storeSize === s} onClick={() => setStoreSize(s)} />
                  ))}
                </div>
              </div>

              {/* Q2 */}
              <div>
                <p className="text-sm font-medium mb-2" style={{ color: "var(--text)" }}>What&apos;s your main category?</p>
                <div className="flex flex-wrap gap-2">
                  {CATEGORIES.map((c) => (
                    <PillButton key={c} label={c} selected={category === c} onClick={() => setCategory(c)} />
                  ))}
                </div>
              </div>

              {/* Q3 */}
              <div>
                <p className="text-sm font-medium mb-2" style={{ color: "var(--text)" }}>What matters most to you?</p>
                <div className="flex flex-wrap gap-2">
                  {GOALS.map((g) => (
                    <PillButton key={g} label={g} selected={goal === g} onClick={() => setGoal(g)} />
                  ))}
                </div>
              </div>
            </div>

            <button
              onClick={finish}
              className="mt-6 w-full flex items-center justify-center gap-2 font-semibold py-3 rounded-xl transition-all hover:brightness-110"
              style={{ background: "var(--green)", color: "#060d18" }}
            >
              See my dashboard
              <ArrowRight className="w-4 h-4" />
            </button>

            <button
              onClick={finish}
              className="mt-2 w-full text-sm py-2 rounded-xl transition-colors hover:bg-white/5"
              style={{ color: "var(--muted)" }}
            >
              Skip for now
            </button>
          </>
        )}
      </div>
    </div>
  );
}

// ── Pill selector ─────────────────────────────────────────────────────────────

function PillButton({ label, selected, onClick }: { label: string; selected: boolean; onClick: () => void }) {
  return (
    <button
      type="button"
      onClick={onClick}
      className="px-3 py-1.5 rounded-full text-sm font-medium transition-all"
      style={{
        background: selected ? "rgba(163,240,0,.15)" : "var(--bg3)",
        border: `1px solid ${selected ? "var(--green)" : "var(--border)"}`,
        color: selected ? "var(--green)" : "var(--muted)",
      }}
    >
      {label}
    </button>
  );
}
