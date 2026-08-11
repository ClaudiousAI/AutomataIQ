import { useEffect, useState } from 'react';
import { AuthProvider, useAuth } from './auth/context.jsx';
import { createDevAuthProvider } from './auth/devProvider.js';

/**
 * SAIE application root (M01 + M02).
 *
 * M02 wiring:
 *   1. ``<AuthProvider>`` mounts the auth provider so ``useAuth()``
 *      can be called anywhere below it.
 *   2. ``<Shell>`` shows the user badge, login/logout buttons, and
 *      fetches ``/api/v1/me`` once a session is present.
 *   3. On 401 the authed fetch wrapper clears the session and fires
 *      the redirect registered here.
 *
 * Traceability: NFR-005, NFR-006, FR-053 (RBAC surface), FR-057
 * (tenant boundary on the API).
 */

const auth = createDevAuthProvider();

function Shell() {
  const { provider, principal, refresh } = useAuth();
  const [health, setHealth] = useState({ status: 'unknown', service: '…' });
  const [error, setError] = useState(null);
  const [loginPending, setLoginPending] = useState(false);

  useEffect(() => {
    let cancelled = false;

    async function fetchHealth() {
      try {
        const response = await fetch('/api/health');
        if (!response.ok) {
          throw new Error(`HTTP ${response.status}`);
        }
        const body = await response.json();
        if (!cancelled) {
          setHealth(body);
          setError(null);
        }
      } catch (err) {
        if (!cancelled) {
          setError(err.message);
          setHealth({ status: 'down', service: '…' });
        }
      }
    }

    fetchHealth();
    const interval = setInterval(fetchHealth, 10_000);
    return () => {
      cancelled = true;
      clearInterval(interval);
    };
  }, []);

  async function devLogin(role) {
    setLoginPending(true);
    try {
      const response = await fetch('/api/v1/auth/dev/login', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          subject: 'demo-user',
          username: 'demo-user',
          email: 'demo@example.com',
          tenant_id: 'demo-tenant',
          roles: [role],
        }),
      });
      if (!response.ok) {
        throw new Error(`login failed: HTTP ${response.status}`);
      }
      const body = await response.json();
      provider.setSession({
        accessToken: body.access_token,
        principal: body.principal,
      });
      await refresh();
    } finally {
      setLoginPending(false);
    }
  }

  async function logout() {
    await provider.logout();
    await refresh();
  }

  return (
    <main className="app">
      <header>
        <h1>SAIE</h1>
        <p className="tagline">SAP Automation Intelligence Engine</p>
      </header>

      <section className="card" aria-labelledby="auth-heading">
        <h2 id="auth-heading">Authentication</h2>
        {principal ? (
          <div data-testid="user-badge">
            <p>
              Signed in as <strong>{principal.username}</strong>{' '}
              <span className="muted">({principal.sub})</span>
            </p>
            <p className="muted">
              tenant: <code>{principal.tenantId}</code> · roles:{' '}
              <code>{principal.roles.join(', ')}</code>
            </p>
            <button type="button" onClick={logout} data-testid="logout-button">
              Sign out
            </button>
          </div>
        ) : (
          <div data-testid="login-panel">
            <p className="muted">Dev sign-in (no Keycloak required):</p>
            <div className="role-row">
              {['platform_admin', 'analyst', 'read_only'].map((role) => (
                <button
                  key={role}
                  type="button"
                  onClick={() => devLogin(role)}
                  disabled={loginPending}
                  data-testid={`login-${role}`}
                >
                  Sign in as {role}
                </button>
              ))}
            </div>
          </div>
        )}
      </section>

      <section className="card" aria-labelledby="health-heading">
        <h2 id="health-heading">Backend status</h2>
        <p>
          <span className={`status status--${health.status}`} data-testid="status">
            {health.status}
          </span>{' '}
          <span className="service-name">{health.service}</span>
        </p>
        {error && (
          <p className="error" role="alert">
            Could not reach API: {error}
          </p>
        )}
      </section>

      <footer>
        <small>M01 + M02. NFR-005, NFR-006, FR-053, FR-057.</small>
      </footer>
    </main>
  );
}

export default function App() {
  return (
    <AuthProvider
      provider={auth}
      onUnauthorized={() => {
        // Soft redirect — the SPA state is already cleared by the
        // fetch wrapper. A real router push would land here.
        window.dispatchEvent(new Event('saie:unauthorized'));
      }}
    >
      <Shell />
    </AuthProvider>
  );
}
