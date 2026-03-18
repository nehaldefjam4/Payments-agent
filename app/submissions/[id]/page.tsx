"use client";

import { useParams } from "next/navigation";
import Link from "next/link";
import { useSubmission } from "@/lib/hooks/useSubmission";
import CompletenessBar from "@/components/results/CompletenessBar";
import ApprovalStatus from "@/components/results/ApprovalStatus";
import DocumentTable from "@/components/results/DocumentTable";
import MissingDocsList from "@/components/results/MissingDocsList";
import ClaudeAnalysis from "@/components/results/ClaudeAnalysis";
import Spinner from "@/components/ui/Spinner";

export default function SubmissionDetailPage() {
  const params = useParams();
  const id = params.id as string;
  const { submission, loading, error } = useSubmission(id);

  if (loading) {
    return (
      <div className="flex flex-col items-center justify-center py-20">
        <Spinner size="lg" />
        <p className="text-gray-400 mt-4">Loading submission details...</p>
      </div>
    );
  }

  if (error || !submission) {
    return (
      <div className="text-center py-20">
        <p className="text-danger text-lg">{error || "Submission not found"}</p>
        <Link
          href="/submissions"
          className="text-accent hover:underline mt-4 inline-block"
        >
          Back to Submissions
        </Link>
      </div>
    );
  }

  const result = submission.result;

  return (
    <div>
      {/* Back Link */}
      <Link
        href="/submissions"
        className="inline-flex items-center gap-1 text-gray-400 hover:text-accent transition-colors mb-6"
      >
        <svg
          className="w-4 h-4"
          fill="none"
          stroke="currentColor"
          viewBox="0 0 24 24"
        >
          <path
            strokeLinecap="round"
            strokeLinejoin="round"
            strokeWidth={2}
            d="M15 19l-7-7 7-7"
          />
        </svg>
        Back to Submissions
      </Link>

      {/* Header */}
      <div className="rounded-lg bg-primary border border-white/10 p-6 mb-6">
        <div className="flex flex-col sm:flex-row sm:items-center sm:justify-between gap-4">
          <div>
            <h1 className="text-2xl font-bold text-white">
              Submission {submission.id.slice(0, 8)}...
            </h1>
            <p className="text-gray-400 mt-1">
              {submission.transaction_label || submission.transaction_type}
            </p>
          </div>
          <div className="text-right text-sm text-gray-400">
            <p>
              Broker:{" "}
              <span className="text-white">{submission.broker_name}</span>
            </p>
            <p>
              Email:{" "}
              <span className="text-white">{submission.broker_email}</span>
            </p>
            <p>
              Property:{" "}
              <span className="text-white">{submission.property_ref}</span>
            </p>
          </div>
        </div>
      </div>

      {/* Completeness Bar */}
      {result?.completeness && (
        <div className="mb-6">
          <CompletenessBar percentage={result.completeness?.completeness_pct ?? 0} />
        </div>
      )}

      {/* Approval Status */}
      {result && (
        <div className="mb-6">
          <ApprovalStatus
            level={result.approval_level}
            status={result.status}
          />
        </div>
      )}

      {/* Document Table */}
      {result?.file_results && result.file_results.length > 0 && (
        <div className="mb-6">
          <DocumentTable files={result.file_results} />
        </div>
      )}

      {/* Missing Documents */}
      {result?.completeness?.missing_documents &&
        result.completeness.missing_documents.length > 0 && (
          <div className="mb-6">
            <MissingDocsList
              documents={result.completeness.missing_documents}
            />
          </div>
        )}

      {/* Claude Analysis */}
      {result?.claude_analysis && (
        <div className="mb-6">
          <ClaudeAnalysis analysis={result.claude_analysis} />
        </div>
      )}

      {/* Agentic Loop Info */}
      {result?.agentic_loop && (
        <div className="rounded-lg bg-primary border border-white/10 p-4">
          <h3 className="text-sm font-semibold text-gray-400 mb-2">
            Agent Activity
          </h3>
          <div className="flex gap-6 text-sm">
            <div>
              <span className="text-gray-400">Turns: </span>
              <span className="text-white font-medium">
                {result.agentic_loop.turns}
              </span>
            </div>
            <div>
              <span className="text-gray-400">Tool Calls: </span>
              <span className="text-white font-medium">
                {result.agentic_loop.tool_calls_count}
              </span>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}
