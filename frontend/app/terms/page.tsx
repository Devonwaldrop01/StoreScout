// Terms of Service — StoreScout
//
// NOTE: Product-accurate starting Terms, not legal advice. Have counsel review
// before going live. Governing law is set to New York (§14). If Anonymous
// Mentality LLC is registered in a different state (e.g. VA or DE), update §14
// to match the state of formation / principal place of business.

import type { Metadata } from "next";
import Link from "next/link";
import { Zap, ArrowLeft } from "lucide-react";

export const metadata: Metadata = {
  title: "Terms of Service — StoreScout",
  description: "The terms that govern your use of StoreScout.",
};

const EFFECTIVE_DATE = "June 29, 2026";

export default function TermsPage() {
  return (
    <div style={{ background: "var(--bg)", minHeight: "100vh" }}>
      <div className="max-w-3xl mx-auto px-6 py-12">
        {/* Header */}
        <div className="flex items-center justify-between mb-10">
          <Link href="/" className="flex items-center gap-2.5">
            <div className="w-6 h-6 rounded-md flex items-center justify-center" style={{ background: "var(--accent)" }}>
              <Zap className="w-3.5 h-3.5" style={{ color: "var(--ink)" }} />
            </div>
            <span className="font-bold" style={{ color: "var(--text)" }}>StoreScout</span>
          </Link>
          <Link href="/" className="flex items-center gap-1.5 text-sm hover:opacity-80 transition-opacity" style={{ color: "var(--muted)" }}>
            <ArrowLeft className="w-3.5 h-3.5" /> Back to home
          </Link>
        </div>

        <article className="legal-prose" style={{ color: "var(--text-2)" }}>
          <h1 className="text-3xl font-bold mb-2" style={{ color: "var(--text)" }}>Terms of Service</h1>
          <p className="text-sm mb-8" style={{ color: "var(--muted)" }}>Effective {EFFECTIVE_DATE}</p>

          <p>
            These Terms of Service (&ldquo;Terms&rdquo;) govern your access to and use of StoreScout (the
            &ldquo;Service&rdquo;), operated by Anonymous Mentality LLC (&ldquo;StoreScout,&rdquo; &ldquo;we,&rdquo;
            &ldquo;us&rdquo;). By creating an account or using the Service, you agree to these Terms. If you do not agree,
            do not use the Service.
          </p>

          <h2>1. The Service</h2>
          <p>StoreScout is a competitor-intelligence tool for Shopify stores. We collect publicly available product-catalog
            data from stores you choose to track, detect changes (such as price changes, launches, and discounts), send
            alerts, and generate AI summaries and recommendations.</p>

          <h2>2. Accounts</h2>
          <p>You must provide accurate information and are responsible for safeguarding your account credentials and for all
            activity under your account. You must be at least 16 years old and able to form a binding contract.</p>

          <h2>3. Acceptable use</h2>
          <p>You agree not to: (a) use the Service to violate any law or third party&rsquo;s rights; (b) attempt to access
            data or systems you are not authorized to access; (c) disrupt, overload, or reverse-engineer the Service;
            (d) resell or redistribute the Service except as expressly permitted by your plan; or (e) use the Service to
            access non-public, private, admin, or checkout areas of any store.</p>

          <h2>4. Public data &amp; your responsibility</h2>
          <p>The Service analyzes publicly available data that stores publish. You are solely responsible for ensuring that
            your use of competitor data complies with applicable laws and any agreements that bind you. The Service is
            provided for lawful competitive-research purposes only.</p>

          <h2>5. Plans, billing &amp; cancellation</h2>
          <p>The Service offers a free plan and paid subscriptions (Pro and Agency), billed monthly or annually through
            Stripe. Paid subscriptions renew automatically until cancelled. You can cancel anytime from your billing
            settings; cancellation takes effect at the end of the current billing period, and you retain access until
            then. Fees are stated at checkout and may change with notice for future billing periods.</p>

          <h2>6. Refunds</h2>
          <p>Except where required by law, payments are non-refundable. You will not be charged for billing periods after
            you cancel. If you believe you were billed in error, contact us and we will work with you in good faith.</p>

          <h2>7. Free plan</h2>
          <p>We may modify or discontinue the free plan, or change its limits, at any time. The free plan is provided
            &ldquo;as is&rdquo; with no service-level commitment.</p>

          <h2>8. Third-party integrations</h2>
          <p>If you connect third-party services (e.g., Shopify, Klaviyo, Google, Slack), your use of those services is
            governed by their terms, and you authorize us to access them on your behalf to provide the Service. We are
            not responsible for third-party services.</p>

          <h2>9. Intellectual property</h2>
          <p>We own all rights in the Service, including its software, design, and content (excluding your data and
            third-party data). We grant you a limited, non-exclusive, non-transferable right to use the Service per these
            Terms. Insights and reports generated for you may be used for your own business purposes.</p>

          <h2>10. Disclaimers</h2>
          <p>THE SERVICE IS PROVIDED &ldquo;AS IS&rdquo; AND &ldquo;AS AVAILABLE&rdquo; WITHOUT WARRANTIES OF ANY KIND. We
            do not guarantee that data is complete, accurate, or available for every store (some stores restrict access),
            that alerts will be delivered within any specific time, or that the Service will be uninterrupted or
            error-free. Insights and AI outputs are informational only and are <strong>not</strong> financial, legal, or
            business advice. You are responsible for decisions you make based on them.</p>

          <h2>11. Limitation of liability</h2>
          <p>To the maximum extent permitted by law, StoreScout and Anonymous Mentality LLC will not be liable for any
            indirect, incidental, special, consequential, or punitive damages, or for lost profits or revenues. Our total
            liability for any claim relating to the Service will not exceed the amount you paid us in the 12 months before
            the claim.</p>

          <h2>12. Indemnification</h2>
          <p>You agree to indemnify and hold harmless StoreScout and Anonymous Mentality LLC from claims arising out of
            your use of the Service or your violation of these Terms or applicable law.</p>

          <h2>13. Termination</h2>
          <p>You may stop using the Service at any time. We may suspend or terminate your access if you violate these Terms
            or use the Service in a way that risks harm to us or others. Upon termination, your right to use the Service
            ceases; sections that by their nature should survive (e.g., 9–12, 14) survive.</p>

          <h2>14. Governing law</h2>
          <p>These Terms are governed by the laws of the State of New York, without regard to its conflict-of-laws
            rules. The exclusive venue for disputes will be the state or federal courts located in New York.</p>

          <h2>15. Changes to these Terms</h2>
          <p>We may update these Terms. Material changes will be reflected by updating the effective date above and, where
            appropriate, by additional notice. Continued use after changes means you accept them.</p>

          <h2>16. Contact</h2>
          <p>Questions about these Terms? Email{" "}
            <a href="mailto:hello@getstorescout.com" style={{ color: "var(--accent)" }}>hello@getstorescout.com</a>.</p>
        </article>
      </div>
    </div>
  );
}
