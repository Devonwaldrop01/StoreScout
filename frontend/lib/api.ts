import { createClient } from "./supabase/client";

const API_BASE = "/api/v1";

async function getAuthHeaders(): Promise<Record<string, string>> {
  const supabase = createClient();
  const { data } = await supabase.auth.getSession();
  const token = data.session?.access_token;
  return token ? { Authorization: `Bearer ${token}` } : {};
}

async function apiFetch<T>(path: string, options: RequestInit = {}): Promise<T> {
  const headers = await getAuthHeaders();
  const res = await fetch(`${API_BASE}${path}`, {
    ...options,
    headers: { "Content-Type": "application/json", ...headers, ...(options.headers || {}) },
  });
  if (!res.ok) {
    const err = await res.json().catch(() => ({ detail: res.statusText }));
    throw Object.assign(new Error(err.detail || "API error"), { status: res.status, data: err });
  }
  return res.json();
}

// ── Competitors ───────────────────────────────────────────────
export const competitors = {
  list: () => apiFetch<{ data: Competitor[] }>("/competitors"),
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
  latestSnapshot: (id: string) =>
    apiFetch<{ data: Snapshot }>(`/competitors/${id}/snapshots/latest`),
  snapshots: (id: string, limit = 30) =>
    apiFetch<{ data: SnapshotMeta[] }>(`/competitors/${id}/snapshots?limit=${limit}`),
  changes: (id: string, limit = 50, changeType?: string) =>
    apiFetch<{ data: ChangeEvent[] }>(
      `/competitors/${id}/changes?limit=${limit}${changeType ? `&change_type=${changeType}` : ""}`
    ),
  aiSummary: (id: string) =>
    apiFetch<{ data: AiSummary | null; status: "ok" | "generating" }>(`/competitors/${id}/ai-summary`),
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
  quickWins: (id: string) =>
    apiFetch<{ data: QuickWinsResponse }>(`/competitors/${id}/quick-wins`),
  priceHistory: (id: string) =>
    apiFetch<{ data: PriceHistoryResponse }>(`/competitors/${id}/price-history`),
  brief: (id: string) =>
    apiFetch<{ data: BriefData }>(`/competitors/${id}/brief`),
  exportCsvUrl: (id: string) => `${API_BASE}/competitors/${id}/export/products.csv`,
  discover: () =>
    apiFetch<{ data: { suggestions: DiscoverySuggestion[] } }>("/competitors/discover"),
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
  prefs: () => apiFetch<{ data: NotificationPrefs }>("/user/notification-prefs"),
  updatePrefs: (prefs: Partial<NotificationPrefs>) =>
    apiFetch<{ status: string }>("/user/notification-prefs", {
      method: "PUT",
      body: JSON.stringify(prefs),
    }),
  testWebhook: (type: "slack" | "generic") =>
    apiFetch<{ status: string; http_status?: number; detail?: string }>("/user/test-webhook", {
      method: "POST",
      body: JSON.stringify({ type }),
    }),
  provision: () =>
    apiFetch<{ status: string }>("/user/provision", { method: "POST" }),
};

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
  // Pro/Agency nested fields
  collection_intel?: CollectionIntel;
  brand_signals?: BrandSignals;
  content_intel?: ContentIntel;
  locked: boolean;
  tier: string;
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
  type: "signal" | "opportunity" | "watch";
  headline: string;
  body: string;
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
  };
}

export interface NotificationPrefs {
  user_id: string;
  email_price_changes: boolean;
  email_new_products: boolean;
  email_discount_changes: boolean;
  email_weekly_digest: boolean;
  digest_day: string;
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
    cards?: { type: "signal" | "opportunity" | "watch"; headline: string; body: string }[];
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
