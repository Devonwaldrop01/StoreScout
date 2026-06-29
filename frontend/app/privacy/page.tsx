// Privacy Policy — StoreScout
//
// NOTE: This is a solid, product-accurate starting policy, not legal advice.
// Have counsel review before relying on it, and keep the subprocessor list in
// sync with the services actually in use.

import type { Metadata } from "next";
import Link from "next/link";
import { Zap, ArrowLeft } from "lucide-react";

export const metadata: Metadata = {
  title: "Privacy Policy — StoreScout",
  description: "How StoreScout collects, uses, and protects your data.",
};

const EFFECTIVE_DATE = "June 29, 2026";

export default function PrivacyPage() {
  return (
    <div style={{ background: "var(--bg)", minHeight: "100vh" }}>
      <div className="max-w-3xl mx-auto px-6 py-12">
        {/* Header */}
        <div className="flex items-center justify-between mb-10">
          <Link href="/" className="flex items-center gap-2.5">
            <div className="w-6 h-6 rounded-md flex items-center justify-center" style={{ background: "var(--accent)" }}>
              <Zap className="w-3.5 h-3.5" style={{ color: "#ffffff" }} />
            </div>
            <span className="font-bold" style={{ color: "var(--text)" }}>StoreScout</span>
          </Link>
          <Link href="/" className="flex items-center gap-1.5 text-sm hover:opacity-80 transition-opacity" style={{ color: "var(--muted)" }}>
            <ArrowLeft className="w-3.5 h-3.5" /> Back to home
          </Link>
        </div>

        <article className="legal-prose" style={{ color: "var(--text-2)" }}>
          <h1 className="text-3xl font-bold mb-2" style={{ color: "var(--text)" }}>Privacy Policy</h1>
          <p className="text-sm mb-8" style={{ color: "var(--muted)" }}>Effective {EFFECTIVE_DATE}</p>

          <p>
            StoreScout (&ldquo;StoreScout,&rdquo; &ldquo;we,&rdquo; &ldquo;us&rdquo;) is operated by Anonymous Mentality LLC.
            This Privacy Policy explains what we collect, how we use it, and the choices you have. By using StoreScout
            (the &ldquo;Service&rdquo;) you agree to this policy.
          </p>

          <h2>1. Information we collect</h2>
          <p><strong>Account information.</strong> When you sign up we collect your email address and any name you provide.
            Authentication is handled by our provider (Supabase); if you sign in with Google, we receive basic profile
            information from Google.</p>
          <p><strong>Billing information.</strong> Paid plans are processed by Stripe. We do <em>not</em> store your full
            card number — Stripe handles payment data. We retain your subscription tier, status, and a Stripe customer
            identifier.</p>
          <p><strong>Competitor &amp; store data you choose to track.</strong> When you add a competitor, we collect and
            store publicly available product-catalog data that the store publishes (for example, products, prices,
            variants, and discounts exposed at public Shopify endpoints). If you connect your own store, we store its
            public data and any details you provide.</p>
          <p><strong>Integration credentials you provide.</strong> If you connect optional integrations, we store the
            credentials needed to operate them — e.g., a Klaviyo API key, Google (GA4/Search Console) OAuth tokens, and
            Slack or webhook URLs. You can remove these at any time in Settings.</p>
          <p><strong>Usage &amp; device data.</strong> We use Google Analytics 4 and the Meta (Facebook) Pixel to understand
            how the Service and our marketing pages are used, and to measure advertising. These tools set cookies and
            collect data such as pages viewed, actions taken, approximate location, device/browser, and referring source.</p>
          <p><strong>Communications.</strong> We send transactional and product emails through Resend (e.g., alerts,
            digests, onboarding). We keep basic records of these communications.</p>

          <h2>2. How we use information</h2>
          <ul>
            <li>Provide the Service: run scans, detect changes, send alerts, and generate AI summaries and playbooks.</li>
            <li>Process payments and manage your subscription.</li>
            <li>Send transactional notifications and, where permitted, product and marketing emails (you can opt out).</li>
            <li>Measure, maintain, secure, and improve the Service and our marketing.</li>
            <li>Comply with legal obligations and enforce our Terms.</li>
          </ul>

          <h2>3. AI processing</h2>
          <p>
            To generate briefs, playbooks, and digests, we send competitor catalog data and related context to our AI
            provider (Anthropic, the maker of Claude). We do not send your password or payment details. This processing
            exists solely to produce the insights you see in the Service.
          </p>

          <h2>4. How we share information</h2>
          <p>We do not sell your personal information. We share data only with service providers (&ldquo;subprocessors&rdquo;)
            that help us run the Service, including:</p>
          <ul>
            <li><strong>Supabase</strong> — database &amp; authentication</li>
            <li><strong>Stripe</strong> — payments &amp; subscription billing</li>
            <li><strong>Anthropic (Claude)</strong> — AI-generated summaries and playbooks</li>
            <li><strong>Resend</strong> — transactional &amp; product email</li>
            <li><strong>Google Analytics</strong> and <strong>Meta Pixel</strong> — analytics &amp; advertising measurement</li>
            <li>Hosting/infrastructure providers (e.g., Vercel, Render) and our Redis provider</li>
          </ul>
          <p>We may also disclose information if required by law, to protect our rights, or in connection with a business
            transfer.</p>

          <h2>5. Cookies</h2>
          <p>We use: <strong>essential cookies</strong> (sign-in/session), <strong>analytics cookies</strong> (Google
            Analytics), and <strong>advertising cookies</strong> (Meta Pixel). You can control cookies through your browser
            settings; disabling some may affect functionality.</p>

          <h2>6. Data retention</h2>
          <p>We retain account and tracked-store data for as long as your account is active. If you delete your account,
            we delete or anonymize associated data within a reasonable period, except where we must retain it to comply
            with legal, accounting, or security obligations.</p>

          <h2>7. Your rights &amp; choices</h2>
          <ul>
            <li>Access, correct, or delete your account data — you can delete your account from Settings.</li>
            <li>Opt out of marketing emails using the unsubscribe link (transactional emails are required for the Service).</li>
            <li>Remove connected integrations at any time in Settings.</li>
            <li>Depending on your location (e.g., EEA/UK or California), you may have additional rights — contact us to exercise them.</li>
          </ul>

          <h2>8. Security</h2>
          <p>We use industry-standard measures to protect your data, including encryption in transit. No method of
            transmission or storage is 100% secure, but we work to protect your information and limit access to it.</p>

          <h2>9. Data on stores you track</h2>
          <p>StoreScout analyzes publicly available product-catalog data that Shopify stores publish. We do not access
            private, admin, checkout, or password-protected areas of any store. You are responsible for ensuring your
            use of competitor data complies with applicable laws and any agreements that bind you.</p>

          <h2>10. Children</h2>
          <p>The Service is not directed to children under 16, and we do not knowingly collect their data.</p>

          <h2>11. Changes</h2>
          <p>We may update this policy. Material changes will be reflected by updating the effective date above and, where
            appropriate, by additional notice.</p>

          <h2>12. Contact</h2>
          <p>Questions about this policy or your data? Email{" "}
            <a href="mailto:hello@getstorescout.com" style={{ color: "var(--accent)" }}>hello@getstorescout.com</a>.</p>
        </article>
      </div>
    </div>
  );
}
