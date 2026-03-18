interface ProgressBarProps {
  value: number;
  label?: string;
}

function getBarColor(value: number): string {
  if (value >= 80) return "bg-emerald-500";
  if (value >= 50) return "bg-amber-500";
  return "bg-red-500";
}

export default function ProgressBar({ value, label }: ProgressBarProps) {
  const clamped = Math.max(0, Math.min(100, value));

  return (
    <div className="w-full">
      {label && (
        <div className="flex items-center justify-between mb-1.5">
          <span className="text-sm text-fam-gray-light">{label}</span>
          <span className="text-sm font-semibold text-fam-dark">
            {clamped}%
          </span>
        </div>
      )}
      {!label && (
        <div className="flex justify-end mb-1.5">
          <span className="text-sm font-semibold text-fam-dark">
            {clamped}%
          </span>
        </div>
      )}
      <div className="w-full h-2 bg-gray-100 rounded-full overflow-hidden">
        <div
          className={`h-full rounded-full transition-all duration-500 ${getBarColor(clamped)}`}
          style={{ width: `${clamped}%` }}
        />
      </div>
    </div>
  );
}
