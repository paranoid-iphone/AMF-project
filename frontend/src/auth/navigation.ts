export function safeReturnPath(candidate: string | null, fallback = "/app") {
  if (!candidate || !candidate.startsWith("/") || candidate.startsWith("//")) return fallback;
  if (candidate.includes("\\") || candidate.includes("\u0000")) return fallback;

  try {
    const parsed = new URL(candidate, globalThis.location.origin);
    if (parsed.origin !== globalThis.location.origin) return fallback;
    return `${parsed.pathname}${parsed.search}${parsed.hash}`;
  } catch {
    return fallback;
  }
}