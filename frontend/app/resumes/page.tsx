"use client";

import Link from "next/link";
import { Navbar } from "@/components/Navbar";
import { ResumeUploadDropzone } from "@/components/ResumeUploadDropzone";
import { useResumes } from "@/lib/resumes";
import { useRequireAuth } from "@/lib/useRequireAuth";

const STATUS_LABEL: Record<string, { text: string; className: string }> = {
  pending: { text: "Parsing…", className: "text-medium" },
  parsed: { text: "Ready", className: "text-high" },
  failed: { text: "Parse failed", className: "text-low" },
};

export default function ResumesPage() {
  useRequireAuth();
  const { data: resumes, isLoading, isError } = useResumes();
  const roots = resumes?.filter((r) => !r.parent_resume_id) ?? [];

  return (
    <div className="min-h-screen">
      <Navbar />
      <main className="mx-auto max-w-3xl px-6 py-8">
        <h1 className="font-display text-2xl font-medium text-text-primary">Resumes</h1>
        <p className="mt-1 text-sm text-text-secondary">
          Upload a resume to get an AI analysis, tailor it for specific roles, and export it.
        </p>

        <div className="mt-6">
          <ResumeUploadDropzone />
        </div>

        <div className="mt-8 space-y-3">
          {isLoading && <p className="text-sm text-text-secondary">Loading resumes…</p>}
          {isError && (
            <p className="text-sm text-low">Couldn&apos;t load your resumes. Make sure the backend is running, then refresh.</p>
          )}
          {roots.length === 0 && !isLoading && !isError && (
            <p className="text-sm text-text-secondary">No resumes yet — upload one above.</p>
          )}
          {roots.map((resume) => {
            const status = STATUS_LABEL[resume.parse_status];
            return (
              <Link
                key={resume.id}
                href={`/resumes/${resume.id}`}
                className="flex items-center justify-between rounded-card border border-border bg-surface p-4 transition-colors hover:border-signal-dim"
              >
                <div>
                  <p className="font-display text-base text-text-primary">
                    {resume.label}
                    {resume.is_primary && (
                      <span className="ml-2 rounded-full border border-signal-dim px-2 py-0.5 text-xs text-signal">
                        Primary
                      </span>
                    )}
                  </p>
                  <p className="mt-1 text-xs text-text-muted">
                    {resume.content?.experience?.length ?? 0} roles ·{" "}
                    {resume.content?.skills?.length ?? 0} skills
                  </p>
                </div>
                <span className={`text-sm ${status?.className ?? "text-text-secondary"}`}>
                  {status?.text ?? resume.parse_status}
                </span>
              </Link>
            );
          })}
        </div>
      </main>
    </div>
  );
}
