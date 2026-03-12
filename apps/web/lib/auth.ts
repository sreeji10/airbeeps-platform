"use client";

const AUTH_COOKIE = "airbeeps_auth_token";

export function setAuthCookie(token: string) {
  const encoded = encodeURIComponent(token);
  document.cookie = `${AUTH_COOKIE}=${encoded}; path=/; max-age=2592000; samesite=lax`;
}

export function clearAuthCookie() {
  document.cookie = `${AUTH_COOKIE}=; path=/; max-age=0; samesite=lax`;
}
