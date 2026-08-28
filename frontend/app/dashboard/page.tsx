"use client";

import { useState } from "react";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { Navbar } from "@/components/Navbar";
import { JobCard } from "@/components/JobCard";
import { apiFetch } from "@/lib/api";
import { useRequireAuth } from "@/lib/useRequireAuth";
import type { MatchScore, PaginatedJobs } from "@/lib/types";

const WORK_MODES = ["", "remote", "hybrid", "onsite"] as const;

export default function DashboardPage() {
  useRequireAuth();
  const [keyword, setKeyword] = useState("");
  const [workMode, setWorkMode] = useState<(typeof WORK_MODES)[number]>("");
  const [postedWithinDays, setPostedWithinDays] = useState<number | "">("");
  const [scoringJobId, setScoringJobId] = useState<string | null>(null);
  const [savedJobIds, setSavedJobIds] = useState<Set<string>>(new Set());
  const [savingJobId, setSavingJobId] = useState<string | null>(null);
  const queryClient = useQueryClient();

  const params = new URLSearchParams();
  if (keyword) params.set("keyword", keyword);
  if (workMode) params.set("work_mode", workMode);
  if (postedWithinDays) params.set("posted_within_days", String(postedWithinDays));

  const { data, isLoading, isError } = useQuery<PaginatedJobs>({
    queryKey: ["jobs", keyword, workMode, postedWithinDays],
    queryFn: () => apiFetch<PaginatedJobs>(`/jobs?${params.toString()}`),
  });

  const computeMatch = useMutation({
    mutationFn: (jobId: string) => {
      setScoringJobId(jobId);
      return apiFetch<MatchScore>(`/jobs/${jobId}/match`, { method: "POST" });
    },
    onSuccess: (match, jobId) => {
      queryClient.setQueryData<PaginatedJobs | undefined>(
        ["jobs", keyword, workMode, postedWithinDays],
        (old) =>
          old
            ? {
                ...old,
                items: old.items.map((job) => (job.id === jobId ? { ...job, match } : job)),
              }
            : old
      );
      setScoringJobId(null);
    },
    onError: () => setScoringJobId(null),
  });

  const saveToPipeline = useMutation({
    mutationFn: (jobId: string) => {
      setSavingJobId(jobId);
      return apiFetch("/applications", {
        method: "POST",
        body: JSON.stringify({ job_id: jobId }),
      });
    },
    onSuccess: (_, jobId) => {
      setSavedJobIds((prev) => new Set(prev).add(jobId));
      setSavingJobId(null);
      queryClient.invalidateQueries({ queryKey: ["applications"] });
    },
    onError: () => setSavingJobId(null),
  });

  return (
    <div className="min-h-screen">
      <Navbar />
      <main className="mx-auto max-w-5xl px-6 py-8">
        <div className="mb-6">
          <h1 className="font-display text-2xl font-medium text-text-primary">Flight deck</h1>
          <p className="mt-1 text-sm text-text-secondary">
            Open roles from your tracked companies, ranked by signal strength.
          </p>
        </div>

        <div className="mb-6 flex flex-wrap gap-3">
          <input
            value={keyword}
            onChange={(e) => setKeyword(e.target.value)}
            placeholder="Search titles — e.g. backend, react"
            className="flex-1 min-w-[220px] rounded-lg border border-border bg-surface px-3.5 py-2 text-sm text-text-primary outline-none focus:border-signal"
          />
          <select
            value={workMode}
            onChange={(e) => setWorkMode(e.target.value as typeof workMode)}
            className="rounded-lg border border-border bg-surface px-3 py-2 text-sm text-text-primary outline-none focus:border-signal"
          >
            <option value="">Any location</option>
            <option value="remote">Remote</option>
            <option value="hybrid">Hybrid</option>
            <option value="onsite">Onsite</option>
          </select>
          <select
            value={postedWithinDays}
            onChange={(e) => setPostedWithinDays(e.target.value ? Number(e.target.value) : "")}
            className="rounded-lg border border-border bg-surface px-3 py-2 text-sm text-text-primary outline-none focus:border-signal"
          >
            <option value="">Any time</option>
            <option value="1">Last 24 hours</option>
            <option value="3">Last 3 days</option>
            <option value="7">Last 7 days</option>
          </select>
        </div>

        {isLoading && <p className="text-sm text-text-secondary">Loading postings…</p>}
        {isError && (
          <p className="text-sm text-low">
            Couldn&apos;t load jobs. Make sure the backend is running and companies have been synced.
          </p>
        )}
        {data && data.items.length === 0 && (
          <p className="text-sm text-text-secondary">
            No postings match yet — try syncing companies via <code className="font-mono">POST /companies/{"{id}"}/sync</code>.
          </p>
        )}

        <div className="space-y-3">
          {data?.items.map((job, i) => (
            <JobCard
              key={job.id}
              job={job}
              index={i}
              onComputeMatch={(jobId) => computeMatch.mutate(jobId)}
              isComputingMatch={scoringJobId === job.id}
              onSaveToPipeline={(jobId) => saveToPipeline.mutate(jobId)}
              isSaving={savingJobId === job.id}
              isSaved={savedJobIds.has(job.id)}
            />
          ))}
        </div>
      </main>
    </div>
  );
}
