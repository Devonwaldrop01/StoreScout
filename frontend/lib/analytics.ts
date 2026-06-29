// Provider-agnostic analytics helper.
//
// Wraps Google Analytics 4 (gtag) and Meta Pixel (fbq). Both are loaded by
// <Analytics /> in the root layout and are env-gated — if the corresponding
// NEXT_PUBLIC_* id is unset, the underlying script never loads and these calls
// are silent no-ops. That means this is safe to call anywhere, in any
// environment, without keys configured.
//
// To add another provider later (PostHog, Mixpanel), add its call inside
// track()/pageview() — call sites don't change.

declare global {
  interface Window {
    gtag?: (...args: unknown[]) => void;
    fbq?: (...args: unknown[]) => void;
    dataLayer?: unknown[];
  }
}

export const GA_ID = process.env.NEXT_PUBLIC_GA_ID || "";
export const FB_PIXEL_ID = process.env.NEXT_PUBLIC_FB_PIXEL_ID || "";

/** Map our internal event names to Meta's standard events where one fits. */
const FB_STANDARD: Record<string, string> = {
  signup_completed: "CompleteRegistration",
  subscription_started: "Subscribe",
  upgrade_clicked: "InitiateCheckout",
};

/**
 * Track a product event. Sends to GA4 and Meta Pixel if loaded.
 * @param event snake_case event name (e.g. "competitor_added")
 * @param props optional flat properties object
 */
export function track(event: string, props: Record<string, unknown> = {}): void {
  if (typeof window === "undefined") return;
  try {
    window.gtag?.("event", event, props);
  } catch { /* never let analytics break the app */ }
  try {
    if (window.fbq) {
      const standard = FB_STANDARD[event];
      if (standard) window.fbq("track", standard, props);
      else window.fbq("trackCustom", event, props);
    }
  } catch { /* ignore */ }
}

/** Fire a page_view. Called on client-side route changes by <RouteTracker />. */
export function pageview(url: string): void {
  if (typeof window === "undefined") return;
  try {
    if (GA_ID) window.gtag?.("event", "page_view", { page_path: url });
  } catch { /* ignore */ }
  try {
    window.fbq?.("track", "PageView");
  } catch { /* ignore */ }
}
