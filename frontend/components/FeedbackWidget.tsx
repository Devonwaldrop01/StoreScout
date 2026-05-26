"use client";

import { useState, useEffect } from "react";
import { MessageSquare, X, Send, Star, Check } from "lucide-react";
import { feedback as feedbackApi } from "@/lib/api";
import { usePathname } from "next/navigation";

const STORAGE_KEY = "ss_feedback_submitted";

export function FeedbackWidget() {
  const [open, setOpen]           = useState(false);
  const [rating, setRating]       = useState(0);
  const [hover, setHover]         = useState(0);
  const [message, setMessage]     = useState("");
  const [allowTestimonial, setAllowTestimonial] = useState(false);
  const [submitting, setSubmitting] = useState(false);
  const [done, setDone]           = useState(false);
  const [error, setError]         = useState("");
  const [alreadySubmitted, setAlreadySubmitted] = useState(false);
  const pathname = usePathname();

  useEffect(() => {
    if (typeof window !== "undefined") {
      setAlreadySubmitted(!!localStorage.getItem(STORAGE_KEY));
    }
  }, []);

  async function handleSubmit(e: React.FormEvent) {
    e.preventDefault();
    if (rating === 0) { setError("Please select a rating."); return; }
    if (message.trim().length < 5) { setError("Please write a bit more."); return; }
    setError("");
    setSubmitting(true);
    try {
      await feedbackApi.submit({
        rating,
        message: message.trim(),
        allow_testimonial: allowTestimonial,
        page: pathname,
      });
      setDone(true);
      if (typeof window !== "undefined") localStorage.setItem(STORAGE_KEY, "1");
    } catch {
      setError("Something went wrong — please try again.");
    } finally {
      setSubmitting(false);
    }
  }

  function handleClose() {
    setOpen(false);
    // Reset state after animation
    setTimeout(() => {
      if (!done) {
        setRating(0);
        setHover(0);
        setMessage("");
        setAllowTestimonial(false);
        setError("");
      }
    }, 300);
  }

  const activeStars = hover || rating;

  return (
    <>
      {/* Floating trigger button */}
      <button
        onClick={() => setOpen(true)}
        className="fixed bottom-6 right-6 z-40 flex items-center gap-2 px-3.5 py-2.5 rounded-full font-medium text-xs shadow-lg transition-all hover:scale-105 active:scale-95"
        style={{
          background: "var(--bg-card)",
          border: "1px solid var(--border)",
          color: "var(--muted)",
          boxShadow: "0 4px 24px rgba(0,0,0,.4)",
        }}
        aria-label="Leave feedback"
      >
        <MessageSquare className="w-3.5 h-3.5" />
        Feedback
      </button>

      {/* Overlay */}
      {open && (
        <div
          className="fixed inset-0 z-50 flex items-end sm:items-center justify-center sm:justify-end p-4 sm:p-6"
          onClick={(e) => e.target === e.currentTarget && handleClose()}
          style={{ background: "rgba(0,0,0,.5)" }}
        >
          <div
            className="w-full sm:w-96 rounded-2xl overflow-hidden fade-up"
            style={{
              background: "var(--bg-card)",
              border: "1px solid var(--border)",
              boxShadow: "0 24px 80px rgba(0,0,0,.6)",
            }}
          >
            {/* Header */}
            <div
              className="flex items-center justify-between px-5 py-4"
              style={{ borderBottom: "1px solid var(--border)" }}
            >
              <div className="flex items-center gap-2">
                <MessageSquare className="w-4 h-4" style={{ color: "var(--accent)" }} />
                <span className="font-semibold text-sm" style={{ color: "var(--text)" }}>
                  Share your feedback
                </span>
              </div>
              <button
                onClick={handleClose}
                className="p-1 rounded-lg hover:bg-white/10 transition-colors"
                style={{ color: "var(--muted)" }}
              >
                <X className="w-4 h-4" />
              </button>
            </div>

            {done ? (
              /* Success state */
              <div className="px-5 py-10 text-center">
                <div
                  className="w-12 h-12 rounded-full flex items-center justify-center mx-auto mb-4"
                  style={{ background: "rgba(168,255,0,.12)", border: "1px solid rgba(168,255,0,.25)" }}
                >
                  <Check className="w-6 h-6" style={{ color: "var(--accent)" }} />
                </div>
                <h3 className="font-bold text-base mb-1.5" style={{ color: "var(--text)" }}>
                  Thanks for the feedback!
                </h3>
                <p className="text-sm leading-relaxed" style={{ color: "var(--muted)" }}>
                  {allowTestimonial
                    ? "We may feature your review on our site. We really appreciate it."
                    : "Your thoughts help us build a better product."}
                </p>
                <button
                  onClick={handleClose}
                  className="mt-5 text-xs font-medium px-4 py-2 rounded-lg hover:bg-white/5 transition-colors"
                  style={{ color: "var(--muted)", border: "1px solid var(--border)" }}
                >
                  Close
                </button>
              </div>
            ) : (
              /* Form */
              <form onSubmit={handleSubmit} className="px-5 py-5 space-y-4">
                {/* Rating */}
                <div>
                  <p className="text-xs font-semibold mb-2.5" style={{ color: "var(--muted)" }}>
                    How would you rate StoreScout?
                  </p>
                  <div className="flex gap-1.5">
                    {[1, 2, 3, 4, 5].map((s) => (
                      <button
                        key={s}
                        type="button"
                        onClick={() => setRating(s)}
                        onMouseEnter={() => setHover(s)}
                        onMouseLeave={() => setHover(0)}
                        className="transition-transform hover:scale-110 active:scale-95"
                      >
                        <Star
                          className="w-7 h-7"
                          style={{
                            color: s <= activeStars ? "#facc15" : "var(--border)",
                            fill: s <= activeStars ? "#facc15" : "transparent",
                            transition: "color .1s, fill .1s",
                          }}
                        />
                      </button>
                    ))}
                  </div>
                </div>

                {/* Message */}
                <div>
                  <label className="text-xs font-semibold mb-1.5 block" style={{ color: "var(--muted)" }}>
                    What&apos;s on your mind?
                  </label>
                  <textarea
                    value={message}
                    onChange={(e) => setMessage(e.target.value)}
                    placeholder="What's working, what's not, what would make you tell a friend about this..."
                    rows={4}
                    className="w-full rounded-xl px-3.5 py-3 text-sm resize-none outline-none transition-colors"
                    style={{
                      background: "var(--bg3)",
                      border: "1px solid var(--border)",
                      color: "var(--text)",
                    }}
                    onFocus={(e) => { e.target.style.borderColor = "rgba(168,255,0,.35)"; }}
                    onBlur={(e) => { e.target.style.borderColor = "var(--border)"; }}
                  />
                  <div className="flex justify-end mt-1">
                    <span className="text-[11px]" style={{ color: "var(--muted)", opacity: 0.5 }}>
                      {message.length}/2000
                    </span>
                  </div>
                </div>

                {/* Testimonial opt-in */}
                <label className="flex items-start gap-3 cursor-pointer group">
                  <div className="relative mt-0.5 shrink-0">
                    <input
                      type="checkbox"
                      checked={allowTestimonial}
                      onChange={(e) => setAllowTestimonial(e.target.checked)}
                      className="sr-only"
                    />
                    <div
                      className="w-4 h-4 rounded flex items-center justify-center transition-colors"
                      style={{
                        background: allowTestimonial ? "var(--accent)" : "var(--bg3)",
                        border: `1px solid ${allowTestimonial ? "var(--accent)" : "var(--border)"}`,
                      }}
                    >
                      {allowTestimonial && <Check className="w-2.5 h-2.5" style={{ color: "#0a0a0f" }} />}
                    </div>
                  </div>
                  <span className="text-xs leading-relaxed" style={{ color: "var(--muted)" }}>
                    It&apos;s okay to feature my review on the StoreScout website
                  </span>
                </label>

                {error && (
                  <p className="text-xs" style={{ color: "#f87171" }}>{error}</p>
                )}

                <button
                  type="submit"
                  disabled={submitting || alreadySubmitted}
                  className="w-full flex items-center justify-center gap-2 py-2.5 rounded-xl font-semibold text-sm transition-all hover:brightness-110 disabled:opacity-50 disabled:cursor-not-allowed"
                  style={{ background: "var(--accent)", color: "#0a0a0f" }}
                >
                  {submitting ? (
                    <span className="animate-pulse">Sending…</span>
                  ) : alreadySubmitted ? (
                    <>
                      <Check className="w-4 h-4" />
                      Already submitted
                    </>
                  ) : (
                    <>
                      <Send className="w-4 h-4" />
                      Send feedback
                    </>
                  )}
                </button>

                <p className="text-[11px] text-center" style={{ color: "var(--muted)", opacity: 0.5 }}>
                  Your feedback goes directly to the founder.
                </p>
              </form>
            )}
          </div>
        </div>
      )}
    </>
  );
}
