import { looksLikeHttpUrl } from "../utils/validators";

type Props = {
  url: string;
  onUrlChange: (v: string) => void;
  onSubmit: () => void;
  loading: boolean;
  clientError: string | null;
};

export function HeroSection({ url, onUrlChange, onSubmit, loading, clientError }: Props) {
  const invalid = url.trim().length > 0 && !looksLikeHttpUrl(url);

  return (
    <section className="space-y-6">
      <div>
        <h1 className="text-3xl sm:text-4xl font-semibold text-white tracking-tight leading-tight">
          Download in a few clicks
        </h1>
        <p className="mt-3 text-slate-400 text-sm sm:text-base leading-relaxed max-w-lg">
          Paste a YouTube link, pick quality, and we&apos;ll prepare your file. Downloads expire after a
          short time — grab them while they&apos;re ready.
        </p>
      </div>

      <div className="space-y-2">
        <label htmlFor="url" className="text-xs font-medium text-slate-500 uppercase tracking-wide">
          Video URL
        </label>
        <input
          id="url"
          type="url"
          inputMode="url"
          autoComplete="url"
          placeholder="https://www.youtube.com/watch?v=…"
          value={url}
          onChange={(e) => onUrlChange(e.target.value)}
          onKeyDown={(e) => {
            if (e.key === "Enter" && !loading && looksLikeHttpUrl(url)) onSubmit();
          }}
          className="w-full rounded-2xl bg-surface-card border border-surface-border px-4 py-3.5 text-base text-white placeholder:text-slate-600 focus:outline-none focus:ring-2 focus:ring-sky-500 focus:border-transparent transition-shadow"
        />
        {invalid && (
          <p className="text-sm text-amber-400/90" role="alert">
            Enter a valid http(s) link before continuing.
          </p>
        )}
        {clientError && (
          <p className="text-sm text-amber-400/90" role="alert">
            {clientError}
          </p>
        )}
      </div>

      <button
        type="button"
        onClick={onSubmit}
        disabled={loading || !looksLikeHttpUrl(url)}
        className="w-full sm:w-auto min-h-[48px] rounded-2xl bg-sky-600 hover:bg-sky-500 disabled:opacity-40 disabled:pointer-events-none text-white font-medium px-8 py-3.5 inline-flex items-center justify-center gap-2 shadow-lg shadow-sky-900/20 transition-colors"
      >
        {loading && (
          <span
            className="h-4 w-4 border-2 border-white/30 border-t-white rounded-full animate-spin"
            aria-hidden
          />
        )}
        {loading ? "Analyzing…" : "Get formats"}
      </button>
    </section>
  );
}
