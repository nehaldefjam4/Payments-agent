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
      <h1 className="text-3xl font-bold text-white mb-2">
        Processing Submission{" "}
        <span className="text-accent">{id.slice(0, 8)}...</span>
      </h1>
      <p className="text-gray-400 mb-8">
        Status:{" "}
        <span className="text-white font-medium">{status}</span>
      </p>

      {/* Progress Timeline */}
      <ProgressTimeline steps={steps} isComplete={isComplete} />

      {/* Processing Indicator */}
      {!isComplete && (
        <div className="flex flex-col items-center justify-center py-12">
          <Spinner size="lg" />
          <p className="text-gray-400 mt-4 text-lg">Agent is working...</p>
          <p className="text-gray-500 mt-1 text-sm">
            Analyzing documents and checking compliance
          </p>
        </div>
      )}

      {/* Complete Message */}
      {isComplete && (
        <div className="rounded-lg bg-success/10 border border-success/30 p-6 text-center mt-8">
          <svg
            className="w-12 h-12 text-success mx-auto mb-3"
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
          <p className="text-success text-lg font-semibold">
            Processing complete!
          </p>
          <p className="text-gray-400 mt-2 text-sm">
            Redirecting to results in a few seconds...
          </p>
          <Link
            href={`/submissions/${id}`}
            className="inline-block mt-4 text-accent hover:underline text-sm"
          >
            View Results Now
          </Link>
        </div>
      )}
    </div>
  );
}
