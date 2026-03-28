import type { JobStatusResponse } from "../types";

type Props = {
  job: JobStatusResponse | null;
  phaseNote?: string | null;
};

const STATUS_HINT: Record<string, string> = {
  queued: "Your job is waiting for a free worker.",
  downloading: "Saving streams from the source…",
  processing: "Combining or encoding — almost there.",
};

export function JobProgressSection({ job, phaseNote }: Props) {
  if (!job) {
    return (
      <section className="rounded-2xl border border-surface-border bg-surface-card/80 p-4 sm:p-5 space-y-3">
        <h2 className="text-xs font-semibold uppercase tracking-wider text-slate-500">Progress</h2>
        <p className="text-sm text-slate-400">Connecting to your job…</p>
        <div className="h-2 rounded-full bg-slate-800 overflow-hidden">
          <div className="h-full w-1/3 rounded-full bg-sky-600/60 animate-pulse" />
        </div>
      </section>
    );
  }
  const terminal = ["completed", "failed", "expired"].includes(job.status);
  const pct = Math.min(100, Math.max(0, job.progress));
  const hint = phaseNote || STATUS_HINT[job.status] || "";

  return (
    <section className="rounded-2xl border border-surface-border bg-surface-card/80 p-4 sm:p-5 space-y-3">
      <h2 className="text-xs font-semibold uppercase tracking-wider text-slate-500">Progress</h2>
      <div className="flex flex-wrap items-baseline gap-2">
        <span className="text-lg font-medium text-white capitalize">{job.status_label || job.status}</span>
        <span className="text-sm text-slate-500">{pct}%</span>
      </div>
      {job.stage && <p className="text-sm text-slate-400">{job.stage}</p>}
      {!terminal && hint && <p className="text-xs text-slate-600">{hint}</p>}
      {!terminal && (
        <div className="h-2 rounded-full bg-slate-800 overflow-hidden">
          <div
            className="h-full rounded-full bg-gradient-to-r from-sky-700 to-sky-400 transition-all duration-500"
            style={{ width: `${Math.max(pct, 4)}%` }}
          />
        </div>
      )}
    </section>
  );
}
