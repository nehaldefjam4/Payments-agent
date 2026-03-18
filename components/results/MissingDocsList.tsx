import type { MissingDocument } from "@/lib/types";

interface MissingDocsListProps {
  documents: MissingDocument[];
}

export default function MissingDocsList({ documents }: MissingDocsListProps) {
  if (!documents || documents.length === 0) {
    return (
      <div className="bg-emerald-50 border border-emerald-200 rounded-2xl px-5 py-4">
        <p className="text-emerald-700 text-sm font-medium">
          All required documents are present.
        </p>
      </div>
    );
  }

  return (
    <div className="bg-white rounded-2xl shadow-sm border border-gray-100 overflow-hidden border-l-4 border-l-fam-orange">
      <div className="bg-red-50 px-5 py-3 border-b border-red-100">
        <h4 className="text-red-600 font-semibold text-sm">
          Missing Documents ({documents.length})
        </h4>
      </div>
      <ul className="divide-y divide-gray-50">
        {documents.map((doc) => (
          <li key={doc.id} className="px-5 py-3.5">
            <p className="text-fam-dark text-sm font-medium">{doc.name}</p>
            <p className="text-fam-gray-lighter text-xs mt-0.5">
              {doc.description}
            </p>
          </li>
        ))}
      </ul>
    </div>
  );
}
