"use client";

import { useEffect } from "react";
import { useParams, useRouter } from "next/navigation";
import Link from "next/link";
import { useAgentSteps } from "@/lib/hooks/useAgentSteps";
import ProgressTimeline from "@/components/processing/ProgressTimeline";
import Spinner from "@/components/ui/Spinner";

export default function ProcessingPage() {
  const params = useParams();
  const router = useRouter();
  const id = params.id as string;
  const { steps, status, isComplete } = useAgentSteps(id);

  useEffect(() => {
    if (isComplete) {
      const timer = setTimeout(() => {
        router.push(`/submissions/${id}`);
      }, 3000);
      return () => clearTimeout(timer);
    }
  }, [isComplete, id, router]);

  return (
    <div className="max-w-3xl mx-auto">
      {/* Page Header */}
      <div className="bg-fam-black rounded-2xl p-8 mb-8">
        <h1 className="text-3xl font-bold text-white">
          Processing Submission{" "}
          <span className="text-fam-orange">{id.slice(0, 8)}...</span>
        </h1>
        <p className="text-white/60 mt-2 text-sm">
          Status:{" "}
          <span className="text-white font-medium">{status}</span>
        </p>
      </div>

      {/* Progress Timeline */}
      <ProgressTimeline steps={steps} isComplete={isComplete} />

      {/* Processing Indicator */}
      {!isComplete && (
        <div className="flex flex-col items-center justify-center py-12">
          <Spinner size="lg" />
          <p className="text-fam-gray-light mt-4 text-lg font-medium">
            Agent is working...
          </p>
          <p className="text-fam-gray-lighter mt-1 text-sm">
            Analyzing documents and checking compliance
          </p>
        </div>
      )}

      {/* Complete Message */}
      {isComplete && (
        <div className="bg-emerald-50 border border-emerald-200 rounded-2xl p-8 text-center mt-8">
          <div className="w-14 h-14 bg-emerald-100 rounded-full flex items-center justify-center mx-auto mb-4">
            <svg
              className="w-8 h-8 text-emerald-600"
              fill="none"
              stroke="currentColor"
              viewBox="0 0 24 24"
            >
              <path
                strokeLinecap="round"
                strokeLinejoin="round"
                strokeWidth={2}
                d="M9 12l2 2 4-4m6 2a9 9 0 11-18 0 9 9 0 0118 0z"
              />
            </svg>
          </div>
          <p className="text-emerald-700 text-lg font-bold">
            Processing complete!
          </p>
          <p className="text-emerald-600/70 mt-2 text-sm">
            Redirecting to results in a few seconds...
          </p>
          <Link
            href={`/submissions/${id}`}
            className="inline-block mt-4 text-fam-orange hover:text-fam-orange-light font-semibold text-sm transition-colors"
          >
            View Results Now
          </Link>
        </div>
      )}
    </div>
  );
}
