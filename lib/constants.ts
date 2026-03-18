export const STATUS_LABELS: Record<string, string> = {
  processing: "Processing",
  completed: "Completed",
  approved: "Approved",
  pending_approval: "Pending Approval",
  error: "Error",
};

export const STATUS_COLORS: Record<string, string> = {
  processing: "bg-blue-500",
  completed: "bg-green-500",
  approved: "bg-green-500",
  pending_approval: "bg-yellow-500",
  error: "bg-red-500",
};

export const VERDICT_COLORS: Record<string, string> = {
  APPROVE: "text-green-400",
  NEEDS_ATTENTION: "text-yellow-400",
  REJECT: "text-red-400",
};

export const RISK_COLORS: Record<string, string> = {
  LOW: "bg-green-500/20 text-green-400",
  MEDIUM: "bg-yellow-500/20 text-yellow-400",
  HIGH: "bg-red-500/20 text-red-400",
};

export const TOOL_ICONS: Record<string, string> = {
  get_submission_summary: "📋",
  check_completeness: "✅",
  validate_document: "🔍",
  request_approval: "📨",
  send_broker_notification: "📧",
};

export const ACCEPTED_FILE_TYPES =
  ".pdf,.jpg,.jpeg,.png,.docx,.doc,.tiff";

export const MAX_FILE_SIZE_MB = 25;
