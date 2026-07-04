"use client";

import { useEffect, useState, use } from "react";
import { useRouter } from "next/navigation";
import Link from "next/link";
import { Users, Loader2, CheckCircle, XCircle } from "lucide-react";
import { team, type InviteDetails } from "@/lib/api";
import { createClient } from "@/lib/supabase/client";

export default function InvitePage({ params }: { params: Promise<{ token: string }> }) {
  const { token } = use(params);
  const router = useRouter();

  const [invite, setInvite] = useState<InviteDetails | null>(null);
  const [inviteError, setInviteError] = useState("");
  const [session, setSession] = useState<{ email?: string } | null>(null);
  const [accepting, setAccepting] = useState(false);
  const [accepted, setAccepted] = useState(false);
  const [acceptError, setAcceptError] = useState("");
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    async function init() {
      // Fetch invite details (public endpoint, no auth needed)
      try {
        const { data } = await team.getInvite(token);
        setInvite(data);
      } catch {
        setInviteError("This invite link is invalid, expired, or has already been used.");
      }

      // Check if user is already signed in
      const supabase = createClient();
      const { data: sessionData } = await supabase.auth.getSession();
      if (sessionData.session?.user) {
        setSession({ email: sessionData.session.user.email });
      }

      setLoading(false);
    }
    init();
  }, [token]);

  async function handleAccept() {
    setAccepting(true);
    setAcceptError("");
    try {
      await team.accept(token);
      setAccepted(true);
      setTimeout(() => router.push("/dashboard"), 2500);
    } catch (err: unknown) {
      const e = err as { data?: { detail?: string } };
      setAcceptError(e?.data?.detail || "Could not accept invite. Make sure you're signed in with the correct email.");
    } finally {
      setAccepting(false);
    }
  }

  if (loading) {
    return (
      <div className="min-h-screen flex items-center justify-center" style={{ background: "#0B0C0A" }}>
        <Loader2 className="w-6 h-6 animate-spin" style={{ color: "#FFB224" }} />
      </div>
    );
  }

  return (
    <div className="min-h-screen flex flex-col items-center justify-center px-4" style={{ background: "#0B0C0A" }}>
      <div className="mb-8">
        <span style={{ color: "#FFB224", fontWeight: 700, fontSize: 18 }}>StoreScout</span>
      </div>

      <div
        className="w-full max-w-md rounded-2xl p-8"
        style={{ background: "#161814", border: "1px solid #1e3a5f" }}
      >
        {inviteError ? (
          <div className="text-center">
            <XCircle className="w-10 h-10 mx-auto mb-4" style={{ color: "#F2555A" }} />
            <h1 className="text-lg font-bold mb-2" style={{ color: "#ECEEE6" }}>Invite unavailable</h1>
            <p className="text-sm" style={{ color: "#6b7fa3" }}>{inviteError}</p>
            <Link href="/" className="inline-block mt-6 text-sm font-medium hover:underline" style={{ color: "#FFB224" }}>
              Go to StoreScout →
            </Link>
          </div>
        ) : accepted ? (
          <div className="text-center">
            <CheckCircle className="w-10 h-10 mx-auto mb-4" style={{ color: "#FFB224" }} />
            <h1 className="text-lg font-bold mb-2" style={{ color: "#ECEEE6" }}>You&apos;re in!</h1>
            <p className="text-sm" style={{ color: "#6b7fa3" }}>Redirecting to the dashboard…</p>
          </div>
        ) : (
          <>
            <div className="flex items-center gap-3 mb-6">
              <div
                className="w-10 h-10 rounded-xl flex items-center justify-center shrink-0"
                style={{ background: "rgba(255,178,36,.1)", border: "1px solid rgba(255,178,36,.2)" }}
              >
                <Users className="w-5 h-5" style={{ color: "#FFB224" }} />
              </div>
              <div>
                <h1 className="font-bold text-base" style={{ color: "#ECEEE6" }}>Team invite</h1>
                <p className="text-xs" style={{ color: "#6b7fa3" }}>StoreScout</p>
              </div>
            </div>

            <p className="text-sm leading-relaxed mb-2" style={{ color: "#A8AC9E" }}>
              <strong style={{ color: "#ECEEE6" }}>{invite?.owner_email}</strong> has invited you
              to access their competitor intelligence dashboard.
            </p>
            <p className="text-sm mb-6" style={{ color: "#6b7fa3" }}>
              This invite is for <strong style={{ color: "#A8AC9E" }}>{invite?.invited_email}</strong>.
            </p>

            {session ? (
              session.email?.toLowerCase() === invite?.invited_email.toLowerCase() ? (
                <>
                  <button
                    onClick={handleAccept}
                    disabled={accepting}
                    className="w-full flex items-center justify-center gap-2 font-bold py-3 rounded-xl transition-all hover:brightness-110 disabled:opacity-60"
                    style={{ background: "#FFB224", color: "#0B0C0A" }}
                  >
                    {accepting ? <Loader2 className="w-4 h-4 animate-spin" /> : null}
                    Accept invite
                  </button>
                  {acceptError && (
                    <p className="text-xs mt-3 text-center" style={{ color: "#F2555A" }}>{acceptError}</p>
                  )}
                </>
              ) : (
                <div className="rounded-xl p-4 text-sm" style={{ background: "rgba(242,85,90,.08)", border: "1px solid rgba(242,85,90,.2)" }}>
                  <p style={{ color: "#F7999C" }}>
                    You&apos;re signed in as <strong>{session.email}</strong>, but this invite is for{" "}
                    <strong>{invite?.invited_email}</strong>.
                  </p>
                  <p className="mt-2" style={{ color: "#6b7fa3" }}>
                    Sign out and sign in with the correct email to accept.
                  </p>
                </div>
              )
            ) : (
              <div className="space-y-3">
                <p className="text-sm mb-4" style={{ color: "#6b7fa3" }}>
                  Sign in or create an account with <strong style={{ color: "#A8AC9E" }}>{invite?.invited_email}</strong> to accept.
                </p>
                <Link
                  href={`/auth/sign-in?redirect=/invite/${token}`}
                  className="block w-full text-center font-bold py-3 rounded-xl transition-all hover:brightness-110"
                  style={{ background: "#FFB224", color: "#0B0C0A" }}
                >
                  Sign in
                </Link>
                <Link
                  href={`/auth/sign-up?redirect=/invite/${token}`}
                  className="block w-full text-center font-semibold py-3 rounded-xl transition-all hover:bg-white/5"
                  style={{ border: "1px solid #1e3a5f", color: "#A8AC9E" }}
                >
                  Create account
                </Link>
              </div>
            )}
          </>
        )}
      </div>
    </div>
  );
}
