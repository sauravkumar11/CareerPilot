"use client";

import { useState, useRef } from "react";
import { useUploadResume } from "@/lib/resumes";

const ALLOWED_TYPES = [
  "application/pdf",
  "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
];

export function ResumeUploadDropzone() {
  const [isDragging, setIsDragging] = useState(false);
  const [label, setLabel] = useState("");
  const inputRef = useRef<HTMLInputElement>(null);
  const upload = useUploadResume();

  const handleFile = (file: File | undefined) => {
    if (!file) return;
    if (!ALLOWED_TYPES.includes(file.type)) {
      upload.reset();
      return;
    }
    upload.mutate({ file, label: label || file.name.replace(/\.(pdf|docx)$/i, "") });
  };

  return (
    <div
      onDragOver={(e) => {
        e.preventDefault();
        setIsDragging(true);
      }}
      onDragLeave={() => setIsDragging(false)}
      onDrop={(e) => {
        e.preventDefault();
        setIsDragging(false);
        handleFile(e.dataTransfer.files?.[0]);
      }}
      className={`rounded-card border-2 border-dashed p-8 text-center transition-colors ${
        isDragging ? "border-signal bg-signal-dim/20" : "border-border"
      }`}
    >
      <p className="font-display text-base text-text-primary">Upload your resume</p>
      <p className="mt-1 text-sm text-text-secondary">PDF or DOCX, up to 5MB. Drag and drop, or</p>

      <input
        value={label}
        onChange={(e) => setLabel(e.target.value)}
        placeholder="Label (optional, e.g. Backend / Python)"
        className="mx-auto mt-4 block w-full max-w-xs rounded-lg border border-border bg-surface px-3 py-2 text-sm text-text-primary outline-none focus:border-signal"
      />

      <input
        ref={inputRef}
        type="file"
        accept=".pdf,.docx"
        className="hidden"
        onChange={(e) => handleFile(e.target.files?.[0])}
      />
      <button
        onClick={() => inputRef.current?.click()}
        disabled={upload.isPending}
        className="mt-4 rounded-full bg-signal px-4 py-2 text-sm font-medium text-bg transition-opacity hover:opacity-90 disabled:opacity-50"
      >
        {upload.isPending ? "Uploading…" : "Choose file"}
      </button>

      {upload.isError && (
        <p className="mt-3 text-sm text-low">
          {upload.error instanceof Error ? upload.error.message : "Upload failed — please try again."}
        </p>
      )}
      {upload.isSuccess && <p className="mt-3 text-sm text-high">Resume uploaded and parsed.</p>}
    </div>
  );
}
