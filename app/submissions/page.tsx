"use client";

import { useSubmissions } from "@/lib/hooks/useSubmissions";
import DashboardStats from "@/components/dashboard/DashboardStats";
import SubmissionCard from "@/components/dashboard/SubmissionCard";
import Spinner from "@/components/ui/Spinner";

export default function SubmissionsPage() {
  const { submissions, loading, error, refresh } = useSubmissions();

  return (
    <div>
      <div className="flex items-center justify-between mb-8">
        <h1 className="text-3xl font-bold text-white">Submissions Dashboard</h1>
        <button
          onClick={refresh}
          disabled={loading}
          className="flex items-center gap-2 rounded-lg bg-primary-light border border-white/10 hover:border-accent/50 px-4 py-2 text-sm text-gray-300 hover:text-white transition-colors disabled:opacity-50"
        >
          <svg
            className={`w-4 h-4 ${loading ? "animate-spin" : ""}`}
            fill="none"
            stroke="currentColor"
            viewBox="0 0 24 24"
          >
            <path
              strokeLinecap="round"
              strokeLinejoin="round"
              strokeWidth={2}
              d="M4 4v5h.582m15.356 2A8.001 8.001 0 004.582 9m0 0H9m11 11v-5h-.581m0 0a8.003 8.003 0 01-15.357-2m15.357 2H15"
            />
          </svg>
          Refresh
        </button>
      </div>

      {/* Stats */}
      <DashboardStats submissions={submissions} />

      {/* Loading */}
      {loading && (
        <div className="flex flex-col items-center justify-center py-20">
          <Spinner size="lg" />
          <p className="text-gray-400 mt-4">Loading submissions...</p>
        </div>
      )}

      {/* Error */}
      {error && (
        <div className="rounded-lg bg-danger/20 border border-danger/50 px-4 py-3 text-danger text-sm mb-6">
          {error}
        </div>
      )}

      {/* Empty State */}
      {!loading && !error && submissions.length === 0 && (
        <div className="text-center py-20">
          <p className="text-gray-400 text-lg">No submissions yet.</p>
          <p className="text-gray-500 mt-2">
            Submit your first set of documents to get started.
          </p>
        </div>
      )}

      {/* Submissions Grid */}
      {!loading && submissions.length > 0 && (
        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4 mt-6">
          {submissions.map((submission) => (
            <SubmissionCard key={submission.id} submission={submission} />
          ))}
        </div>
      )}
    </div>
  );
}
