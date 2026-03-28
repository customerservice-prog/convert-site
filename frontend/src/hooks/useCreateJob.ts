import { useCallback, useState } from "react";
import { postJob } from "../services/api";

export function useCreateJob() {
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const create = useCallback(
    async (params: {
      url: string;
      format_id: string;
      output_type: string;
      preset_key?: string | null;
    }) => {
      setLoading(true);
      setError(null);
      try {
        return await postJob(params);
      } catch (e) {
        const msg = e instanceof Error ? e.message : "Could not start download.";
        setError(msg);
        return null;
      } finally {
        setLoading(false);
      }
    },
    []
  );

  return { create, loading, error, setError };
}
