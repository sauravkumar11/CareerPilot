"use client";

import Link from "next/link";
import { useState } from "react";
import { useRegister } from "@/lib/auth";
import { ApiError } from "@/lib/api";

export default function RegisterPage() {
  const [fullName, setFullName] = useState("");
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const register = useRegister();

  return (
    <main className="flex min-h-screen items-center justify-center px-6">
      <div className="w-full max-w-sm">
        <h1 className="font-display text-2xl font-medium text-text-primary">
          Start your <span className="text-signal">flight plan</span>
        </h1>
        <p className="mt-2 text-sm text-text-secondary">
          Set up your profile once — CareerPilot handles the rest.
        </p>

        <form
          className="mt-8 space-y-4"
          onSubmit={(e) => {
            e.preventDefault();
            register.mutate({ full_name: fullName, email, password });
          }}
        >
          <div>
            <label className="mb-1.5 block text-sm text-text-secondary">Full name</label>
            <input
              required
              value={fullName}
              onChange={(e) => setFullName(e.target.value)}
              className="w-full rounded-lg border border-border bg-surface px-3.5 py-2.5 text-text-primary outline-none focus:border-signal"
              placeholder="Jane Doe"
            />
          </div>
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
              minLength={8}
              value={password}
              onChange={(e) => setPassword(e.target.value)}
              className="w-full rounded-lg border border-border bg-surface px-3.5 py-2.5 text-text-primary outline-none focus:border-signal"
              placeholder="At least 8 characters"
            />
          </div>

          {register.isError && (
            <p className="text-sm text-low">
              {register.error instanceof ApiError ? register.error.message : "Something went wrong."}
            </p>
          )}
          {register.isSuccess && (
            <p className="text-sm text-high">Account created — sign in to continue.</p>
          )}

          <button
            type="submit"
            disabled={register.isPending}
            className="w-full rounded-lg bg-signal py-2.5 font-medium text-bg transition-opacity hover:opacity-90 disabled:opacity-50"
          >
            {register.isPending ? "Creating account…" : "Create account"}
          </button>
        </form>

        <p className="mt-6 text-center text-sm text-text-secondary">
          Already flying with us?{" "}
          <Link href="/login" className="text-signal">
            Sign in
          </Link>
        </p>
      </div>
    </main>
  );
}
