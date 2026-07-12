/**
 * Frontend entitlement display helpers.
 *
 * Purely presentational — the backend (app/services/entitlements.py) remains
 * the authority on what a plan can do; this only formats those facts truthfully
 * so the UI never contradicts the real cadence or gates. Kept pure + tested.
 */

/** Truthful scan-cadence label from the plan's scan interval in hours.
 * Every tier gets automatic scans, so no plan is ever labeled "Manual". */
export function scanCadenceLabel(scanHours: number | undefined | null): string {
  const h = typeof scanHours === "number" && scanHours > 0 ? scanHours : 168;
  if (h >= 168) return "Weekly";
  if (h === 24) return "Daily";
  if (h % 24 === 0) return `Every ${h / 24}d`;
  return `Every ${h}h`;
}

/** History-retention label. Free retains no history (current state only). */
export function historyLabel(historyDays: number | undefined | null): string {
  if (!historyDays || historyDays <= 0) return "Current only";
  if (historyDays >= 3650) return "Full history";
  return `${historyDays}d`;
}

/** A short, human subscription-state note for a past-due / canceling account —
 * null when nothing needs saying (active/trialing/free). */
export function subscriptionNotice(
  state: string | undefined | null,
): { text: string; tone: "warn" | "info" } | null {
  switch (state) {
    case "past_due":
      return { text: "Payment past due — update your card to keep Pro features.", tone: "warn" };
    case "canceled":
      return { text: "Subscription canceled — access continues until the end of your billing period.", tone: "info" };
    default:
      return null;
  }
}
