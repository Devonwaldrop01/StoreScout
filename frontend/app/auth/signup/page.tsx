"use client";

import { useState, Suspense } from "react";
import Link from "next/link";
import { useRouter, useSearchParams } from "next/navigation";
import { Zap, Eye, EyeOff, CheckCircle2, AlertCircle, Check } from "lucide-react";
import { createClient } from "@/lib/supabase/client";
import { user as userApi } from "@/lib/api";

function GoogleIcon() {
  return (
    <svg className="w-5 h-5" viewBox="0 0 24 24" fill="none">
      <path d="M22.56 12.25c0-.78-.07-1.53-.2-2.25H12v4.26h5.92c-.26 1.37-1.04 2.53-2.21 3.31v2.77h3.57c2.08-1.92 3.28-4.74 3.28-8.09z" fill="#4285F4"/>
      <path d="M12 23c2.97 0 5.46-.98 7.28-2.66l-3.57-2.77c-.98.66-2.23 1.06-3.71 1.06-2.86 0-5.29-1.93-6.16-4.53H2.18v2.84C3.99 20.53 7.7 23 12 23z" fill="#34A853"/>
      <path d="M5.84 14.09c-.22-.66-.35-1.36-.35-2.09s.13-1.43.35-2.09V7.07H2.18C1.43 8.55 1 10.22 1 12s.43 3.45 1.18 4.93l3.66-2.84z" fill="#FBBC05"/>
      <path d="M12 5.38c1.62 0 3.06.56 4.21 1.64l3.15-3.15C17.45 2.09 14.97 1 12 1 7.7 1 3.99 3.47 2.18 7.07l3.66 2.84c.87-2.6 3.3-4.53 6.16-4.53z" fill="#EA4335"/>
    </svg>
  );
}

const BENEFITS = [
  "Track any Shopify competitor in minutes",
  "Alerts when they change prices or launch products",
  "Weekly AI-generated competitive digest",
  "No credit card required to start",
];

function BrandPanel() {
  return (
    <div className="hidden lg:flex flex-col justify-between p-10 w-[400px] shrink-0 border-r"
         style={{ background: "var(--bg2)", borderColor: "var(--border)" }}>
      <div>
        <div className="flex items-center gap-2.5 mb-12">
          <div style={{ width: "30px", height: "30px", borderRadius: "8px", background: "var(--accent)", display: "flex", alignItems: "center", justifyContent: "center", flexShrink: 0 }}>
            <Zap style={{ width: "15px", height: "15px", color: "#fff" }} />
          </div>
          <span className="text-base font-bold" style={{ color: "var(--text)" }}>StoreScout</span>
        </div>

        <h2 className="text-2xl font-bold mb-3 leading-snug" style={{ color: "var(--text)" }}>
          Always know what your competitors are doing
        </h2>
        <p className="text-sm mb-8" style={{ color: "var(--muted)" }}>
          Monitor pricing, product launches, and discount campaigns across any Shopify store — automatically.
        </p>

        <ul className="space-y-3">
          {BENEFITS.map((b) => (
            <li key={b} className="flex items-start gap-3">
              <div className="mt-0.5 flex-shrink-0 w-4 h-4 rounded-full flex items-center justify-center" style={{ background: "rgba(34,197,94,.15)" }}>
                <Check style={{ width: "10px", height: "10px", color: "var(--emerald)" }} />
              </div>
              <span className="text-sm" style={{ color: "var(--text-2)" }}>{b}</span>
            </li>
          ))}
        </ul>
      </div>

      <p className="text-xs" style={{ color: "var(--muted)" }}>
        Trusted by Shopify DTC operators tracking 1,000+ stores
      </p>
    </div>
  );
}

function SignupContent() {
  const router = useRouter();
  const searchParams = useSearchParams();
  const supabase = createClient();
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [showPassword, setShowPassword] = useState(false);
  const [loading, setLoading] = useState(false);
  const [googleLoading, setGoogleLoading] = useState(false);
  const [error, setError] = useState("");
  const [done, setDone] = useState(false);
  const [focusedField, setFocusedField] = useState<string | null>(null);

  async function handleSubmit(e: React.FormEvent) {
    e.preventDefault();
    setLoading(true);
    setError("");

    const plan = searchParams.get("plan");
    const onboardingPath = plan ? `/onboarding?plan=${encodeURIComponent(plan)}` : "/onboarding";

    const { data, error: err } = await supabase.auth.signUp({
      email,
      password,
      options: { emailRedirectTo: `${window.location.origin}/auth/callback?next=${encodeURIComponent(onboardingPath)}` },
    });
    if (err) {
      setError(err.message);
      setLoading(false);
      return;
    }

    if (data.session) {
      await userApi.provision().catch(() => {});
      router.push(onboardingPath);
    } else {
      setDone(true);
      setLoading(false);
    }
  }

  async function handleGoogleSignup() {
    setGoogleLoading(true);
    setError("");
    const plan = searchParams.get("plan");
    const onboardingPath = plan ? `/onboarding?plan=${encodeURIComponent(plan)}` : "/onboarding";
    const { error: err } = await supabase.auth.signInWithOAuth({
      provider: "google",
      options: { redirectTo: `${window.location.origin}/auth/callback?next=${encodeURIComponent(onboardingPath)}` },
    });
    if (err) {
      setError(err.message);
      setGoogleLoading(false);
    }
  }

  const inputStyle = (field: string) => ({
    background: "var(--bg3)",
    border: `1px solid ${focusedField === field ? "rgba(59,130,246,.5)" : "var(--border)"}`,
    color: "var(--text)",
    boxShadow: focusedField === field ? "0 0 0 3px rgba(59,130,246,.08)" : "none",
    outline: "none",
    transition: "border-color 0.15s, box-shadow 0.15s",
  });

  if (done) {
    return (
      <div className="min-h-screen flex" style={{ background: "var(--bg)" }}>
        <BrandPanel />
        <div className="flex-1 flex items-center justify-center p-6">
          <div className="w-full max-w-sm text-center p-10 rounded-2xl"
               style={{ background: "var(--bg-card)", border: "1px solid var(--border)" }}>
            <div className="mx-auto mb-5 w-12 h-12 rounded-full flex items-center justify-center"
                 style={{ background: "rgba(59,130,246,.1)" }}>
              <CheckCircle2 style={{ width: "24px", height: "24px", color: "var(--accent)" }} />
            </div>
            <h2 className="text-xl font-bold mb-2" style={{ color: "var(--text)" }}>Check your email</h2>
            <p className="text-sm" style={{ color: "var(--muted)" }}>
              We&apos;ve sent a confirmation link to{" "}
              <strong style={{ color: "var(--text)" }}>{email}</strong>. Click it to activate your account.
            </p>
            <p className="text-xs mt-5" style={{ color: "var(--muted)" }}>
              Wrong email?{" "}
              <button onClick={() => setDone(false)} className="hover:underline" style={{ color: "var(--accent)" }}>
                Go back
              </button>
            </p>
          </div>
        </div>
      </div>
    );
  }

  return (
    <div className="min-h-screen flex" style={{ background: "var(--bg)" }}>
      <BrandPanel />

      <div className="flex-1 flex items-center justify-center p-6">
        <div className="w-full max-w-sm">
          {/* Mobile logo */}
          <div className="flex items-center gap-2.5 mb-8 lg:hidden">
            <div style={{ width: "28px", height: "28px", borderRadius: "8px", background: "var(--accent)", display: "flex", alignItems: "center", justifyContent: "center", flexShrink: 0 }}>
              <Zap style={{ width: "14px", height: "14px", color: "#fff" }} />
            </div>
            <span className="text-base font-bold" style={{ color: "var(--text)" }}>StoreScout</span>
          </div>

          <h1 className="text-2xl font-bold mb-1" style={{ color: "var(--text)" }}>Create your account</h1>
          <p className="text-sm mb-7" style={{ color: "var(--muted)" }}>Free to start — no credit card required</p>

          {/* Google */}
          <button
            type="button"
            onClick={handleGoogleSignup}
            disabled={googleLoading || loading}
            className="w-full flex items-center justify-center gap-3 py-3 rounded-xl font-medium text-sm mb-4 transition-all disabled:opacity-50"
            style={{ background: "var(--bg3)", border: "1px solid var(--border)", color: "var(--text)" }}
            onMouseEnter={(e) => (e.currentTarget.style.borderColor = "rgba(255,255,255,.15)")}
            onMouseLeave={(e) => (e.currentTarget.style.borderColor = "var(--border)")}
          >
            {googleLoading ? (
              <div className="w-5 h-5 border-2 border-t-transparent rounded-full animate-spin" style={{ borderColor: "var(--muted)" }} />
            ) : (
              <GoogleIcon />
            )}
            Continue with Google
          </button>

          <div className="flex items-center gap-3 mb-5">
            <div className="flex-1 h-px" style={{ background: "var(--border)" }} />
            <span className="text-xs" style={{ color: "var(--muted)" }}>or</span>
            <div className="flex-1 h-px" style={{ background: "var(--border)" }} />
          </div>

          <form onSubmit={handleSubmit} className="space-y-4">
            <div>
              <label className="block text-sm font-medium mb-1.5" style={{ color: "var(--text-2)" }}>Email</label>
              <input
                type="email"
                value={email}
                onChange={(e) => setEmail(e.target.value)}
                required
                autoFocus
                placeholder="you@yourstore.com"
                className="w-full px-4 py-3 rounded-xl text-sm"
                style={inputStyle("email")}
                onFocus={() => setFocusedField("email")}
                onBlur={() => setFocusedField(null)}
              />
            </div>

            <div>
              <label className="block text-sm font-medium mb-1.5" style={{ color: "var(--text-2)" }}>Password</label>
              <div className="relative">
                <input
                  type={showPassword ? "text" : "password"}
                  value={password}
                  onChange={(e) => setPassword(e.target.value)}
                  required
                  minLength={8}
                  placeholder="Min. 8 characters"
                  className="w-full px-4 py-3 pr-11 rounded-xl text-sm"
                  style={inputStyle("password")}
                  onFocus={() => setFocusedField("password")}
                  onBlur={() => setFocusedField(null)}
                />
                <button
                  type="button"
                  onClick={() => setShowPassword((v) => !v)}
                  className="absolute right-3 top-1/2 -translate-y-1/2 p-1 rounded"
                  style={{ color: "var(--muted)" }}
                  tabIndex={-1}
                >
                  {showPassword ? <EyeOff className="w-4 h-4" /> : <Eye className="w-4 h-4" />}
                </button>
              </div>
            </div>

            {error && (
              <div className="flex items-center gap-2 px-4 py-3 rounded-xl text-sm" style={{ background: "rgba(239,68,68,.08)", border: "1px solid rgba(239,68,68,.2)", color: "#f87171" }}>
                <AlertCircle className="w-4 h-4 flex-shrink-0" />
                {error}
              </div>
            )}

            <button
              type="submit"
              disabled={loading || googleLoading}
              className="w-full font-semibold py-3 rounded-xl transition-all disabled:opacity-50"
              style={{ background: "var(--accent)", color: "#fff" }}
              onMouseEnter={(e) => (e.currentTarget.style.opacity = "0.9")}
              onMouseLeave={(e) => (e.currentTarget.style.opacity = "1")}
            >
              {loading ? "Creating account…" : "Create free account"}
            </button>
          </form>

          <p className="text-sm text-center mt-6" style={{ color: "var(--muted)" }}>
            Already have an account?{" "}
            <Link href="/auth/login" className="hover:underline" style={{ color: "var(--accent)" }}>
              Sign in
            </Link>
          </p>
        </div>
      </div>
    </div>
  );
}

export default function SignupPage() {
  return (
    <Suspense fallback={null}>
      <SignupContent />
    </Suspense>
  );
}
