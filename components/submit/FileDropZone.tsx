"use client";

import { useCallback, useRef, useState } from "react";
import { ACCEPTED_FILE_TYPES, MAX_FILE_SIZE_MB } from "@/lib/constants";

interface FileDropZoneProps {
  files: File[];
  onFilesChange: (files: File[]) => void;
}

function formatFileSize(bytes: number): string {
  if (bytes < 1024) return `${bytes} B`;
  if (bytes < 1024 * 1024) return `${(bytes / 1024).toFixed(1)} KB`;
  return `${(bytes / (1024 * 1024)).toFixed(2)} MB`;
}

export default function FileDropZone({
  files,
  onFilesChange,
}: FileDropZoneProps) {
  const [isDragging, setIsDragging] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const inputRef = useRef<HTMLInputElement>(null);

  const validateAndAddFiles = useCallback(
    (incoming: FileList | File[]) => {
      setError(null);
      const newFiles: File[] = [];
      const maxBytes = MAX_FILE_SIZE_MB * 1024 * 1024;
      const accepted = ACCEPTED_FILE_TYPES.split(",");

      for (const file of Array.from(incoming)) {
        const ext = `.${file.name.split(".").pop()?.toLowerCase()}`;
        if (!accepted.includes(ext)) {
          setError(`File type ${ext} is not accepted.`);
          continue;
        }
        if (file.size > maxBytes) {
          setError(`${file.name} exceeds the ${MAX_FILE_SIZE_MB}MB limit.`);
          continue;
        }
        newFiles.push(file);
      }

      if (newFiles.length > 0) {
        onFilesChange([...files, ...newFiles]);
      }
    },
    [files, onFilesChange]
  );

  const handleDragOver = useCallback((e: React.DragEvent) => {
    e.preventDefault();
    setIsDragging(true);
  }, []);

  const handleDragLeave = useCallback((e: React.DragEvent) => {
    e.preventDefault();
    setIsDragging(false);
  }, []);

  const handleDrop = useCallback(
    (e: React.DragEvent) => {
      e.preventDefault();
      setIsDragging(false);
      if (e.dataTransfer.files.length > 0) {
        validateAndAddFiles(e.dataTransfer.files);
      }
    },
    [validateAndAddFiles]
  );

  const handleInputChange = useCallback(
    (e: React.ChangeEvent<HTMLInputElement>) => {
      if (e.target.files && e.target.files.length > 0) {
        validateAndAddFiles(e.target.files);
      }
      if (inputRef.current) {
        inputRef.current.value = "";
      }
    },
    [validateAndAddFiles]
  );

  const removeFile = useCallback(
    (index: number) => {
      onFilesChange(files.filter((_, i) => i !== index));
    },
    [files, onFilesChange]
  );

  return (
    <div>
      <div
        onDragOver={handleDragOver}
        onDragLeave={handleDragLeave}
        onDrop={handleDrop}
        onClick={() => inputRef.current?.click()}
        className={`border-2 border-dashed rounded-2xl p-10 text-center cursor-pointer transition-all ${
          isDragging
            ? "border-fam-orange bg-fam-orange/5"
            : "border-gray-200 hover:border-fam-orange/50 hover:bg-fam-off-white"
        }`}
      >
        <input
          ref={inputRef}
          type="file"
          multiple
          accept={ACCEPTED_FILE_TYPES}
          onChange={handleInputChange}
          className="hidden"
        />
        {/* Upload Icon */}
        <div className="flex justify-center mb-4">
          <svg
            className="w-12 h-12 text-fam-orange"
            fill="none"
            stroke="currentColor"
            viewBox="0 0 24 24"
          >
            <path
              strokeLinecap="round"
              strokeLinejoin="round"
              strokeWidth={1.5}
              d="M7 16a4 4 0 01-.88-7.903A5 5 0 1115.9 6L16 6a5 5 0 011 9.9M15 13l-3-3m0 0l-3 3m3-3v12"
            />
          </svg>
        </div>
        <p className="text-fam-gray text-sm">
          Drag and drop files here, or{" "}
          <span className="text-fam-orange font-semibold">browse</span>
        </p>
        <p className="text-fam-gray-lighter text-xs mt-2">
          Accepted: PDF, JPG, PNG, DOCX, DOC, TIFF &middot; Max{" "}
          {MAX_FILE_SIZE_MB}MB per file
        </p>
      </div>

      {error && <p className="text-red-500 text-sm mt-2">{error}</p>}

      {files.length > 0 && (
        <ul className="mt-4 space-y-2">
          {files.map((file, idx) => (
            <li
              key={`${file.name}-${idx}`}
              className="flex items-center justify-between bg-fam-off-white rounded-xl px-4 py-3 border border-gray-100"
            >
              <div className="flex items-center gap-3 min-w-0">
                <svg
                  className="w-5 h-5 text-fam-gray-lighter shrink-0"
                  fill="none"
                  stroke="currentColor"
                  viewBox="0 0 24 24"
                >
                  <path
                    strokeLinecap="round"
                    strokeLinejoin="round"
                    strokeWidth={1.5}
                    d="M15.172 7l-6.586 6.586a2 2 0 102.828 2.828l6.414-6.586a4 4 0 00-5.656-5.656l-6.415 6.585a6 6 0 108.486 8.486L20.5 13"
                  />
                </svg>
                <span className="text-sm text-fam-dark truncate">
                  {file.name}
                </span>
                <span className="text-xs text-fam-gray-lighter shrink-0">
                  {formatFileSize(file.size)}
                </span>
              </div>
              <button
                type="button"
                onClick={(e) => {
                  e.stopPropagation();
                  removeFile(idx);
                }}
                className="text-fam-gray-lighter hover:text-red-500 transition-colors ml-3 shrink-0"
                aria-label={`Remove ${file.name}`}
              >
                <svg
                  className="w-4 h-4"
                  fill="none"
                  stroke="currentColor"
                  viewBox="0 0 24 24"
                >
                  <path
                    strokeLinecap="round"
                    strokeLinejoin="round"
                    strokeWidth={2}
                    d="M6 18L18 6M6 6l12 12"
                  />
                </svg>
              </button>
            </li>
          ))}
        </ul>
      )}
    </div>
  );
}
