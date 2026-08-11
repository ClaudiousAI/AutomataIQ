/**
 * React context wiring for the auth provider.
 *
 * The provider is supplied at app boot via ``<AuthProvider>`` so the
 * rest of the tree can ``useAuth()`` without caring whether the
 * backing implementation is the dev stub or the production
 * Keycloak OIDC flow.
 *
 * Traceability: FR-053, FR-057, NFR-004.
 */

import { createContext, useContext, useEffect, useMemo, useState } from 'react';
import { authedFetch, setOnUnauthorized } from './fetch.js';

const AuthCtx = createContext(
  /** @type {{ provider: any, principal: any|null, refresh: () => Promise<void> }} */ (null)
);

/**
 * @param {{ provider: import('./types.js').AuthProvider, onUnauthorized?: () => void, children: React.ReactNode }} props
 */
export function AuthProvider({ provider, onUnauthorized, children }) {
  const [principal, setPrincipal] = useState(/** @type {any} */ (null));

  const refresh = useMemo(
    () => async () => {
      const session = await provider.getSession();
      if (!session) {
        setPrincipal(null);
        return;
      }
      // Verify the token is still good by hitting /me. The endpoint
      // returns 200 with the principal payload, or 401 if the token
      // expired or was revoked.
      try {
        const response = await authedFetch(provider, '/api/v1/me');
        if (response.ok) {
          const body = await response.json();
          setPrincipal({
            sub: body.sub,
            username: body.username,
            email: body.email,
            tenantId: body.tenant_id,
            roles: body.roles,
          });
        } else {
          setPrincipal(null);
        }
      } catch {
        setPrincipal(null);
      }
    },
    [provider]
  );

  useEffect(() => {
    if (onUnauthorized) setOnUnauthorized(onUnauthorized);
    void refresh();
  }, [refresh, onUnauthorized]);

  const value = useMemo(() => ({ provider, principal, refresh }), [provider, principal, refresh]);
  return <AuthCtx.Provider value={value}>{children}</AuthCtx.Provider>;
}

/** @returns {{ provider: import('./types.js').AuthProvider, principal: any|null, refresh: () => Promise<void> }} */
export function useAuth() {
  const ctx = useContext(AuthCtx);
  if (!ctx) throw new Error('useAuth() called outside <AuthProvider>');
  return ctx;
}
