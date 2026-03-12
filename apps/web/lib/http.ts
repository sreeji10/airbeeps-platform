export function normalizeApiPrefix(prefix: string): string {
  const trimmed = prefix.trim();
  if (!trimmed) {
    return "/v1";
  }
  return trimmed.startsWith("/") ? trimmed : `/${trimmed}`;
}
