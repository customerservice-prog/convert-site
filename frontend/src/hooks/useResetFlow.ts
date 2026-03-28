import { useCallback } from "react";

export function useResetFlow(resetters: Array<() => void>) {
  return useCallback(() => {
    resetters.forEach((fn) => fn());
  }, [resetters]);
}
