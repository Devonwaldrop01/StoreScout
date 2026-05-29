"use client";

import { useState } from "react";
import Link from "next/link";
import { Zap, CheckCircle2, AlertCircle, Mail } from "lucide-react";
import { createClient } from "@/lib/supabase/client";

export default function ForgotPasswordPage() {
  const supabase = createClient();
  const [email, setEmail] = useState("");
  const [loading, setLoading] = useState(false);
  const [done, setDone] = useState(false);
  const [error, setError] = useState("");
  const [focusedField, setFocusedField] = useState<string | null>(null);

  async function handleSubmit(e: React.FormEvent) {
    e.preventDefault();
    setLoading(true);
    setError("");
    const { error: err } = await supabase.auth.resetPasswordForEmail(email, {
      redirectTo: `${window.location.origin}/auth/reset-password`,
    });
    if (err) {
      setError(err.message);
      setLoading(false);
    } else {
      setDone(true);
      setLoading(false);
    }
  }

  const inputStyle = (field: string) => ({
    background: "var(--bg3)",
    border: `1px solid ${focusedField === field ? "rgba(59,130,246,.4)" : "var(--border)"}`,
    color: "var(--text)",
    boxShadow: focusedField === field ? "0 0 0 3px rgba(59,130,246,.08)" : "none",
    outline: "none",
    transition: "border-color 0.15s, box-shadow 0.15s",
  });

  return (
    <div className="relative min-h-screen flex items-center justify-center p-4" style={{ background: "var(--bg)" }}>
      {/* Ambient glows */}
      <div className="fixed pointer-events-none" style={{ top: "-80px", left: "-80px", width: "400px", height: "400px", borderRadius: "50%", background: "rgba(59,130,246,.06)", filter: "blur(80px)", zIndex: 0 }} />
      <div className="fixed pointer-events-none" style={{ top: "-60px", right: "-60px", width: "300px", height: "300px", borderRadius: "50%", background: "rgba(96,165,250,.04)", filter: "blur(80px)", zIndex: 0 }} />
      <div className="fixed pointer-events-none" style={{ bottom: "-80px", left: "50%", transform: "translateX(-50%)", width: "350px", height: "350px", borderRadius: "50%", background: "rgba(59,130,246,.04)", filter: "blur(80px)", zIndex: 0 }} />

      <div className="relative w-full max-w-sm" style={{ zIndex: 1 }}>
        {/* Logo */}
        <div className="flex items-center justify-center gap-3 mb-8">
          <div style={{ width: "32px", height: "32px", borderRadius: "12px", background: "var(--accent)", boxShadow: "0 0 20px rgba(59,130,246,.4)", display: "flex", alignItems: "center", justifyContent: "center", flexShrink: 0 }}>
            <Zap style={{ width: "16px", height: "16px", color: "#ffffff" }} />
          </div>
          <span className="text-xl font-bold" style={{ color: "var(--text)" }}>StoreScout</span>
        </div>

        {done ? (
          <div
            className="rounded-2xl p-10 text-center"
            style={{ background: "var(--bg2)", border: "1px solid var(--border)", boxShadow: "0 24px 80px rgba(0,0,0,.5)" }}
          >
            <div className="mx-auto mb-5 flex items-center justify-center" style={{ width: "56px", height: "56px", borderRadius: "50%", background: "rgba(59,130,246,.1)" }}>
              <Mail style={{ width: "28px", height: "28px", color: "var(--accent)" }} />
            </div>
            <h2 className="text-xl font-bold mb-2" style={{ color: "var(--text)" }}>Check your email</h2>
            <p className="text-sm" style={{ color: "var(--muted)" }}>
              We&apos;ve sent a reset link to{" "}
              <strong style={{ color: "var(--text)" }}>{email}</strong>.
              {" "}Check your spam folder if it doesn&apos;t arrive within a minute.
            </p>
            <div className="mt-6 flex flex-col gap-2">
              <Link
                href="/auth/login"
                className="block w-full py-2.5 rounded-xl text-sm font-semibold text-center transition-all hover:brightness-110"
                style={{ background: "var(--accent)", color: "#ffffff" }}
              >
                Back to sign in
              </Link>
              <button
                onClick={() => { setDone(false); setEmail(""); }}
                className="text-sm hover:underline"
                style={{ color: "var(--muted)" }}
              >
                Try a different email
              </button>
            </div>
          </div>
        ) : (
          <div className="rounded-2xl p-7" style={{ background: "var(--bg2)", border: "1px solid var(--border)", boxShadow: "0 24px 80px rgba(0,0,0,.5)" }}>
            <h1 className="text-xl font-bold mb-2 text-center" style={{ color: "var(--text)" }}>Reset your password</h1>
            <p className="text-sm text-center mb-6" style={{ color: "var(--muted)" }}>
              Enter your email and we&apos;ll send you a reset link.
            </p>

            <form onSubmit={handleSubmit} className="space-y-4">
              <div>
                <label className="block text-sm font-medium mb-1.5" style={{ color: "var(--muted)" }}>Email</label>
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

              {error && (
                <div className="flex items-center gap-2 px-4 py-3 rounded-xl text-sm" style={{ background: "rgba(239,68,68,.1)", border: "1px solid rgba(239,68,68,.2)", color: "#f87171" }}>
                  <AlertCircle className="w-4 h-4 flex-shrink-0" />
                  {error}
                </div>
              )}

              <button
                type="submit"
                disabled={loading}
                className="w-full font-semibold py-3 rounded-xl transition-all hover:brightness-110 disabled:opacity-50"
                style={{ background: "var(--accent)", color: "#ffffff" }}
              >
                {loading ? "Sending…" : "Send reset link"}
              </button>
            </form>

            <p className="text-sm text-center mt-5" style={{ color: "var(--muted)" }}>
              <Link href="/auth/login" className="hover:underline" style={{ color: "var(--accent)" }}>
                Back to sign in
              </Link>
            </p>
          </div>
        )}
      </div>
    </div>
  );
}
