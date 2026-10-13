/**
 * Safe Auth navigation and URL building utilities for MORPH Studio.
 */

export function sanitizeReturnTo(url: string | null | undefined): string {
  if (!url) return "/account";
  const trimmed = url.trim();

  // Validate internal path: must start with single '/' and not '//' or '/\'
  if (!trimmed.startsWith("/") || trimmed.startsWith("//") || trimmed.startsWith("/\\")) {
    return "/account";
  }

  // Prevent auth loops back into /auth, /auth/login, /auth/register
  if (trimmed.startsWith("/auth")) {
    return "/account";
  }

  return trimmed;
}

export interface AuthUrlParams {
  returnTo?: string | null;
  intent?: string | null;
  scanId?: string | null;
  guestToken?: string | null;
}

export function buildAuthUrl(mode: "login" | "register", options?: AuthUrlParams): string {
  const base = `/auth/${mode}`;
  const params = new URLSearchParams();

  if (options?.returnTo) {
    const safeReturn = sanitizeReturnTo(options.returnTo);
    if (safeReturn !== "/account") {
      params.set("returnTo", safeReturn);
    }
  }

  if (options?.intent) {
    params.set("intent", options.intent);
  }

  if (options?.scanId) {
    params.set("scan_id", options.scanId);
  }

  if (options?.guestToken) {
    params.set("guest_token", options.guestToken);
  }

  const qs = params.toString();
  return qs ? `${base}?${qs}` : base;
}
