"use client";

import { useState } from "react";
import Link from "next/link";
import { useRouter } from "next/navigation";
import { Zap, CheckCircle2 } from "lucide-react";
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

export default function SignupPage() {
  const router = useRouter();
  const supabase = createClient();
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [loading, setLoading] = useState(false);
  const [googleLoading, setGoogleLoading] = useState(false);
  const [error, setError] = useState("");
  const [done, setDone] = useState(false);
  const [focusedField, setFocusedField] = useState<string | null>(null);

  async function handleSubmit(e: React.FormEvent) {
    e.preventDefault();
    setLoading(true);
    setError("");

    const { data, error: err } = await supabase.auth.signUp({
      email,
      password,
      options: { emailRedirectTo: `${window.location.origin}/auth/callback` },
    });
    if (err) {
      setError(err.message);
      setLoading(false);
      return;
    }

    // If email confirmation is disabled in Supabase (dev mode), session is immediate
    if (data.session) {
      await userApi.provision().catch(() => {});
      router.push("/onboarding");
    } else {
      setDone(true);
      setLoading(false);
    }
  }

  async function handleGoogleSignup() {
    setGoogleLoading(true);
    setError("");
    const { error: err } = await supabase.auth.signInWithOAuth({
      provider: "google",
      options: {
        redirectTo: `${window.location.origin}/auth/callback`,
      },
    });
    if (err) {
      setError(err.message);
      setGoogleLoading(false);
    }
  }

  if (done) {
    return (
      <div
        className="relative min-h-screen flex items-center justify-center p-4"
        style={{ background: "var(--bg)" }}
      >
        {/* Ambient glows */}
        <div
          className="fixed pointer-events-none"
          style={{
            top: "-80px",
            left: "-80px",
            width: "400px",
            height: "400px",
            borderRadius: "50%",
            background: "rgba(168,255,0,.06)",
            filter: "blur(80px)",
            zIndex: 0,
          }}
        />
        <div
          className="fixed pointer-events-none"
          style={{
            top: "-60px",
            right: "-60px",
            width: "300px",
            height: "300px",
            borderRadius: "50%",
            background: "rgba(96,165,250,.04)",
            filter: "blur(80px)",
            zIndex: 0,
          }}
        />
        <div
          className="fixed pointer-events-none"
          style={{
            bottom: "-80px",
            left: "50%",
            transform: "translateX(-50%)",
            width: "350px",
            height: "350px",
            borderRadius: "50%",
            background: "rgba(167,139,250,.04)",
            filter: "blur(80px)",
            zIndex: 0,
          }}
        />

        <div
          className="relative text-center max-w-sm w-full rounded-2xl p-10"
          style={{
            zIndex: 1,
            background: "var(--bg2)",
            border: "1px solid var(--border)",
            boxShadow: "0 24px 80px rgba(0,0,0,.5)",
          }}
        >
          <div
            className="mx-auto mb-5 flex items-center justify-center"
            style={{
              width: "56px",
              height: "56px",
              borderRadius: "50%",
              background: "rgba(168,255,0,.1)",
            }}
          >
            <CheckCircle2
              style={{ width: "28px", height: "28px", color: "var(--accent)" }}
            />
          </div>
          <h2 className="text-xl font-bold mb-2" style={{ color: "var(--text)" }}>
            Check your email
          </h2>
          <p style={{ color: "var(--muted)" }}>
            We&apos;ve sent a confirmation link to{" "}
            <strong style={{ color: "var(--text)" }}>{email}</strong>. Click it to
            activate your account and set up your first competitor.
          </p>
        </div>
      </div>
    );
  }

  const features = [
    "Track any Shopify competitor",
    "Get alerted on price changes",
    "Weekly AI competitive digest",
    "No credit card required",
  ];

  const inputStyle = (field: string) => ({
    background: "var(--bg3)",
    border: `1px solid ${focusedField === field ? "rgba(168,255,0,.4)" : "var(--border)"}`,
    color: "var(--text)",
    boxShadow: focusedField === field ? "0 0 0 3px rgba(168,255,0,.08)" : "none",
    outline: "none",
    transition: "border-color 0.15s, box-shadow 0.15s",
  });

  return (
    <div
      className="relative min-h-screen flex items-center justify-center p-4"
      style={{ background: "var(--bg)" }}
    >
      {/* Ambient glows */}
      <div
        className="fixed pointer-events-none"
        style={{
          top: "-80px",
          left: "-80px",
          width: "400px",
          height: "400px",
          borderRadius: "50%",
          background: "rgba(168,255,0,.06)",
          filter: "blur(80px)",
          zIndex: 0,
        }}
      />
      <div
        className="fixed pointer-events-none"
        style={{
          top: "-60px",
          right: "-60px",
          width: "300px",
          height: "300px",
          borderRadius: "50%",
          background: "rgba(96,165,250,.04)",
          filter: "blur(80px)",
          zIndex: 0,
        }}
      />
      <div
        className="fixed pointer-events-none"
        style={{
          bottom: "-80px",
          left: "50%",
          transform: "translateX(-50%)",
          width: "350px",
          height: "350px",
          borderRadius: "50%",
          background: "rgba(167,139,250,.04)",
          filter: "blur(80px)",
          zIndex: 0,
        }}
      />

      {/* Content */}
      <div className="relative w-full max-w-sm" style={{ zIndex: 1 }}>
        {/* Logo */}
        <div className="flex items-center justify-center gap-3 mb-5">
          <div
            style={{
              width: "32px",
              height: "32px",
              borderRadius: "12px",
              background: "var(--accent)",
              boxShadow: "0 0 20px rgba(168,255,0,.4)",
              display: "flex",
              alignItems: "center",
              justifyContent: "center",
              flexShrink: 0,
            }}
          >
            <Zap style={{ width: "16px", height: "16px", color: "#0a0a0f" }} />
          </div>
          <span className="text-xl font-bold" style={{ color: "var(--text)" }}>StoreScout</span>
        </div>

        {/* Feature list — outside the card, between logo and card */}
        <ul className="grid grid-cols-2 gap-x-6 gap-y-2 mb-5 px-1">
          {features.map((f) => (
            <li key={f} className="flex items-center gap-1.5">
              <span className="text-xs font-bold" style={{ color: "var(--accent)" }}>✓</span>
              <span className="text-xs" style={{ color: "var(--muted)" }}>{f}</span>
            </li>
          ))}
        </ul>

        {/* Card */}
        <div
          className="rounded-2xl p-7"
          style={{
            background: "var(--bg2)",
            border: "1px solid var(--border)",
            boxShadow: "0 24px 80px rgba(0,0,0,.5)",
          }}
        >
          <h1 className="text-2xl font-bold mb-1 text-center" style={{ color: "var(--text)" }}>
            Start free
          </h1>
          <p className="text-xs text-center mb-6" style={{ color: "var(--muted)" }}>
            No credit card required · Cancel anytime
          </p>

          {/* Google */}
          <button
            type="button"
            onClick={handleGoogleSignup}
            disabled={googleLoading || loading}
            className="w-full flex items-center justify-center gap-3 py-3 rounded-xl font-medium text-sm mb-4 transition-all disabled:opacity-50"
            style={{
              background: "var(--bg3)",
              border: "1px solid var(--border)",
              color: "var(--text)",
            }}
            onMouseEnter={(e) => (e.currentTarget.style.background = "rgba(255,255,255,.06)")}
            onMouseLeave={(e) => (e.currentTarget.style.background = "var(--bg3)")}
          >
            {googleLoading ? (
              <div
                className="w-5 h-5 border-2 border-t-transparent rounded-full animate-spin"
                style={{ borderColor: "var(--muted)" }}
              />
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
              <label className="block text-sm font-medium mb-1.5" style={{ color: "var(--muted)" }}>
                Email
              </label>
              <input
                type="email"
                value={email}
                onChange={(e) => setEmail(e.target.value)}
                required
                placeholder="you@yourstore.com"
                className="w-full px-4 py-3 rounded-xl text-sm"
                style={inputStyle("email")}
                onFocus={() => setFocusedField("email")}
                onBlur={() => setFocusedField(null)}
              />
            </div>
            <div>
              <label className="block text-sm font-medium mb-1.5" style={{ color: "var(--muted)" }}>
                Password
              </label>
              <input
                type="password"
                value={password}
                onChange={(e) => setPassword(e.target.value)}
                required
                minLength={8}
                placeholder="Min. 8 characters"
                className="w-full px-4 py-3 rounded-xl text-sm"
                style={inputStyle("password")}
                onFocus={() => setFocusedField("password")}
                onBlur={() => setFocusedField(null)}
              />
            </div>

            {error && (
              <p className="text-sm text-red-400 text-center">{error}</p>
            )}

            <button
              type="submit"
              disabled={loading || googleLoading}
              className="w-full font-bold py-3 rounded-xl transition-all hover:brightness-110 disabled:opacity-50"
              style={{ background: "var(--accent)", color: "#0a0a0f" }}
            >
              {loading ? "Creating account…" : "Create free account"}
            </button>
          </form>

          <p className="text-sm text-center mt-5" style={{ color: "var(--muted)" }}>
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
