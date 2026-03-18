interface CompletenessBarProps {
  percentage: number;
}

function getColor(pct: number): string {
  if (pct >= 80) return "text-emerald-600";
  if (pct >= 50) return "text-amber-500";
  return "text-red-500";
}

function getStrokeColor(pct: number): string {
  if (pct >= 80) return "#22c55e";
  if (pct >= 50) return "#f59e0b";
  return "#ef4444";
}

export default function CompletenessBar({ percentage }: CompletenessBarProps) {
  const clamped = Math.max(0, Math.min(100, percentage));
  const radius = 54;
  const circumference = 2 * Math.PI * radius;
  const offset = circumference - (clamped / 100) * circumference;

  return (
    <div className="bg-white rounded-2xl shadow-sm border border-gray-100 p-8 flex flex-col items-center gap-4">
      <div className="relative w-40 h-40">
        <svg className="w-full h-full -rotate-90" viewBox="0 0 120 120">
          <circle
            cx="60"
            cy="60"
            r={radius}
            fill="none"
            stroke="#f3f4f6"
            strokeWidth="10"
          />
          <circle
            cx="60"
            cy="60"
            r={radius}
            fill="none"
            stroke={getStrokeColor(clamped)}
            strokeWidth="10"
            strokeLinecap="round"
            strokeDasharray={circumference}
            strokeDashoffset={offset}
            className="transition-all duration-700"
          />
        </svg>
        <div className="absolute inset-0 flex items-center justify-center">
          <span className={`text-4xl font-bold ${getColor(clamped)}`}>
            {clamped}%
          </span>
        </div>
      </div>
      <span className="text-sm font-medium text-fam-gray-light">
        Document Completeness
      </span>
    </div>
  );
}
