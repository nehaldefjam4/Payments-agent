"use client";
import { useState, useEffect } from "react";
import { fetchSubmission } from "@/lib/api";
import type { Submission } from "@/lib/types";

export function useSubmission(id: string) {
  const [submission, setSubmission] = useState<Submission | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    if (!id) return;
    setLoading(true);
    fetchSubmission(id)
      .then((data) => {
        setSubmission(data);
        setError(null);
      })
      .catch((e) => {
        setError(e instanceof Error ? e.message : "Failed to load submission");
      })
      .finally(() => setLoading(false));
  }, [id]);

  return { submission, loading, error };
}
