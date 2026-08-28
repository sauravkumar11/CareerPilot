"use client";

import { useParams } from "next/navigation";
import { Navbar } from "@/components/Navbar";
import { useApplication, useGenerateInterviewPrep, useInterviewPrep } from "@/lib/applications";
import { useRequireAuth } from "@/lib/useRequireAuth";

function QuestionList({ title, questions }: { title: string; questions: string[] }) {
  if (questions.length === 0) return null;
  return (
    <div>
      <p className="text-xs font-mono uppercase tracking-wide text-text-muted">{title}</p>
      <ul className="mt-1.5 list-inside list-disc space-y-1 text-sm text-text-secondary">
        {questions.map((q, i) => (
          <li key={i}>{q}</li>
        ))}
      </ul>
    </div>
  );
}

export default function ApplicationDetailPage() {
  useRequireAuth();
  const params = useParams<{ id: string }>();
  const applicationId = params.id;

  const { data: application, isError } = useApplication(applicationId);

  const { data: prep, isError: noPrepYet } = useInterviewPrep(applicationId);
  const generatePrep = useGenerateInterviewPrep(applicationId);

  const displayedPrep = generatePrep.data || prep;

  if (isError) {
    return (
      <div className="min-h-screen">
        <Navbar />
        <main className="mx-auto max-w-3xl px-6 py-8">
          <p className="text-sm text-low">Couldn&apos;t load this application. It may not exist, or the backend may be unreachable.</p>
        </main>
      </div>
    );
  }

  if (!application) {
    return (
      <div className="min-h-screen">
        <Navbar />
        <main className="mx-auto max-w-3xl px-6 py-8">
          <p className="text-sm text-text-secondary">Loading application…</p>
        </main>
      </div>
    );
  }

  return (
    <div className="min-h-screen">
      <Navbar />
      <main className="mx-auto max-w-3xl px-6 py-8">
        <h1 className="font-display text-2xl font-medium text-text-primary">{application.job.title}</h1>
        <p className="mt-1 text-sm text-text-secondary">
          {application.job.company.name} · {application.status}
        </p>

        <section className="mt-8 rounded-card border border-border bg-surface p-5">
          <div className="flex items-center justify-between">
            <h2 className="font-display text-lg text-text-primary">Interview Prep</h2>
            <div className="flex gap-2">
              {displayedPrep && (
                <button
                  onClick={() => generatePrep.mutate(true)}
                  disabled={generatePrep.isPending}
                  className="rounded-full border border-border px-3 py-1.5 text-xs text-text-secondary transition-colors hover:text-text-primary disabled:opacity-50"
                  title="Re-run the web search for company news too"
                >
                  Refresh news
                </button>
              )}
              <button
                onClick={() => generatePrep.mutate(false)}
                disabled={generatePrep.isPending}
                className="rounded-full border border-signal-dim px-3 py-1.5 text-xs font-medium text-signal transition-colors hover:bg-signal-dim disabled:opacity-50"
              >
                {generatePrep.isPending
                  ? "Generating…"
                  : displayedPrep
                    ? "Regenerate"
                    : "Generate prep"}
              </button>
            </div>
          </div>

          {generatePrep.isError && (
            <p className="mt-3 text-sm text-low">
              {generatePrep.error instanceof Error ? generatePrep.error.message : "Generation failed."}
            </p>
          )}

          {!displayedPrep && !generatePrep.isPending && noPrepYet && (
            <p className="mt-3 text-sm text-text-secondary">
              No prep generated yet — click &quot;Generate prep&quot; for a company summary, likely
              interview rounds, and tailored practice questions.
            </p>
          )}

          {displayedPrep && (
            <div className="mt-4 space-y-5">
              <p className="text-sm text-text-secondary">{displayedPrep.company_summary}</p>

              {displayedPrep.latest_news.length > 0 && (
                <div>
                  <p className="text-xs font-mono uppercase tracking-wide text-text-muted">Recent news</p>
                  <ul className="mt-1.5 list-inside list-disc space-y-1 text-sm text-text-secondary">
                    {displayedPrep.latest_news.map((n, i) => (
                      <li key={i}>{n}</li>
                    ))}
                  </ul>
                </div>
              )}

              {displayedPrep.tech_stack.length > 0 && (
                <div>
                  <p className="text-xs font-mono uppercase tracking-wide text-text-muted">Tech stack</p>
                  <div className="mt-1.5 flex flex-wrap gap-1.5">
                    {displayedPrep.tech_stack.map((t) => (
                      <span
                        key={t}
                        className="rounded-full border border-border px-2.5 py-1 font-mono text-xs text-text-secondary"
                      >
                        {t}
                      </span>
                    ))}
                  </div>
                </div>
              )}

              <QuestionList title="Likely interview rounds" questions={displayedPrep.likely_rounds} />
              <QuestionList title="Behavioral" questions={displayedPrep.behavioral_questions} />
              <QuestionList title="Coding" questions={displayedPrep.coding_questions} />
              <QuestionList title="System design" questions={displayedPrep.system_design_questions} />
              <QuestionList title="Frontend" questions={displayedPrep.frontend_questions} />
              <QuestionList title="Low-level design" questions={displayedPrep.lld_questions} />
              <QuestionList title="High-level design" questions={displayedPrep.hld_questions} />
            </div>
          )}
        </section>
      </main>
    </div>
  );
}
