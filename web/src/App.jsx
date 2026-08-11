import { useEffect, useState } from 'react';

/**
 * SAIE application root (M01).
 *
 * M01 intentionally renders a single "shell" view that:
 *   1. Shows the product name and a one-line mission statement.
 *   2. Polls the backend's ``/health`` endpoint and surfaces the
 *      status. This proves the cross-container wiring during local
 *      ``docker compose up`` and exercises the API contract surface
 *      that M02 (auth) and M13 (dashboard) will inherit.
 *
 * Traceability: NFR-005 (UI surfaces backend liveness), NFR-006
 * (typed prop / data contract at the service boundary).
 */
export default function App() {
  const [health, setHealth] = useState({ status: 'unknown', service: '…' });
  const [error, setError] = useState(null);

  useEffect(() => {
    let cancelled = false;

    async function fetchHealth() {
      try {
        // Vite dev server proxies ``/api/*`` to the API container.
        // In production, nginx (M01 infra) performs the same proxy.
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

  return (
    <main className="app">
      <header>
        <h1>SAIE</h1>
        <p className="tagline">SAP Automation Intelligence Engine</p>
      </header>
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
        <small>M01 — Project Foundation. NFR-005, NFR-006.</small>
      </footer>
    </main>
  );
}
