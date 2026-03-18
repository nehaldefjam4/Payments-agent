import type { ClaudeAnalysis as ClaudeAnalysisType } from "@/lib/types";
import Badge from "@/components/ui/Badge";

interface ClaudeAnalysisProps {
  analysis: ClaudeAnalysisType | null;
}

const verdictBadge: Record<
  string,
  { label: string; variant: "success" | "warning" | "danger" }
> = {
  APPROVE: { label: "APPROVE", variant: "success" },
  NEEDS_ATTENTION: { label: "NEEDS ATTENTION", variant: "warning" },
  REJECT: { label: "REJECT", variant: "danger" },
};

const riskBadge: Record<
  string,
  { label: string; variant: "success" | "warning" | "danger" }
> = {
  LOW: { label: "Low Risk", variant: "success" },
  MEDIUM: { label: "Medium Risk", variant: "warning" },
  HIGH: { label: "High Risk", variant: "danger" },
};

const verdictColors: Record<string, string> = {
  APPROVE: "text-emerald-400",
  NEEDS_ATTENTION: "text-amber-400",
  REJECT: "text-red-400",
};

export default function ClaudeAnalysis({ analysis }: ClaudeAnalysisProps) {
  if (!analysis) {
    return (
      <p className="text-fam-gray-lighter text-sm text-center py-4">
        No analysis available yet.
      </p>
    );
  }

  const verdict =
    verdictBadge[analysis.verdict] || verdictBadge.NEEDS_ATTENTION;
  const risk = riskBadge[analysis.risk] || riskBadge.MEDIUM;

  return (
    <div className="bg-fam-dark rounded-2xl p-6 border border-fam-gray/30">
      <div className="flex items-center gap-2 mb-5">
        <span className="text-sm text-gray-400 font-medium">AI Analysis</span>
        {analysis.mode === "rule_based" && (
          <span className="text-xs text-gray-500">(rule-based)</span>
        )}
      </div>

      <div className="flex flex-wrap items-center gap-3 mb-6">
        <span
          className={`text-xl font-bold ${
            verdictColors[analysis.verdict] || "text-gray-300"
          }`}
        >
          {analysis.verdict}
        </span>
        <Badge label={verdict.label} variant={verdict.variant} />
        <Badge label={risk.label} variant={risk.variant} />
      </div>

      {analysis.recommendations.length > 0 && (
        <div className="mb-5">
          <h4 className="text-sm font-semibold text-gray-300 mb-3">
            Recommendations
          </h4>
          <ul className="space-y-2">
            {analysis.recommendations.map((rec, idx) => (
              <li
                key={idx}
                className="flex items-start gap-2.5 text-sm text-gray-400"
              >
                <span className="w-1.5 h-1.5 rounded-full bg-fam-orange mt-1.5 shrink-0" />
                <span>{rec}</span>
              </li>
            ))}
          </ul>
        </div>
      )}

      {analysis.red_flags.length > 0 && (
        <div>
          <h4 className="text-sm font-semibold text-red-400 mb-3">
            Red Flags
          </h4>
          <ul className="space-y-2">
            {analysis.red_flags.map((flag, idx) => (
              <li
                key={idx}
                className="flex items-start gap-2.5 text-sm text-red-300"
              >
                <svg
                  className="w-4 h-4 text-red-400 mt-0.5 shrink-0"
                  fill="none"
                  stroke="currentColor"
                  viewBox="0 0 24 24"
                >
                  <path
                    strokeLinecap="round"
                    strokeLinejoin="round"
                    strokeWidth={2}
                    d="M12 9v2m0 4h.01m-6.938 4h13.856c1.54 0 2.502-1.667 1.732-3L13.732 4c-.77-1.333-2.694-1.333-3.464 0L3.34 16c-.77 1.333.192 3 1.732 3z"
                  />
                </svg>
                <span>{flag}</span>
              </li>
            ))}
          </ul>
        </div>
      )}
    </div>
  );
}
