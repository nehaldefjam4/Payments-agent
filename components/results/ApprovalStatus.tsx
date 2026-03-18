interface ApprovalStatusProps {
  level: string;
  status: string;
}

const levelStyles: Record<string, string> = {
  auto_approved:
    "bg-emerald-50 text-emerald-700 border-emerald-200",
  agent: "bg-blue-50 text-blue-700 border-blue-200",
  manager: "bg-amber-50 text-amber-700 border-amber-200",
  director: "bg-red-50 text-red-700 border-red-200",
};

const levelLabels: Record<string, string> = {
  auto_approved: "Auto-Approved",
  agent: "Agent Review",
  manager: "Manager Review",
  director: "Director Review",
};

export default function ApprovalStatus({
  level,
  status,
}: ApprovalStatusProps) {
  const style =
    levelStyles[level] || "bg-gray-50 text-gray-600 border-gray-200";
  const label = levelLabels[level] || level;

  return (
    <div
      className={`inline-flex items-center gap-2 px-4 py-2 rounded-full border font-medium ${style}`}
    >
      <span className="text-sm font-semibold">{label}</span>
      <span className="text-xs opacity-60">&middot;</span>
      <span className="text-xs capitalize">{status}</span>
    </div>
  );
}
