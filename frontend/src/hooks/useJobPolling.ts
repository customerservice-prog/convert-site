import { useEffect, useRef } from "react";
import { getJobStatus } from "../services/api";
import type { JobStatusResponse } from "../types";

const INTERVAL_MS = 2500;
const MAX_RETRIES = 6;

export function useJobPolling(
  jobId: string | null,
  onUpdate: (s: JobStatusResponse) => void,
  onPollFatal: (message: string) => void
) {
  const retries = useRef(0);

  useEffect(() => {
    if (!jobId) return;

    let stopped = false;

    const poll = async () => {
      try {
        const s = await getJobStatus(jobId);
        if (stopped) return;
        retries.current = 0;
        onUpdate(s);
        if (["completed", "failed", "expired"].includes(s.status)) {
          stopped = true;
        }
      } catch {
        if (stopped) return;
        retries.current += 1;
        if (retries.current >= MAX_RETRIES) {
          onPollFatal(
            "We couldn’t reach the server after several tries. Check your connection or refresh the page."
          );
          stopped = true;
        }
      }
    };

    poll();
    const id = window.setInterval(poll, INTERVAL_MS);
    return () => {
      stopped = true;
      clearInterval(id);
    };
  }, [jobId, onUpdate, onPollFatal]);
}
