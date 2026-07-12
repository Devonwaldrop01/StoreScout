"use client";

import Link from "next/link";
import { Terminal, Key, Copy, Check } from "lucide-react";
import { useState } from "react";

const BASE = process.env.NEXT_PUBLIC_API_URL || "https://your-api.storescout.com";

function CodeBlock({ code, language = "bash" }: { code: string; language?: string }) {
  const [copied, setCopied] = useState(false);
  function copy() {
    navigator.clipboard.writeText(code).then(() => {
      setCopied(true);
      setTimeout(() => setCopied(false), 2000);
    });
  }
  return (
    <div className="relative rounded-md overflow-hidden" style={{ background: "#101110", border: "1px solid var(--border)" }}>
      <div className="flex items-center justify-between px-4 py-2 border-b" style={{ borderColor: "var(--border)" }}>
        <span className="text-xs font-mono" style={{ color: "var(--muted)" }}>{language}</span>
        <button
          onClick={copy}
          className="flex items-center gap-1 text-xs font-medium transition-colors"
          style={{ color: copied ? "var(--emerald)" : "var(--muted)" }}
        >
          {copied ? <Check className="w-3 h-3" /> : <Copy className="w-3 h-3" />}
          {copied ? "Copied" : "Copy"}
        </button>
      </div>
      <pre className="px-4 py-4 overflow-x-auto text-sm font-mono leading-relaxed" style={{ color: "#A8AC9E" }}>
        <code>{code}</code>
      </pre>
    </div>
  );
}

function Pill({ label, color }: { label: string; color: string }) {
  return (
    <span
      className="inline-block text-xs font-bold px-2 py-0.5 rounded-md font-mono mr-2"
      style={{ background: `${color}18`, color }}
    >
      {label}
    </span>
  );
}

function Section({ title, children }: { title: string; children: React.ReactNode }) {
  return (
    <section className="mb-10">
      <h2 className="text-base font-bold mb-4" style={{ color: "var(--text)" }}>{title}</h2>
      {children}
    </section>
  );
}

function Endpoint({
  method,
  path,
  desc,
  auth = true,
  params,
  example,
  response,
}: {
  method: "GET" | "POST" | "DELETE" | "PUT";
  path: string;
  desc: string;
  auth?: boolean;
  params?: { name: string; type: string; required?: boolean; desc: string }[];
  example: string;
  response: string;
}) {
  const methodColor: Record<string, string> = {
    GET: "var(--emerald)",
    POST: "var(--accent)",
    DELETE: "#F2555A",
    PUT: "var(--amber)",
  };

  return (
    <div className="mb-8 rounded-md p-5" style={{ background: "var(--bg-card)", border: "1px solid var(--border)" }}>
      <div className="flex items-start gap-3 mb-3">
        <Pill label={method} color={methodColor[method]} />
        <code className="text-sm font-mono" style={{ color: "var(--text)" }}>{path}</code>
        {auth && (
          <span
            className="ml-auto shrink-0 text-xs px-2 py-0.5 rounded-md"
            style={{ background: "rgba(255,178,36,.1)", color: "#FFB224", border: "1px solid rgba(255,178,36,.2)" }}
          >
            Auth required
          </span>
        )}
      </div>
      <p className="text-sm mb-4" style={{ color: "var(--muted)" }}>{desc}</p>

      {params && params.length > 0 && (
        <div className="mb-4">
          <p className="text-xs font-semibold uppercase tracking-wide mb-2" style={{ color: "var(--muted)" }}>Parameters</p>
          <div className="space-y-2">
            {params.map((p) => (
              <div key={p.name} className="flex gap-3 text-sm">
                <code className="shrink-0 font-mono text-xs px-1.5 py-0.5 rounded" style={{ background: "var(--bg3)", color: "#7DB8C9" }}>
                  {p.name}
                </code>
                <span className="text-xs" style={{ color: "var(--muted)" }}>{p.type}</span>
                {p.required && (
                  <span className="text-xs font-semibold" style={{ color: "#F2555A" }}>required</span>
                )}
                <span className="text-xs" style={{ color: "var(--muted)" }}>{p.desc}</span>
              </div>
            ))}
          </div>
        </div>
      )}

      <div className="grid grid-cols-1 lg:grid-cols-2 gap-3">
        <div>
          <p className="text-xs font-semibold uppercase tracking-wide mb-2" style={{ color: "var(--muted)" }}>Request</p>
          <CodeBlock code={example} language="curl" />
        </div>
        <div>
          <p className="text-xs font-semibold uppercase tracking-wide mb-2" style={{ color: "var(--muted)" }}>Response</p>
          <CodeBlock code={response} language="json" />
        </div>
      </div>
    </div>
  );
}

export default function ApiDocsPage() {
  return (
    <div className="max-w-4xl">
      <div className="flex items-center gap-3 mb-2">
        <Terminal className="w-5 h-5" style={{ color: "#7DB8C9" }} />
        <p className="tick-label mb-1.5">Developer · REST API</p>
        <h1 className="text-2xl font-bold tracking-tight" style={{ color: "var(--text)" }}>API Reference</h1>
      </div>
      <p className="text-sm mb-8" style={{ color: "var(--muted)" }}>
        StoreScout REST API — base URL: <code className="font-mono text-xs px-1.5 py-0.5 rounded" style={{ background: "var(--bg-card)" }}>{BASE}/api/v1</code>
      </p>

      {/* Auth */}
      <Section title="Authentication">
        <div className="rounded-md p-5 mb-4" style={{ background: "var(--bg-card)", border: "1px solid var(--border)" }}>
          <p className="text-sm mb-4" style={{ color: "var(--muted)" }}>
            All endpoints require an <code className="font-mono text-xs">Authorization</code> header.
            You can use either a Supabase JWT (for browser sessions) or an API key (for server-to-server calls).
          </p>
          <div className="grid grid-cols-1 lg:grid-cols-2 gap-4">
            <div>
              <p className="text-xs font-semibold mb-2 flex items-center gap-1.5" style={{ color: "var(--text)" }}>
                <Key className="w-3.5 h-3.5" style={{ color: "#7DB8C9" }} />
                API key (recommended for integrations)
              </p>
              <CodeBlock
                code={`curl ${BASE}/api/v1/competitors \\
  -H "Authorization: Bearer sk_live_xxxxxxxxxxxx"`}
              />
            </div>
            <div>
              <p className="text-xs font-semibold mb-2" style={{ color: "var(--text)" }}>Supabase JWT (browser)</p>
              <CodeBlock
                code={`curl ${BASE}/api/v1/competitors \\
  -H "Authorization: Bearer <supabase_access_token>"`}
              />
            </div>
          </div>
          <p className="text-xs mt-4" style={{ color: "var(--muted)" }}>
            Generate API keys in{" "}
            <Link href="/settings" className="underline" style={{ color: "#7DB8C9" }}>
              Settings → API keys
            </Link>
            . Keys are available on Pro, Agency, and Developer plans.
          </p>
        </div>
      </Section>

      {/* Rate limits */}
      <Section title="Rate limits">
        <div className="rounded-md p-5" style={{ background: "var(--bg-card)", border: "1px solid var(--border)" }}>
          <p className="text-sm" style={{ color: "var(--muted)" }}>
            100 requests per minute per user. Exceeding this returns{" "}
            <code className="font-mono text-xs">429 Too Many Requests</code> with a{" "}
            <code className="font-mono text-xs">Retry-After</code> header.
            Manual rescans have a short per-competitor cooldown (about a minute) between requests.
          </p>
        </div>
      </Section>

      {/* Competitors */}
      <Section title="Competitors">
        <Endpoint
          method="GET"
          path="/api/v1/competitors"
          desc="List all competitors tracked by the authenticated user."
          example={`curl ${BASE}/api/v1/competitors \\
  -H "Authorization: Bearer sk_live_xxxx"`}
          response={`{
  "data": [
    {
      "id": "uuid",
      "hostname": "gymshark.com",
      "display_name": "Gymshark",
      "scan_status": "done",
      "product_count": 412,
      "last_scanned_at": "2026-05-24T07:00:00Z",
      "next_scan_at": "2026-05-25T07:00:00Z"
    }
  ]
}`}
        />

        <Endpoint
          method="POST"
          path="/api/v1/competitors"
          desc="Add a new competitor. Triggers an initial background scan immediately."
          params={[
            { name: "store_url", type: "string", required: true, desc: "Any URL on the Shopify store (e.g. https://gymshark.com)" },
            { name: "display_name", type: "string", desc: "Optional human-readable label" },
          ]}
          example={`curl -X POST ${BASE}/api/v1/competitors \\
  -H "Authorization: Bearer sk_live_xxxx" \\
  -H "Content-Type: application/json" \\
  -d '{"store_url":"https://gymshark.com"}'`}
          response={`{
  "data": {
    "id": "uuid",
    "hostname": "gymshark.com",
    "scan_status": "pending",
    "created_at": "2026-05-24T08:00:00Z"
  }
}`}
        />

        <Endpoint
          method="DELETE"
          path="/api/v1/competitors/{id}"
          desc="Remove a tracked competitor and all associated snapshots and change events."
          example={`curl -X DELETE ${BASE}/api/v1/competitors/uuid \\
  -H "Authorization: Bearer sk_live_xxxx"`}
          response={`204 No Content`}
        />

        <Endpoint
          method="POST"
          path="/api/v1/competitors/{id}/rescan"
          desc="Trigger an immediate manual rescan. Short per-competitor cooldown (~1 min) between requests."
          example={`curl -X POST ${BASE}/api/v1/competitors/uuid/rescan \\
  -H "Authorization: Bearer sk_live_xxxx"`}
          response={`{ "status": "queued" }`}
        />
      </Section>

      {/* Snapshots */}
      <Section title="Snapshots">
        <Endpoint
          method="GET"
          path="/api/v1/competitors/{id}/snapshots/latest"
          desc="Return the most recent scan snapshot with full analytics data."
          example={`curl ${BASE}/api/v1/competitors/uuid/snapshots/latest \\
  -H "Authorization: Bearer sk_live_xxxx"`}
          response={`{
  "data": {
    "id": "uuid",
    "scanned_at": "2026-05-24T07:00:00Z",
    "product_count": 412,
    "median_price": 64.99,
    "promo_rate": 18.4,
    "new_30d": 23,
    "snapshot_data": { ... }
  }
}`}
        />

        <Endpoint
          method="GET"
          path="/api/v1/competitors/{id}/snapshots"
          desc="Paginated list of all snapshots for a competitor. History availability depends on your plan."
          params={[
            { name: "limit", type: "integer", desc: "Max results (default 30, max 100)" },
            { name: "offset", type: "integer", desc: "Pagination offset" },
          ]}
          example={`curl "${BASE}/api/v1/competitors/uuid/snapshots?limit=10" \\
  -H "Authorization: Bearer sk_live_xxxx"`}
          response={`{
  "data": [
    {
      "id": "uuid",
      "scanned_at": "2026-05-24T07:00:00Z",
      "product_count": 412,
      "median_price": 64.99,
      "promo_rate": 18.4
    }
  ],
  "meta": { "total": 48, "limit": 10, "offset": 0 }
}`}
        />
      </Section>

      {/* Changes */}
      <Section title="Change events">
        <Endpoint
          method="GET"
          path="/api/v1/competitors/{id}/changes"
          desc="Return detected change events for a competitor. Includes price changes, new products, discount campaigns, and removals."
          params={[
            { name: "limit", type: "integer", desc: "Max results (default 50)" },
            { name: "change_type", type: "string", desc: "Filter: price_change | new_product | product_removed | discount_start | discount_end" },
          ]}
          example={`curl "${BASE}/api/v1/competitors/uuid/changes?change_type=price_change" \\
  -H "Authorization: Bearer sk_live_xxxx"`}
          response={`{
  "data": [
    {
      "id": "uuid",
      "detected_at": "2026-05-23T14:30:00Z",
      "change_type": "price_change",
      "product_title": "Crest Hoodie",
      "old_value": { "price": 65.00 },
      "new_value": { "price": 49.99 },
      "delta_pct": -23.09,
      "severity": "warning"
    }
  ]
}`}
        />

        <Endpoint
          method="GET"
          path="/api/v1/alerts"
          desc="Aggregated change feed across all of the user's competitors."
          params={[
            { name: "limit", type: "integer", desc: "Max results (default 50)" },
            { name: "change_type", type: "string", desc: "Optional filter (same values as above)" },
          ]}
          example={`curl ${BASE}/api/v1/alerts \\
  -H "Authorization: Bearer sk_live_xxxx"`}
          response={`{
  "data": [
    {
      "id": "uuid",
      "hostname": "gymshark.com",
      "change_type": "new_product",
      "product_title": "Apex Shorts",
      "detected_at": "2026-05-24T06:15:00Z",
      "severity": "info"
    }
  ]
}`}
        />
      </Section>

      {/* AI summary */}
      <Section title="AI insights">
        <Endpoint
          method="GET"
          path="/api/v1/competitors/{id}/ai-summary"
          desc="Return the latest Claude-generated strategic summary for a competitor. Generated weekly on Pro+ plans."
          example={`curl ${BASE}/api/v1/competitors/uuid/ai-summary \\
  -H "Authorization: Bearer sk_live_xxxx"`}
          response={`{
  "data": {
    "id": "uuid",
    "generated_at": "2026-05-20T02:00:00Z",
    "model": "claude-haiku-4-5",
    "summary_type": "weekly",
    "summary_text": "Gymshark ran a broad 25% markdown across..."
  }
}`}
        />
      </Section>

      {/* User */}
      <Section title="User & billing">
        <Endpoint
          method="GET"
          path="/api/v1/user/subscription"
          desc="Return the authenticated user's current plan, tier limits, and Stripe subscription status."
          example={`curl ${BASE}/api/v1/user/subscription \\
  -H "Authorization: Bearer sk_live_xxxx"`}
          response={`{
  "data": {
    "tier": "pro",
    "subscription_status": "active",
    "limits": {
      "max_competitors": 10,
      "scan_hours": 24,
      "history_days": 90,
      "ai_digest": true
    }
  }
}`}
        />
      </Section>

      {/* Error format */}
      <Section title="Error format">
        <div className="rounded-md p-5" style={{ background: "var(--bg-card)", border: "1px solid var(--border)" }}>
          <p className="text-sm mb-4" style={{ color: "var(--muted)" }}>
            All errors return a JSON body with a <code className="font-mono text-xs">detail</code> field.
          </p>
          <CodeBlock
            code={`{
  "detail": "API keys require a Pro or higher plan"
}`}
            language="json"
          />
          <div className="mt-4 space-y-2 text-sm" style={{ color: "var(--muted)" }}>
            <div className="flex gap-3">
              <code className="font-mono text-xs shrink-0" style={{ color: "#F2555A" }}>401</code>
              <span>Missing or invalid token / revoked API key</span>
            </div>
            <div className="flex gap-3">
              <code className="font-mono text-xs shrink-0" style={{ color: "#F2555A" }}>403</code>
              <span>Feature not available on your current plan</span>
            </div>
            <div className="flex gap-3">
              <code className="font-mono text-xs shrink-0" style={{ color: "var(--amber)" }}>429</code>
              <span>Rate limit exceeded — check <code className="font-mono text-xs">Retry-After</code> header</span>
            </div>
            <div className="flex gap-3">
              <code className="font-mono text-xs shrink-0" style={{ color: "#F2555A" }}>422</code>
              <span>Validation error — malformed request body</span>
            </div>
          </div>
        </div>
      </Section>
    </div>
  );
}
