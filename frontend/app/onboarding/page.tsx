"use client";

import { useEffect, useRef, useState, Suspense } from "react";
import { useRouter, useSearchParams } from "next/navigation";
import {
  Zap, CheckCircle2, AlertCircle, AlertTriangle, ArrowRight,
  Search, TrendingDown, Bell, Package, Sparkles,
} from "lucide-react";
import { createClient } from "@/lib/supabase/client";
import { competitors as competitorsApi, user as userApi, ensureProvisioned, type AIDiscoverySuggestion } from "@/lib/api";
import { cn } from "@/lib/utils";
import { track } from "@/lib/analytics";

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

// Brand descriptors — feed direct-competitor matching + personalization.
const BRAND_TRAITS = [
  "Premium", "Luxury", "Budget", "Value", "Sustainable", "Handmade",
  "Performance", "Minimalist", "Bold", "Classic", "Playful", "Tech-forward",
] as const;

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
    accent: "#FFB224",
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
    accent: "#7DB8C9",
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

const STEP_LABELS: Record<Step, string> = {
  1: "About you",
  2: "Find competitors",
  3: "Choose plan",
  4: "First scan",
};

function OnboardingContent() {
  const router = useRouter();
  const searchParams = useSearchParams();
  const supabase = createClient();

  const [authChecked, setAuthChecked] = useState(false);
  const [provisionFailed, setProvisionFailed] = useState(false);
  const [retryNonce, setRetryNonce] = useState(0);
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
  const [name, setName] = useState("");
  const [category, setCategory] = useState<Category>("");
  const [goalId, setGoalId] = useState<GoalId>("");
  const [priceRange, setPriceRange] = useState<"" | "budget" | "mid" | "premium" | "luxury">("");
  const [sells, setSells] = useState("");
  const [brandTraits, setBrandTraits] = useState<string[]>([]);
  const [notes, setNotes] = useState("");
  const [quickAdding, setQuickAdding] = useState<string | null>(null); // url being quick-added

  // Whether they skipped the competitor step without adding one
  const [skipped, setSkipped] = useState(false);

  // Personalized discovery — kicked off from the business answers so the
  // competitor step is already populated with verified, relevant Shopify stores.
  const [discovering, setDiscovering] = useState(false);
  const [discovery, setDiscovery] = useState<AIDiscoverySuggestion | null>(null);
  const [discoveryError, setDiscoveryError] = useState("");

  function buildDescription(): string {
    return [
      sells.trim() ? sells.trim() : (category && `Sells ${category}`),
      brandTraits.length > 0 && `${brandTraits.join(", ")} brand`,
      priceRange && `${priceRange} pricing`,
      notes.trim() && notes.trim(),
    ].filter(Boolean).join(". ");
  }

  async function runDiscovery() {
    const desc = buildDescription();
    if (!desc || discovering) return;
    setDiscovering(true);
    setDiscoveryError("");
    setDiscovery(null);
    try {
      const r = await competitorsApi.discoverAI(desc);
      setDiscovery(r.data);
    } catch {
      // Non-fatal — the curated category picks and manual URL still work.
      setDiscoveryError("Couldn't auto-find competitors — pick from the suggestions below or paste a URL.");
    } finally {
      setDiscovering(false);
    }
  }

  async function handleTrackDiscovered(domain: string) {
    setQuickAdding(domain);
    try {
      const { data } = await competitorsApi.add(normalizeUrl(domain));
      setNewCompetitorId(data.id);
      setTrackedHostname(data.hostname || domain);
      setSkipped(false);
      setStep(3);
    } catch (err: unknown) {
      const apiErr = err as { data?: { detail?: string | { code?: string } } };
      const detail = apiErr?.data?.detail;
      setAddError(typeof detail === "string" ? detail : "Couldn't track that store — try another.");
    } finally {
      setQuickAdding(null);
    }
  }

  // Step 3 — plan
  const [selectedPlan, setSelectedPlan] = useState<"free" | "pro" | "agency">("pro");

  // Step 4 — scan polling. Real, evidence-based stages (no fake percentage).
  const [scanDone, setScanDone] = useState(false);
  const [scanStage, setScanStage] = useState<"queued" | "scanning" | "analyzing" | "complete" | "failed" | "timed_out">("queued");
  const [scanTimedOut, setScanTimedOut] = useState(false);

  const checkTimerRef = useRef<ReturnType<typeof setTimeout> | null>(null);
  const pollCountRef = useRef(0);

  // Auth guard
  useEffect(() => {
    async function check() {
      const { data: { session } } = await supabase.auth.getSession();
      if (!session) { router.replace("/auth/login"); return; }
      // Pre-fill name from OAuth metadata (editable — onboarding value wins)
      const meta = session.user.user_metadata ?? {};
      const existingName = (meta.display_name || meta.full_name || meta.name) as string | undefined;
      if (existingName) setName(existingName);
      // Provisioning is REQUIRED — never continue onboarding with an unknown
      // account state. Idempotent + concurrency-safe server-side. On failure,
      // block with a retry panel instead of silently proceeding.
      const provisioned = await ensureProvisioned();
      if (!provisioned) {
        setProvisionFailed(true);
        setAuthChecked(true);
        return;
      }
      try {
        const result = await competitorsApi.list();
        if ((result.data || []).length > 0) { router.replace("/dashboard"); return; }
      } catch {}
      // New user reaching onboarding (0 competitors) = a completed signup.
      // Guard so it fires at most once per browser.
      try {
        if (!localStorage.getItem("ss_signup_tracked")) {
          track("signup_completed", { provider: session.user.app_metadata?.provider ?? "email" });
          localStorage.setItem("ss_signup_tracked", "1");
        }
      } catch {}
      // Pre-fill competitor URL if coming from a shared report
      const prefilledCompetitor = searchParams.get("competitor");
      if (prefilledCompetitor) {
        const normalized = prefilledCompetitor.startsWith("https://")
          ? prefilledCompetitor
          : prefilledCompetitor.startsWith("http://")
          ? prefilledCompetitor.replace("http://", "https://")
          : `https://${prefilledCompetitor}`;
        setUrl(normalized);
      }
      // Pre-select plan if forwarded from landing page CTA
      const planParam = searchParams.get("plan");
      if (planParam === "free" || planParam === "pro" || planParam === "agency") {
        setSelectedPlan(planParam);
      }
      setAuthChecked(true);
    }
    check();
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [router, supabase, retryNonce]);

  // Real scan lifecycle — drives evidence-based stages from the normalized
  // scan-status endpoint (queued → scanning → analyzing → complete), never a
  // simulated percentage. Bounded (~3 min) and cleaned up on unmount. An escape
  // hatch to the dashboard appears after 40s so the scan is never a dead-end.
  useEffect(() => {
    if (!newCompetitorId || scanDone) return;
    pollCountRef.current = 0;
    setScanTimedOut(false);
    setScanStage("queued");
    let cancelled = false;
    const escape = setTimeout(() => setScanTimedOut(true), 40000);
    const poll = setInterval(async () => {
      pollCountRef.current += 1;
      if (pollCountRef.current > 60) {   // ~3 min ceiling — no infinite loading
        clearInterval(poll);
        setScanStage("timed_out");
        setScanTimedOut(true);
        return;
      }
      try {
        const st = await competitorsApi.scanStatus(newCompetitorId);
        if (cancelled) return;
        const s = st.data.state;
        if (s === "failed") { setScanStage("failed"); clearInterval(poll); return; }
        if (s === "timed_out") { setScanStage("timed_out"); setScanTimedOut(true); clearInterval(poll); return; }
        if (s === "queued") { setScanStage("queued"); return; }
        if (s === "running") { setScanStage("scanning"); return; }
        // scan_status is done → confirm the analysis (snapshot) is actually written
        try {
          await competitorsApi.latestSnapshot(newCompetitorId);
          if (cancelled) return;
          setScanStage("complete");
          setScanDone(true);
          track("first_scan_completed", { competitor_id: newCompetitorId });
          clearInterval(poll);
          clearTimeout(escape);
        } catch {
          if (!cancelled) setScanStage("analyzing"); // scan done, analysis still writing
        }
      } catch { /* transient — keep polling up to the ceiling */ }
    }, 3000);
    return () => { cancelled = true; clearInterval(poll); clearTimeout(escape); };
  }, [newCompetitorId, scanDone]);

  // Retry a failed / timed-out first scan — preserves the selected competitor.
  async function retryFirstScan() {
    if (!newCompetitorId) return;
    setScanTimedOut(false);
    setScanDone(false);
    setScanStage("queued");
    pollCountRef.current = 0;
    try { await competitorsApi.rescan(newCompetitorId); } catch { /* the poll reflects real state */ }
  }

  const SCAN_STAGE_LABEL: Record<typeof scanStage, string> = {
    queued: "Queued — waiting for a worker…",
    scanning: "Scanning the store…",
    analyzing: "Analyzing catalog, pricing & launches…",
    complete: "Intelligence ready",
    failed: "Scan failed",
    timed_out: "Scan is taking longer than usual",
  };

  function normalizeUrl(raw: string): string {
    const s = raw.trim();
    if (s.startsWith("https://")) return s;
    if (s.startsWith("http://")) return s.replace("http://", "https://");
    return `https://${s}`;
  }

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
      const { data } = await competitorsApi.add(normalizeUrl(url));
      setNewCompetitorId(data.id);
      setTrackedHostname(data.hostname || normalizeUrl(url).replace(/^https?:\/\//, "").replace(/\/$/, ""));
      setSkipped(false);
      setStep(3);
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
      const { data } = await competitorsApi.add(normalizeUrl(storeUrl));
      setNewCompetitorId(data.id);
      setTrackedHostname(data.hostname || storeName);
      setUrl(storeUrl);
      setSkipped(false);
      setStep(3); // Jump straight to plan selection, scan runs in background
    } catch (err: unknown) {
      const apiErr = err as { data?: { detail?: string | { code?: string } } };
      const detail = apiErr?.data?.detail;
      // On error, pre-fill the URL field so they can retry from the same step
      setUrl(storeUrl);
      if (typeof detail === "string") setAddError(detail);
    } finally {
      setQuickAdding(null);
    }
  }

  function handleSkip() {
    setSkipped(true);
    setNewCompetitorId("");
    setTrackedHostname("");
    setStep(3);
  }

  function finish() {
    // First scan done → walk through what we discovered before the dashboard.
    // The reveal page carries the plan through to the upgrade modal.
    if (newCompetitorId && scanDone) {
      router.push(
        selectedPlan !== "free"
          ? `/onboarding/reveal/${newCompetitorId}?plan=${selectedPlan}`
          : `/onboarding/reveal/${newCompetitorId}`
      );
      return;
    }
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

  // Required provisioning failed — block here with a retry instead of entering
  // onboarding with a half-initialized account.
  if (provisionFailed) {
    return (
      <div className="min-h-screen flex items-center justify-center px-6" style={{ background: "var(--bg)" }}>
        <div className="max-w-sm text-center rounded-lg p-6" style={{ background: "var(--bg-card)", border: "1px solid var(--border)" }}>
          <p className="text-sm font-semibold mb-2" style={{ color: "var(--text)" }}>We couldn&apos;t finish setting up your account</p>
          <p className="text-[13px] leading-relaxed mb-4" style={{ color: "var(--text-2)" }}>
            This is usually temporary. Retry to complete setup — your progress is safe.
          </p>
          <button
            onClick={() => { setProvisionFailed(false); setAuthChecked(false); setRetryNonce((n) => n + 1); }}
            className="text-sm font-semibold px-4 py-2 rounded-md"
            style={{ background: "var(--accent)", color: "var(--ink)" }}
          >
            Retry setup
          </button>
        </div>
      </div>
    );
  }

  const urlBorderColor =
    storeStatus === "ok" ? "var(--emerald)"
    : storeStatus === "restricted" ? "var(--amber)"
    : storeStatus === "error" ? "#F2555A"
    : "var(--border)";

  const categorySuggestions = category ? SUGGESTED_STORES[category] : [];

  return (
    <div className="min-h-screen flex flex-col" style={{ background: "var(--bg)" }}>
      {/* Nav */}
      <header className="flex items-center justify-between px-6 py-5">
        <div className="flex items-center gap-2">
          <div style={{ width: "24px", height: "24px", borderRadius: "6px", background: "var(--accent)", display: "flex", alignItems: "center", justifyContent: "center" }}>
            <Zap style={{ width: "12px", height: "12px", color: "var(--ink)" }} />
          </div>
          <span className="font-bold text-sm" style={{ color: "var(--text)" }}>StoreScout</span>
        </div>
        <div className="flex items-center gap-1.5">
          {([1, 2, 3, 4] as const).map((s) => (
            <div
              key={s}
              className="rounded-full transition-all duration-500"
              style={{
                width: s === step ? 16 : 6,
                height: 6,
                background: s <= step ? "var(--accent)" : "rgba(255,255,255,.12)",
              }}
            />
          ))}
        </div>
      </header>

      {/* Main content */}
      <div className="flex-1 flex flex-col items-center justify-center px-4 py-10">
        <div
          className="w-full max-w-lg rounded-md p-7 shadow-xl"
          style={{ background: "var(--bg2)", border: "1px solid var(--border)" }}
        >

          {/* ─── Step 1: About your business (personalizes discovery) ─── */}
          {step === 1 && (
            <div>
              <p className="tick-label mb-2">Step 01 / 04</p>
              <h1 className="text-2xl font-bold mb-2" style={{ color: "var(--text)" }}>
                Tell us about your business
              </h1>
              <p className="text-sm mb-7" style={{ color: "var(--muted)" }}>
                Four quick answers — StoreScout uses them to find your direct competitors and personalize everything you see next.
              </p>

              <div className="space-y-7">
                <div>
                  <p className="text-sm font-semibold mb-3" style={{ color: "var(--text)" }}>
                    What should we call you?
                  </p>
                  <input
                    type="text"
                    value={name}
                    onChange={(e) => setName(e.target.value)}
                    placeholder="Your first name"
                    autoComplete="given-name"
                    className="w-full px-4 py-3 rounded-md text-sm transition-all outline-none"
                    style={{ background: "var(--bg3)", border: "1px solid var(--border)", color: "var(--text)" }}
                  />
                </div>

                <div>
                  <p className="text-sm font-semibold mb-3" style={{ color: "var(--text)" }}>
                    What do you sell? <span className="font-normal" style={{ color: "var(--muted)" }}>(required)</span>
                  </p>
                  <input
                    value={sells}
                    onChange={(e) => setSells(e.target.value)}
                    placeholder="Be specific — e.g. premium golf apparel, organic dog treats, handmade jewelry"
                    className="w-full mb-3 px-4 py-2.5 rounded-md text-sm outline-none"
                    style={{ background: "var(--bg3)", border: "1px solid var(--border)", color: "var(--text)" }}
                  />
                  <p className="text-[11px] mb-2" style={{ color: "var(--muted)" }}>…and the closest category:</p>
                  <div className="grid grid-cols-2 gap-2 sm:grid-cols-3">
                    {CATEGORIES.map((c) => (
                      <button
                        key={c}
                        type="button"
                        onClick={() => setCategory(c)}
                        className="px-3 py-2.5 rounded-md text-xs font-medium transition-all text-left"
                        style={{
                          background: category === c ? "rgba(255,178,36,.1)" : "var(--bg3)",
                          border: `1px solid ${category === c ? "rgba(255,178,36,.5)" : "var(--border)"}`,
                          color: category === c ? "var(--accent)" : "var(--muted)",
                        }}
                      >
                        {c}
                      </button>
                    ))}
                  </div>
                </div>

                <div>
                  <p className="text-sm font-semibold mb-3" style={{ color: "var(--text)" }}>
                    Where do you price?
                  </p>
                  <div className="grid grid-cols-2 sm:grid-cols-4 gap-2">
                    {([
                      { v: "budget", l: "Budget" },
                      { v: "mid", l: "Mid-market" },
                      { v: "premium", l: "Premium" },
                      { v: "luxury", l: "Luxury" },
                    ] as const).map((pr) => (
                      <button
                        key={pr.v}
                        type="button"
                        onClick={() => setPriceRange(pr.v)}
                        className="px-3 py-2 rounded-md text-sm font-medium transition-all"
                        style={{
                          background: priceRange === pr.v ? "rgba(255,178,36,.1)" : "var(--bg3)",
                          border: `1px solid ${priceRange === pr.v ? "rgba(255,178,36,.5)" : "var(--border)"}`,
                          color: priceRange === pr.v ? "var(--accent)" : "var(--muted)",
                        }}
                      >
                        {pr.l}
                      </button>
                    ))}
                  </div>
                </div>

                <div>
                  <p className="text-sm font-semibold mb-2" style={{ color: "var(--text)" }}>
                    How would you describe your brand? <span className="font-normal" style={{ color: "var(--muted)" }}>(pick any)</span>
                  </p>
                  <div className="flex flex-wrap gap-2">
                    {BRAND_TRAITS.map((t) => {
                      const on = brandTraits.includes(t);
                      return (
                        <button
                          key={t}
                          type="button"
                          onClick={() => setBrandTraits((prev) => on ? prev.filter((x) => x !== t) : [...prev, t])}
                          className="px-3 py-1.5 rounded-full text-xs font-medium transition-all"
                          style={{
                            background: on ? "rgba(255,178,36,.12)" : "var(--bg3)",
                            border: `1px solid ${on ? "rgba(255,178,36,.5)" : "var(--border)"}`,
                            color: on ? "var(--accent)" : "var(--muted)",
                          }}
                        >
                          {t}
                        </button>
                      );
                    })}
                  </div>
                </div>

                <div>
                  <p className="text-sm font-semibold mb-2" style={{ color: "var(--text)" }}>
                    Anything else we should know? <span className="font-normal" style={{ color: "var(--muted)" }}>(optional)</span>
                  </p>
                  <textarea
                    value={notes}
                    onChange={(e) => setNotes(e.target.value)}
                    rows={2}
                    placeholder="e.g. we sell orthopedic dog beds for older large dogs with joint issues"
                    className="w-full px-4 py-2.5 rounded-md text-sm outline-none resize-none"
                    style={{ background: "var(--bg3)", border: "1px solid var(--border)", color: "var(--text)" }}
                  />
                </div>

                <div>
                  <p className="text-sm font-semibold mb-3" style={{ color: "var(--text)" }}>
                    What&apos;s your primary intel goal? <span className="font-normal" style={{ color: "var(--muted)" }}>(required)</span>
                  </p>
                  <div className="space-y-2">
                    {GOALS.map((g) => {
                      const selected = goalId === g.id;
                      return (
                        <button
                          key={g.id}
                          type="button"
                          onClick={() => setGoalId(g.id)}
                          className="w-full flex items-start gap-3 px-4 py-3 rounded-md transition-all text-left"
                          style={{
                            background: selected ? "rgba(255,178,36,.07)" : "var(--bg3)",
                            border: `1px solid ${selected ? "rgba(255,178,36,.5)" : "var(--border)"}`,
                          }}
                        >
                          <div
                            className="w-4 h-4 rounded-full border-2 mt-0.5 shrink-0 flex items-center justify-center transition-all"
                            style={{
                              borderColor: selected ? "var(--accent)" : "var(--border)",
                              background: selected ? "var(--accent)" : "transparent",
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
                onClick={() => {
                  const trimmed = name.trim();
                  if (trimmed) {
                    supabase.auth.updateUser({ data: { display_name: trimmed } }).catch(() => {});
                  }
                  // Persist the profile — personalizes dashboard, Playbook, vs-You, and AI.
                  userApi.saveBusinessProfile({
                    category: category || undefined,
                    price_range: priceRange || undefined,
                    primary_goal: goalId || undefined,
                    sells: sells.trim() || undefined,
                    brand_traits: brandTraits.length ? brandTraits : undefined,
                    notes: notes.trim() || undefined,
                  }).catch(() => {});
                  // Kick discovery now so the competitor step is already personalized.
                  runDiscovery();
                  setStep(2);
                }}
                disabled={!category || !goalId}
                className={cn(
                  "mt-8 w-full flex items-center justify-center gap-2 font-semibold py-3.5 rounded-md transition-all",
                  !category || !goalId ? "opacity-40 cursor-not-allowed" : "hover:opacity-90"
                )}
                style={{ background: "var(--accent)", color: "var(--ink)" }}
              >
                Find my competitors <ArrowRight className="w-4 h-4" />
              </button>
            </div>
          )}

          {/* ─── Step 2: Personalized competitor discovery + track ─── */}
          {step === 2 && (
            <div>
              <p className="tick-label mb-2">Step 02 / 04</p>
              <h1 className="text-2xl font-bold mb-2" style={{ color: "var(--text)" }}>
                Your competitors{category ? ` in ${category}` : ""}
              </h1>
              <p className="text-sm mb-6" style={{ color: "var(--muted)" }}>
                Verified Shopify stores matched to what you sell. Track one to start — you can add more anytime.
              </p>

              {/* Discovery running — personalized to their answers */}
              {discovering && (
                <div className="mb-5 px-4 py-4 rounded-md analyzing-sweep flex items-center gap-3" style={{ background: "var(--bg-card)", border: "1px solid var(--border)" }}>
                  <div className="w-4 h-4 border-2 border-t-transparent rounded-full animate-spin shrink-0" style={{ borderColor: "var(--accent)" }} />
                  <div>
                    <p className="text-sm font-semibold" style={{ color: "var(--text)" }}>Finding verified {category || "Shopify"} competitors…</p>
                    <p className="text-xs" style={{ color: "var(--muted)" }}>Mapping your market and verifying each store — about a minute. Pick a suggestion below in the meantime.</p>
                  </div>
                </div>
              )}

              {/* Personalized verified results */}
              {discovery && discovery.suggestions.length > 0 && (
                <div className="mb-5">
                  <p className="tick-label mb-2">Matched to your business — {discovery.suggestions.length}</p>
                  <div className="space-y-2">
                    {discovery.suggestions.map((sug) => (
                      <button
                        key={sug.domain}
                        type="button"
                        onClick={() => handleTrackDiscovered(sug.domain)}
                        disabled={quickAdding !== null}
                        className="w-full flex items-center justify-between gap-3 px-4 py-3 rounded-md text-left transition-all hover:border-white/20 disabled:opacity-50"
                        style={{ background: "var(--bg3)", border: "1px solid var(--border)" }}
                      >
                        <div className="min-w-0">
                          <div className="flex items-center gap-2">
                            <p className="text-sm font-mono font-semibold truncate" style={{ color: "var(--text)" }}>{sug.domain}</p>
                            {typeof sug.confidence === "number" && (
                              <span className="text-[9px] font-bold px-1.5 py-0.5 rounded shrink-0" style={{ background: "rgba(76,195,138,.1)", color: "#4CC38A", border: "1px solid rgba(76,195,138,.2)" }}>
                                {sug.confidence}% Shopify
                              </span>
                            )}
                          </div>
                          <p className="text-xs truncate mt-0.5" style={{ color: "var(--muted)" }}>{sug.reason}</p>
                        </div>
                        {quickAdding === sug.domain
                          ? <div className="w-3.5 h-3.5 border-2 border-t-transparent rounded-full animate-spin shrink-0" style={{ borderColor: "var(--accent)" }} />
                          : <span className="text-xs font-semibold shrink-0" style={{ color: "var(--accent)" }}>Track →</span>}
                      </button>
                    ))}
                  </div>
                </div>
              )}

              {/* Curated picks — instant + fallback when AI is still running or empty */}
              {(discovering || (discovery && discovery.suggestions.length === 0) || discoveryError) && categorySuggestions.length > 0 && (
                <div className="mb-5">
                  <p className="tick-label mb-2">Popular {category} stores</p>
                  <div className="grid grid-cols-2 gap-2">
                    {categorySuggestions.map((store) => (
                      <button
                        key={store.url}
                        type="button"
                        onClick={() => handleQuickAdd(store.url, store.name)}
                        disabled={quickAdding !== null}
                        className="flex items-center justify-between px-3 py-2.5 rounded-md text-left transition-all hover:border-white/20 disabled:opacity-50"
                        style={{ background: "var(--bg3)", border: "1px solid var(--border)" }}
                      >
                        <div className="min-w-0">
                          <p className="text-xs font-semibold truncate" style={{ color: "var(--text)" }}>{store.name}</p>
                          <p className="text-xs truncate" style={{ color: "var(--muted)" }}>{store.tag}</p>
                        </div>
                        {quickAdding === store.url
                          ? <div className="w-3.5 h-3.5 border-2 border-t-transparent rounded-full animate-spin ml-2 shrink-0" style={{ borderColor: "var(--green)" }} />
                          : <ArrowRight className="w-3.5 h-3.5 ml-2 shrink-0 opacity-40" style={{ color: "var(--green)" }} />}
                      </button>
                    ))}
                  </div>
                </div>
              )}

              {discoveryError && (
                <p className="text-xs mb-4" style={{ color: "var(--muted)" }}>{discoveryError}</p>
              )}

              {/* Know exactly who to track? Paste any Shopify URL */}
              <div className="rounded-md p-4 mb-4" style={{ background: "var(--bg-card)", border: "1px solid var(--border)" }}>
                <p className="text-sm font-semibold mb-2" style={{ color: "var(--text)" }}>Know exactly who to track?</p>
                <form onSubmit={handleAddCompetitor} className="flex gap-2">
                  <input
                    type="text"
                    value={url}
                    onChange={handleUrlChange}
                    placeholder="paste any Shopify store URL"
                    className="flex-1 px-3 py-2.5 rounded-md text-sm font-mono outline-none"
                    style={{ background: "var(--bg3)", border: `1px solid ${urlBorderColor}`, color: "var(--text)" }}
                  />
                  <button
                    type="submit"
                    disabled={submitting || !url.trim() || storeStatus === "error" || checking}
                    className="font-semibold text-sm px-4 py-2.5 rounded-md transition-all hover:brightness-110 disabled:opacity-50 shrink-0"
                    style={{ background: "var(--accent)", color: "var(--ink)" }}
                  >
                    {submitting ? "…" : "Track"}
                  </button>
                </form>
                {storeStatus === "error" && <p className="text-xs mt-1.5" style={{ color: "#F2555A" }}>{storeError}</p>}
                {addError && <p className="text-xs mt-1.5" style={{ color: "#F2555A" }}>{addError}</p>}
              </div>

              <div className="flex items-center justify-between">
                <button
                  onClick={() => setStep(1)}
                  className="text-sm py-2 hover:opacity-80 transition-opacity"
                  style={{ color: "var(--muted)" }}
                >
                  ← Back
                </button>
                <button
                  onClick={handleSkip}
                  className="text-sm py-2 hover:opacity-80 transition-opacity"
                  style={{ color: "var(--muted)" }}
                >
                  Skip for now →
                </button>
              </div>
            </div>
          )}

          {/* ─── Step 3: Plan selection ─── */}
          {step === 3 && (
            <div>
              {newCompetitorId && (
                <div
                  className="flex items-center gap-2 px-3 py-2 rounded-lg mb-6"
                  style={{ background: "rgba(255,178,36,.07)", border: "1px solid rgba(255,178,36,.15)" }}
                >
                  <div className="w-2 h-2 rounded-full animate-pulse shrink-0" style={{ background: scanDone ? "var(--emerald)" : "var(--green)" }} />
                  <p className="text-xs font-medium" style={{ color: "var(--green)" }}>
                    {scanDone ? `Scan complete — ${trackedHostname}` : `${SCAN_STAGE_LABEL[scanStage]} — ${trackedHostname}`}
                  </p>
                </div>
              )}

              <p className="tick-label mb-2">Step 03 / 04</p>
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
                      className="w-full text-left rounded-md p-4 transition-all"
                      style={{
                        background: selected
                          ? plan.id === "pro"
                            ? "rgba(255,178,36,.07)"
                            : plan.id === "agency"
                            ? "rgba(125,184,201,.07)"
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
                                style={{ background: plan.id === "free" ? "var(--bg)" : "#0B0C0A" }}
                              />
                            )}
                          </div>
                          <span className="font-bold text-sm" style={{ color: "var(--text)" }}>
                            {plan.label}
                          </span>
                          {plan.recommended && (
                            <span
                              className="text-xs px-2 py-0.5 rounded-full font-semibold"
                              style={{ background: "rgba(255,178,36,.14)", color: "var(--green)" }}
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
                className="w-full flex items-center justify-center gap-2 font-semibold py-3.5 rounded-md hover:opacity-90 transition-all"
                style={{ background: "var(--accent)", color: "var(--ink)" }}
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
              <p className="tick-label mb-2">Step 04 / 04</p>

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
                    className="rounded-md p-5 mb-6"
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
                    className="w-full flex items-center justify-center gap-2 font-semibold py-3.5 rounded-md hover:opacity-90 transition-all"
                    style={{ background: "var(--accent)", color: "var(--ink)" }}
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

                  {/* Scan progress card — the scanline motif earns its keep here */}
                  <div
                    className={cn("rounded-md p-5 mb-6 transition-all duration-500", !scanDone && "scan-shimmer")}
                    style={{
                      background: scanDone ? "rgba(76,195,138,.06)" : "var(--bg3)",
                      border: `1px solid ${scanDone ? "rgba(76,195,138,.3)" : "rgba(255,178,36,.25)"}`,
                    }}
                  >
                    <div className="flex items-center gap-3 mb-4">
                      {scanDone ? (
                        <CheckCircle2 className="w-5 h-5 shrink-0 text-green-400" />
                      ) : (
                        <div
                          className="w-5 h-5 border-2 border-t-transparent rounded-full animate-spin shrink-0"
                          style={{ borderColor: "var(--accent)" }}
                        />
                      )}
                      <div className="min-w-0">
                        <p className="num text-sm font-semibold" style={{ color: scanDone ? "var(--emerald)" : "var(--text)" }}>
                          {scanDone ? "Scan complete!" : trackedHostname}
                        </p>
                        <p className="text-xs" style={{ color: "var(--muted)" }}>{SCAN_STAGE_LABEL[scanStage]}</p>
                      </div>
                    </div>
                    {/* Real stage indicator — indeterminate while working, solid
                        green when complete. No fabricated percentage. */}
                    <div className="h-2 rounded-full overflow-hidden" style={{ background: "rgba(255,255,255,.07)" }}>
                      {scanDone ? (
                        <div className="h-full rounded-full" style={{ width: "100%", background: "var(--emerald)" }} />
                      ) : scanStage === "failed" || scanStage === "timed_out" ? (
                        <div className="h-full rounded-full" style={{ width: "100%", background: "#F2555A", opacity: .5 }} />
                      ) : (
                        <div className="h-full rounded-full scan-shimmer" style={{ width: "100%", background: "var(--accent)", opacity: .5 }} />
                      )}
                    </div>
                    {(scanStage === "failed" || scanStage === "timed_out") && (
                      <button
                        onClick={retryFirstScan}
                        className="mt-3 text-xs font-semibold px-3 py-1.5 rounded-md"
                        style={{ background: "var(--accent)", color: "var(--ink)" }}
                      >
                        Retry scan
                      </button>
                    )}
                  </div>

                  {/* Checklist */}
                  {!scanDone && (
                    <div className="mb-6">
                      <p className="text-xs font-semibold uppercase tracking-wider mb-3" style={{ color: "var(--muted)" }}>
                        What's being analyzed
                      </p>
                      <div className="space-y-2">
                        {[
                          { Icon: TrendingDown, label: "Price distribution & median price" },
                          { Icon: Package, label: "New product launch velocity" },
                          { Icon: Bell, label: "Active discounts & promo rate" },
                        ].map(({ Icon, label }) => {
                          const done = scanStage === "complete";
                          return (
                            <div key={label} className="flex items-center gap-3 py-1.5">
                              <div
                                className="w-6 h-6 rounded-full flex items-center justify-center shrink-0 transition-all duration-500"
                                style={{
                                  background: done ? "rgba(255,178,36,.14)" : "var(--bg3)",
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
                      "w-full flex items-center justify-center gap-2 font-semibold py-3.5 rounded-md transition-all",
                      scanDone ? "hover:brightness-110" : "opacity-60 hover:opacity-75 cursor-default"
                    )}
                    style={{
                      background: scanDone ? "var(--accent)" : "var(--bg3)",
                      color: scanDone ? "#fff" : "var(--text)",
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
                      className="mt-2 w-full text-sm py-2 rounded-md hover:bg-white/5 transition-colors"
                      style={{ color: scanTimedOut ? "var(--text)" : "var(--muted)" }}
                    >
                      {scanTimedOut
                        ? "Scan is taking longer than usual — continue to dashboard"
                        : "Go to dashboard now (scan continues in background)"}
                    </button>
                  )}
                </>
              )}
            </div>
          )}
        </div>

      </div>
    </div>
  );
}

export default function OnboardingPage() {
  return (
    <Suspense fallback={null}>
      <OnboardingContent />
    </Suspense>
  );
}
