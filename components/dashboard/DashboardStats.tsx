import type { Submission } from "@/lib/types";

interface DashboardStatsProps {
  submissions: Submission[];
}

interface StatItem {
  label: string;
  value: string | number;
  borderColor: string;
  valueColor: string;
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
      borderColor: "border-t-fam-orange",
      valueColor: "text-fam-orange",
    },
    {
      label: "Approved",
      value: approved,
      borderColor: "border-t-emerald-500",
      valueColor: "text-emerald-600",
    },
    {
      label: "Pending",
      value: pending,
      borderColor: "border-t-amber-500",
      valueColor: "text-amber-500",
    },
    {
      label: "Avg Completeness",
      value: `${avgCompleteness}%`,
      borderColor:
        avgCompleteness >= 80
          ? "border-t-emerald-500"
          : avgCompleteness >= 50
          ? "border-t-amber-500"
          : "border-t-red-500",
      valueColor:
        avgCompleteness >= 80
          ? "text-emerald-600"
          : avgCompleteness >= 50
          ? "text-amber-500"
          : "text-red-500",
    },
  ];

  return (
    <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-4">
      {stats.map((stat) => (
        <div
          key={stat.label}
          className={`bg-white rounded-2xl shadow-sm border border-gray-100 border-t-4 ${stat.borderColor} p-5`}
        >
          <p className="text-xs text-fam-gray-lighter uppercase tracking-wider font-semibold">
            {stat.label}
          </p>
          <p className={`text-3xl font-bold mt-2 ${stat.valueColor}`}>
            {stat.value}
          </p>
        </div>
      ))}
    </div>
  );
}
