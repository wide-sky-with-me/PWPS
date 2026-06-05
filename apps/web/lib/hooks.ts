"use client";

import { useEffect, useState } from "react";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import {
  createEventStream,
  createRun,
  fetchCurrentDecision,
  fetchOutputs,
  fetchRun,
  submitDecision,
  type Mode,
  type SSEMessage,
  type TraceEvent,
} from "./api";

export function useCreateRun() {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: ({ input, mode }: { input: string; mode: Mode }) =>
      createRun(input, mode),
    onSuccess: (data) => {
      queryClient.invalidateQueries({ queryKey: ["run", data.run_id] });
      // M2: Also invalidate decision query to avoid delay
      queryClient.invalidateQueries({ queryKey: ["decision", data.run_id] });
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
    // M7: Retry on network errors but not on 404
    retry: (failureCount, error) => {
      if (error.message.includes("404")) return false;
      return failureCount < 1;
    },
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
    // H4/M9: Always fetch fresh data for outputs
    staleTime: 0,
  });
}

// H5: SSE Event Stream Hook
export function useEventStream(runId: string | null) {
  const [events, setEvents] = useState<TraceEvent[]>([]);
  const [isConnected, setIsConnected] = useState(false);
  const [isDone, setIsDone] = useState(false);
  const queryClient = useQueryClient();

  useEffect(() => {
    if (!runId) {
      setEvents([]);
      setIsConnected(false);
      setIsDone(false);
      return;
    }

    const eventSource = createEventStream(
      runId,
      (message: SSEMessage) => {
        switch (message.type) {
          case "trace":
            setEvents((prev) => [...prev, message.data]);
            break;
          case "done":
            setIsDone(true);
            setIsConnected(false);
            // Invalidate queries to fetch final state
            queryClient.invalidateQueries({ queryKey: ["run", runId] });
            queryClient.invalidateQueries({ queryKey: ["outputs", runId] });
            break;
          case "error":
            console.error("SSE error:", message.data.error);
            setIsConnected(false);
            break;
        }
      },
      (error) => {
        console.error("SSE connection error:", error);
        setIsConnected(false);
      },
    );

    setIsConnected(true);

    return () => {
      eventSource.close();
      setIsConnected(false);
    };
  }, [runId, queryClient]);

  return { events, isConnected, isDone };
}
