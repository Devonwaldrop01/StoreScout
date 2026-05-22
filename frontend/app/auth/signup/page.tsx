"use client";

import { useState } from "react";
import Link from "next/link";
import { useRouter } from "next/navigation";
import { Zap, CheckCircle2 } from "lucide-react";
import { createClient } from "@/lib/supabase/client";
import { user as userApi } from "@/lib/api";

export default function SignupPage() {
  const router = useRouter();
  const supabase = createClient();
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [loading, setLoading] = useState(false);
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
              disabled={loading}
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
