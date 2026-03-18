import type { FileResult } from "@/lib/types";
import Badge from "@/components/ui/Badge";

interface DocumentTableProps {
  files: FileResult[];
}

function getConfidenceColor(confidence: number): string {
  if (confidence >= 0.8) return "bg-emerald-500";
  if (confidence >= 0.5) return "bg-amber-500";
  return "bg-red-500";
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
      <p className="text-fam-gray-lighter text-sm text-center py-4">
        No files processed yet.
      </p>
    );
  }

  return (
    <div className="bg-white rounded-2xl shadow-sm border border-gray-100 overflow-hidden">
      <div className="overflow-x-auto">
        <table className="w-full text-sm">
          <thead>
            <tr className="border-b border-gray-100 bg-fam-off-white">
              <th className="text-left py-3 px-5 text-fam-gray-light font-semibold text-xs uppercase tracking-wider">
                File Name
              </th>
              <th className="text-left py-3 px-5 text-fam-gray-light font-semibold text-xs uppercase tracking-wider">
                Classified As
              </th>
              <th className="text-left py-3 px-5 text-fam-gray-light font-semibold text-xs uppercase tracking-wider">
                Confidence
              </th>
              <th className="text-left py-3 px-5 text-fam-gray-light font-semibold text-xs uppercase tracking-wider">
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
                  className={`border-b border-gray-50 hover:bg-fam-off-white transition-colors ${
                    idx % 2 === 1 ? "bg-gray-50/50" : "bg-white"
                  }`}
                >
                  <td className="py-3.5 px-5 text-fam-dark font-medium truncate max-w-[200px]">
                    {file.file_name}
                  </td>
                  <td className="py-3.5 px-5 text-fam-gray-light">
                    {file.classified_label || "Unknown"}
                  </td>
                  <td className="py-3.5 px-5">
                    <div className="flex items-center gap-2">
                      <div className="w-20 h-1.5 bg-gray-100 rounded-full overflow-hidden">
                        <div
                          className={`h-full rounded-full ${getConfidenceColor(file.confidence)}`}
                          style={{ width: `${pct}%` }}
                        />
                      </div>
                      <span className="text-fam-gray-lighter text-xs">
                        {pct}%
                      </span>
                    </div>
                  </td>
                  <td className="py-3.5 px-5">
                    <Badge label={status.label} variant={status.variant} />
                  </td>
                </tr>
              );
            })}
          </tbody>
        </table>
      </div>
    </div>
  );
}
