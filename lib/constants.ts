export const STATUS_LABELS: Record<string, string> = {
  processing: "Processing",
  completed: "Completed",
  approved: "Approved",
  pending_approval: "Pending Approval",
  error: "Error",
};

export const STATUS_COLORS: Record<string, string> = {
  processing: "bg-blue-500",
  completed: "bg-emerald-500",
  approved: "bg-emerald-500",
  pending_approval: "bg-amber-500",
  error: "bg-red-500",
};

export const VERDICT_COLORS: Record<string, string> = {
  APPROVE: "text-emerald-400",
  NEEDS_ATTENTION: "text-amber-400",
  REJECT: "text-red-400",
};

export const RISK_COLORS: Record<string, string> = {
  LOW: "bg-emerald-50 text-emerald-600",
  MEDIUM: "bg-amber-50 text-amber-600",
  HIGH: "bg-red-50 text-red-600",
};

export const TOOL_ICONS: Record<string, string> = {
  get_submission_summary: "\u{1F4CB}",
  check_completeness: "\u{2705}",
  validate_document: "\u{1F50D}",
  request_approval: "\u{1F4E8}",
  send_broker_notification: "\u{1F4E7}",
};

export const ACCEPTED_FILE_TYPES =
  ".pdf,.jpg,.jpeg,.png,.docx,.doc,.tiff";

export const MAX_FILE_SIZE_MB = 25;
