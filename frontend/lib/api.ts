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
    apiFetch<{ data: AiSummary }>(`/competitors/${id}/ai-summary`),
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
}

export interface AiSummary {
  id: string;
  competitor_id: string;
  generated_at: string;
  model: string;
  summary_text: string;
  summary_type: string;
}

export interface UserSubscription {
  id: string;
  email: string;
  tier: "free" | "pro" | "agency";
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
}
