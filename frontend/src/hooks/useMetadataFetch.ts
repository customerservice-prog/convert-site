import { useCallback, useState } from "react";
import { postMetadata } from "../services/api";
import type { MetadataResponse } from "../types";

export function useMetadataFetch() {
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const fetchMetadata = useCallback(async (url: string) => {
    setLoading(true);
    setError(null);
    try {
      const data = await postMetadata(url);
      return data;
    } catch (e) {
      const msg = e instanceof Error ? e.message : "Could not load video info.";
      setError(msg);
      return null;
    } finally {
      setLoading(false);
    }
  }, []);

  return { fetchMetadata, loading, error, setError };
}
