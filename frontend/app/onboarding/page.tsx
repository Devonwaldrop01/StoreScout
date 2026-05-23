"use client";

import { useEffect, useRef, useState } from "react";
import { useRouter } from "next/navigation";
import { Zap, CheckCircle2, AlertCircle, AlertTriangle, ArrowRight, Search } from "lucide-react";
import { createClient } from "@/lib/supabase/client";
import { competitors as competitorsApi, user as userApi } from "@/lib/api";
import { cn } from "@/lib/utils";

const STORE_SIZES = ["Just starting out", "$100K–$500K", "$500K–$2M", "$2M+"] as const;
const CATEGORIES = ["Apparel", "Beauty & Health", "Home & Living", "Sports & Fitness", "Other"] as const;
const GOALS = ["Monitor pricing", "Track new launches", "Watch discount campaigns", "All of the above"] as const;

type StoreSize = (typeof STORE_SIZES)[number] | "";
type Category = (typeof CATEGORIES)[number] | "";
type Goal = (typeof GOALS)[number] | "";

const SCAN_PHASES: [number, string][] = [
  [0,  "Connecting to store..."],
  [12, "Fetching product catalog..."],
  [30, "Normalizing products..."],
  [52, "Analyzing pricing patterns..."],
  [70, "Computing launch velocity..."],
  [84, "Building intelligence report..."],
  [94, "Almost done..."],
];

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
  const [trackedHostname, setTrackedHostname] = useState("");

  // Step 2 state
  const [storeSize, setStoreSize] = useState<StoreSize>("");
  const [category, setCategory] = useState<Category>("");
  const [goal, setGoal] = useState<Goal>("");

  // Scan progress state
  const [scanDone, setScanDone] = useState(false);
  const [progress, setProgress] = useState(0);
  const [scanPhase, setScanPhase] = useState("Connecting to store...");

  const checkTimerRef = useRef<ReturnType<typeof setTimeout> | null>(null);
  const progressRef = useRef(0);

  // ── Auth guard ────────────────────────────────────────────────────────────
  useEffect(() => {
    async function check() {
      const { data: { session } } = await supabase.auth.getSession();
      if (!session) { router.replace("/auth/login"); return; }
      await userApi.provision().catch(() => {});
      try {
        const result = await competitorsApi.list();
        if ((result.data || []).length > 0) { router.replace("/dashboard"); return; }
      } catch {}
      setAuthChecked(true);
    }
    check();
  }, [router, supabase]);

  // ── Fake progress simulation ──────────────────────────────────────────────
  useEffect(() => {
    if (step !== 2 || scanDone) return;
    progressRef.current = 0;
    const timer = setInterval(() => {
      const increment = progressRef.current < 40
        ? Math.random() * 4 + 2
        : progressRef.current < 75
        ? Math.random() * 2 + 0.8
        : Math.random() * 0.6 + 0.2;
      progressRef.current = Math.min(progressRef.current + increment, 96);
      const p = Math.floor(progressRef.current);
      setProgress(p);
      const phase = [...SCAN_PHASES].reverse().find(([min]) => p >= min);
      if (phase) setScanPhase(phase[1]);
    }, 600);
    return () => clearInterval(timer);
  }, [step, scanDone]);

  // ── Real scan polling ─────────────────────────────────────────────────────
  useEffect(() => {
    if (step !== 2 || !newCompetitorId || scanDone) return;
    const poll = setInterval(async () => {
      try {
        await competitorsApi.latestSnapshot(newCompetitorId);
        setScanDone(true);
        setProgress(100);
        setScanPhase("Scan complete!");
      } catch {
        // 404 = still pending, keep polling
      }
    }, 3000);
    return () => clearInterval(poll);
  }, [step, newCompetitorId, scanDone]);

  // ── Step 1: URL validation ────────────────────────────────────────────────
  async function checkStore(value: string) {
    if (!value.trim()) return;
    setChecking(true);
    setStoreStatus("idle");
    try {
      const res = await fetch(`/api/check_store?store_url=${encodeURIComponent(value.trim())}`);
      const data = await res.json();
      if (data.ok && data.restricted) { setStoreStatus("restricted"); setStoreError(""); }
      else if (data.ok) { setStoreStatus("ok"); setStoreError(""); }
      else { setStoreStatus("error"); setStoreError("Doesn't look like a Shopify store"); }
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
      setTrackedHostname(data.hostname || url.trim().replace(/^https?:\/\//, ""));
      setStep(2);
    } catch (err: unknown) {
      const apiErr = err as { data?: { detail?: string | { code?: string } } };
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

  function finish() {
    const dest = newCompetitorId ? `/dashboard/${newCompetitorId}` : "/dashboard";
    router.push(dest);
  }

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
              <div className="w-10 h-px" style={{ background: step > s ? "var(--green)" : "var(--border)" }} />
            )}
          </div>
        ))}
      </div>

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
              Paste any Shopify store URL. We&apos;ll scan their full catalog and have data ready in about 30 seconds.
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
                {storeStatus === "ok" && <p className="text-xs mt-1.5 text-green-400">✓ Shopify store detected</p>}
                {storeStatus === "restricted" && <p className="text-xs mt-1.5 text-yellow-400">This store restricts public access — we&apos;ll still attempt to scan it</p>}
                {storeStatus === "error" && <p className="text-xs mt-1.5 text-red-400">{storeError}</p>}
              </div>

              {addError && (
                <div className="flex items-start gap-2 p-3 rounded-xl text-sm" style={{ background: "rgba(248,113,113,.1)", border: "1px solid rgba(248,113,113,.3)", color: "#fca5a5" }}>
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
            <h1 className="text-xl font-bold mb-1" style={{ color: "var(--text)" }}>
              Scan in progress
            </h1>
            <p className="text-sm mb-5" style={{ color: "var(--muted)" }}>
              Tell us about yourself while we work — takes 10 seconds.
            </p>

            {/* Scan progress block */}
            <div
              className="rounded-xl p-4 mb-6 transition-all"
              style={{
                background: scanDone ? "rgba(34,197,94,.06)" : "var(--bg3)",
                border: `1px solid ${scanDone ? "rgba(34,197,94,.3)" : "var(--border)"}`,
              }}
            >
              <div className="flex items-center gap-3 mb-3">
                {scanDone ? (
                  <CheckCircle2 className="w-5 h-5 shrink-0 text-green-400" />
                ) : (
                  <div
                    className="w-5 h-5 border-2 border-t-transparent rounded-full animate-spin shrink-0"
                    style={{ borderColor: "var(--green)" }}
                  />
                )}
                <div className="min-w-0">
                  <p className="text-sm font-semibold" style={{ color: scanDone ? "#4ade80" : "var(--text)" }}>
                    {scanDone ? "Scan complete!" : trackedHostname || "Scanning store..."}
                  </p>
                  <p className="text-xs truncate" style={{ color: "var(--muted)" }}>{scanPhase}</p>
                </div>
              </div>
              <div className="h-1.5 rounded-full overflow-hidden" style={{ background: "rgba(255,255,255,.08)" }}>
                <div
                  className="h-full rounded-full transition-all duration-700"
                  style={{
                    width: `${progress}%`,
                    background: scanDone ? "#22c55e" : "var(--green)",
                  }}
                />
              </div>
            </div>

            {/* Survey */}
            <div className="space-y-5">
              <div>
                <p className="text-sm font-medium mb-2" style={{ color: "var(--text)" }}>How big is your store?</p>
                <div className="flex flex-wrap gap-2">
                  {STORE_SIZES.map((s) => (
                    <PillButton key={s} label={s} selected={storeSize === s} onClick={() => setStoreSize(s)} />
                  ))}
                </div>
              </div>
              <div>
                <p className="text-sm font-medium mb-2" style={{ color: "var(--text)" }}>What&apos;s your main category?</p>
                <div className="flex flex-wrap gap-2">
                  {CATEGORIES.map((c) => (
                    <PillButton key={c} label={c} selected={category === c} onClick={() => setCategory(c)} />
                  ))}
                </div>
              </div>
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
              className={cn(
                "mt-6 w-full flex items-center justify-center gap-2 font-semibold py-3 rounded-xl transition-all",
                scanDone ? "animate-pulse hover:animate-none hover:brightness-110" : "hover:brightness-90 opacity-80"
              )}
              style={{ background: scanDone ? "var(--green)" : "var(--bg3)", color: scanDone ? "#060d18" : "var(--muted)", border: scanDone ? "none" : "1px solid var(--border)" }}
            >
              {scanDone ? (
                <>See your results <ArrowRight className="w-4 h-4" /></>
              ) : (
                <>Go to dashboard <ArrowRight className="w-4 h-4" /></>
              )}
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
