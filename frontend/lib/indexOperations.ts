export interface WorkerEvidence {
  enabled: boolean;
  state?: string;
  last_activity?: string | null;
  last_successful_run?: string | null;
  last_verification?: string | null;
  last_classification?: string | null;
  throughput?: { window_minutes: number; attempts: number; successful_catalogs: number } | null;
}

export function workerStatusLabel(worker: WorkerEvidence): string {
  switch (worker.state) {
    case "deployment_hold": return "API deployment hold enabled · worker state unconfirmed";
    case "disabled": return "Automatic pipeline paused";
    case "recent_activity": return "Recent task activity · live worker unconfirmed";
    case "inactive_or_unknown": return "No recent task activity · worker may be paused or inert";
    default: return "Worker status unavailable";
  }
}
