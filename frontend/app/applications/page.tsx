"use client";

import Link from "next/link";
import { Navbar } from "@/components/Navbar";
import { useApplications } from "@/lib/applications";
import { useRequireAuth } from "@/lib/useRequireAuth";
import type { ApplicationStatus } from "@/lib/types";

const STATUS_ORDER: ApplicationStatus[] = ["saved", "applied", "oa", "interview", "offer", "accepted"];

const STATUS_LABEL: Record<ApplicationStatus, string> = {
  saved: "Saved",
  applied: "Applied",
  oa: "Online Assessment",
  interview: "Interview",
  offer: "Offer",
  accepted: "Accepted",
  rejected: "Rejected",
  withdrawn: "Withdrawn",
};

export default function ApplicationsPage() {
  useRequireAuth();
  const { data: applications, isLoading, isError } = useApplications();

  const grouped = STATUS_ORDER.reduce<Record<string, typeof applications>>((acc, status) => {
    acc[status] = applications?.filter((a) => a.status === status) ?? [];
    return acc;
  }, {});

  return (
    <div className="min-h-screen">
      <Navbar />
      <main className="mx-auto max-w-4xl px-6 py-8">
        <h1 className="font-display text-2xl font-medium text-text-primary">Application pipeline</h1>
        <p className="mt-1 text-sm text-text-secondary">
          Track every application, then generate interview prep once you&apos;re past the screen.
        </p>

        {isLoading && <p className="mt-6 text-sm text-text-secondary">Loading applications…</p>}

        {isError && (
          <p className="mt-6 text-sm text-low">
            Couldn&apos;t load your applications. Make sure the backend is running, then refresh.
          </p>
        )}

        {!isLoading && !isError && applications?.length === 0 && (
          <p className="mt-6 text-sm text-text-secondary">
            No applications yet — save a job from the{" "}
            <Link href="/dashboard" className="text-signal">
              flight deck
            </Link>{" "}
            to get started.
          </p>
        )}

        <div className="mt-6 space-y-8">
          {STATUS_ORDER.map((status) => {
            const items = grouped[status];
            if (!items || items.length === 0) return null;
            return (
              <section key={status}>
                <h2 className="font-mono text-xs uppercase tracking-wide text-text-muted">
                  {STATUS_LABEL[status]} · {items.length}
                </h2>
                <div className="mt-2 space-y-2">
                  {items.map((application) => (
                    <Link
                      key={application.id}
                      href={`/applications/${application.id}`}
                      className="flex items-center justify-between rounded-card border border-border bg-surface p-4 transition-colors hover:border-signal-dim"
                    >
                      <div>
                        <p className="text-sm font-medium text-text-primary">{application.job.title}</p>
                        <p className="text-xs text-text-muted">{application.job.company.name}</p>
                      </div>
                      <span className="text-xs text-text-secondary">
                        {new Date(application.created_at).toLocaleDateString()}
                      </span>
                    </Link>
                  ))}
                </div>
              </section>
            );
          })}
        </div>
      </main>
    </div>
  );
}
