interface ApprovalStatusProps {
  level: string;
  status: string;
}

const levelStyles: Record<string, string> = {
  auto_approved: "bg-success/20 text-success border-success/30",
  agent: "bg-blue-500/20 text-blue-400 border-blue-500/30",
  manager: "bg-warning/20 text-warning border-warning/30",
  director: "bg-danger/20 text-danger border-danger/30",
};

const levelLabels: Record<string, string> = {
  auto_approved: "Auto-Approved",
  agent: "Agent Review",
  manager: "Manager Review",
  director: "Director Review",
};

export default function ApprovalStatus({ level, status }: ApprovalStatusProps) {
  const style = levelStyles[level] || "bg-gray-500/20 text-gray-300 border-gray-500/30";
  const label = levelLabels[level] || level;

  return (
    <div className={`inline-flex items-center gap-2 px-3 py-1.5 rounded-lg border ${style}`}>
      <span className="text-sm font-medium">{label}</span>
      <span className="text-xs opacity-75">&middot;</span>
      <span className="text-xs capitalize">{status}</span>
    </div>
  );
}
