// Fires the feedback widget open at most once per user, after they've shown
// real engagement. Gated by two localStorage keys so a user is never nagged:
//   - ss_feedback_submitted : set once they actually submit (FeedbackWidget)
//   - ss_feedback_prompted  : set the first time we auto-open the modal
export function requestFeedbackOnce(heading = "How's StoreScout so far?") {
  try {
    if (
      localStorage.getItem("ss_feedback_submitted") ||
      localStorage.getItem("ss_feedback_prompted")
    ) {
      return;
    }
    localStorage.setItem("ss_feedback_prompted", "1");
    window.dispatchEvent(new CustomEvent("ss:open-feedback", { detail: { heading } }));
  } catch {
    /* localStorage unavailable — skip the prompt rather than crash */
  }
}

/** Open the feedback widget immediately (manual click — not gated). */
export function openFeedback(heading?: string) {
  try {
    window.dispatchEvent(new CustomEvent("ss:open-feedback", { detail: heading ? { heading } : {} }));
  } catch { /* ignore */ }
}
