"use client";

import { useSubmissions } from "@/lib/hooks/useSubmissions";
import DashboardStats from "@/components/dashboard/DashboardStats";
import SubmissionCard from "@/components/dashboard/SubmissionCard";
import Spinner from "@/components/ui/Spinner";

export default function SubmissionsPage() {
  const { submissions, loading, error, refresh } = useSubmissions();

  return (
    <div>
      {/* Page Header */}
      <div className="bg-fam-black rounded-2xl p-8 mb-8">
        <div className="flex items-center justify-between">
          <div>
            <h1 className="text-3xl font-bold text-white">
              Submissions Dashboard
            </h1>
            <p className="text-white/60 mt-2 text-sm">
              Track and manage all document submissions.
            </p>
          </div>
          <button
            onClick={refresh}
            disabled={loading}
            className="flex items-center gap-2 rounded-pill bg-white/10 hover:bg-white/20 border border-white/20 px-5 py-2.5 text-sm text-white font-medium transition-colors disabled:opacity-50"
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
      </div>

      {/* Stats */}
      <DashboardStats submissions={submissions} />

      {/* Loading */}
      {loading && (
        <div className="flex flex-col items-center justify-center py-20">
          <Spinner size="lg" />
          <p className="text-fam-gray-lighter mt-4">Loading submissions...</p>
        </div>
      )}

      {/* Error */}
      {error && (
        <div className="rounded-xl bg-red-50 border border-red-200 px-4 py-3 text-red-600 text-sm mb-6 mt-6">
          {error}
        </div>
      )}

      {/* Empty State */}
      {!loading && !error && submissions.length === 0 && (
        <div className="text-center py-20">
          <div className="w-16 h-16 bg-fam-off-white rounded-full flex items-center justify-center mx-auto mb-4">
            <svg
              className="w-8 h-8 text-fam-gray-lighter"
              fill="none"
              stroke="currentColor"
              viewBox="0 0 24 24"
            >
              <path
                strokeLinecap="round"
                strokeLinejoin="round"
                strokeWidth={1.5}
                d="M9 12h6m-6 4h6m2 5H7a2 2 0 01-2-2V5a2 2 0 012-2h5.586a1 1 0 01.707.293l5.414 5.414a1 1 0 01.293.707V19a2 2 0 01-2 2z"
              />
            </svg>
          </div>
          <p className="text-fam-gray-light text-lg font-semibold">
            No submissions yet.
          </p>
          <p className="text-fam-gray-lighter mt-2 text-sm">
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
