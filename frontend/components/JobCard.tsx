"use client";

import { motion } from "framer-motion";
import { MatchGauge } from "./MatchGauge";
import type { Job } from "@/lib/types";

const WORK_MODE_LABEL: Record<string, string> = {
  remote: "Remote",
  hybrid: "Hybrid",
  onsite: "Onsite",
  unknown: "Location TBD",
};

function formatSalary(job: Job): string | null {
  if (!job.salary_min && !job.salary_max) return null;
  const currency = job.salary_currency || "USD";
  const fmt = (n: number) => `${(n / 1000).toFixed(0)}k`;
  if (job.salary_min && job.salary_max) {
    return `${currency} ${fmt(job.salary_min)}–${fmt(job.salary_max)}`;
  }
  return `${currency} ${fmt((job.salary_min || job.salary_max) as number)}`;
}

export function JobCard({
  job,
  index = 0,
  onComputeMatch,
  isComputingMatch,
  onSaveToPipeline,
  isSaving,
  isSaved,
}: {
  job: Job;
  index?: number;
  onComputeMatch?: (jobId: string) => void;
  isComputingMatch?: boolean;
  onSaveToPipeline?: (jobId: string) => void;
  isSaving?: boolean;
  isSaved?: boolean;
}) {
  const salary = formatSalary(job);

  return (
    <motion.article
      initial={{ opacity: 0, y: 12 }}
      animate={{ opacity: 1, y: 0 }}
      transition={{ duration: 0.35, delay: Math.min(index * 0.04, 0.4) }}
      className="group rounded-card border border-border bg-surface p-5 shadow-panel transition-colors hover:border-signal-dim"
    >
      <div className="flex items-start justify-between gap-4">
        <div className="min-w-0 flex-1">
          <p className="truncate text-xs font-mono uppercase tracking-wide text-text-muted">
            {job.company.name} · {job.ats_provider}
          </p>
          <h3 className="mt-1 truncate font-display text-lg font-medium text-text-primary">
            {job.title}
          </h3>
          <div className="mt-2 flex flex-wrap items-center gap-x-3 gap-y-1 text-sm text-text-secondary">
            <span>{WORK_MODE_LABEL[job.work_mode]}</span>
            {job.location && <span>· {job.location}</span>}
            {salary && <span className="font-mono text-text-primary">· {salary}</span>}
            {job.visa_sponsorship && <span className="text-high">· Visa sponsorship</span>}
          </div>
          {job.tags && job.tags.length > 0 && (
            <div className="mt-3 flex flex-wrap gap-1.5">
              {job.tags.slice(0, 5).map((tag) => (
                <span
                  key={tag}
                  className="rounded-full border border-border px-2 py-0.5 font-mono text-[11px] text-text-secondary"
                >
                  {tag}
                </span>
              ))}
            </div>
          )}
        </div>

        <div className="flex flex-col items-center gap-2">
          {job.match ? (
            <MatchGauge score={job.match.score} />
          ) : (
            <button
              onClick={() => onComputeMatch?.(job.id)}
              disabled={isComputingMatch}
              className="rounded-full border border-signal-dim px-3 py-1.5 text-xs font-medium text-signal transition-colors hover:bg-signal-dim disabled:opacity-50"
            >
              {isComputingMatch ? "Scoring…" : "Get match"}
            </button>
          )}
        </div>
      </div>

      {job.match && (
        <p className="mt-4 border-t border-border pt-3 text-sm text-text-secondary">
          {job.match.reasoning}
        </p>
      )}

      <div className="mt-4 flex items-center justify-between">
        <span className="text-xs text-text-muted">
          {job.posted_at ? new Date(job.posted_at).toLocaleDateString() : "Date unknown"}
        </span>
        <div className="flex items-center gap-2">
          {onSaveToPipeline && (
            <button
              onClick={() => onSaveToPipeline(job.id)}
              disabled={isSaving || isSaved}
              className="rounded-full border border-border px-4 py-1.5 text-sm text-text-secondary transition-colors hover:border-signal-dim hover:text-text-primary disabled:opacity-50"
            >
              {isSaved ? "Saved" : isSaving ? "Saving…" : "Save"}
            </button>
          )}
          <a
            href={job.apply_url}
            target="_blank"
            rel="noopener noreferrer"
            className="rounded-full bg-signal px-4 py-1.5 text-sm font-medium text-bg transition-opacity hover:opacity-90"
          >
            View posting
          </a>
        </div>
      </div>
    </motion.article>
  );
}
