interface BadgeProps {
  label: string;
  variant?: "success" | "warning" | "danger" | "info" | "default";
}

const variantClasses: Record<string, string> = {
  success: "bg-success/20 text-success",
  warning: "bg-warning/20 text-warning",
  danger: "bg-danger/20 text-danger",
  info: "bg-blue-500/20 text-blue-400",
  default: "bg-gray-500/20 text-gray-300",
};

export default function Badge({ label, variant = "default" }: BadgeProps) {
  return (
    <span
      className={`inline-flex items-center px-2.5 py-0.5 rounded-full text-xs font-medium ${
        variantClasses[variant] || variantClasses.default
      }`}
    >
      {label}
    </span>
  );
}
