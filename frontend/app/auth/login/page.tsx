"use client";

import { useState } from "react";
import Link from "next/link";
import { useRouter } from "next/navigation";
import { Zap } from "lucide-react";
import { createClient } from "@/lib/supabase/client";

export default function LoginPage() {
  const router = useRouter();
  const supabase = createClient();
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [loading, setLoading] = useState(false);
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

  return (
    <div className="min-h-screen flex items-center justify-center p-4" style={{ background: "var(--bg)" }}>
      <div className="w-full max-w-sm">
        <div className="flex items-center justify-center gap-2 mb-8">
          <Zap className="w-6 h-6" style={{ color: "#a3f000" }} />
          <span className="text-xl font-bold" style={{ color: "var(--text)" }}>StoreScout</span>
        </div>

        <div className="rounded-2xl p-7" style={{ background: "var(--bg2)", border: "1px solid var(--border)" }}>
          <h1 className="text-xl font-bold mb-6 text-center" style={{ color: "var(--text)" }}>Welcome back</h1>

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
              <label className="block text-sm font-medium mb-1.5" style={{ color: "var(--muted)" }}>Password</label>
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
              disabled={loading}
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
