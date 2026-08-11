import { describe, it, expect, vi, beforeEach, afterEach } from 'vitest';
import { render, screen, waitFor, fireEvent } from '@testing-library/react';
import App from './App.jsx';

/**
 * M02 — Frontend auth wiring smoke tests (FR-053, NFR-004).
 *
 * The SPA's auth surface is the seam between the user and the
 * Keycloak-protected API. These tests pin:
 *   1. The login panel renders unauthenticated.
 *   2. ``Sign in as <role>`` calls the dev login endpoint, stores the
 *      session in sessionStorage, and swaps to the user-badge view.
 *   3. The user badge surfaces the verified principal returned by
 *      ``GET /api/v1/me``.
 */

function mockOkJson(json) {
  return { ok: true, status: 200, json: async () => json };
}

describe('App — auth surface (M02)', () => {
  beforeEach(() => {
    vi.stubGlobal('fetch', vi.fn());
    sessionStorage.clear();
  });

  afterEach(() => {
    vi.unstubAllGlobals();
    vi.useRealTimers();
    sessionStorage.clear();
  });

  it('shows the login panel when no session exists', async () => {
    // /health passes; /me returns 401 to confirm "no session".
    fetch.mockImplementation((url) => {
      if (url === '/api/health') {
        return Promise.resolve(mockOkJson({ status: 'ok', service: 'saie-api' }));
      }
      if (url === '/api/v1/me') {
        return Promise.resolve({ ok: false, status: 401, json: async () => ({}) });
      }
      return Promise.resolve(mockOkJson({}));
    });

    render(<App />);

    await waitFor(() => {
      expect(screen.getByTestId('login-panel')).toBeTruthy();
    });
  });

  it('signs in and surfaces the user badge on the dev login success', async () => {
    // /api/health ok, /api/v1/me initially 401 then ok with principal.
    fetch.mockImplementation((url, init) => {
      if (url === '/api/health') {
        return Promise.resolve(mockOkJson({ status: 'ok', service: 'saie-api' }));
      }
      if (url === '/api/v1/me') {
        const headers = init?.headers ?? new Headers();
        const hasBearer =
          headers instanceof Headers
            ? headers.has('Authorization')
            : Boolean(headers?.Authorization);
        if (!hasBearer) {
          return Promise.resolve({ ok: false, status: 401, json: async () => ({}) });
        }
        return Promise.resolve(
          mockOkJson({
            sub: 'demo-user',
            username: 'demo-user',
            email: 'demo@example.com',
            tenant_id: 'demo-tenant',
            roles: ['analyst'],
          })
        );
      }
      if (url === '/api/v1/auth/dev/login' && init?.method === 'POST') {
        return Promise.resolve(
          mockOkJson({
            access_token: 'fake.jwt.token',
            token_type: 'Bearer',
            expires_in: 300,
            principal: {
              sub: 'demo-user',
              username: 'demo-user',
              email: 'demo@example.com',
              tenant_id: 'demo-tenant',
              roles: ['analyst'],
            },
          })
        );
      }
      return Promise.resolve(mockOkJson({}));
    });

    render(<App />);

    // The login panel is visible.
    await waitFor(() => {
      expect(screen.getByTestId('login-panel')).toBeTruthy();
    });

    // Click Sign in as analyst — this triggers the dev login.
    fireEvent.click(screen.getByTestId('login-analyst'));

    // The user badge swaps in.
    await waitFor(() => {
      expect(screen.getByTestId('user-badge')).toBeTruthy();
    });
    expect(screen.getByTestId('user-badge').textContent).toMatch(/demo-user/);
  });
});

describe('App — backend health surface (M01)', () => {
  beforeEach(() => {
    vi.stubGlobal('fetch', vi.fn());
  });

  afterEach(() => {
    vi.unstubAllGlobals();
    vi.useRealTimers();
    sessionStorage.clear();
  });

  it('shows the backend status when /api/health responds ok', async () => {
    fetch.mockImplementation((url) => {
      if (url === '/api/health') {
        return Promise.resolve(mockOkJson({ status: 'ok', service: 'saie-api' }));
      }
      if (url === '/api/v1/me') {
        return Promise.resolve({ ok: false, status: 401, json: async () => ({}) });
      }
      return Promise.resolve(mockOkJson({}));
    });

    render(<App />);

    await waitFor(() => {
      expect(screen.getByTestId('status')).toHaveTextContent('ok');
    });
  });

  it('shows "down" when the network call rejects', async () => {
    fetch.mockImplementation((url) => {
      if (url === '/api/health') {
        return Promise.reject(new Error('network down'));
      }
      if (url === '/api/v1/me') {
        return Promise.resolve({ ok: false, status: 401, json: async () => ({}) });
      }
      return Promise.resolve(mockOkJson({}));
    });

    render(<App />);

    await waitFor(() => {
      expect(screen.getByTestId('status')).toHaveTextContent('down');
    });
    expect(screen.getByRole('alert')).toHaveTextContent('network down');
  });
});
