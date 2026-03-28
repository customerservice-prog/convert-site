import { getApiBase } from "../services/api";
import { formatBytes } from "../utils/formatters";
import type { JobStatusResponse } from "../types";

type Props = {
  job: JobStatusResponse;
  onNewDownload: () => void;
};

export function SuccessSection({ job, onNewDownload }: Props) {
  const base = getApiBase();
  const href = job.download_url ? `${base}${job.download_url}` : "#";

  return (
    <section className="rounded-2xl border border-emerald-800/50 bg-emerald-950/25 p-4 sm:p-5 space-y-4">
      <h2 className="text-xs font-semibold uppercase tracking-wider text-emerald-500">Ready</h2>
      <p className="text-white font-medium">Your file is prepared.</p>
      <dl className="grid grid-cols-2 gap-2 text-sm">
        <dt className="text-slate-500">Type</dt>
        <dd className="text-slate-200">{job.output_type === "audio" ? "Audio" : "Video"}</dd>
        {job.filename && (
          <>
            <dt className="text-slate-500">Name</dt>
            <dd className="text-slate-200 truncate" title={job.filename}>
              {job.filename}
            </dd>
          </>
        )}
        {job.file_size != null && (
          <>
            <dt className="text-slate-500">Size</dt>
            <dd className="text-slate-200">{formatBytes(job.file_size)}</dd>
          </>
        )}
      </dl>
      <p className="text-xs text-amber-200/80 leading-relaxed">
        Files expire after a limited time. Save now — you may need to start again if you wait too long.
      </p>
      <div className="flex flex-col sm:flex-row gap-3">
        <a
          href={href}
          download
          className="inline-flex justify-center items-center min-h-[48px] rounded-2xl bg-white text-slate-900 font-semibold px-6 py-3 hover:bg-slate-100 transition-colors"
        >
          Download file
        </a>
        <button
          type="button"
          onClick={onNewDownload}
          className="inline-flex justify-center items-center min-h-[48px] rounded-2xl border border-slate-600 text-slate-200 font-medium px-6 py-3 hover:bg-white/5"
        >
          New link
        </button>
      </div>
    </section>
  );
}
