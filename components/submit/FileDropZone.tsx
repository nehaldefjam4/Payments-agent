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

export default function FileDropZone({ files, onFilesChange }: FileDropZoneProps) {
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
        className={`border-2 border-dashed rounded-xl p-8 text-center cursor-pointer transition-colors ${
          isDragging
            ? "border-accent bg-accent/10"
            : "border-gray-600 hover:border-accent/50 hover:bg-white/5"
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
        <div className="text-4xl mb-3">
          {isDragging ? "\u{1F4E5}" : "\u{1F4C1}"}
        </div>
        <p className="text-gray-300 text-sm">
          Drag and drop files here, or{" "}
          <span className="text-accent font-medium">browse</span>
        </p>
        <p className="text-gray-500 text-xs mt-2">
          Accepted: PDF, JPG, PNG, DOCX, DOC, TIFF &middot; Max {MAX_FILE_SIZE_MB}MB per file
        </p>
      </div>

      {error && (
        <p className="text-danger text-sm mt-2">{error}</p>
      )}

      {files.length > 0 && (
        <ul className="mt-4 space-y-2">
          {files.map((file, idx) => (
            <li
              key={`${file.name}-${idx}`}
              className="flex items-center justify-between bg-primary rounded-lg px-4 py-2"
            >
              <div className="flex items-center gap-3 min-w-0">
                <span className="text-gray-400 text-sm shrink-0">
                  {"\u{1F4CE}"}
                </span>
                <span className="text-sm text-gray-200 truncate">
                  {file.name}
                </span>
                <span className="text-xs text-gray-500 shrink-0">
                  {formatFileSize(file.size)}
                </span>
              </div>
              <button
                type="button"
                onClick={() => removeFile(idx)}
                className="text-gray-400 hover:text-danger transition-colors ml-3 shrink-0"
                aria-label={`Remove ${file.name}`}
              >
                &times;
              </button>
            </li>
          ))}
        </ul>
      )}
    </div>
  );
}
