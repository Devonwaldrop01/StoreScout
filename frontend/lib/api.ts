import { createClient } from "./supabase/client";

const API_BASE = "/api/v1";

// During client-side navigation the Supabase session can be momentarily
// unavailable (token refresh in flight). If we fire a request without the
// Authorization header the backend 401s and pages that treat "no data" as
// "new account" render a false empty state. So: wait briefly for a token,
// and on a 401 force one session refresh and retry the request.
async function getAuthHeaders(): Promise<Record<string, string>> {
  const supabase = createClient();
  for (let attempt = 0; attempt < 4; attempt++) {
    const { data } = await supabase.auth.getSession();
    const token = data.session?.access_token;
    if (token) return { Authorization: `Bearer ${token}` };
    await new Promise((r) => setTimeout(r, 250 * (attempt + 1)));
  }
  return {};
}

async function apiFetch<T>(path: string, options: RequestInit = {}): Promise<T> {
  const doFetch = async (headers: Record<string, string>) =>
    fetch(`${API_BASE}${path}`, {
      ...options,
      headers: { "Content-Type": "application/json", ...headers, ...(options.headers || {}) },
    });

  let res = await doFetch(await getAuthHeaders());

  if (res.status === 401) {
    // Stale token — refresh the session once and retry before failing.
    try {
      const supabase = createClient();
      const { data } = await supabase.auth.refreshSession();
      const token = data.session?.access_token;
      if (token) res = await doFetch({ Authorization: `Bearer ${token}` });
    } catch {
      /* fall through to the error below */
    }
  }

  if (!res.ok) {
    const err = await res.json().catch(() => ({ detail: res.statusText }));
    throw Object.assign(new Error(err.detail || "API error"), { status: res.status, data: err });
  }
  return res.json();
}

// ── Last-good cache ───────────────────────────────────────────
// Session-scoped memory of the last successful competitors.list() response.
// Pages hydrate from this instantly on mount (no skeleton flash on every
// navigation) and revalidate in the background. Cleared on sign-out.
let lastGoodCompetitors: Competitor[] | null = null;

export function getCachedCompetitors(): Competitor[] | null {
  return lastGoodCompetitors;
}

export function clearApiCache() {
  lastGoodCompetitors = null;
}

// ── Competitors ───────────────────────────────────────────────
export type ScanLifecycle = "idle" | "queued" | "running" | "completed" | "failed" | "timed_out";
export interface ScanState {
  state: ScanLifecycle;
  scan_status: string | null;
  since: string | null;
  last_scanned_at: string | null;
  running_seconds: number | null;
  timed_out: boolean;
}

export const competitors = {
  list: async () => {
    const res = await apiFetch<{ data: Competitor[] }>("/competitors");
    lastGoodCompetitors = res.data;
    return res;
  },
  get: (id: string) => apiFetch<{ data: Competitor }>(`/competitors/${id}`),
  add: (store_url: string, display_name?: string) =>
    apiFetch<{ data: Competitor }>("/competitors", {
      method: "POST",
      body: JSON.stringify({ store_url, display_name }),
    }),
  remove: (id: string) =>
    apiFetch<void>(`/competitors/${id}`, { method: "DELETE" }),
  rescan: (id: string) =>
    apiFetch<{ status: string }>(`/competitors/${id}/rescan`, { method: "POST" }),
  scanStatus: (id: string) =>
    apiFetch<{ data: ScanState }>(`/competitors/${id}/scan-status`),
  latestSnapshot: (id: string) =>
    apiFetch<{ data: Snapshot }>(`/competitors/${id}/snapshots/latest`),
  snapshots: (id: string, limit = 30) =>
    apiFetch<{ data: SnapshotMeta[] }>(`/competitors/${id}/snapshots?limit=${limit}`),
  changes: (id: string, limit = 50, changeType?: string) =>
    apiFetch<{ data: ChangeEvent[] }>(
      `/competitors/${id}/changes?limit=${limit}${changeType ? `&change_type=${changeType}` : ""}`
    ),
  aiSummary: (id: string) =>
    apiFetch<{ data: AiSummary | null; status: "ok" | "refreshing" | "generating" }>(`/competitors/${id}/ai-summary`),
  regenerateSummary: (id: string) =>
    apiFetch<{ status: string }>(`/competitors/${id}/ai-summary/regenerate`, { method: "POST" }),
  winningProducts: (id: string) =>
    apiFetch<{ data: WinningProductsResponse }>(`/competitors/${id}/winning-products`),
  gaps: (id: string) =>
    apiFetch<{ data: GapsResponse }>(`/competitors/${id}/gaps`),
  storeProfile: (id: string) =>
    apiFetch<{ data: StoreProfileResponse }>(`/competitors/${id}/store-profile`),
  comparison: (id: string) =>
    apiFetch<{ data: ComparisonResponse }>(`/competitors/${id}/comparison`),
  ask: (id: string, question: string) =>
    apiFetch<{ data: { answer: string | null; followups: string[] } }>(`/competitors/${id}/ask`, {
      method: "POST", body: JSON.stringify({ question }),
    }),
  benchmarks: (id: string) =>
    apiFetch<{ data: BenchmarksData }>(`/competitors/${id}/benchmarks`),
  quickWins: (id: string) =>
    apiFetch<{ data: QuickWinsResponse }>(`/competitors/${id}/quick-wins`),
  priceHistory: (id: string) =>
    apiFetch<{ data: PriceHistoryResponse }>(`/competitors/${id}/price-history`),
  brief: (id: string) =>
    apiFetch<{ data: BriefData }>(`/competitors/${id}/brief`),
  marketContext: (id: string) =>
    apiFetch<{ data: MarketContext }>(`/competitors/${id}/market-context`),
  exportCsvUrl: (id: string) => `${API_BASE}/competitors/${id}/export/products.csv`,
  discover: () =>
    apiFetch<{ data: { suggestions: DiscoverySuggestion[] } }>("/competitors/discover"),
  discoveryFeedback: (domain: string, correct: boolean) =>
    apiFetch<{ status: string }>("/competitors/discovery-feedback", {
      method: "POST",
      body: JSON.stringify({ domain, correct }),
    }),
  discoverAI: (description: string) =>
    apiFetch<{ data: AIDiscoverySuggestion }>("/competitors/discover-ai", {
      method: "POST",
      body: JSON.stringify({ description }),
    }),
};

// ── API Keys ──────────────────────────────────────────────────
export const apiKeys = {
  list: () => apiFetch<{ data: ApiKey[] }>("/api-keys"),
  create: (name = "API key") =>
    apiFetch<{ data: { key: string; key_prefix: string; name: string } }>("/api-keys", {
      method: "POST",
      body: JSON.stringify({ name }),
    }),
  revoke: (keyId: string) => apiFetch<void>(`/api-keys/${keyId}`, { method: "DELETE" }),
};

// ── Team ──────────────────────────────────────────────────────
export const team = {
  members: () => apiFetch<{ data: TeamMember[] }>("/team/members"),
  invite: (email: string) =>
    apiFetch<{ status: string }>("/team/invite", {
      method: "POST",
      body: JSON.stringify({ email }),
    }),
  remove: (memberId: string) =>
    apiFetch<void>(`/team/members/${memberId}`, { method: "DELETE" }),
  getInvite: (token: string) =>
    apiFetch<{ data: InviteDetails }>(`/team/invite/${token}`),
  accept: (token: string) =>
    apiFetch<{ status: string }>("/team/accept", {
      method: "POST",
      body: JSON.stringify({ token }),
    }),
};

// ── Public Reports ────────────────────────────────────────────
export const reports = {
  get: (snapshotId: string) =>
    apiFetch<{ data: PublicReport }>(`/reports/${snapshotId}`),
};

// ── My Store ──────────────────────────────────────────────────
export const myStore = {
  get: () => apiFetch<{ data: Competitor | null }>("/my-store"),
  set: (store_url: string, display_name?: string) =>
    apiFetch<{ data: Competitor }>("/my-store", {
      method: "POST",
      body: JSON.stringify({ store_url, display_name }),
    }),
  remove: () => apiFetch<void>("/my-store", { method: "DELETE" }),
};

// ── Alerts ────────────────────────────────────────────────────
export const alerts = {
  list: (limit = 50, changeType?: string) =>
    apiFetch<{ data: AlertEvent[] }>(
      `/alerts?limit=${limit}${changeType ? `&change_type=${changeType}` : ""}`
    ),
  unreadCount: () => apiFetch<{ count: number }>("/alerts/unread-count"),
  markRead: (id: string) =>
    apiFetch<{ status: string }>(`/alerts/${id}/read`, { method: "PUT" }),
  markAllRead: () =>
    apiFetch<{ status: string; marked: number }>("/alerts/mark-all-read", { method: "POST" }),
};

// ── Feedback ──────────────────────────────────────────────────
export const storeIndex = {
  networkStats: () =>
    apiFetch<{ data: { verified_stores: number; discovered_universe: number; categories: number } }>("/store-index/network-stats"),
};

export interface MarketSignalInterpretation {
  what_happened?: string;
  why_it_matters?: string;
  your_move?: string;
}

export const market = {
  // Rewrite deterministic Market Signals with per-category nuance grounded in
  // the user's own business. Returns {} interpretations on any failure so the
  // caller keeps its deterministic copy.
  interpretSignals: (
    signals: { id: string; headline?: string; what_happened?: string; competitor_count: number; members: { hostname: string; label?: string }[] }[],
  ) =>
    apiFetch<{ data: { interpretations: Record<string, MarketSignalInterpretation> } }>("/market/signals/interpret", {
      method: "POST",
      body: JSON.stringify({ signals }),
    }),
};

export const feedback = {
  submit: (data: { rating: number; message: string; allow_testimonial: boolean; page?: string }) =>
    apiFetch<{ ok: boolean }>("/feedback", {
      method: "POST",
      body: JSON.stringify(data),
    }),
  publicTestimonials: () =>
    apiFetch<{ data: Array<{ id: string; rating: number; message: string; created_at: string; initials: string }> }>("/feedback/public"),
};

// ── Billing ───────────────────────────────────────────────────
export const billing = {
  checkout: (plan: string, billingPeriod: "monthly" | "annual" = "monthly") =>
    apiFetch<{ url: string }>("/billing/checkout", {
      method: "POST",
      body: JSON.stringify({ plan, billing: billingPeriod }),
    }),
  portal: () =>
    apiFetch<{ url: string }>("/billing/portal", { method: "POST" }),
};

// ── User ──────────────────────────────────────────────────────
export const user = {
  subscription: () => apiFetch<{ data: UserSubscription }>("/user/subscription"),
  actionItems: () => apiFetch<{ data: ActionItem[]; locked?: boolean; locked_count?: number }>("/action-items"),
  playbook: () => apiFetch<PlaybookResponse>("/playbook"),
  regeneratePlaybook: () =>
    apiFetch<{ status: string; ai_state: string }>("/playbook/regenerate", { method: "POST" }),
  prefs: () => apiFetch<{ data: NotificationPrefs }>("/user/notification-prefs"),
  updatePrefs: (prefs: Partial<NotificationPrefs>) =>
    apiFetch<{ status: string }>("/user/notification-prefs", {
      method: "PUT",
      body: JSON.stringify(prefs),
    }),
  businessProfile: () => apiFetch<{ data: BusinessProfile | null }>("/user/business-profile"),
  saveBusinessProfile: (profile: Partial<BusinessProfile>) =>
    apiFetch<{ status: string }>("/user/business-profile", {
      method: "PUT",
      body: JSON.stringify(profile),
    }),
  testWebhook: (type: "slack" | "generic") =>
    apiFetch<{ status: string; http_status?: number; detail?: string }>("/user/test-webhook", {
      method: "POST",
      body: JSON.stringify({ type }),
    }),
  provision: () =>
    apiFetch<{ status: string; provisioned?: boolean }>("/user/provision", { method: "POST" }),
};

/**
 * Provision the account, blocking until it genuinely succeeds. Idempotent and
 * concurrency-safe server-side, so retrying is free. Returns true only when the
 * account is confirmed provisioned; callers must NOT proceed into onboarding on
 * a false return. Retries transient failures a couple of times before giving up.
 */
export async function ensureProvisioned(retries = 2): Promise<boolean> {
  for (let attempt = 0; attempt <= retries; attempt++) {
    try {
      const res = await user.provision();
      if (res?.provisioned || res?.status === "created" || res?.status === "exists") return true;
    } catch {
      // fall through to retry
    }
    if (attempt < retries) await new Promise((r) => setTimeout(r, 400 * (attempt + 1)));
  }
  return false;
}

/**
 * Pure post-auth routing decision (unit-tested). A completed user (>=1 tracked
 * competitor) goes to the dashboard; a new user goes to onboarding. An explicit,
 * safe internal `next` is honored — but never an /auth path (loop guard), and a
 * default /onboarding `next` is ignored for a completed user.
 */
export function postAuthDestination(hasCompetitor: boolean, next?: string | null): string {
  const safeNext = !!next && next.startsWith("/") && !next.startsWith("/auth");
  if (hasCompetitor) {
    if (safeNext && !next!.startsWith("/onboarding")) return next!;   // deep link honored
    return "/dashboard";
  }
  if (safeNext && next!.startsWith("/onboarding")) return next!;      // preserve plan-carrying onboarding
  return "/onboarding";
}

/**
 * Validate account state after auth, then resolve where to send the user.
 * Ensures provisioning first (repairs a partial account); returns null if
 * provisioning genuinely fails so the caller can show a retry WITHOUT looping
 * back through auth. Never creates duplicate users (provision is idempotent).
 */
export async function resolvePostAuthDestination(next?: string | null): Promise<string | null> {
  const ok = await ensureProvisioned();
  if (!ok) return null;
  let hasCompetitor = false;
  try {
    hasCompetitor = ((await competitors.list()).data || []).length > 0;
  } catch {
    // Unknown account state → onboarding is the safe default (never dashboard).
  }
  return postAuthDestination(hasCompetitor, next);
}

// ── Types ─────────────────────────────────────────────────────
export interface Competitor {
  id: string;
  user_id: string;
  store_url: string;
  hostname: string;
  display_name?: string;
  is_active: boolean;
  last_scanned_at?: string;
  next_scan_at?: string;
  scan_status: "pending" | "scanning" | "done" | "error";
  error_message?: string;
  product_count?: number;
  promo_rate?: number;
  median_price?: number;
  new_30d?: number;
  snapshot_data?: Record<string, unknown>;
  created_at: string;
}

export interface Snapshot {
  id: string;
  competitor_id: string;
  scanned_at: string;
  product_count?: number;
  median_price?: number;
  promo_rate?: number;
  new_30d?: number;
  snapshot_data: Record<string, unknown>;
}

export interface SnapshotMeta {
  id: string;
  scanned_at: string;
  product_count?: number;
  median_price?: number;
  promo_rate?: number;
  new_30d?: number;
}

export interface ChangeEvent {
  id: string;
  competitor_id: string;
  detected_at: string;
  change_type: string;
  product_handle?: string;
  product_title?: string;
  product_url?: string;
  old_value?: Record<string, unknown>;
  new_value?: Record<string, unknown>;
  delta_pct?: number;
  severity: "info" | "warning" | "critical";
  alert_sent: boolean;
}

export interface AlertEvent extends ChangeEvent {
  hostname: string;
  read_at?: string | null;
}

export interface AiSummary {
  id: string;
  competitor_id: string;
  generated_at: string;
  model: string;
  summary_text: string;
  summary_type: string;
}

export interface WinningProduct {
  title?: string;
  product_url?: string;
  handle?: string;
  price_min?: number;
  image?: string | null;
  score: number;
  signals?: Record<string, number>;
  age_days?: number | null;
  variants_count?: number;
  discounted?: boolean;
  discount_pct?: number | null;
  available?: boolean;
  reason?: string | null;
  signal_tags?: string[];
  locked?: boolean;
  // Product Intelligence tiers (scans after the tier system shipped)
  tier?: "hero" | "strong" | "emerging" | "monitor" | "ignore";
  premium_position?: boolean;
  cross_sell?: boolean;
  why?: string[];
  reveals?: string;
  respond?: string | null;
}

export interface MarketContext {
  category: string | null;
  subcategory?: string | null;
  saturation: number;
  peers: { domain: string; brand_name: string | null; median_price: number | null; business_stage: string | null; pricing_tier: string | null }[];
}

export interface NewestProduct {
  title?: string;
  product_url?: string;
  price_min?: number;
  image?: string | null;
  age_days?: number;
  variants_count?: number;
  available?: boolean;
}

export interface WinningProductsResponse {
  products: WinningProduct[];
  newest: NewestProduct[];
  locked: boolean;
  locked_count: number;
  tier: string;
}

export interface Gap {
  type: string;
  title: string;
  detail?: string | null;
  opportunity?: number;
  metric?: Record<string, unknown>;
  locked?: boolean;
}

export interface GapsResponse {
  gaps: Gap[];
  locked: boolean;
  locked_count: number;
  tier: string;
  median_price?: number;
}

export interface CollectionIntel {
  count: number;
  names: string[];
  has_sale: boolean;
  has_new_arrivals: boolean;
  has_best_sellers: boolean;
  has_bundles: boolean;
  has_subscription: boolean;
  has_gift: boolean;
}

export interface BrandSignals {
  has_wholesale: boolean;
  has_affiliate: boolean;
  has_press: boolean;
  has_sustainability: boolean;
  has_size_guide: boolean;
  has_rewards: boolean;
  page_count: number;
}

export interface ContentIntel {
  blog_count: number;
  sampled_article_count: number;
  content_investment_score: number;
  recent_article_titles: string[];
}

export interface StoreProfileResponse {
  // Free tier flat fields
  collection_count?: number;
  has_sale_collection?: boolean;
  has_new_arrivals?: boolean;
  has_best_sellers?: boolean;
  has_blog?: boolean;
  has_wholesale?: boolean;
  content_investment_score?: number;
  decode_teaser?: { headline?: string; positioning?: string } | null;
  // Pro/Agency nested fields
  decode?: BrandDecode | null;
  collection_intel?: CollectionIntel;
  brand_signals?: BrandSignals;
  content_intel?: ContentIntel;
  locked: boolean;
  tier: string;
}

export interface BrandDecode {
  headline: string;
  positioning?: string;
  merchandising?: string;
  marketing_engine?: string;
  vulnerabilities?: string[];
  openings?: string[];
  one_move: string;
}

export type ComparisonVerdict = "winning" | "losing" | "matched" | "neutral";

export interface ComparisonDimension {
  key: string;
  label: string;
  verdict: ComparisonVerdict;
  your_value: string;
  their_value: string;
  insight: string;
  action?: string | null;
  action_locked?: boolean;
}

export interface MatchStrategy {
  is_newcomer: boolean;
  narrative?: string | null;
  match_these: string[];
  own_these: string[];
  locked?: boolean;
}

export interface BenchmarkItem {
  key: string;
  label: string;
  unit: string;
  value: number;
  average: number;
  median: number;
  percentile: number;
  diff_pct: number;
  read: string;
}
export interface BenchmarksData {
  category: string | null;
  sample_size?: number;
  benchmarks: BenchmarkItem[];
  note?: string;
}

export interface ComparisonResponse {
  has_store: boolean;
  ready?: boolean;
  reason?: string;
  my_hostname?: string;
  their_hostname?: string;
  overall?: {
    verdict: string;
    summary: string;
    score: { winning: number; losing: number; matched: number; neutral: number };
  };
  dimensions?: ComparisonDimension[];
  match_strategy?: MatchStrategy;
  locked?: boolean;
  tier?: string;
}

export interface QuickWin {
  id: string;
  type: "opportunity" | "signal" | "watch";
  headline: string;
  detail: string;
}

export interface QuickWinsResponse {
  wins: QuickWin[];
  locked: boolean;
  locked_count: number;
  tier: string;
}

export interface PriceHistoryPoint {
  scanned_at: string;
  median_price: number | null;
  promo_rate: number | null;
  product_count: number | null;
}

export interface PriceHistoryResponse {
  points: PriceHistoryPoint[];
  locked: boolean;
  locked_count: number;
  tier: string;
}

export interface BriefCard {
  type: "signal" | "opportunity" | "watch" | "action";
  headline: string;
  body: string;
}

export interface PlaybookDetail {
  steps: string[];
  competitors?: Array<{ hostname: string; metric: string }>;
  why?: string;
  outcome?: string;
}

export interface DraftAsset {
  type: "email" | "ad" | "none";
  label?: string;
  subject?: string;
  body_opening?: string;
  headlines?: string[];
  ad_body?: string;
}

export interface PlaybookPlay {
  id: string;
  section: "act_now" | "right_now" | "this_week" | "watch";
  priority: number;
  competitor_id: string;
  hostname: string;
  headline: string;
  action: string;
  deadline: string;
  type: "availability" | "pricing" | "catalog" | "positioning" | "change" | "product" | "discounts" | "alert" | string;
  source: "snapshot" | "change_event" | "ai";
  tab?: string;
  detail?: PlaybookDetail;
  draft_asset?: DraftAsset | null;
  // ── Strategy-first schema (Playbook 2.0) — present on AI recommendations ──
  category?: string;
  title?: string;
  what_happened?: string;
  why_it_matters?: string;
  interpretation?: string;
  objective?: string;
  execution_paths?: { surface: string; action: string }[];
  expected_outcome?: string;
  evidence?: string[];
  confidence?: "verified" | "estimated" | "predicted" | string;
  priority_label?: "high" | "medium" | "low" | string;
  effort?: string;
  timeframe?: string;
}

export interface PlaybookResponse {
  plays: PlaybookPlay[];
  competitor_count: number;
  locked: boolean;
  locked_count?: number;
  ai_source?: boolean;
  ai_generating?: boolean;
  ai_state?: "not_requested" | "queued" | "generating" | "ready" | "failed" | "timed_out" | "unavailable";
}

export interface ActionItem {
  id: string;
  type: "threat" | "opportunity" | "gap";
  competitor_id: string;
  hostname: string;
  headline: string;
  action_text: string;
  context: string;
  tab: string;
}

export interface BriefData {
  id: string;
  summary_text: string;
  generated_at: string;
  model: string;
}

export interface UserSubscription {
  id: string;
  email: string;
  tier: "free" | "pro" | "agency" | "developer";
  subscription_status: string;
  stripe_customer_id?: string;
  limits: {
    max_competitors: number;
    scan_hours: number;
    history_days: number;
    ai_digest: boolean;
    // Additive (canonical entitlements). Optional so older cached responses
    // still type-check.
    watch_cap?: number;
    automatic_scans?: boolean;
  };
  // Canonical feature gates + normalized subscription state (additive).
  features?: Record<string, boolean>;
  subscription_state?: "active" | "trialing" | "past_due" | "canceled" | "inactive" | "none";
}

export interface BusinessProfile {
  category?: string;
  price_range?: "budget" | "mid" | "premium" | "luxury";
  target_customer?: string;
  primary_goal?: string;
  sells?: string;
  brand_traits?: string[];
  notes?: string;
  own_store_url?: string;
}

export interface NotificationPrefs {
  user_id: string;
  email_price_changes: boolean;
  email_new_products: boolean;
  email_discount_changes: boolean;
  email_weekly_digest: boolean;
  digest_day: string;
  notification_level?: "critical_only" | "daily" | "weekly" | "quiet";
  digest_hour?: number;
  slack_webhook_url?: string;
  slack_enabled?: boolean;
  webhook_url?: string;
  webhook_enabled?: boolean;
}

export interface PublicReport {
  snapshot_id: string;
  scanned_at: string;
  hostname: string;
  product_count?: number;
  pricing: {
    median?: number;
    min?: number;
    max?: number;
    p25?: number;
    p75?: number;
    bucket_counts: Record<string, number>;
  };
  discounts: { discounted_pct?: number; avg_discount_pct?: number };
  launch: { new_30d?: number; new_90d?: number };
  positioning: {
    market_position?: Record<string, unknown>;
    promo_intensity?: Record<string, unknown>;
    launch_velocity?: Record<string, unknown>;
    catalog_complexity?: Record<string, unknown>;
  };
  takeaways: string[];
  ai_brief?: {
    cards?: { type: "signal" | "opportunity" | "watch" | "action"; headline: string; body: string }[];
  } | null;
}

export interface ApiKey {
  id: string;
  name: string;
  key_prefix: string;
  last_used_at?: string | null;
  created_at: string;
}

export interface TeamMember {
  id: string;
  invited_email: string;
  status: "pending" | "active" | "removed";
  invited_at: string;
  accepted_at?: string | null;
}

export interface InviteDetails {
  invited_email: string;
  owner_email: string;
}

export interface AIDiscoverySuggestion {
  suggestions: Array<{ domain: string; reason: string; confidence?: number; signals?: string[] }>;
  relevant_non_shopify?: Array<{ domain: string; reason: string; note?: string }>;
  searches_used: number | null;
  searches_limit: number | null;
}

export interface DiscoverySuggestion {
  hostname: string;
  competitor_id: string;
  score: number;
  match_reasons: string[];
  product_count?: number | null;
  median_price?: number | null;
  market_position?: string | null;
  is_curated?: boolean;
  category?: string | null;
}

export interface ShopifyConnection {
  shop: string;
  shop_name: string;
  scope: string;
  created_at: string;
}

export const shopify = {
  connectUrl: (shop: string) =>
    apiFetch<{ url: string }>(`/shopify/connect-url?shop=${encodeURIComponent(shop)}`),
  connection: () =>
    apiFetch<{ data: ShopifyConnection | null }>("/shopify/connection"),
  disconnect: () =>
    apiFetch<void>("/shopify/connection", { method: "DELETE" }),
};

export interface KlaviyoStatus {
  connected: boolean;
  key_preview: string | null;
}

export interface KlaviyoTestResult {
  status: string;
  list_count: number;
  total_profiles: number;
  lists: { name: string; profile_count: number }[];
}

export interface GoogleStatus {
  connected: boolean;
  ga4_property_id: string | null;
  gsc_site_url: string | null;
}

export interface GoogleProperties {
  ga4_properties: { id: string; display_name: string; website_url: string }[];
  gsc_sites: { url: string; permission: string }[];
}

export interface WatchedProduct {
  id: string;
  competitor_id: string;
  hostname: string;
  handle: string;
  title: string | null;
  url: string | null;
  pinned_price: number | null;
  current_price: number | null;
  available: boolean | null;
  removed: boolean;
  delta_pct: number | null;
}

// ── Playbook items (saved moves — the persisted action loop) ──
export interface PlaybookItem {
  id: string;
  source_type: "signal" | "gap" | "winning_product" | "pricing" | "brief" | "pro_analysis" | "manual";
  source_ref: string | null;
  competitor_id: string | null;
  hostname: string | null;
  title: string;
  reason: string | null;
  evidence: string | null;
  priority: "high" | "medium" | "low";
  due_at: string | null;
  status: "pending" | "done" | "dismissed";
  outcome: "worked" | "too_early" | "not_relevant" | null;
  notes: string | null;
  created_at: string;
  updated_at: string;
  completed_at: string | null;
}

export interface SavePlaybookItemInput {
  source_type: PlaybookItem["source_type"];
  title: string;
  source_ref?: string;
  competitor_id?: string;
  hostname?: string;
  reason?: string;
  evidence?: string;
  priority?: PlaybookItem["priority"];
}

export const playbookItems = {
  list: (status?: string) =>
    apiFetch<{ data: PlaybookItem[] }>(`/playbook-items${status ? `?status=${status}` : ""}`),
  create: (body: SavePlaybookItemInput) =>
    apiFetch<{ data: PlaybookItem; created: boolean }>("/playbook-items", {
      method: "POST",
      body: JSON.stringify(body),
    }),
  update: (id: string, body: Partial<Pick<PlaybookItem, "status" | "outcome" | "notes" | "priority" | "due_at">>) =>
    apiFetch<{ data: PlaybookItem }>(`/playbook-items/${id}`, {
      method: "PATCH",
      body: JSON.stringify(body),
    }),
};

export const watchlist = {
  list: () => apiFetch<{ data: WatchedProduct[]; cap: number }>("/watchlist"),
  add: (body: {
    competitor_id: string;
    product_handle: string;
    product_title?: string | null;
    product_url?: string | null;
    pinned_price?: number | null;
  }) => apiFetch<{ status: string }>("/watchlist", { method: "POST", body: JSON.stringify(body) }),
  remove: (id: string) => apiFetch<void>(`/watchlist/${id}`, { method: "DELETE" }),
};

export interface IntelligenceSource {
  key: string;
  name: string;
  category: string;
  connected: boolean;
  detail: string | null;
  understands: string[];
  unlocks: string[];
}

export interface BusinessKnowledge {
  understanding_score: number;
  depth_tier: "strategic" | "operational" | "customer" | "full";
  sources: IntelligenceSource[];
  understood: string[];
  missing: { name: string; unlock: string }[];
  competitors_tracked: number;
  scan_history: number;
}

export interface IntegrationEntry {
  id: string;
  name: string;
  category: string;
  dimensions: string[];
  learns: string[];
  gets_better: string;
  capabilities: string[];
  status: "connected" | "available" | "coming_soon";
}
export interface IntegrationHubData {
  categories: { key: string; label: string; count: number }[];
  integrations: IntegrationEntry[];
  intelligence: { key: string; label: string; pct: number; connected: number; total: number }[];
  connected_count: number;
}

export const integrations = {
  get: () => apiFetch<{ data: { klaviyo: KlaviyoStatus; google_enabled?: boolean } }>("/integrations"),
  intelligenceSources: () =>
    apiFetch<{ data: BusinessKnowledge }>("/integrations/intelligence-sources"),
  hub: () => apiFetch<{ data: IntegrationHubData }>("/integrations/hub"),
  klaviyo: {
    save: (api_key: string) =>
      apiFetch<{ data: KlaviyoStatus }>("/integrations/klaviyo", {
        method: "PUT",
        body: JSON.stringify({ api_key }),
      }),
    remove: () => apiFetch<void>("/integrations/klaviyo", { method: "DELETE" }),
    test: () => apiFetch<KlaviyoTestResult>("/integrations/klaviyo/test", { method: "POST" }),
  },
  google: {
    connectUrl: () => apiFetch<{ url: string }>("/integrations/google/connect-url"),
    properties: () => apiFetch<GoogleProperties>("/integrations/google/properties"),
    saveProperty: (ga4_property_id: string | null, gsc_site_url: string | null) =>
      apiFetch<{ status: string }>("/integrations/google/property", {
        method: "PUT",
        body: JSON.stringify({ ga4_property_id, gsc_site_url }),
      }),
    disconnect: () => apiFetch<void>("/integrations/google", { method: "DELETE" }),
  },
};
