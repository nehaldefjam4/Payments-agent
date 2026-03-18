"use client";
import { useState, useEffect } from "react";
import { fetchSubmissions } from "@/lib/api";
import type { Submission } from "@/lib/types";

export function useSubmissions() {
  const [submissions, setSubmissions] = useState<Submission[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  const refresh = async () => {
    try {
      setLoading(true);
      const data = await fetchSubmissions();
      setSubmissions(data.submissions);
      setError(null);
    } catch (e) {
      setError(e instanceof Error ? e.message : "Failed to load submissions");
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    refresh();
  }, []);

  return { submissions, loading, error, refresh };
}
