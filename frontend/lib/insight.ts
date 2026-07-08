/**
 * StoreScout's intelligence language — the four categories every important
 * insight maps into, plus the act-now marker. One vocabulary, one color,
 * one icon per category, everywhere intelligence is presented (briefs,
 * Pro analysis, reveal, dossier). Users should learn what each color means
 * once and recognize it on every screen.
 *
 *   Notable Signal  amber   — something unusual has happened
 *   Opportunity     green   — an actionable opening to gain an advantage
 *   Watch Closely   neutral — no action needed yet; keep an eye on it
 *   Prediction      cyan    — StoreScout's best estimate of what happens next
 *   Your Move       amber   — the act-now marker (the amber budget's job)
 */
import { Target, TrendingUp, Eye, Compass, Zap, type LucideIcon } from "lucide-react";

export type InsightKind = "signal" | "opportunity" | "watch" | "prediction" | "action";

export const INSIGHT_LANGUAGE: Record<InsightKind, { label: string; color: string; Icon: LucideIcon }> = {
  signal:      { label: "Notable Signal", color: "#FFB224", Icon: Target },
  opportunity: { label: "Opportunity",    color: "#4CC38A", Icon: TrendingUp },
  watch:       { label: "Watch Closely",  color: "#A8AC9E", Icon: Eye },
  prediction:  { label: "Prediction",     color: "#7DB8C9", Icon: Compass },
  action:      { label: "Your Move",      color: "#FFB224", Icon: Zap },
};

export function insightKind(type: string | undefined): InsightKind {
  return (type && type in INSIGHT_LANGUAGE ? type : "signal") as InsightKind;
}
