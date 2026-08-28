"use client";

import { useState } from "react";
import { useExportResume } from "@/lib/resumes";
import type { DocumentFormat } from "@/lib/types";

export function ExportButtons({ resumeId }: { resumeId: string }) {
  const exportResume = useExportResume(resumeId);
  const [lastFormat, setLastFormat] = useState<DocumentFormat | null>(null);

  const handleExport = (format: DocumentFormat) => {
    setLastFormat(format);
    exportResume.mutate(format);
  };

  return (
    <div className="flex items-center gap-2">
      <button
        onClick={() => handleExport("pdf")}
        disabled={exportResume.isPending}
        className="rounded-full border border-border px-3 py-1.5 text-sm text-text-secondary transition-colors hover:border-signal-dim hover:text-text-primary disabled:opacity-50"
      >
        {exportResume.isPending && lastFormat === "pdf" ? "Exporting…" : "Export PDF"}
      </button>
      <button
        onClick={() => handleExport("docx")}
        disabled={exportResume.isPending}
        className="rounded-full border border-border px-3 py-1.5 text-sm text-text-secondary transition-colors hover:border-signal-dim hover:text-text-primary disabled:opacity-50"
      >
        {exportResume.isPending && lastFormat === "docx" ? "Exporting…" : "Export DOCX"}
      </button>
      {exportResume.isSuccess && (
        <span className="text-xs text-high">Document generated and saved to your account.</span>
      )}
      {exportResume.isError && (
        <span className="text-xs text-low">Export failed. Try again.</span>
      )}
    </div>
  );
}
