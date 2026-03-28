import type { NormalizedChoice } from "../types";

type Props = {
  summary: string;
  loading: boolean;
  disabled: boolean;
  onStart: () => void;
};

export function StartJobCard({ summary, loading, disabled, onStart }: Props) {
  return (
    <section className="rounded-2xl border border-emerald-900/40 bg-emerald-950/20 p-4 sm:p-5 space-y-4">
      <h2 className="text-xs font-semibold uppercase tracking-wider text-emerald-600/90">Start download</h2>
      <p className="text-sm text-slate-300">
        <span className="text-white font-medium">Selected:</span> {summary}
      </p>
      <p className="text-xs text-slate-500 leading-relaxed">
        Processing can take a minute or longer for long videos. Files are kept temporarily — download soon
        after they&apos;re ready.
      </p>
      <button
        type="button"
        onClick={onStart}
        disabled={disabled || loading}
        className="w-full min-h-[52px] rounded-2xl bg-emerald-600 hover:bg-emerald-500 disabled:opacity-40 disabled:pointer-events-none text-white font-semibold py-3.5 inline-flex items-center justify-center gap-2"
      >
        {loading && (
          <span className="h-4 w-4 border-2 border-white/30 border-t-white rounded-full animate-spin" />
        )}
        {loading ? "Starting…" : "Start download"}
      </button>
    </section>
  );
}

export function formatChoiceSummary(choice: NormalizedChoice | undefined, advancedLabel: string): string {
  if (choice) return `${choice.label} (${choice.container || choice.output_type})`;
  return advancedLabel || "Custom format";
}
