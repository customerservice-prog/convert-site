import type { MetadataResponse } from "../types";

type Props = { meta: MetadataResponse };

export function VideoMetadataCard({ meta }: Props) {
  return (
    <section className="rounded-2xl border border-surface-border bg-surface-card/90 p-4 sm:p-5 shadow-xl shadow-black/20">
      <h2 className="text-xs font-semibold uppercase tracking-wider text-slate-500 mb-4">Preview</h2>
      <div className="flex flex-col sm:flex-row gap-4">
        {meta.thumbnail && (
          <div className="sm:w-44 shrink-0">
            <img
              src={meta.thumbnail}
              alt=""
              className="w-full rounded-xl object-cover max-h-40 sm:max-h-none sm:aspect-video bg-black/40"
            />
          </div>
        )}
        <div className="min-w-0 flex-1 space-y-2">
          <h3 className="text-lg font-semibold text-white leading-snug break-words">{meta.title}</h3>
          <dl className="grid grid-cols-1 sm:grid-cols-2 gap-x-4 gap-y-1 text-sm text-slate-400">
            {meta.source_site && (
              <>
                <dt className="text-slate-500">Source</dt>
                <dd className="text-slate-300">{meta.source_site}</dd>
              </>
            )}
            {meta.duration_label && (
              <>
                <dt className="text-slate-500">Duration</dt>
                <dd className="text-slate-300">{meta.duration_label}</dd>
              </>
            )}
            {meta.uploader && (
              <>
                <dt className="text-slate-500">Channel</dt>
                <dd className="text-slate-300 break-words">{meta.uploader}</dd>
              </>
            )}
            {meta.upload_date && (
              <>
                <dt className="text-slate-500">Published</dt>
                <dd className="text-slate-300">{meta.upload_date}</dd>
              </>
            )}
          </dl>
        </div>
      </div>
    </section>
  );
}
