"use client";

import type { AgentStep } from "@/lib/types";
import { TOOL_ICONS } from "@/lib/constants";

interface ProgressTimelineProps {
  steps: AgentStep[];
  isComplete: boolean;
}

function formatTimestamp(ts: string): string {
  try {
    const date = new Date(ts);
    return date.toLocaleTimeString([], {
      hour: "2-digit",
      minute: "2-digit",
      second: "2-digit",
    });
  } catch {
    return ts;
  }
}

function getStepIcon(toolName: string | null): string {
  if (!toolName) return "\u{1F4AC}";
  return TOOL_ICONS[toolName] || "\u{2699}\uFE0F";
}

export default function ProgressTimeline({
  steps,
  isComplete,
}: ProgressTimelineProps) {
  return (
    <div className="relative bg-white rounded-2xl shadow-sm border border-gray-100 p-6">
      {/* Vertical line */}
      <div className="absolute left-10 top-6 bottom-6 w-px bg-gray-200" />

      <div className="space-y-0">
        {steps.map((step) => (
          <div key={step.id} className="relative flex items-start gap-4 pb-6">
            {/* Icon circle */}
            <div className="relative z-10 flex items-center justify-center w-8 h-8 rounded-full bg-fam-orange/10 border-2 border-fam-orange text-sm shrink-0">
              {getStepIcon(step.tool_name)}
            </div>

            {/* Content */}
            <div className="pt-0.5 min-w-0 flex-1">
              <p className="text-sm text-fam-dark font-medium">
                {step.description}
              </p>
              <div className="flex items-center gap-2 mt-1">
                {step.tool_name && (
                  <span className="text-xs text-fam-orange font-mono bg-fam-orange/5 px-1.5 py-0.5 rounded">
                    {step.tool_name}
                  </span>
                )}
                <span className="text-xs text-fam-gray-lighter">
                  {formatTimestamp(step.created_at)}
                </span>
              </div>
            </div>
          </div>
        ))}
      </div>

      {/* Pulsing dot when processing */}
      {!isComplete && (
        <div className="relative flex items-center gap-4">
          <div className="relative z-10 flex items-center justify-center w-8 h-8">
            <span className="absolute inline-flex h-4 w-4 rounded-full bg-fam-orange opacity-75 animate-ping" />
            <span className="relative inline-flex h-3 w-3 rounded-full bg-fam-orange" />
          </div>
          <span className="text-sm text-fam-gray-lighter font-medium">
            Processing...
          </span>
        </div>
      )}
    </div>
  );
}
