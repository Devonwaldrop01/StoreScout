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
      <div className="min-h-screen flex items-center justify-center p-4" style={{ background: "var(--bg)" }}>
        <div className="text-center max-w-sm">
          <CheckCircle2 className="w-12 h-12 mx-auto mb-4 text-green-400" />
          <h2 className="text-xl font-bold mb-2" style={{ color: "var(--text)" }}>Check your email</h2>
          <p style={{ color: "var(--muted)" }}>
            We&apos;ve sent a confirmation link to <strong>{email}</strong>. Click it to activate your account and set up your first competitor.
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

  return (
    <div className="min-h-screen flex items-center justify-center p-4" style={{ background: "var(--bg)" }}>
      <div className="w-full max-w-sm">
        <div className="flex items-center justify-center gap-2 mb-8">
          <Zap className="w-6 h-6" style={{ color: "#a3f000" }} />
          <span className="text-xl font-bold" style={{ color: "var(--text)" }}>StoreScout</span>
        </div>

        <div className="rounded-2xl p-7" style={{ background: "var(--bg2)", border: "1px solid var(--border)" }}>
          <h1 className="text-xl font-bold mb-1 text-center" style={{ color: "var(--text)" }}>Start for free</h1>
          <p className="text-sm text-center mb-5" style={{ color: "var(--muted)" }}>No credit card required</p>

          <ul className="grid grid-cols-2 gap-2 mb-6">
            {features.map((f) => (
              <li key={f} className="flex items-center gap-1.5 text-xs" style={{ color: "#a3f000" }}>
                <span>✓</span>
                <span style={{ color: "var(--muted)" }}>{f}</span>
              </li>
            ))}
          </ul>

          {/* Google */}
          <button
            type="button"
            onClick={handleGoogleSignup}
            disabled={googleLoading || loading}
            className="w-full flex items-center justify-center gap-3 py-3 rounded-xl font-medium text-sm mb-4 transition-all hover:opacity-90 disabled:opacity-50"
            style={{ background: "var(--bg3)", border: "1px solid var(--border)", color: "var(--text)" }}
          >
            {googleLoading ? (
              <div className="w-5 h-5 border-2 border-t-transparent rounded-full animate-spin" style={{ borderColor: "var(--muted)" }} />
            ) : (
              <GoogleIcon />
            )}
            Continue with Google
          </button>

          <div className="flex items-center gap-3 mb-4">
            <div className="flex-1 h-px" style={{ background: "var(--border)" }} />
            <span className="text-xs" style={{ color: "var(--muted)" }}>or</span>
            <div className="flex-1 h-px" style={{ background: "var(--border)" }} />
          </div>

          <form onSubmit={handleSubmit} className="space-y-4">
            <div>
              <label className="block text-sm font-medium mb-1.5" style={{ color: "var(--muted)" }}>Email</label>
              <input
                type="email"
                value={email}
                onChange={(e) => setEmail(e.target.value)}
                required
                placeholder="you@yourstore.com"
                className="w-full px-4 py-3 rounded-xl text-sm outline-none"
                style={{ background: "var(--bg3)", border: "1px solid var(--border)", color: "var(--text)" }}
              />
            </div>
            <div>
              <label className="block text-sm font-medium mb-1.5" style={{ color: "var(--muted)" }}>Password</label>
              <input
                type="password"
                value={password}
                onChange={(e) => setPassword(e.target.value)}
                required
                minLength={8}
                placeholder="Min. 8 characters"
                className="w-full px-4 py-3 rounded-xl text-sm outline-none"
                style={{ background: "var(--bg3)", border: "1px solid var(--border)", color: "var(--text)" }}
              />
            </div>

            {error && (
              <p className="text-sm text-red-400 text-center">{error}</p>
            )}

            <button
              type="submit"
              disabled={loading || googleLoading}
              className="w-full font-semibold py-3 rounded-xl transition-all hover:brightness-110 disabled:opacity-50"
              style={{ background: "#a3f000", color: "#060d18" }}
            >
              {loading ? "Creating account…" : "Create free account"}
            </button>
          </form>

          <p className="text-sm text-center mt-5" style={{ color: "var(--muted)" }}>
            Already have an account?{" "}
            <Link href="/auth/login" className="hover:underline" style={{ color: "#a3f000" }}>
              Sign in
            </Link>
          </p>
        </div>
      </div>
    </div>
  );
}
