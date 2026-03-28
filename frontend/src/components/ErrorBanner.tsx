type Props = {
  message: string | null;
  onDismiss?: () => void;
  title?: string;
};

export function ErrorBanner({ message, onDismiss, title = "Something went wrong" }: Props) {
  if (!message) return null;
  return (
    <div
      className="rounded-2xl border border-red-900/50 bg-red-950/40 px-4 py-3 text-sm text-red-100 flex gap-3 justify-between items-start"
      role="alert"
    >
      <div>
        <p className="font-medium text-red-200">{title}</p>
        <p className="mt-1 text-red-100/90 whitespace-pre-wrap">{message}</p>
        <p className="mt-2 text-xs text-red-300/70">Try again, or paste a different URL.</p>
      </div>
      {onDismiss && (
        <button
          type="button"
          onClick={onDismiss}
          className="text-xs text-red-300 hover:text-red-100 shrink-0"
        >
          Dismiss
        </button>
      )}
    </div>
  );
}
