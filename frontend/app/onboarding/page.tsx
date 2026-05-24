"use client";

import { useEffect, useRef, useState } from "react";
import { useRouter } from "next/navigation";
import {
  Zap, CheckCircle2, AlertCircle, AlertTriangle, ArrowRight,
  Search, TrendingDown, Bell, Package, Sparkles,
} from "lucide-react";
import { createClient } from "@/lib/supabase/client";
import { competitors as competitorsApi, user as userApi } from "@/lib/api";
import { cn } from "@/lib/utils";

type Step = 1 | 2 | 3 | 4;

const CATEGORIES = [
  "Apparel & Fashion",
  "Beauty & Health",
  "Home & Living",
  "Sports & Fitness",
  "Electronics",
  "Other",
] as const;
type Category = (typeof CATEGORIES)[number] | "";

const GOALS = [
  {
    id: "price",
    label: "Catch price changes",
    desc: "Know immediately when competitors raise or drop prices",
  },
  {
    id: "launches",
    label: "Spot new products",
    desc: "Get notified the moment they launch something new",
  },
  {
    id: "discounts",
    label: "Track discount cycles",
    desc: "See when they run sales and how deep they discount",
  },
  {
    id: "all",
    label: "Full picture",
    desc: "Every change, one feed — pricing, launches, discounts",
  },
] as const;
type GoalId = (typeof GOALS)[number]["id"] | "";

// Curated Shopify stores by category — used when users don't know who to track yet.
// All confirmed Shopify / Shopify Plus stores with public /products.json access.
const SUGGESTED_STORES: Record<
  Category,
  { name: string; url: string; tag: string }[]
> = {
  "Apparel & Fashion": [
    { name: "Gymshark", url: "gymshark.com", tag: "Fitness apparel" },
    { name: "Allbirds", url: "allbirds.com", tag: "Sustainable sneakers" },
    { name: "Fashion Nova", url: "fashionnova.com", tag: "Fast fashion" },
    { name: "Chubbies", url: "chubbiesshorts.com", tag: "Men's shorts" },
    { name: "Outdoor Voices", url: "outdoorvoices.com", tag: "Activewear" },
    { name: "Bombas", url: "bombas.com", tag: "Socks & basics" },
  ],
  "Beauty & Health": [
    { name: "Kylie Cosmetics", url: "kyliecosmetics.com", tag: "Makeup" },
    { name: "ColourPop", url: "colourpop.com", tag: "Affordable cosmetics" },
    { name: "Fenty Beauty", url: "fentybeauty.com", tag: "Inclusive beauty" },
    { name: "ILIA Beauty", url: "iliabeauty.com", tag: "Clean beauty" },
    { name: "Patrick Ta", url: "patrickta.com", tag: "Pro makeup" },
    { name: "Saie Beauty", url: "saiebeauty.com", tag: "Clean makeup" },
  ],
  "Home & Living": [
    { name: "Brooklinen", url: "brooklinen.com", tag: "Luxury bedding" },
    { name: "Parachute", url: "parachutehome.com", tag: "Home essentials" },
    { name: "Ruggable", url: "ruggable.com", tag: "Washable rugs" },
    { name: "Snowe", url: "snowehome.com", tag: "Modern home goods" },
    { name: "Jungalow", url: "jungalow.com", tag: "Bohemian decor" },
    { name: "Letterfolk", url: "letterfolk.com", tag: "Letter boards & gifts" },
  ],
  "Sports & Fitness": [
    { name: "Gymshark", url: "gymshark.com", tag: "Fitness apparel" },
    { name: "NOBULL", url: "nobullproject.com", tag: "Training gear" },
    { name: "Gorilla Mind", url: "gorillamind.com", tag: "Supplements" },
    { name: "LMNT", url: "drinklmnt.com", tag: "Electrolytes" },
    { name: "Gainful", url: "gainful.com", tag: "Custom protein" },
    { name: "Ten Thousand", url: "tenthousand.cc", tag: "Training apparel" },
  ],
  Electronics: [
    { name: "Nomad Goods", url: "nomadgoods.com", tag: "Accessories" },
    { name: "Caudabe", url: "caudabe.com", tag: "Phone cases" },
    { name: "Moment", url: "shopmoment.com", tag: "Camera gear" },
    { name: "Dbrand", url: "dbrand.com", tag: "Skins & cases" },
    { name: "Pela Case", url: "pelacase.com", tag: "Eco phone cases" },
    { name: "Moft", url: "moft.us", tag: "Laptop & phone stands" },
  ],
  Other: [
    { name: "Gymshark", url: "gymshark.com", tag: "Fitness apparel" },
    { name: "Allbirds", url: "allbirds.com", tag: "Sustainable sneakers" },
    { name: "Brooklinen", url: "brooklinen.com", tag: "Luxury bedding" },
    { name: "ColourPop", url: "colourpop.com", tag: "Cosmetics" },
    { name: "NOBULL", url: "nobullproject.com", tag: "Training gear" },
    { name: "Ruggable", url: "ruggable.com", tag: "Washable rugs" },
  ],
  "": [],
};

const PLANS = [
  {
    id: "free" as const,
    label: "Free",
    price: "$0",
    per: "",
    accent: "rgba(255,255,255,.35)",
    features: ["1 competitor", "Manual scans", "Current snapshot only"],
    recommended: false,
  },
  {
    id: "pro" as const,
    label: "Pro",
    price: "$29",
    per: "/mo",
    accent: "#a3f000",
    features: [
      "10 competitors",
      "Daily auto-scans",
      "90-day price history",
      "Email change alerts",
      "Weekly AI digest",
    ],
    recommended: true,
  },
  {
    id: "agency" as const,
    label: "Agency",
    price: "$79",
    per: "/mo",
    accent: "#38bdf8",
    features: [
      "50 competitors",
      "Daily auto-scans",
      "Unlimited history",
      "Email change alerts",
      "AI digest + shareable reports",
    ],
    recommended: false,
  },
] as const;

const SCAN_PHASES: [number, string][] = [
  [0, "Connecting to store..."],
  [12, "Fetching product catalog..."],
  [30, "Normalizing products..."],
  [52, "Analyzing pricing patterns..."],
  [70, "Computing launch velocity..."],
  [84, "Building intelligence report..."],
  [94, "Almost done..."],
];

// Zeigarnik effect: progress starts at 20%, never 0%
const STEP_PROGRESS: Record<Step, number> = { 1: 20, 2: 48, 3: 72, 4: 90 };
const STEP_LABELS: Record<Step, string> = {
  1: "Add competitor",
  2: "About you",
  3: "Choose plan",
  4: "First scan",
};

export default function OnboardingPage() {
  const router = useRouter();
  const supabase = createClient();

  const [authChecked, setAuthChecked] = useState(false);
  const [step, setStep] = useState<Step>(1);

  // Step 1 — competitor URL
  const [url, setUrl] = useState("");
  const [checking, setChecking] = useState(false);
  const [storeStatus, setStoreStatus] = useState<"idle" | "ok" | "restricted" | "error">("idle");
  const [storeError, setStoreError] = useState("");
  const [submitting, setSubmitting] = useState(false);
  const [addError, setAddError] = useState("");
  const [newCompetitorId, setNewCompetitorId] = useState("");
  const [trackedHostname, setTrackedHostname] = useState("");

  // Step 2 — survey
  const [category, setCategory] = useState<Category>("");
  const [goalId, setGoalId] = useState<GoalId>("");
  const [quickAdding, setQuickAdding] = useState<string | null>(null); // url being quick-added

  // Whether they skipped step 1 without adding a competitor
  const [skipped, setSkipped] = useState(false);

  // Step 3 — plan
  const [selectedPlan, setSelectedPlan] = useState<"free" | "pro" | "agency">("pro");

  // Step 4 — scan polling
  const [scanDone, setScanDone] = useState(false);
  const [scanProgress, setScanProgress] = useState(0);
  const [scanPhase, setScanPhase] = useState("Connecting to store...");

  const checkTimerRef = useRef<ReturnType<typeof setTimeout> | null>(null);
  const progressRef = useRef(0);

  // Auth guard
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

  // Fake scan progress animation — runs whenever a competitor has been added
  useEffect(() => {
    if (!newCompetitorId || scanDone) return;
    progressRef.current = 0;
    const timer = setInterval(() => {
      const inc =
        progressRef.current < 40
          ? Math.random() * 4 + 2
          : progressRef.current < 75
          ? Math.random() * 2 + 0.8
          : Math.random() * 0.6 + 0.2;
      progressRef.current = Math.min(progressRef.current + inc, 96);
      const p = Math.floor(progressRef.current);
      setScanProgress(p);
      const phase = [...SCAN_PHASES].reverse().find(([min]) => p >= min);
      if (phase) setScanPhase(phase[1]);
    }, 600);
    return () => clearInterval(timer);
  }, [newCompetitorId, scanDone]);

  // Real scan polling
  useEffect(() => {
    if (!newCompetitorId || scanDone) return;
    const poll = setInterval(async () => {
      try {
        await competitorsApi.latestSnapshot(newCompetitorId);
        setScanDone(true);
        setScanProgress(100);
        setScanPhase("Scan complete!");
      } catch {
        // 404 = still pending
      }
    }, 3000);
    return () => clearInterval(poll);
  }, [newCompetitorId, scanDone]);

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
      setTrackedHostname(data.hostname || url.trim().replace(/^https?:\/\//, "").replace(/\/$/, ""));
      setSkipped(false);
      setStep(2);
    } catch (err: unknown) {
      const apiErr = err as { data?: { detail?: string | { code?: string } } };
      const detail = apiErr?.data?.detail;
      if (typeof detail === "string") setAddError(detail);
      else setAddError("Something went wrong — please try again.");
    } finally {
      setSubmitting(false);
    }
  }

  // Quick-add a suggested store from step 2
  async function handleQuickAdd(storeUrl: string, storeName: string) {
    setQuickAdding(storeUrl);
    try {
      const { data } = await competitorsApi.add(storeUrl);
      setNewCompetitorId(data.id);
      setTrackedHostname(data.hostname || storeName);
      setUrl(storeUrl);
      setSkipped(false);
      setStep(3); // Jump straight to plan selection, scan runs in background
    } catch (err: unknown) {
      const apiErr = err as { data?: { detail?: string | { code?: string } } };
      const detail = apiErr?.data?.detail;
      // If limit reached or error, just pre-fill the URL field and go back to step 1
      setUrl(storeUrl);
      setStep(1);
      if (typeof detail === "string") setAddError(detail);
    } finally {
      setQuickAdding(null);
    }
  }

  function handleSkip() {
    setSkipped(true);
    setNewCompetitorId("");
    setTrackedHostname("");
    setStep(2);
  }

  function finish() {
    const dest = newCompetitorId ? `/dashboard/${newCompetitorId}` : "/dashboard";
    if (selectedPlan !== "free") {
      router.push(`${dest}?upgrade=${selectedPlan}`);
    } else {
      router.push(dest);
    }
  }

  if (!authChecked) {
    return (
      <div className="min-h-screen flex items-center justify-center" style={{ background: "var(--bg)" }}>
        <div className="w-6 h-6 border-2 border-t-transparent rounded-full animate-spin" style={{ borderColor: "var(--green)" }} />
      </div>
    );
  }

  const progressPct = STEP_PROGRESS[step];
  const urlBorderColor =
    storeStatus === "ok" ? "#22c55e"
    : storeStatus === "restricted" ? "#facc15"
    : storeStatus === "error" ? "#f87171"
    : "var(--border)";

  const categorySuggestions = category ? SUGGESTED_STORES[category] : [];

  return (
    <div className="min-h-screen flex flex-col" style={{ background: "var(--bg)" }}>
      {/* Top progress bar */}
      <div className="fixed top-0 left-0 right-0 z-50 h-1" style={{ background: "rgba(255,255,255,.06)" }}>
        <div
          className="h-full transition-all duration-700 ease-out"
          style={{ width: `${progressPct}%`, background: "var(--green)" }}
        />
      </div>

      {/* Nav */}
      <header className="flex items-center justify-between px-6 py-4 mt-1">
        <div className="flex items-center gap-2">
          <Zap className="w-4 h-4" style={{ color: "var(--green)" }} />
          <span className="font-bold text-sm" style={{ color: "var(--text)" }}>StoreScout</span>
        </div>
        <div className="flex items-center gap-1.5 text-xs" style={{ color: "var(--muted)" }}>
          <span>Step {step} of 4</span>
          <span className="opacity-40">·</span>
          <span>{STEP_LABELS[step]}</span>
        </div>
      </header>

      {/* Main content */}
      <div className="flex-1 flex flex-col items-center justify-center px-4 py-10">
        <div
          className="w-full max-w-lg rounded-2xl p-7 shadow-xl"
          style={{ background: "var(--bg2)", border: "1px solid var(--border)" }}
        >

          {/* ─── Step 1: Add competitor ─── */}
          {step === 1 && (
            <div>
              <p className="text-xs font-bold uppercase tracking-widest mb-2" style={{ color: "var(--green)" }}>
                Step 1
              </p>
              <h1 className="text-2xl font-bold mb-2" style={{ color: "var(--text)" }}>
                Who are you watching?
              </h1>
              <p className="text-sm mb-7" style={{ color: "var(--muted)" }}>
                Paste any Shopify store URL. We'll scan their full catalog and have
                pricing intelligence ready in about 60 seconds.
              </p>

              <form onSubmit={handleAddCompetitor} className="space-y-4">
                <div>
                  <label className="block text-xs font-semibold uppercase tracking-wider mb-2" style={{ color: "var(--muted)" }}>
                    Shopify store URL
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
                        border: `1px solid ${urlBorderColor}`,
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
                    <p className="text-xs mt-1.5 text-green-400">✓ Shopify store detected — ready to scan</p>
                  )}
                  {storeStatus === "restricted" && (
                    <p className="text-xs mt-1.5 text-yellow-400">Restricts public access — we'll still attempt to scan</p>
                  )}
                  {storeStatus === "error" && (
                    <p className="text-xs mt-1.5 text-red-400">{storeError}</p>
                  )}
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
                    "w-full flex items-center justify-center gap-2 font-semibold py-3.5 rounded-xl transition-all",
                    submitting || !url.trim() || storeStatus === "error" || checking
                      ? "opacity-50 cursor-not-allowed"
                      : "hover:brightness-110"
                  )}
                  style={{ background: "var(--green)", color: "#060d18" }}
                >
                  {submitting ? (
                    <>
                      <div className="w-4 h-4 border-2 border-t-transparent rounded-full animate-spin border-black/40" />
                      Starting scan…
                    </>
                  ) : (
                    <>
                      <Search className="w-4 h-4" />
                      Start tracking
                    </>
                  )}
                </button>
              </form>

              {/* Don't know your competitors? */}
              <div
                className="mt-6 rounded-xl p-4"
                style={{ background: "var(--bg3)", border: "1px solid var(--border)" }}
              >
                <div className="flex items-start gap-3">
                  <Sparkles className="w-4 h-4 mt-0.5 shrink-0" style={{ color: "var(--green)" }} />
                  <div className="min-w-0">
                    <p className="text-sm font-semibold mb-0.5" style={{ color: "var(--text)" }}>
                      Don't know your competitors yet?
                    </p>
                    <p className="text-xs leading-relaxed" style={{ color: "var(--muted)" }}>
                      No problem — tell us your category next and we'll suggest popular Shopify stores
                      in your niche to track. You can also skip this step and add competitors later.
                    </p>
                    <button
                      onClick={handleSkip}
                      className="mt-3 text-xs font-semibold flex items-center gap-1 hover:opacity-80 transition-opacity"
                      style={{ color: "var(--green)" }}
                    >
                      Skip for now — show me suggestions <ArrowRight className="w-3.5 h-3.5" />
                    </button>
                  </div>
                </div>
              </div>
            </div>
          )}

          {/* ─── Step 2: Survey + category-based suggestions ─── */}
          {step === 2 && (
            <div>
              {/* Scan running pill (only if a competitor was added) */}
              {newCompetitorId && (
                <div
                  className="flex items-center gap-2 px-3 py-2 rounded-lg mb-6"
                  style={{ background: "rgba(163,240,0,.07)", border: "1px solid rgba(163,240,0,.15)" }}
                >
                  <div className="w-2 h-2 rounded-full animate-pulse shrink-0" style={{ background: "var(--green)" }} />
                  <p className="text-xs font-medium" style={{ color: "var(--green)" }}>
                    Scan running — {trackedHostname}
                  </p>
                  <span className="text-xs ml-auto" style={{ color: "var(--muted)" }}>
                    {scanProgress}%
                  </span>
                </div>
              )}

              {skipped && (
                <div
                  className="flex items-center gap-2 px-3 py-2 rounded-lg mb-6"
                  style={{ background: "rgba(56,189,248,.07)", border: "1px solid rgba(56,189,248,.2)" }}
                >
                  <Sparkles className="w-3.5 h-3.5 shrink-0" style={{ color: "#38bdf8" }} />
                  <p className="text-xs font-medium" style={{ color: "#38bdf8" }}>
                    Pick your category below and we'll suggest competitors to track
                  </p>
                </div>
              )}

              <p className="text-xs font-bold uppercase tracking-widest mb-2" style={{ color: "var(--green)" }}>
                Step 2
              </p>
              <h1 className="text-2xl font-bold mb-2" style={{ color: "var(--text)" }}>
                Tell us about your store
              </h1>
              <p className="text-sm mb-7" style={{ color: "var(--muted)" }}>
                Two quick questions — helps us surface the right signals for your market.
              </p>

              <div className="space-y-7">
                <div>
                  <p className="text-sm font-semibold mb-3" style={{ color: "var(--text)" }}>
                    What do you sell?
                  </p>
                  <div className="grid grid-cols-2 gap-2 sm:grid-cols-3">
                    {CATEGORIES.map((c) => (
                      <button
                        key={c}
                        type="button"
                        onClick={() => setCategory(c)}
                        className="px-3 py-2.5 rounded-xl text-xs font-medium transition-all text-left"
                        style={{
                          background: category === c ? "rgba(163,240,0,.1)" : "var(--bg3)",
                          border: `1px solid ${category === c ? "var(--green)" : "var(--border)"}`,
                          color: category === c ? "var(--green)" : "var(--muted)",
                        }}
                      >
                        {c}
                      </button>
                    ))}
                  </div>
                </div>

                {/* Category suggestions — only shown after category selected + no competitor yet */}
                {category && categorySuggestions.length > 0 && !newCompetitorId && (
                  <div>
                    <div className="flex items-center gap-2 mb-3">
                      <Sparkles className="w-3.5 h-3.5" style={{ color: "var(--green)" }} />
                      <p className="text-sm font-semibold" style={{ color: "var(--text)" }}>
                        Popular {category} stores to track
                      </p>
                    </div>
                    <p className="text-xs mb-3" style={{ color: "var(--muted)" }}>
                      Click any store to start tracking it — we'll scan their full catalog right now.
                    </p>
                    <div className="grid grid-cols-2 gap-2">
                      {categorySuggestions.map((store) => (
                        <button
                          key={store.url}
                          type="button"
                          onClick={() => handleQuickAdd(store.url, store.name)}
                          disabled={quickAdding !== null}
                          className="flex items-center justify-between px-3 py-2.5 rounded-xl text-left transition-all hover:border-green-500/40 hover:bg-green-500/5 disabled:opacity-50"
                          style={{ background: "var(--bg3)", border: "1px solid var(--border)" }}
                        >
                          <div className="min-w-0">
                            <p className="text-xs font-semibold truncate" style={{ color: "var(--text)" }}>
                              {store.name}
                            </p>
                            <p className="text-xs truncate" style={{ color: "var(--muted)" }}>
                              {store.tag}
                            </p>
                          </div>
                          {quickAdding === store.url ? (
                            <div className="w-3.5 h-3.5 border-2 border-t-transparent rounded-full animate-spin ml-2 shrink-0" style={{ borderColor: "var(--green)" }} />
                          ) : (
                            <ArrowRight className="w-3.5 h-3.5 ml-2 shrink-0 opacity-40" style={{ color: "var(--green)" }} />
                          )}
                        </button>
                      ))}
                    </div>
                    <p className="text-xs mt-2 text-center" style={{ color: "var(--muted)" }}>
                      Or{" "}
                      <button
                        onClick={() => setStep(1)}
                        className="underline hover:opacity-80 transition-opacity"
                        style={{ color: "var(--green)" }}
                      >
                        go back and enter any URL manually
                      </button>
                    </p>
                  </div>
                )}

                <div>
                  <p className="text-sm font-semibold mb-3" style={{ color: "var(--text)" }}>
                    What's your primary intel goal?
                  </p>
                  <div className="space-y-2">
                    {GOALS.map((g) => {
                      const selected = goalId === g.id;
                      return (
                        <button
                          key={g.id}
                          type="button"
                          onClick={() => setGoalId(g.id)}
                          className="w-full flex items-start gap-3 px-4 py-3 rounded-xl transition-all text-left"
                          style={{
                            background: selected ? "rgba(163,240,0,.07)" : "var(--bg3)",
                            border: `1px solid ${selected ? "var(--green)" : "var(--border)"}`,
                          }}
                        >
                          <div
                            className="w-4 h-4 rounded-full border-2 mt-0.5 shrink-0 flex items-center justify-center transition-all"
                            style={{
                              borderColor: selected ? "var(--green)" : "var(--border)",
                              background: selected ? "var(--green)" : "transparent",
                            }}
                          >
                            {selected && <div className="w-1.5 h-1.5 rounded-full bg-black" />}
                          </div>
                          <div>
                            <p className="text-sm font-medium" style={{ color: selected ? "var(--text)" : "var(--muted)" }}>
                              {g.label}
                            </p>
                            <p className="text-xs mt-0.5" style={{ color: "var(--muted)", opacity: 0.7 }}>
                              {g.desc}
                            </p>
                          </div>
                        </button>
                      );
                    })}
                  </div>
                </div>
              </div>

              <button
                onClick={() => setStep(3)}
                disabled={!category || !goalId}
                className={cn(
                  "mt-8 w-full flex items-center justify-center gap-2 font-semibold py-3.5 rounded-xl transition-all",
                  !category || !goalId ? "opacity-40 cursor-not-allowed" : "hover:brightness-110"
                )}
                style={{ background: "var(--green)", color: "#060d18" }}
              >
                Next <ArrowRight className="w-4 h-4" />
              </button>

              {!skipped && (
                <button
                  onClick={() => setStep(1)}
                  className="mt-2 w-full text-sm py-2 rounded-xl hover:bg-white/5 transition-colors"
                  style={{ color: "var(--muted)" }}
                >
                  ← Back
                </button>
              )}
            </div>
          )}

          {/* ─── Step 3: Plan selection ─── */}
          {step === 3 && (
            <div>
              {newCompetitorId && (
                <div
                  className="flex items-center gap-2 px-3 py-2 rounded-lg mb-6"
                  style={{ background: "rgba(163,240,0,.07)", border: "1px solid rgba(163,240,0,.15)" }}
                >
                  <div className="w-2 h-2 rounded-full animate-pulse shrink-0" style={{ background: scanDone ? "#22c55e" : "var(--green)" }} />
                  <p className="text-xs font-medium" style={{ color: "var(--green)" }}>
                    {scanDone ? `Scan complete — ${trackedHostname}` : `Scan running — ${trackedHostname}`}
                  </p>
                  <span className="text-xs ml-auto" style={{ color: "var(--muted)" }}>{scanProgress}%</span>
                </div>
              )}

              <p className="text-xs font-bold uppercase tracking-widest mb-2" style={{ color: "var(--green)" }}>
                Step 3
              </p>
              <h1 className="text-2xl font-bold mb-1.5" style={{ color: "var(--text)" }}>
                Choose your plan
              </h1>
              <p className="text-sm mb-6" style={{ color: "var(--muted)" }}>
                Start free and upgrade when you see value. No credit card needed for Free.
              </p>

              <div className="space-y-3 mb-6">
                {PLANS.map((plan) => {
                  const selected = selectedPlan === plan.id;
                  return (
                    <button
                      key={plan.id}
                      type="button"
                      onClick={() => setSelectedPlan(plan.id)}
                      className="w-full text-left rounded-xl p-4 transition-all"
                      style={{
                        background: selected
                          ? plan.id === "pro"
                            ? "rgba(163,240,0,.07)"
                            : plan.id === "agency"
                            ? "rgba(56,189,248,.07)"
                            : "rgba(255,255,255,.04)"
                          : "var(--bg3)",
                        border: `1px solid ${selected ? plan.accent : "var(--border)"}`,
                      }}
                    >
                      <div className="flex items-center justify-between mb-2.5">
                        <div className="flex items-center gap-2.5">
                          <div
                            className="w-4 h-4 rounded-full border-2 shrink-0 flex items-center justify-center transition-all"
                            style={{
                              borderColor: selected ? plan.accent : "var(--border)",
                              background: selected ? plan.accent : "transparent",
                            }}
                          >
                            {selected && (
                              <div
                                className="w-1.5 h-1.5 rounded-full"
                                style={{ background: plan.id === "free" ? "var(--bg)" : "#060d18" }}
                              />
                            )}
                          </div>
                          <span className="font-bold text-sm" style={{ color: "var(--text)" }}>
                            {plan.label}
                          </span>
                          {plan.recommended && (
                            <span
                              className="text-xs px-2 py-0.5 rounded-full font-semibold"
                              style={{ background: "rgba(163,240,0,.14)", color: "var(--green)" }}
                            >
                              Recommended
                            </span>
                          )}
                        </div>
                        <div className="text-right">
                          <span className="font-bold text-lg" style={{ color: "var(--text)" }}>{plan.price}</span>
                          <span className="text-xs" style={{ color: "var(--muted)" }}>{plan.per}</span>
                        </div>
                      </div>
                      <div className="ml-6 flex flex-wrap gap-x-4 gap-y-1">
                        {plan.features.map((f) => (
                          <span key={f} className="text-xs flex items-center gap-1" style={{ color: "var(--muted)" }}>
                            <span style={{ color: plan.accent }}>✓</span> {f}
                          </span>
                        ))}
                      </div>
                    </button>
                  );
                })}
              </div>

              <button
                onClick={() => setStep(4)}
                className="w-full flex items-center justify-center gap-2 font-semibold py-3.5 rounded-xl hover:brightness-110 transition-all"
                style={{ background: "var(--green)", color: "#060d18" }}
              >
                Continue with {PLANS.find((p) => p.id === selectedPlan)?.label}
                <ArrowRight className="w-4 h-4" />
              </button>

              <p className="text-xs text-center mt-3" style={{ color: "var(--muted)" }}>
                {selectedPlan === "free"
                  ? "No credit card required. Upgrade from the dashboard anytime."
                  : "You can set up billing after your first scan — no charge until then."}
              </p>
            </div>
          )}

          {/* ─── Step 4: Scan OR completion (if skipped) ─── */}
          {step === 4 && (
            <div>
              <p className="text-xs font-bold uppercase tracking-widest mb-2" style={{ color: "var(--green)" }}>
                Step 4
              </p>

              {skipped ? (
                // No competitor was added — show a helpful completion screen
                <>
                  <h1 className="text-2xl font-bold mb-2" style={{ color: "var(--text)" }}>
                    You're all set
                  </h1>
                  <p className="text-sm mb-7" style={{ color: "var(--muted)" }}>
                    Your account is ready. Head to the dashboard to add your first competitor —
                    we'll scan them and have intelligence ready in about 60 seconds.
                  </p>

                  <div
                    className="rounded-xl p-5 mb-6"
                    style={{ background: "var(--bg3)", border: "1px solid var(--border)" }}
                  >
                    <div className="flex items-start gap-3">
                      <Sparkles className="w-5 h-5 mt-0.5 shrink-0" style={{ color: "var(--green)" }} />
                      <div>
                        <p className="text-sm font-semibold mb-1" style={{ color: "var(--text)" }}>
                          Competitor discovery — coming soon
                        </p>
                        <p className="text-xs leading-relaxed" style={{ color: "var(--muted)" }}>
                          We're building a feature to help you find competitors in your niche automatically.
                          For now, you can search by store URL or use our category suggestions when adding
                          a competitor from the dashboard.
                        </p>
                      </div>
                    </div>
                  </div>

                  <button
                    onClick={finish}
                    className="w-full flex items-center justify-center gap-2 font-semibold py-3.5 rounded-xl hover:brightness-110 transition-all"
                    style={{ background: "var(--green)", color: "#060d18" }}
                  >
                    Go to dashboard <ArrowRight className="w-4 h-4" />
                  </button>
                </>
              ) : (
                // Competitor was added — show scan progress
                <>
                  <h1 className="text-2xl font-bold mb-2" style={{ color: "var(--text)" }}>
                    {scanDone ? "Intelligence ready" : "Building your first report"}
                  </h1>
                  <p className="text-sm mb-7" style={{ color: "var(--muted)" }}>
                    {scanDone
                      ? `We've scanned ${trackedHostname}. Your pricing and product intelligence is ready to explore.`
                      : `Scanning ${trackedHostname} — usually 60–90 seconds.`}
                  </p>

                  {/* Scan progress card */}
                  <div
                    className="rounded-xl p-5 mb-6 transition-all duration-500"
                    style={{
                      background: scanDone ? "rgba(34,197,94,.06)" : "var(--bg3)",
                      border: `1px solid ${scanDone ? "rgba(34,197,94,.3)" : "var(--border)"}`,
                    }}
                  >
                    <div className="flex items-center gap-3 mb-4">
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
                          {scanDone ? "Scan complete!" : trackedHostname}
                        </p>
                        <p className="text-xs" style={{ color: "var(--muted)" }}>{scanPhase}</p>
                      </div>
                      <span className="ml-auto text-sm font-semibold tabular-nums" style={{ color: "var(--muted)" }}>
                        {scanProgress}%
                      </span>
                    </div>
                    <div className="h-2 rounded-full overflow-hidden" style={{ background: "rgba(255,255,255,.07)" }}>
                      <div
                        className="h-full rounded-full transition-all duration-700"
                        style={{ width: `${scanProgress}%`, background: scanDone ? "#22c55e" : "var(--green)" }}
                      />
                    </div>
                  </div>

                  {/* Checklist */}
                  {!scanDone && (
                    <div className="mb-6">
                      <p className="text-xs font-semibold uppercase tracking-wider mb-3" style={{ color: "var(--muted)" }}>
                        What's being analyzed
                      </p>
                      <div className="space-y-2">
                        {[
                          { Icon: TrendingDown, label: "Price distribution & median price", doneAt: 52 },
                          { Icon: Package, label: "New product launch velocity", doneAt: 70 },
                          { Icon: Bell, label: "Active discounts & promo rate", doneAt: 84 },
                        ].map(({ Icon, label, doneAt }) => {
                          const done = scanProgress >= doneAt;
                          return (
                            <div key={label} className="flex items-center gap-3 py-1.5">
                              <div
                                className="w-6 h-6 rounded-full flex items-center justify-center shrink-0 transition-all duration-500"
                                style={{
                                  background: done ? "rgba(163,240,0,.14)" : "var(--bg3)",
                                  border: `1px solid ${done ? "var(--green)" : "var(--border)"}`,
                                }}
                              >
                                {done ? (
                                  <CheckCircle2 className="w-3.5 h-3.5" style={{ color: "var(--green)" }} />
                                ) : (
                                  <Icon className="w-3 h-3" style={{ color: "var(--muted)" }} />
                                )}
                              </div>
                              <span className="text-sm transition-colors duration-500" style={{ color: done ? "var(--text)" : "var(--muted)" }}>
                                {label}
                              </span>
                            </div>
                          );
                        })}
                      </div>
                    </div>
                  )}

                  <button
                    onClick={finish}
                    className={cn(
                      "w-full flex items-center justify-center gap-2 font-semibold py-3.5 rounded-xl transition-all",
                      scanDone ? "hover:brightness-110" : "opacity-60 hover:opacity-75 cursor-default"
                    )}
                    style={{
                      background: scanDone ? "var(--green)" : "var(--bg3)",
                      color: scanDone ? "#060d18" : "var(--text)",
                      border: scanDone ? "none" : "1px solid var(--border)",
                    }}
                  >
                    {scanDone ? (
                      <>View intelligence dashboard <ArrowRight className="w-4 h-4" /></>
                    ) : (
                      <>Waiting for scan to complete…</>
                    )}
                  </button>

                  {!scanDone && (
                    <button
                      onClick={finish}
                      className="mt-2 w-full text-sm py-2 rounded-xl hover:bg-white/5 transition-colors"
                      style={{ color: "var(--muted)" }}
                    >
                      Go to dashboard now (scan continues in background)
                    </button>
                  )}
                </>
              )}
            </div>
          )}
        </div>

        {/* Progress dots */}
        <div className="flex items-center gap-2 mt-6">
          {([1, 2, 3, 4] as const).map((s) => (
            <div
              key={s}
              className="rounded-full transition-all duration-500"
              style={{
                width: s === step ? 20 : 6,
                height: 6,
                background: s <= step ? "var(--green)" : "rgba(255,255,255,.14)",
              }}
            />
          ))}
        </div>
      </div>
    </div>
  );
}
