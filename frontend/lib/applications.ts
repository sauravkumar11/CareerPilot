"use client";

import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { apiFetch } from "./api";
import type { Application, ApplicationStatus, InterviewPrep } from "./types";

export function useApplications(status?: ApplicationStatus) {
  const params = status ? `?status_filter=${status}` : "";
  return useQuery<Application[]>({
    queryKey: ["applications", status],
    queryFn: () => apiFetch<Application[]>(`/applications${params}`),
  });
}

export function useApplication(applicationId: string | undefined) {
  return useQuery<Application>({
    queryKey: ["applications", applicationId],
    queryFn: () => apiFetch<Application>(`/applications/${applicationId}`),
    enabled: !!applicationId,
  });
}

export function useUpdateApplicationStatus(applicationId: string) {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: (status: ApplicationStatus) =>
      apiFetch<Application>(`/applications/${applicationId}/status`, {
        method: "PATCH",
        body: JSON.stringify({ status }),
      }),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["applications"] });
    },
  });
}

export function useInterviewPrep(applicationId: string | undefined) {
  return useQuery<InterviewPrep>({
    queryKey: ["applications", applicationId, "interview-prep"],
    queryFn: () => apiFetch<InterviewPrep>(`/applications/${applicationId}/interview-prep`),
    enabled: !!applicationId,
    retry: false,
  });
}

export function useGenerateInterviewPrep(applicationId: string) {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: (forceRefreshNews: boolean = false) =>
      apiFetch<InterviewPrep>(`/applications/${applicationId}/interview-prep`, {
        method: "POST",
        body: JSON.stringify({ force_refresh_news: forceRefreshNews }),
      }),
    onSuccess: (data) => {
      queryClient.setQueryData(["applications", applicationId, "interview-prep"], data);
    },
  });
}
