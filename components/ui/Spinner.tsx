interface SpinnerProps {
  size?: "sm" | "md" | "lg";
}

const sizeClasses: Record<string, string> = {
  sm: "h-4 w-4 border-2",
  md: "h-8 w-8 border-2",
  lg: "h-12 w-12 border-3",
};

export default function Spinner({ size = "md" }: SpinnerProps) {
  return (
    <div
      className={`animate-spin rounded-full border-accent border-t-transparent ${
        sizeClasses[size]
      }`}
      role="status"
      aria-label="Loading"
    />
  );
}
