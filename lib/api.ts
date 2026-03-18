import type {
  HealthStatus,
  TransactionType,
  Submission,
  SubmissionResult,
  AgentStep,
} from "./types";

const API_BASE = "/api";

export async function fetchHealth(): Promise<HealthStatus> {
  const res = await fetch(`${API_BASE}/health`);
  return res.json();
}

export async function fetchTransactionTypes(): Promise<
  Record<string, TransactionType>
> {
  const res = await fetch(`${API_BASE}/transaction-types`);
  return res.json();
}

export async function submitDocuments(
  formData: FormData
): Promise<SubmissionResult> {
  const res = await fetch(`${API_BASE}/check`, {
    method: "POST",
    body: formData,
  });
  if (!res.ok) {
    const err = await res.json().catch(() => ({ detail: "Submission failed" }));
    throw new Error(err.detail || "Submission failed");
  }
  return res.json();
}

export async function fetchSubmissions(): Promise<{
  count: number;
  submissions: Submission[];
}> {
  const res = await fetch(`${API_BASE}/submissions`);
  return res.json();
}

export async function fetchSubmission(id: string): Promise<Submission> {
  const res = await fetch(`${API_BASE}/submissions/${id}`);
  if (!res.ok) throw new Error("Submission not found");
  return res.json();
}

export async function fetchAgentSteps(
  id: string
): Promise<{ steps: AgentStep[]; status: string; total_steps: number }> {
  const res = await fetch(`${API_BASE}/submissions/${id}/steps`);
  return res.json();
}
