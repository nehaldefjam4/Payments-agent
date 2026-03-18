import type { Submission } from "@/lib/types";
import Card from "@/components/ui/Card";

interface DashboardStatsProps {
  submissions: Submission[];
}

interface StatItem {
  label: string;
  value: string | number;
  accent: string;
  borderColor: string;
}

export default function DashboardStats({ submissions }: DashboardStatsProps) {
  const total = submissions.length;
  const approved = submissions.filter(
    (s) => s.status === "approved" || s.status === "completed"
  ).length;
  const pending = submissions.filter(
    (s) => s.status === "pending_approval" || s.status === "processing"
  ).length;
  const avgCompleteness =
    total > 0
      ? Math.round(
          submissions.reduce((sum, s) => sum + s.completeness_pct, 0) / total
        )
      : 0;

  const stats: StatItem[] = [
    {
      label: "Total Submissions",
      value: total,
      accent: "text-accent",
      borderColor: "border-accent/30",
    },
    {
      label: "Approved",
      value: approved,
      accent: "text-success",
      borderColor: "border-success/30",
    },
    {
      label: "Pending",
      value: pending,
      accent: "text-warning",
      borderColor: "border-warning/30",
    },
    {
      label: "Avg Completeness",
      value: `${avgCompleteness}%`,
      accent:
        avgCompleteness >= 80
          ? "text-success"
          : avgCompleteness >= 50
          ? "text-warning"
          : "text-danger",
      borderColor:
        avgCompleteness >= 80
          ? "border-success/30"
          : avgCompleteness >= 50
          ? "border-warning/30"
          : "border-danger/30",
    },
  ];

  return (
    <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-4">
      {stats.map((stat) => (
        <Card
          key={stat.label}
          className={`border-l-4 ${stat.borderColor}`}
        >
          <p className="text-xs text-gray-400 uppercase tracking-wide">
            {stat.label}
          </p>
          <p className={`text-3xl font-bold mt-1 ${stat.accent}`}>
            {stat.value}
          </p>
        </Card>
      ))}
    </div>
  );
}
