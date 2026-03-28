import type { FormatRow, NormalizedChoice } from "../types";
import { formatBytes } from "../utils/formatters";

type Props = {
  choices: NormalizedChoice[];
  selectedKey: string;
  onSelectKey: (key: string) => void;
  advanced: boolean;
  onToggleAdvanced: (v: boolean) => void;
  formats: FormatRow[];
  advancedFormatId: string;
  onAdvancedFormatId: (id: string) => void;
};

export function FormatSelector({
  choices,
  selectedKey,
  onSelectKey,
  advanced,
  onToggleAdvanced,
  formats,
  advancedFormatId,
  onAdvancedFormatId,
}: Props) {
  return (
    <div className="rounded-2xl border border-surface-border bg-slate-950/40 p-4 sm:p-5 space-y-4">
      <div className="flex items-center justify-between gap-2">
        <h2 className="text-xs font-semibold uppercase tracking-wider text-slate-500">Format</h2>
        <button
          type="button"
          onClick={() => onToggleAdvanced(!advanced)}
          className="text-xs text-sky-400 hover:text-sky-300 font-medium"
        >
          {advanced ? "Simple mode" : "Advanced"}
        </button>
      </div>

      {!advanced && (
        <ul className="space-y-2">
          {choices.map((c) => (
            <li key={c.key}>
              <label className="flex items-start gap-3 p-3 rounded-xl border border-transparent has-[:checked]:border-sky-500/50 has-[:checked]:bg-sky-950/30 cursor-pointer hover:bg-white/5 transition-colors">
                <input
                  type="radio"
                  name="preset"
                  className="mt-1 text-sky-500"
                  checked={selectedKey === c.key}
                  onChange={() => onSelectKey(c.key)}
                />
                <span>
                  <span className="block text-sm font-medium text-white">{c.label}</span>
                  {c.description && (
                    <span className="block text-xs text-slate-500 mt-0.5">{c.description}</span>
                  )}
                  {c.container && (
                    <span className="inline-block mt-1 text-[10px] uppercase tracking-wide text-slate-600">
                      {c.container}
                    </span>
                  )}
                </span>
              </label>
            </li>
          ))}
        </ul>
      )}

      {advanced && (
        <div className="space-y-2">
          <label className="text-xs text-slate-500" htmlFor="advfmt">
            Format ID (from extractor)
          </label>
          <select
            id="advfmt"
            value={advancedFormatId}
            onChange={(e) => onAdvancedFormatId(e.target.value)}
            className="w-full rounded-xl bg-slate-900 border border-surface-border px-3 py-2.5 text-sm text-white focus:ring-2 focus:ring-sky-500 focus:outline-none"
          >
            <option value="">Select a row…</option>
            {formats.map((f) => (
              <option key={f.format_id} value={f.format_id}>
                {[f.format_id, f.resolution || (f.height ? `${f.height}p` : ""), f.ext]
                  .filter(Boolean)
                  .join(" · ")}
                {f.filesize ? ` · ${formatBytes(f.filesize)}` : ""}
              </option>
            ))}
          </select>
          <p className="text-xs text-slate-600">
            Advanced options use a single yt-dlp stream where possible; video+audio merges still run on the
            server when required.
          </p>
        </div>
      )}
    </div>
  );
}
