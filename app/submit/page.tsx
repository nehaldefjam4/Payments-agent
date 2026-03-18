"use client";

import { useState, useEffect } from "react";
import { useRouter } from "next/navigation";
import { fetchTransactionTypes, submitDocuments } from "@/lib/api";
import type { TransactionType } from "@/lib/types";
import FileDropZone from "@/components/submit/FileDropZone";
import Spinner from "@/components/ui/Spinner";

export default function SubmitPage() {
  const router = useRouter();
  const [transactionTypes, setTransactionTypes] = useState<
    Record<string, TransactionType>
  >({});
  const [selectedType, setSelectedType] = useState("");
  const [brokerName, setBrokerName] = useState("");
  const [brokerEmail, setBrokerEmail] = useState("");
  const [propertyRef, setPropertyRef] = useState("");
  const [files, setFiles] = useState<File[]>([]);
  const [submitting, setSubmitting] = useState(false);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    fetchTransactionTypes()
      .then((data) => setTransactionTypes(data))
      .catch(() => setError("Failed to load transaction types"));
  }, []);

  const selectedTypeData = selectedType
    ? transactionTypes[selectedType]
    : null;

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!selectedType || files.length === 0) return;

    setSubmitting(true);
    setError(null);

    try {
      const formData = new FormData();
      formData.append("transaction_type", selectedType);
      formData.append("broker_name", brokerName);
      formData.append("broker_email", brokerEmail);
      formData.append("property_ref", propertyRef);
      files.forEach((file) => formData.append("files", file));

      const result = await submitDocuments(formData);
      router.push(`/submissions/${result.submission_id}`);
    } catch (err) {
      setError(
        err instanceof Error ? err.message : "Submission failed. Please try again."
      );
    } finally {
      setSubmitting(false);
    }
  };

  return (
    <div className="max-w-2xl mx-auto">
      <h1 className="text-3xl font-bold text-white mb-8">Submit Documents</h1>

      <form onSubmit={handleSubmit} className="space-y-6">
        {/* Transaction Type */}
        <div>
          <label
            htmlFor="transaction_type"
            className="block text-sm font-medium text-gray-300 mb-2"
          >
            Transaction Type
          </label>
          <select
            id="transaction_type"
            value={selectedType}
            onChange={(e) => setSelectedType(e.target.value)}
            className="w-full rounded-lg bg-primary border border-white/10 px-4 py-3 text-white focus:outline-none focus:ring-2 focus:ring-accent"
          >
            <option value="">Select a transaction type...</option>
            {Object.entries(transactionTypes).map(([key, type]) => (
              <option key={key} value={key}>
                {type.label}
              </option>
            ))}
          </select>
        </div>

        {/* Required Documents Info */}
        {selectedTypeData && (
          <div className="rounded-lg bg-primary-light border border-white/10 p-4">
            <h3 className="text-sm font-semibold text-accent mb-2">
              Required Documents ({selectedTypeData.required_count})
            </h3>
            <ul className="space-y-1">
              {selectedTypeData.required.map((doc) => (
                <li
                  key={doc.id}
                  className="text-sm text-gray-300 flex items-start gap-2"
                >
                  <span className="text-accent mt-0.5">*</span>
                  <span>
                    <span className="text-white">{doc.name}</span>
                    {doc.description && (
                      <span className="text-gray-400 ml-1">
                        -- {doc.description}
                      </span>
                    )}
                  </span>
                </li>
              ))}
            </ul>
            {selectedTypeData.optional_count > 0 && (
              <>
                <h3 className="text-sm font-semibold text-gray-400 mt-4 mb-2">
                  Optional Documents ({selectedTypeData.optional_count})
                </h3>
                <ul className="space-y-1">
                  {selectedTypeData.optional.map((doc) => (
                    <li key={doc.id} className="text-sm text-gray-400">
                      {doc.name}
                    </li>
                  ))}
                </ul>
              </>
            )}
          </div>
        )}

        {/* Broker Name */}
        <div>
          <label
            htmlFor="broker_name"
            className="block text-sm font-medium text-gray-300 mb-2"
          >
            Broker Name
          </label>
          <input
            id="broker_name"
            type="text"
            value={brokerName}
            onChange={(e) => setBrokerName(e.target.value)}
            placeholder="Enter broker name"
            className="w-full rounded-lg bg-primary border border-white/10 px-4 py-3 text-white placeholder-gray-500 focus:outline-none focus:ring-2 focus:ring-accent"
          />
        </div>

        {/* Broker Email */}
        <div>
          <label
            htmlFor="broker_email"
            className="block text-sm font-medium text-gray-300 mb-2"
          >
            Broker Email
          </label>
          <input
            id="broker_email"
            type="email"
            value={brokerEmail}
            onChange={(e) => setBrokerEmail(e.target.value)}
            placeholder="broker@example.com"
            className="w-full rounded-lg bg-primary border border-white/10 px-4 py-3 text-white placeholder-gray-500 focus:outline-none focus:ring-2 focus:ring-accent"
          />
        </div>

        {/* Property Reference */}
        <div>
          <label
            htmlFor="property_ref"
            className="block text-sm font-medium text-gray-300 mb-2"
          >
            Property Reference
          </label>
          <input
            id="property_ref"
            type="text"
            value={propertyRef}
            onChange={(e) => setPropertyRef(e.target.value)}
            placeholder="e.g. PROP-2026-001"
            className="w-full rounded-lg bg-primary border border-white/10 px-4 py-3 text-white placeholder-gray-500 focus:outline-none focus:ring-2 focus:ring-accent"
          />
        </div>

        {/* File Drop Zone */}
        <div>
          <label className="block text-sm font-medium text-gray-300 mb-2">
            Upload Documents
          </label>
          <FileDropZone files={files} onFilesChange={setFiles} />
        </div>

        {/* Error Message */}
        {error && (
          <div className="rounded-lg bg-danger/20 border border-danger/50 px-4 py-3 text-danger text-sm">
            {error}
          </div>
        )}

        {/* Submit Button */}
        <button
          type="submit"
          disabled={submitting || !selectedType || files.length === 0}
          className="w-full flex items-center justify-center gap-2 rounded-lg bg-accent hover:bg-accent-dark disabled:opacity-50 disabled:cursor-not-allowed px-6 py-3 text-white font-semibold transition-colors"
        >
          {submitting ? (
            <>
              <Spinner size="sm" />
              Processing...
            </>
          ) : (
            "Submit Documents"
          )}
        </button>
      </form>
    </div>
  );
}
