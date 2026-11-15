// Is the server awake? A free host sleeps when idle and takes up to a minute to start, then
// loads its search models. GET /health answers as soon as the server is up and says whether
// the models are loaded ("warm"), so the page can say what is happening instead of failing.

import { useQuery, useQueryClient } from "@tanstack/react-query";
import { useEffect, useRef } from "react";

export type ServerStatus = "up" | "warming" | "down";

/** Reads one /health reply (null = no reply at all) into what the page should show. */
export function statusFrom(reply: { status?: string; warm?: string } | null): ServerStatus {
  if (!reply || reply.status !== "ok") return "down";
  // "idle" is a server that never started a warm-up (the tests); "failed" still serves
  // questions, loading the models on the first one, so neither blocks the page.
  return reply.warm === "warming" ? "warming" : "up";
}

async function probe(): Promise<ServerStatus> {
  try {
    const response = await fetch("/health", { cache: "no-store" });
    // A 5xx from the host's proxy while the app boots is "down", not an error to show.
    return response.ok ? statusFrom(await response.json()) : "down";
  } catch {
    return "down";
  }
}

export function useServerStatus(): { status: ServerStatus; since: number } {
  const client = useQueryClient();
  const started = useRef(Date.now());
  const query = useQuery({
    queryKey: ["health"],
    queryFn: probe,
    // Poll quickly until the server is fully up, then stop.
    refetchInterval: (q) => (q.state.data === "up" ? false : 2500),
    refetchOnReconnect: true,
  });
  const status = query.data ?? "down";
  const previous = useRef<ServerStatus>("down");
  useEffect(() => {
    // When the server comes up, everything that failed while it slept is fetched again.
    if (status === "up" && previous.current !== "up") {
      client.invalidateQueries({ predicate: (q) => q.queryKey[0] !== "health" });
    }
    previous.current = status;
  }, [status, client]);
  return { status, since: started.current };
}
