import type { MissingDocument } from "@/lib/types";

interface MissingDocsListProps {
  documents: MissingDocument[];
}

export default function MissingDocsList({ documents }: MissingDocsListProps) {
  if (!documents || documents.length === 0) {
    return (
      <p className="text-success text-sm py-2">
        All required documents are present.
      </p>
    );
  }

  return (
    <div className="border border-danger/40 rounded-xl overflow-hidden">
      <div className="bg-danger/10 px-4 py-2 border-b border-danger/30">
        <h4 className="text-danger font-medium text-sm">
          Missing Documents ({documents.length})
        </h4>
      </div>
      <ul className="divide-y divide-white/5">
        {documents.map((doc) => (
          <li key={doc.id} className="px-4 py-3">
            <p className="text-gray-200 text-sm font-medium">{doc.name}</p>
            <p className="text-gray-400 text-xs mt-0.5">{doc.description}</p>
          </li>
        ))}
      </ul>
    </div>
  );
}
