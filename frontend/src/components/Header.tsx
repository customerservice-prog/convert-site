export function Header() {
  return (
    <header className="border-b border-surface-border/80 bg-black/25 backdrop-blur-md">
      <div className="max-w-xl mx-auto px-4 py-4 flex items-start justify-between gap-4">
        <div>
          <p className="text-lg font-semibold text-white tracking-tight">Convert Site</p>
          <p className="text-xs text-slate-500 mt-0.5 max-w-xs">
            Save YouTube videos or audio — fast, simple, temporary storage.
          </p>
        </div>
        <nav className="flex flex-col items-end gap-1 text-xs shrink-0">
          <a className="text-slate-500 hover:text-slate-300" href="/legal/terms">
            Terms
          </a>
          <a className="text-slate-500 hover:text-slate-300" href="/legal/privacy">
            Privacy
          </a>
        </nav>
      </div>
    </header>
  );
}
