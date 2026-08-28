"use client";

import Link from "next/link";
import { useCurrentUser, useLogout } from "@/lib/auth";

export function Navbar() {
  const { data: user } = useCurrentUser();
  const logout = useLogout();

  return (
    <header className="sticky top-0 z-10 border-b border-border bg-bg/80 backdrop-blur">
      <div className="mx-auto flex max-w-5xl items-center justify-between px-6 py-4">
        <Link href="/dashboard" className="font-display text-base font-semibold tracking-tight text-text-primary">
          CareerPilot <span className="text-signal">AI</span>
        </Link>
        {user && (
          <div className="flex items-center gap-4">
            <Link href="/applications" className="text-sm text-text-secondary transition-colors hover:text-text-primary">
              Applications
            </Link>
            <Link href="/resumes" className="text-sm text-text-secondary transition-colors hover:text-text-primary">
              Resumes
            </Link>
            <span className="text-sm text-text-secondary">{user.full_name}</span>
            <button
              onClick={logout}
              className="rounded-full border border-border px-3 py-1.5 text-sm text-text-secondary transition-colors hover:border-signal-dim hover:text-text-primary"
            >
              Sign out
            </button>
          </div>
        )}
      </div>
    </header>
  );
}
