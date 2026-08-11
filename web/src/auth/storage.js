/**
 * Session storage helpers.
 *
 * The session is kept in ``sessionStorage`` so it is cleared when the
 * user closes the tab — a defence-in-depth choice that limits the
 * blast radius of an XSS that exfiltrates the JWT.
 *
 * Production may switch to a SameSite=Strict cookie flow alongside
 * M16's deploy integration tests, but the seam is here so the swap is
 * a one-file change.
 *
 * Traceability: NFR-004, NFR-006.
 */

const KEY = 'saie.auth.session.v1';

/**
 * @param {import('./types.js').AuthSession|null} session
 */
export function saveSessionStorage(session) {
  if (!session) {
    clearSessionStorage();
    return;
  }
  sessionStorage.setItem(KEY, JSON.stringify(session));
}

/** @returns {import('./types.js').AuthSession|null} */
export function loadSessionStorage() {
  const raw = sessionStorage.getItem(KEY);
  if (!raw) return null;
  try {
    const parsed = JSON.parse(raw);
    if (!parsed.accessToken || !parsed.principal) return null;
    return parsed;
  } catch {
    return null;
  }
}

export function clearSessionStorage() {
  sessionStorage.removeItem(KEY);
}
