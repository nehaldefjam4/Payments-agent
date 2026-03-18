interface BadgeProps {
  label: string;
  variant?: "success" | "warning" | "danger" | "info" | "default";
}

const variantClasses: Record<string, string> = {
  success: "bg-emerald-50 text-emerald-700 border border-emerald-200",
  warning: "bg-amber-50 text-amber-700 border border-amber-200",
  danger: "bg-red-50 text-red-700 border border-red-200",
  info: "bg-blue-50 text-blue-700 border border-blue-200",
  default: "bg-gray-100 text-gray-600 border border-gray-200",
};

export default function Badge({ label, variant = "default" }: BadgeProps) {
  return (
    <span
      className={`inline-flex items-center px-3 py-0.5 rounded-full text-xs font-semibold ${
        variantClasses[variant] || variantClasses.default
      }`}
    >
      {label}
    </span>
  );
}
