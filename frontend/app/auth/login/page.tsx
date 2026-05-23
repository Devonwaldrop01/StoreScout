"use client";

import { useState } from "react";
import Link from "next/link";
import { useRouter } from "next/navigation";
import { Zap } from "lucide-react";
import { createClient } from "@/lib/supabase/client";

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

export default function LoginPage() {
  const router = useRouter();
  const supabase = createClient();
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [loading, setLoading] = useState(false);
  const [googleLoading, setGoogleLoading] = useState(false);
  const [error, setError] = useState("");

  async function handleSubmit(e: React.FormEvent) {
    e.preventDefault();
    setLoading(true);
    setError("");
    const { error: err } = await supabase.auth.signInWithPassword({ email, password });
    if (err) {
      setError(err.message);
      setLoading(false);
    } else {
      router.push("/dashboard");
    }
  }

  async function handleGoogleLogin() {
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
    // On success, browser redirects to Google — no further action needed here
  }

  return (
    <div className="min-h-screen flex items-center justify-center p-4" style={{ background: "var(--bg)" }}>
      <div className="w-full max-w-sm">
        <div className="flex items-center justify-center gap-2 mb-8">
          <Zap className="w-6 h-6" style={{ color: "#a3f000" }} />
          <span className="text-xl font-bold" style={{ color: "var(--text)" }}>StoreScout</span>
        </div>

        <div className="rounded-2xl p-7" style={{ background: "var(--bg2)", border: "1px solid var(--border)" }}>
          <h1 className="text-xl font-bold mb-6 text-center" style={{ color: "var(--text)" }}>Welcome back</h1>

          {/* Google */}
          <button
            type="button"
            onClick={handleGoogleLogin}
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
                className="w-full px-4 py-3 rounded-xl text-sm outline-none"
                style={{ background: "var(--bg3)", border: "1px solid var(--border)", color: "var(--text)" }}
              />
            </div>
            <div>
              <div className="flex items-center justify-between mb-1.5">
                <label className="text-sm font-medium" style={{ color: "var(--muted)" }}>Password</label>
                <Link href="/auth/forgot-password" className="text-xs hover:underline" style={{ color: "var(--muted)" }}>
                  Forgot password?
                </Link>
              </div>
              <input
                type="password"
                value={password}
                onChange={(e) => setPassword(e.target.value)}
                required
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
              {loading ? "Signing in…" : "Sign in"}
            </button>
          </form>

          <p className="text-sm text-center mt-5" style={{ color: "var(--muted)" }}>
            Don&apos;t have an account?{" "}
            <Link href="/auth/signup" className="hover:underline" style={{ color: "#a3f000" }}>
              Sign up free
            </Link>
          </p>
        </div>
      </div>
    </div>
  );
}
