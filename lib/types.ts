export interface Submission {
  id: string;
  transaction_type: string;
  transaction_label: string;
  broker_name: string;
  broker_email: string;
  property_ref: string;
  status: "processing" | "completed" | "approved" | "pending_approval" | "error";
  completeness_pct: number;
  files_processed: number;
  approval_level: string | null;
  approval_label: string | null;
  result: SubmissionResult | null;
  claude_analysis: ClaudeAnalysis | null;
  created_at: string;
  updated_at: string;
  file_results?: FileResult[];
}

export interface SubmissionResult {
  submission_id: string;
  status: string;
  transaction_type: string;
  broker: { name: string; email: string };
  property_ref: string;
  files_processed: number;
  completeness: CompletenessResult;
  approval_level: string;
  approval_request: Record<string, unknown> | null;
  claude_analysis: ClaudeAnalysis | null;
  agentic_loop?: { turns: number; tool_calls_count: number };
  emails_sent: number;
  file_results?: FileResult[];
  processed_at: string;
}

export interface FileResult {
  file_name: string;
  classified_as: string | null;
  classified_label: string;
  confidence: number;
  size_mb: number;
  issues: ValidationIssue[];
}

export interface ValidationIssue {
  severity: "error" | "warning" | "info";
  code: string;
  message: string;
  file?: string;
}

export interface CompletenessResult {
  transaction_type: string;
  transaction_label: string;
  completeness_pct: number;
  required_total: number;
  required_present: number;
  required_missing: number;
  present_documents: string[];
  missing_documents: MissingDocument[];
  validation_issues: ValidationIssue[];
}

export interface MissingDocument {
  id: string;
  name: string;
  description: string;
}

export interface ClaudeAnalysis {
  verdict: "APPROVE" | "NEEDS_ATTENTION" | "REJECT";
  risk: "LOW" | "MEDIUM" | "HIGH";
  recommendations: string[];
  red_flags: string[];
  approval_level?: string;
  completeness_pct?: number;
  mode?: "rule_based";
}

export interface AgentStep {
  id: number;
  submission_id: string;
  step_number: number;
  step_type: "tool_call" | "tool_result" | "thinking" | "status";
  tool_name: string | null;
  description: string;
  data: Record<string, unknown>;
  created_at: string;
}

export interface TransactionType {
  label: string;
  required_count: number;
  optional_count: number;
  required: { id: string; name: string; description: string }[];
  optional: { id: string; name: string; description: string }[];
}

export interface HealthStatus {
  status: string;
  claude_enabled: boolean;
  supabase_connected: boolean;
  timestamp: string;
}
