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
    return date.toLocaleTimeString([], { hour: "2-digit", minute: "2-digit", second: "2-digit" });
  } catch {
    return ts;
  }
}

function getStepIcon(toolName: string | null): string {
  if (!toolName) return "\u{1F4AC}";
  return TOOL_ICONS[toolName] || "\u{2699}\uFE0F";
}

export default function ProgressTimeline({ steps, isComplete }: ProgressTimelineProps) {
  return (
    <div className="relative">
      {/* Vertical line */}
      <div className="absolute left-4 top-0 bottom-0 w-px bg-white/10" />

      <div className="space-y-0">
        {steps.map((step, idx) => (
          <div key={step.id} className="relative flex items-start gap-4 pb-6">
            {/* Icon circle */}
            <div className="relative z-10 flex items-center justify-center w-8 h-8 rounded-full bg-primary-light border border-white/10 text-sm shrink-0">
              {getStepIcon(step.tool_name)}
            </div>

            {/* Content */}
            <div className="pt-0.5 min-w-0">
              <p className="text-sm text-gray-200">{step.description}</p>
              <div className="flex items-center gap-2 mt-1">
                {step.tool_name && (
                  <span className="text-xs text-accent/70 font-mono">
                    {step.tool_name}
                  </span>
                )}
                <span className="text-xs text-gray-500">
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
            <span className="absolute inline-flex h-4 w-4 rounded-full bg-accent opacity-75 animate-ping" />
            <span className="relative inline-flex h-3 w-3 rounded-full bg-accent" />
          </div>
          <span className="text-sm text-gray-400">Processing...</span>
        </div>
      )}
    </div>
  );
}
