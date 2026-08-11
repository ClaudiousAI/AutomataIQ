/**
 * Dev-mode auth provider.
 *
 * In CI / local dev there is no Keycloak realm to talk to. This
 * provider returns an unauthenticated session and exposes a
 * ``devLogin(role)`` action that asks the backend test issuer to mint
 * a token. The backend ships this endpoint behind the
 * ``SAIE_ENV=dev`` gate (see backend/app/auth/api.py).
 *
 * In production the swap is to ``keycloakProvider.js`` (lands in
 * M16's deploy integration tests). The interface is identical, so no
 * caller changes.
 *
 * Traceability: FR-053, FR-057, NFR-004.
 */

import { clearSessionStorage, loadSessionStorage, saveSessionStorage } from './storage.js';

/**
 * @typedef {import('./types.js').AuthSession} AuthSession
 * @typedef {import('./types.js').AuthProvider} AuthProvider
 */

/**
 * Build a dev-mode provider.
 *
 * @param {{ apiBase?: string }} [opts]
 * @returns {AuthProvider}
 */
export function createDevAuthProvider({ apiBase = '' } = {}) {
  /** @type {AuthSession|null} */
  let session = loadSessionStorage();

  return {
    async getSession() {
      // Refresh the in-memory view from storage so cross-tab logouts
      // take effect on the next call. (Storage events would be
      // preferable but add a global listener we don't need here.)
      session = loadSessionStorage();
      return session;
    },

    setSession(next) {
      session = next;
      saveSessionStorage(next);
    },

    clearSession() {
      session = null;
      clearSessionStorage();
    },

    async login() {
      // Dev mode has no automatic login — the test pages render a
      // ``devLogin(role)`` button that calls the backend's dev
      // endpoint directly. Throwing keeps the interface honest.
      throw new Error(
        'dev auth provider has no automatic login — call /api/v1/auth/dev/login from a test harness'
      );
    },

    async logout() {
      if (session?.accessToken) {
        try {
          await fetch(`${apiBase}/api/v1/auth/logout`, {
            method: 'POST',
            headers: { Authorization: `Bearer ${session.accessToken}` },
          });
        } catch {
          // Network failure on logout is non-fatal — local state
          // is the source of truth for the SPA.
        }
      }
      session = null;
      clearSessionStorage();
    },
  };
}
