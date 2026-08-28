"use client";

import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { apiFetch, getToken } from "./api";
import type { AppDocument, DocumentFormat, Resume, ResumeAnalysis } from "./types";

const API_URL = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000/api/v1";

export function useResumes() {
  return useQuery<Resume[]>({
    queryKey: ["resumes"],
    queryFn: () => apiFetch<Resume[]>("/resumes"),
  });
}

export function useResume(resumeId: string | undefined) {
  return useQuery<Resume>({
    queryKey: ["resumes", resumeId],
    queryFn: () => apiFetch<Resume>(`/resumes/${resumeId}`),
    enabled: !!resumeId,
  });
}

export function useResumeAnalysis(resumeId: string | undefined) {
  return useQuery<ResumeAnalysis>({
    queryKey: ["resumes", resumeId, "analysis"],
    queryFn: () => apiFetch<ResumeAnalysis>(`/resumes/${resumeId}/analysis`),
    enabled: !!resumeId,
    retry: false,
  });
}

export function useUploadResume() {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: async ({ file, label }: { file: File; label: string }) => {
      const formData = new FormData();
      formData.append("file", file);

      const token = getToken();
      const response = await fetch(
        `${API_URL}/resumes/upload?${new URLSearchParams({ label })}`,
        {
          method: "POST",
          headers: token ? { Authorization: `Bearer ${token}` } : undefined,
          body: formData,
        }
      );

      if (!response.ok) {
        const body = await response.json().catch(() => ({}));
        throw new Error(body.detail || "Upload failed");
      }
      return response.json();
    },
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["resumes"] });
    },
  });
}

export function useAnalyzeResume(resumeId: string) {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: (targetJobId?: string) =>
      apiFetch<ResumeAnalysis>(`/resumes/${resumeId}/analyze`, {
        method: "POST",
        body: JSON.stringify({ target_job_id: targetJobId || null }),
      }),
    onSuccess: (data) => {
      queryClient.setQueryData(["resumes", resumeId, "analysis"], data);
    },
  });
}

export function useExportResume(resumeId: string) {
  return useMutation({
    mutationFn: (documentFormat: DocumentFormat) =>
      apiFetch<AppDocument>(`/resumes/${resumeId}/export`, {
        method: "POST",
        body: JSON.stringify({ document_format: documentFormat }),
      }),
  });
}

export function useCustomizeResume(resumeId: string) {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: (jobId: string) =>
      apiFetch<Resume>(`/resumes/${resumeId}/customize`, {
        method: "POST",
        body: JSON.stringify({ job_id: jobId }),
      }),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["resumes"] });
    },
  });
}

export function useGenerateCoverLetter(applicationId: string) {
  return useMutation({
    mutationFn: ({ resumeId, tone }: { resumeId?: string; tone?: string }) =>
      apiFetch<AppDocument>(`/applications/${applicationId}/cover-letter`, {
        method: "POST",
        body: JSON.stringify({ resume_id: resumeId || null, tone: tone || "professional" }),
      }),
  });
}
