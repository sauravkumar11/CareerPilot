"use client";

import Link from "next/link";
import { useState } from "react";
import { useLogin } from "@/lib/auth";
import { ApiError } from "@/lib/api";

export default function LoginPage() {
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const login = useLogin();

  return (
    <main className="flex min-h-screen items-center justify-center px-6">
      <div className="w-full max-w-sm">
        <h1 className="font-display text-2xl font-medium text-text-primary">
          Welcome back to <span className="text-signal">CareerPilot</span>
        </h1>
        <p className="mt-2 text-sm text-text-secondary">Sign in to see today&apos;s matches.</p>

        <form
          className="mt-8 space-y-4"
          onSubmit={(e) => {
            e.preventDefault();
            login.mutate({ email, password });
          }}
        >
          <div>
            <label className="mb-1.5 block text-sm text-text-secondary">Email</label>
            <input
              type="email"
              required
              value={email}
              onChange={(e) => setEmail(e.target.value)}
              className="w-full rounded-lg border border-border bg-surface px-3.5 py-2.5 text-text-primary outline-none focus:border-signal"
              placeholder="you@example.com"
            />
          </div>
          <div>
            <label className="mb-1.5 block text-sm text-text-secondary">Password</label>
            <input
              type="password"
              required
              value={password}
              onChange={(e) => setPassword(e.target.value)}
              className="w-full rounded-lg border border-border bg-surface px-3.5 py-2.5 text-text-primary outline-none focus:border-signal"
              placeholder="••••••••"
            />
          </div>

          {login.isError && (
            <p className="text-sm text-low">
              {login.error instanceof ApiError ? login.error.message : "Something went wrong."}
            </p>
          )}

          <button
            type="submit"
            disabled={login.isPending}
            className="w-full rounded-lg bg-signal py-2.5 font-medium text-bg transition-opacity hover:opacity-90 disabled:opacity-50"
          >
            {login.isPending ? "Signing in…" : "Sign in"}
          </button>
        </form>

        <p className="mt-6 text-center text-sm text-text-secondary">
          New here?{" "}
          <Link href="/register" className="text-signal">
            Create an account
          </Link>
        </p>
      </div>
    </main>
  );
}
