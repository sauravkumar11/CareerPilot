"use client";

import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { useRouter } from "next/navigation";
import { apiFetch, clearToken, setToken } from "./api";

export interface CurrentUser {
  id: string;
  email: string;
  full_name: string;
  github_url?: string | null;
  linkedin_url?: string | null;
  portfolio_url?: string | null;
}

export function useCurrentUser() {
  return useQuery<CurrentUser>({
    queryKey: ["me"],
    queryFn: () => apiFetch<CurrentUser>("/users/me"),
    retry: false,
  });
}

export function useLogin() {
  const queryClient = useQueryClient();
  const router = useRouter();

  return useMutation({
    mutationFn: (payload: { email: string; password: string }) =>
      apiFetch<{ access_token: string; refresh_token: string }>("/auth/login", {
        method: "POST",
        body: JSON.stringify(payload),
      }),
    onSuccess: async (data) => {
      setToken(data.access_token);
      await queryClient.invalidateQueries({ queryKey: ["me"] });
      router.push("/dashboard");
    },
  });
}

export function useRegister() {
  const router = useRouter();

  return useMutation({
    mutationFn: (payload: { email: string; password: string; full_name: string }) =>
      apiFetch("/auth/register", {
        method: "POST",
        body: JSON.stringify(payload),
      }),
    onSuccess: () => {
      router.push("/login");
    },
  });
}

export function useLogout() {
  const queryClient = useQueryClient();
  const router = useRouter();

  return () => {
    clearToken();
    queryClient.clear();
    router.push("/login");
  };
}
