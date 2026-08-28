"use client";

import { useParams } from "next/navigation";
import { Navbar } from "@/components/Navbar";
import { MatchGauge } from "@/components/MatchGauge";
import { SkillTagList } from "@/components/SkillTagList";
import { ExportButtons } from "@/components/ExportButtons";
import { useAnalyzeResume, useResume, useResumeAnalysis } from "@/lib/resumes";
import { useRequireAuth } from "@/lib/useRequireAuth";

export default function ResumeDetailPage() {
  useRequireAuth();
  const params = useParams<{ id: string }>();
  const resumeId = params.id;

  const { data: resume, isLoading, isError } = useResume(resumeId);
  const { data: analysis, isError: noAnalysisYet } = useResumeAnalysis(resumeId);
  const analyze = useAnalyzeResume(resumeId);

  if (isError) {
    return (
      <div className="min-h-screen">
        <Navbar />
        <main className="mx-auto max-w-3xl px-6 py-8">
          <p className="text-sm text-low">Couldn&apos;t load this resume. It may not exist, or the backend may be unreachable.</p>
        </main>
      </div>
    );
  }

  if (isLoading || !resume) {
    return (
      <div className="min-h-screen">
        <Navbar />
        <main className="mx-auto max-w-3xl px-6 py-8">
          <p className="text-sm text-text-secondary">Loading resume…</p>
        </main>
      </div>
    );
  }

  const content = resume.content;

  return (
    <div className="min-h-screen">
      <Navbar />
      <main className="mx-auto max-w-3xl px-6 py-8">
        <div className="flex items-start justify-between gap-4">
          <div>
            <h1 className="font-display text-2xl font-medium text-text-primary">{resume.label}</h1>
            <p className="mt-1 text-sm text-text-secondary">
              Version {resume.version} · {resume.parse_status}
            </p>
          </div>
          {resume.parse_status === "parsed" && <ExportButtons resumeId={resume.id} />}
        </div>

        {resume.parse_status === "failed" && (
          <p className="mt-4 rounded-card border border-low/30 bg-low/10 p-4 text-sm text-low">
            We couldn&apos;t parse this resume. Try re-uploading a text-based PDF or DOCX (not a scanned image).
          </p>
        )}

        {resume.parse_status === "parsed" && (
          <>
            {/* AI Analysis */}
            <section className="mt-8 rounded-card border border-border bg-surface p-5">
              <div className="flex items-center justify-between">
                <h2 className="font-display text-lg text-text-primary">AI Analysis</h2>
                <button
                  onClick={() => analyze.mutate(undefined)}
                  disabled={analyze.isPending}
                  className="rounded-full border border-signal-dim px-3 py-1.5 text-xs font-medium text-signal transition-colors hover:bg-signal-dim disabled:opacity-50"
                >
                  {analyze.isPending ? "Analyzing…" : analysis || noAnalysisYet ? "Re-run analysis" : "Run analysis"}
                </button>
              </div>

              {(analyze.data || analysis) && (
                <div className="mt-4 flex flex-col gap-4 sm:flex-row sm:items-start">
                  <MatchGauge score={(analyze.data || analysis)!.ats_score} size={80} />
                  <div className="flex-1 space-y-3">
                    <div>
                      <p className="text-xs font-mono uppercase tracking-wide text-text-muted">Extracted skills</p>
                      <div className="mt-1.5">
                        <SkillTagList skills={(analyze.data || analysis)!.extracted_skills} />
                      </div>
                    </div>
                    <div>
                      <p className="text-xs font-mono uppercase tracking-wide text-text-muted">Strengths</p>
                      <ul className="mt-1 list-inside list-disc text-sm text-text-secondary">
                        {(analyze.data || analysis)!.strengths.map((s, i) => (
                          <li key={i}>{s}</li>
                        ))}
                      </ul>
                    </div>
                    <div>
                      <p className="text-xs font-mono uppercase tracking-wide text-text-muted">To improve</p>
                      <ul className="mt-1 list-inside list-disc text-sm text-text-secondary">
                        {(analyze.data || analysis)!.weaknesses.map((w, i) => (
                          <li key={i}>{w}</li>
                        ))}
                      </ul>
                    </div>
                  </div>
                </div>
              )}

              {!analysis && !analyze.data && !analyze.isPending && (
                <p className="mt-3 text-sm text-text-secondary">
                  No analysis yet — run one to get an ATS score and skill breakdown.
                </p>
              )}
              {analyze.isError && (
                <p className="mt-3 text-sm text-low">
                  {analyze.error instanceof Error ? analyze.error.message : "Analysis failed."}
                </p>
              )}
            </section>

            {/* Parsed content */}
            <section className="mt-6 rounded-card border border-border bg-surface p-5">
              <h2 className="font-display text-lg text-text-primary">{content.contact.full_name}</h2>
              <p className="mt-1 text-sm text-text-secondary">
                {[content.contact.email, content.contact.phone, content.contact.location]
                  .filter(Boolean)
                  .join(" · ")}
              </p>

              {content.summary && <p className="mt-4 text-sm text-text-secondary">{content.summary}</p>}

              {content.skills.length > 0 && (
                <div className="mt-4">
                  <SkillTagList skills={content.skills} />
                </div>
              )}

              {content.experience.length > 0 && (
                <div className="mt-6">
                  <p className="text-xs font-mono uppercase tracking-wide text-text-muted">Experience</p>
                  <div className="mt-2 space-y-4">
                    {content.experience.map((exp, i) => (
                      <div key={i}>
                        <p className="text-sm font-medium text-text-primary">
                          {exp.title} · {exp.company}
                        </p>
                        <p className="text-xs text-text-muted">
                          {[exp.start_date, exp.end_date].filter(Boolean).join(" – ")}
                        </p>
                        <ul className="mt-1 list-inside list-disc text-sm text-text-secondary">
                          {exp.bullets.map((b, j) => (
                            <li key={j}>{b}</li>
                          ))}
                        </ul>
                      </div>
                    ))}
                  </div>
                </div>
              )}
            </section>
          </>
        )}
      </main>
    </div>
  );
}
