export type Mode = "auto" | "guided";
export type RunStatus =
  | "initialized"
  | "understanding"
  | "field_confirming"
  | "waiting_for_user"
  | "auditing"
  | "finalizing"
  | "finished"
  | "blocked";

export type CandidateItem = {
  value: unknown;
  confidence: number;
  reason: string;
  evidence_ids: string[];
  risks: string[];
};

export type Evidence = {
  evidence_id: string;
  source_type: string;
  source_title: string;
  source_ref?: string | null;
  section_path: string[];
  content: string;
  target_fields: string[];
  credibility: number;
  limitations?: string | null;
};

/** Guard violation from the output validation layer. */
export type GuardViolation = {
  rule: string;
  field_name: string;
  message: string;
  severity: "error" | "warning";
};

export type CurrentDecision = {
  run_id: string;
  session_id: string;
  target_group: string;
  target_fields: string[];
  summary: string;
  candidates: Record<string, CandidateItem[]>;
  evidence: Evidence[];
  risks: Record<string, unknown>[];
  recommended: Record<string, unknown>;
};

export type RunState = {
  run_id: string;
  status: RunStatus;
  mode: Mode | null;
  current_target: { group_name: string; fields: string[] } | null;
  progress: {
    confirmed_groups: string[];
    remaining_groups: string[];
  };
  publishability: string | null;
};

export type RunOutputs = {
  pwps: Record<string, unknown>;
  field_report: Record<string, unknown>;
  evidence_report: { evidence: Evidence[] };
  risk_report: {
    publishability?: string | null;
    issues?: {
      severity: string;
      description: string;
      recommended_action: string;
    }[];
  };
  discussion_trace: Record<string, unknown>;
  publishability: string | null;
};

const API_BASE = process.env.NEXT_PUBLIC_API_BASE_URL ?? "http://127.0.0.1:8000";

async function requestJson<T>(path: string, init?: RequestInit): Promise<T> {
  const response = await fetch(`${API_BASE}${path}`, {
    ...init,
    headers: {
      "Content-Type": "application/json",
      ...init?.headers,
    },
  });
  if (!response.ok) {
    const payload = (await response.json()) as { message?: string };
    throw new Error(payload.message ?? `Request failed with ${response.status}`);
  }
  return (await response.json()) as T;
}

export function createRun(input: string, mode: Mode): Promise<{ run_id: string; status: RunStatus }> {
  return requestJson("/api/runs", {
    method: "POST",
    body: JSON.stringify({ input, mode, attachments: [] }),
  });
}

export function fetchRun(runId: string): Promise<RunState> {
  return requestJson(`/api/runs/${runId}`);
}

export function fetchCurrentDecision(runId: string): Promise<CurrentDecision> {
  return requestJson(`/api/runs/${runId}/current-decision`);
}

export function submitDecision(
  runId: string,
  payload: {
    session_id: string;
    decision_type: "accept_recommended" | "choose_alternative" | "override";
    selected_values: Record<string, unknown>;
    comment?: string;
  },
): Promise<{ run_id: string; status: RunStatus; accepted: boolean }> {
  return requestJson(`/api/runs/${runId}/decision`, {
    method: "POST",
    body: JSON.stringify(payload),
  });
}

export function fetchOutputs(runId: string): Promise<RunOutputs> {
  return requestJson(`/api/runs/${runId}/outputs`);
}
