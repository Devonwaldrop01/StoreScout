"use client";

import { useEffect, useState } from "react";
import { feedback as feedbackApi } from "@/lib/api";

interface Testimonial {
  id: string;
  rating: number;
  message: string;
  created_at: string;
  initials: string;
}

/**
 * Real opt-in customer reviews, pulled live from GET /feedback/public
 * (server already filters to rating >= 4 + allow_testimonial). Renders nothing
 * until there are real reviews — we never show placeholder/fake testimonials.
 */
export function Testimonials() {
  const [items, setItems] = useState<Testimonial[] | null>(null);

  useEffect(() => {
    feedbackApi.publicTestimonials()
      .then((r) => setItems(r.data || []))
      .catch(() => setItems([]));
  }, []);

  // Hide the entire section until we have at least one real review.
  if (!items || items.length === 0) return null;

  return (
    <div className="max-w-5xl mx-auto px-6 pb-28">
      <div className="text-center mb-12">
        <h2 className="text-3xl font-black mb-3" style={{ color: "var(--text)", letterSpacing: "-0.03em" }}>
          What operators say
        </h2>
        <p className="text-sm" style={{ color: "var(--muted)" }}>From real StoreScout users</p>
      </div>
      <div className="grid md:grid-cols-3 gap-5">
        {items.slice(0, 6).map((t) => (
          <div
            key={t.id}
            className="rounded-2xl p-6 flex flex-col gap-4"
            style={{ background: "var(--bg-card)", border: "1px solid var(--border)" }}
          >
            <div className="flex gap-0.5">
              {[1, 2, 3, 4, 5].map((s) => (
                <span key={s} className="text-sm" style={{ color: s <= t.rating ? "#3b82f6" : "var(--border)" }}>★</span>
              ))}
            </div>
            <p className="text-sm leading-relaxed flex-1" style={{ color: "var(--muted)" }}>
              &ldquo;{t.message}&rdquo;
            </p>
            <div className="flex items-center gap-2.5">
              <div
                className="w-8 h-8 rounded-full flex items-center justify-center text-xs font-bold shrink-0"
                style={{ background: "rgba(59,130,246,.12)", color: "var(--accent)" }}
              >
                {t.initials || "★"}
              </div>
              <p className="text-sm font-semibold" style={{ color: "var(--text)" }}>
                Verified user
              </p>
            </div>
          </div>
        ))}
      </div>
    </div>
  );
}
