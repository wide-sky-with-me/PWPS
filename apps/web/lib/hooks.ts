"use client";

import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import {
  createRun,
  fetchCurrentDecision,
  fetchOutputs,
  fetchRun,
  submitDecision,
  type Mode,
} from "./api";

export function useCreateRun() {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: ({ input, mode }: { input: string; mode: Mode }) =>
      createRun(input, mode),
    onSuccess: (data) => {
      queryClient.invalidateQueries({ queryKey: ["run", data.run_id] });
    },
  });
}

export function useRun(runId: string | null) {
  return useQuery({
    queryKey: ["run", runId],
    queryFn: () => fetchRun(runId!),
    enabled: !!runId,
    refetchInterval: (query) => {
      const status = query.state.data?.status;
      if (status === "finished" || status === "blocked") return false;
      return 2000;
    },
  });
}

export function useCurrentDecision(runId: string | null) {
  return useQuery({
    queryKey: ["decision", runId],
    queryFn: () => fetchCurrentDecision(runId!),
    enabled: !!runId,
    retry: false,
  });
}

export function useSubmitDecision(runId: string) {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: (payload: {
      session_id: string;
      decision_type: "accept_recommended" | "choose_alternative" | "override";
      selected_values: Record<string, unknown>;
      comment?: string;
    }) => submitDecision(runId, payload),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["run", runId] });
      queryClient.invalidateQueries({ queryKey: ["decision", runId] });
      queryClient.invalidateQueries({ queryKey: ["outputs", runId] });
    },
  });
}

export function useOutputs(runId: string | null) {
  return useQuery({
    queryKey: ["outputs", runId],
    queryFn: () => fetchOutputs(runId!),
    enabled: !!runId,
  });
}
