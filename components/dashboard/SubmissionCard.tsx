import Link from "next/link";
import type { Submission } from "@/lib/types";
import { STATUS_LABELS } from "@/lib/constants";
import Badge from "@/components/ui/Badge";
import Card from "@/components/ui/Card";

interface SubmissionCardProps {
  submission: Submission;
}

function getStatusVariant(
  status: string
): "success" | "warning" | "danger" | "info" | "default" {
  switch (status) {
    case "approved":
    case "completed":
      return "success";
    case "pending_approval":
      return "warning";
    case "error":
      return "danger";
    case "processing":
      return "info";
    default:
      return "default";
  }
}

function getCompletenessColor(pct: number): string {
  if (pct >= 80) return "text-success";
  if (pct >= 50) return "text-warning";
  return "text-danger";
}

function formatDate(dateStr: string): string {
  try {
    const date = new Date(dateStr);
    return date.toLocaleDateString([], {
      month: "short",
      day: "numeric",
      hour: "2-digit",
      minute: "2-digit",
    });
  } catch {
    return dateStr;
  }
}

export default function SubmissionCard({ submission }: SubmissionCardProps) {
  return (
    <Link href={`/submissions/${submission.id}`}>
      <Card className="hover:bg-primary-light/80 transition-colors cursor-pointer">
        <div className="flex items-start justify-between mb-3">
          <div>
            <p className="text-xs text-gray-500 font-mono">{submission.id.slice(0, 8)}...</p>
            <p className="text-sm font-medium text-white mt-0.5">
              {submission.transaction_label}
            </p>
          </div>
          <Badge
            label={STATUS_LABELS[submission.status] || submission.status}
            variant={getStatusVariant(submission.status)}
          />
        </div>

        <div className="flex items-center justify-between text-sm">
          <span className="text-gray-400">{submission.broker_name}</span>
          <span className={`font-semibold ${getCompletenessColor(submission.completeness_pct)}`}>
            {submission.completeness_pct}%
          </span>
        </div>

        <div className="mt-3 pt-3 border-t border-white/5 flex items-center justify-between">
          <span className="text-xs text-gray-500">
            {formatDate(submission.created_at)}
          </span>
          <span className="text-xs text-gray-500">
            {submission.files_processed} file{submission.files_processed !== 1 ? "s" : ""}
          </span>
        </div>
      </Card>
    </Link>
  );
}
