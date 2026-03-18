interface CompletenessBarProps {
  percentage: number;
}

function getColor(pct: number): string {
  if (pct >= 80) return "text-success";
  if (pct >= 50) return "text-warning";
  return "text-danger";
}

function getTrackColor(pct: number): string {
  if (pct >= 80) return "stroke-success";
  if (pct >= 50) return "stroke-warning";
  return "stroke-danger";
}

export default function CompletenessBar({ percentage }: CompletenessBarProps) {
  const clamped = Math.max(0, Math.min(100, percentage));
  const radius = 54;
  const circumference = 2 * Math.PI * radius;
  const offset = circumference - (clamped / 100) * circumference;

  return (
    <div className="flex flex-col items-center gap-3">
      <div className="relative w-36 h-36">
        <svg
          className="w-full h-full -rotate-90"
          viewBox="0 0 120 120"
        >
          <circle
            cx="60"
            cy="60"
            r={radius}
            fill="none"
            stroke="currentColor"
            strokeWidth="10"
            className="text-primary"
          />
          <circle
            cx="60"
            cy="60"
            r={radius}
            fill="none"
            strokeWidth="10"
            strokeLinecap="round"
            strokeDasharray={circumference}
            strokeDashoffset={offset}
            className={`${getTrackColor(clamped)} transition-all duration-700`}
          />
        </svg>
        <div className="absolute inset-0 flex items-center justify-center">
          <span className={`text-3xl font-bold ${getColor(clamped)}`}>
            {clamped}%
          </span>
        </div>
      </div>
      <span className="text-sm text-gray-400">Document Completeness</span>
    </div>
  );
}
