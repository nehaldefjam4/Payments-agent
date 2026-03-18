import type { ClaudeAnalysis as ClaudeAnalysisType } from "@/lib/types";
import { VERDICT_COLORS, RISK_COLORS } from "@/lib/constants";
import Badge from "@/components/ui/Badge";

interface ClaudeAnalysisProps {
  analysis: ClaudeAnalysisType | null;
}

const verdictBadge: Record<string, { label: string; variant: "success" | "warning" | "danger" }> = {
  APPROVE: { label: "APPROVE", variant: "success" },
  NEEDS_ATTENTION: { label: "NEEDS ATTENTION", variant: "warning" },
  REJECT: { label: "REJECT", variant: "danger" },
};

const riskBadge: Record<string, { label: string; variant: "success" | "warning" | "danger" }> = {
  LOW: { label: "Low Risk", variant: "success" },
  MEDIUM: { label: "Medium Risk", variant: "warning" },
  HIGH: { label: "High Risk", variant: "danger" },
};

export default function ClaudeAnalysis({ analysis }: ClaudeAnalysisProps) {
  if (!analysis) {
    return (
      <p className="text-gray-400 text-sm text-center py-4">
        No analysis available yet.
      </p>
    );
  }

  const verdict = verdictBadge[analysis.verdict] || verdictBadge.NEEDS_ATTENTION;
  const risk = riskBadge[analysis.risk] || riskBadge.MEDIUM;

  return (
    <div className="bg-gradient-to-br from-primary-light to-primary rounded-xl p-6 border border-white/10">
      <div className="flex items-center gap-2 mb-5">
        <span className="text-sm text-gray-400">AI Analysis</span>
        {analysis.mode === "rule_based" && (
          <span className="text-xs text-gray-500">(rule-based)</span>
        )}
      </div>

      <div className="flex flex-wrap items-center gap-3 mb-6">
        <span className={`text-xl font-bold ${VERDICT_COLORS[analysis.verdict] || "text-gray-300"}`}>
          {analysis.verdict}
        </span>
        <Badge label={verdict.label} variant={verdict.variant} />
        <Badge label={risk.label} variant={risk.variant} />
      </div>

      {analysis.recommendations.length > 0 && (
        <div className="mb-5">
          <h4 className="text-sm font-medium text-gray-300 mb-2">
            Recommendations
          </h4>
          <ul className="space-y-1.5">
            {analysis.recommendations.map((rec, idx) => (
              <li key={idx} className="flex items-start gap-2 text-sm text-gray-400">
                <span className="text-accent mt-0.5 shrink-0">&bull;</span>
                <span>{rec}</span>
              </li>
            ))}
          </ul>
        </div>
      )}

      {analysis.red_flags.length > 0 && (
        <div>
          <h4 className="text-sm font-medium text-danger mb-2">
            Red Flags
          </h4>
          <ul className="space-y-1.5">
            {analysis.red_flags.map((flag, idx) => (
              <li
                key={idx}
                className="flex items-start gap-2 text-sm text-danger/80"
              >
                <span className="mt-0.5 shrink-0">{"\u26A0\uFE0F"}</span>
                <span>{flag}</span>
              </li>
            ))}
          </ul>
        </div>
      )}
    </div>
  );
}
