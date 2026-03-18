import Link from "next/link";
import type { Submission } from "@/lib/types";
import { STATUS_LABELS } from "@/lib/constants";
import Badge from "@/components/ui/Badge";

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
  if (pct >= 80) return "text-emerald-600";
  if (pct >= 50) return "text-amber-500";
  return "text-red-500";
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
      <div className="bg-white rounded-2xl shadow-sm border border-gray-100 p-6 hover:shadow-md hover:border-fam-orange/30 transition-all cursor-pointer group">
        <div className="flex items-start justify-between mb-3">
          <div>
            <p className="text-xs text-fam-gray-lighter font-mono">
              {submission.id.slice(0, 8)}...
            </p>
            <p className="text-sm font-semibold text-fam-dark mt-0.5 group-hover:text-fam-orange transition-colors">
              {submission.transaction_label}
            </p>
          </div>
          <Badge
            label={STATUS_LABELS[submission.status] || submission.status}
            variant={getStatusVariant(submission.status)}
          />
        </div>

        <div className="flex items-center justify-between text-sm">
          <span className="text-fam-gray-light">{submission.broker_name}</span>
          <span
            className={`font-bold ${getCompletenessColor(submission.completeness_pct)}`}
          >
            {submission.completeness_pct}%
          </span>
        </div>

        <div className="mt-3 pt-3 border-t border-gray-100 flex items-center justify-between">
          <span className="text-xs text-fam-gray-lighter">
            {formatDate(submission.created_at)}
          </span>
          <span className="text-xs text-fam-gray-lighter">
            {submission.files_processed} file
            {submission.files_processed !== 1 ? "s" : ""}
          </span>
        </div>
      </div>
    </Link>
  );
}
