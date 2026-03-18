"use client";
import { useState, useEffect, useRef } from "react";
import { fetchAgentSteps } from "@/lib/api";
import type { AgentStep } from "@/lib/types";

export function useAgentSteps(submissionId: string) {
  const [steps, setSteps] = useState<AgentStep[]>([]);
  const [status, setStatus] = useState<string>("processing");
  const [isComplete, setIsComplete] = useState(false);
  const intervalRef = useRef<ReturnType<typeof setInterval> | null>(null);

  useEffect(() => {
    if (!submissionId || isComplete) return;

    const poll = async () => {
      try {
        const data = await fetchAgentSteps(submissionId);
        setSteps(data.steps);
        setStatus(data.status);

        if (data.status !== "processing") {
          setIsComplete(true);
          if (intervalRef.current) {
            clearInterval(intervalRef.current);
          }
        }
      } catch {
        // Ignore polling errors
      }
    };

    poll();
    intervalRef.current = setInterval(poll, 2000);

    return () => {
      if (intervalRef.current) {
        clearInterval(intervalRef.current);
      }
    };
  }, [submissionId, isComplete]);

  return { steps, status, isComplete };
}
