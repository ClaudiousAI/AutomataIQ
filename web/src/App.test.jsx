import { describe, it, expect, vi, beforeEach, afterEach } from 'vitest';
import { render, screen, waitFor } from '@testing-library/react';
import App from './App.jsx';

/**
 * M01 — Frontend smoke test (NFR-005, NFR-006).
 *
 * The SPA is intentionally minimal: a status pill that mirrors the
 * backend's ``/health``. This test pins two behaviours that are easy
 * to break and very expensive to discover only after a deploy:
 *
 *   1. The UI surfaces the backend's reported status.
 *   2. A network failure does NOT crash the page — it shows "down".
 */

describe('App — backend health surface', () => {
  beforeEach(() => {
    vi.stubGlobal('fetch', vi.fn());
  });

  afterEach(() => {
    vi.unstubAllGlobals();
    vi.useRealTimers();
  });

  it('shows the backend status when /api/health responds ok', async () => {
    fetch.mockResolvedValueOnce({
      ok: true,
      status: 200,
      json: async () => ({ status: 'ok', service: 'saie-api' }),
    });

    render(<App />);

    await waitFor(() => {
      expect(screen.getByTestId('status')).toHaveTextContent('ok');
    });
  });

  it('shows "down" when the network call rejects', async () => {
    fetch.mockRejectedValueOnce(new Error('network down'));

    render(<App />);

    await waitFor(() => {
      expect(screen.getByTestId('status')).toHaveTextContent('down');
    });
    expect(screen.getByRole('alert')).toHaveTextContent('network down');
  });
});
