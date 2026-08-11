/**
 * Auth provider interface — the seam between the SPA and Keycloak.
 *
 * In production, the concrete implementation runs the OIDC
 * authorization-code flow against the configured Keycloak realm and
 * exchanges the code at ``/protocol/openid-connect/token`` for a JWT.
 *
 * In dev / CI, the in-memory implementation returns a token minted by
 * the backend test issuer (``POST /api/v1/auth/dev/login`` once that
 * surface lands in M02.1 — for M02 it's a typed no-op until the
 * Keycloak deploy integration tests arrive in M16).
 *
 * The interface is intentionally tiny so the production swap is a
 * one-file change.
 *
 * Traceability: FR-053, FR-057, NFR-004, NFR-006.
 */

/**
 * @typedef {Object} AuthPrincipal
 * @property {string} sub            — token subject (user id)
 * @property {string} username       — display name
 * @property {string} email          — user email
 * @property {string} tenantId       — tenant the token binds to
 * @property {string[]} roles        — role names from the realm
 * @property {number} expiresAt      — epoch seconds the JWT expires
 */

/**
 * @typedef {Object} AuthSession
 * @property {string} accessToken    — raw JWT (kept in sessionStorage)
 * @property {AuthPrincipal} principal — typed view of the principal
 */

/**
 * @typedef {Object} AuthProvider
 * @property {() => Promise<AuthSession|null>} getSession
 * @property {(session: AuthSession) => void}   setSession
 * @property {() => void}                       clearSession
 * @property {() => Promise<void>}              login
 * @property {() => Promise<void>}              logout
 */

export {};
