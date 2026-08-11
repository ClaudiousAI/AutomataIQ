/**
 * Authenticated fetch wrapper.
 *
 * Adds the Bearer token from the active session and triggers a
 * session-clearing redirect on 401. The 401 handler is wired in
 * ``App.jsx`` via ``setOnUnauthorized`` so the redirect is policy,
 * not a hard import cycle.
 *
 * Traceability: FR-053, NFR-004.
 */

/**
 * @typedef {import('./types.js').AuthProvider} AuthProvider
 */

let onUnauthorized = null;

/**
 * Register the callback fired when a request returns 401.
 * @param {() => void} handler
 */
export function setOnUnauthorized(handler) {
  onUnauthorized = handler;
}

/**
 * @param {AuthProvider} auth
 * @param {string} path — same-origin path, e.g. ``/api/v1/me``.
 * @param {RequestInit} [init]
 */
export async function authedFetch(auth, path, init = {}) {
  const session = await auth.getSession();
  const headers = new Headers(init.headers ?? {});
  if (session?.accessToken) {
    headers.set('Authorization', `Bearer ${session.accessToken}`);
  }
  if (!headers.has('Content-Type') && init.body && typeof init.body === 'string') {
    headers.set('Content-Type', 'application/json');
  }
  const response = await fetch(path, { ...init, headers });
  if (response.status === 401 && session) {
    auth.clearSession();
    if (onUnauthorized) onUnauthorized();
  }
  return response;
}
