export function looksLikeHttpUrl(raw: string): boolean {
  const s = raw.trim();
  if (s.length < 12) return false;
  try {
    const u = new URL(s);
    return u.protocol === "http:" || u.protocol === "https:";
  } catch {
    return false;
  }
}
