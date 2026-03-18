import type { FileResult } from "@/lib/types";
import Badge from "@/components/ui/Badge";

interface DocumentTableProps {
  files: FileResult[];
}

function getConfidenceColor(confidence: number): string {
  if (confidence >= 0.8) return "bg-success";
  if (confidence >= 0.5) return "bg-warning";
  return "bg-danger";
}

function getStatusInfo(file: FileResult): {
  label: string;
  variant: "success" | "warning" | "danger";
} {
  const hasErrors = file.issues.some((i) => i.severity === "error");
  const hasWarnings = file.issues.some((i) => i.severity === "warning");

  if (hasErrors) return { label: "Error", variant: "danger" };
  if (hasWarnings) return { label: "Warning", variant: "warning" };
  return { label: "Valid", variant: "success" };
}

export default function DocumentTable({ files }: DocumentTableProps) {
  if (!files || files.length === 0) {
    return (
      <p className="text-gray-400 text-sm text-center py-4">
        No files processed yet.
      </p>
    );
  }

  return (
    <div className="overflow-x-auto">
      <table className="w-full text-sm">
        <thead>
          <tr className="border-b border-white/10">
            <th className="text-left py-3 px-4 text-gray-400 font-medium">
              File Name
            </th>
            <th className="text-left py-3 px-4 text-gray-400 font-medium">
              Classified As
            </th>
            <th className="text-left py-3 px-4 text-gray-400 font-medium">
              Confidence
            </th>
            <th className="text-left py-3 px-4 text-gray-400 font-medium">
              Status
            </th>
          </tr>
        </thead>
        <tbody>
          {files.map((file, idx) => {
            const status = getStatusInfo(file);
            const pct = Math.round(file.confidence * 100);

            return (
              <tr
                key={`${file.file_name}-${idx}`}
                className="border-b border-white/5 hover:bg-white/5 transition-colors"
              >
                <td className="py-3 px-4 text-gray-200 truncate max-w-[200px]">
                  {file.file_name}
                </td>
                <td className="py-3 px-4 text-gray-300">
                  {file.classified_label || "Unknown"}
                </td>
                <td className="py-3 px-4">
                  <div className="flex items-center gap-2">
                    <div className="w-20 h-2 bg-primary rounded-full overflow-hidden">
                      <div
                        className={`h-full rounded-full ${getConfidenceColor(file.confidence)}`}
                        style={{ width: `${pct}%` }}
                      />
                    </div>
                    <span className="text-gray-400 text-xs">{pct}%</span>
                  </div>
                </td>
                <td className="py-3 px-4">
                  <Badge label={status.label} variant={status.variant} />
                </td>
              </tr>
            );
          })}
        </tbody>
      </table>
    </div>
  );
}
