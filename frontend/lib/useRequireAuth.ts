"use client";

import { useEffect } from "react";
import { useRouter } from "next/navigation";
import { getToken } from "./api";

/**
 * Redirects to /login if there's no access token. Call this at the top of
 * any page that requires auth. Doesn't validate the token itself (an
 * expired/invalid token still reaches the page and its API calls will 401
 * normally — this only guards against the "no token at all" case, e.g. a
 * bookmarked URL or direct navigation after logging out).
 */
export function useRequireAuth() {
  const router = useRouter();

  useEffect(() => {
    if (!getToken()) {
      router.replace("/login");
    }
  }, [router]);
}
