import { act, renderHook, waitFor } from '@testing-library/react';
import type { ReactNode } from 'react';
import { TOKEN_KEY, USER_KEY } from '../config';
import * as api from '../services/api';
import { AuthProvider } from './AuthContext';
import { useAuth } from './useAuth';

vi.mock('../services/api', () => ({
  loginRequest: vi.fn(),
  logoutRequest: vi.fn(),
}));

function wrapper({ children }: { children: ReactNode }) {
  return <AuthProvider>{children}</AuthProvider>;
}

describe('AuthProvider (browser session)', () => {
  it('rejects login when email or password is empty without calling the API', async () => {
    const { result } = renderHook(() => useAuth(), { wrapper });

    let loginResult: { success: boolean; message: string } | undefined;
    await act(async () => {
      loginResult = await result.current.login('', 'password');
    });

    expect(loginResult).toEqual({ success: false, message: 'Please fill in all fields.' });
    expect(api.loginRequest).not.toHaveBeenCalled();
  });

  it('persists token and user in localStorage after successful login', async () => {
    vi.mocked(api.loginRequest).mockResolvedValue({
      ok: true,
      data: {
        access_token: 'jwt-123',
        expires_in_minutes: 60,
        user_id: 'user-1',
        email: 'client@example.com',
        name: 'Client User',
        role: 'client',
      },
    });

    const { result } = renderHook(() => useAuth(), { wrapper });

    await act(async () => {
      await result.current.login('client@example.com', 'secret');
    });

    await waitFor(() => {
      expect(result.current.isAuthenticated).toBe(true);
    });

    expect(JSON.parse(localStorage.getItem(TOKEN_KEY) ?? '{}').token).toBe('jwt-123');
    expect(JSON.parse(localStorage.getItem(USER_KEY) ?? '{}').email).toBe('client@example.com');
    expect(result.current.getAuthHeader()).toBe('Bearer jwt-123');
  });

  it('drops expired sessions loaded from localStorage', async () => {
    localStorage.setItem(
      TOKEN_KEY,
      JSON.stringify({ token: 'old-token', expiresAt: Date.now() - 1000 }),
    );
    localStorage.setItem(
      USER_KEY,
      JSON.stringify({
        id: 'user-1',
        email: 'client@example.com',
        name: 'Client',
        role: 'client',
      }),
    );

    const { result } = renderHook(() => useAuth(), { wrapper });

    await waitFor(() => {
      expect(result.current.isAuthenticated).toBe(false);
    });

    expect(localStorage.getItem(TOKEN_KEY)).toBeNull();
    expect(result.current.getAuthHeader()).toBeNull();
  });

  it('clears session on logout even if logout request fails', async () => {
    vi.mocked(api.loginRequest).mockResolvedValue({
      ok: true,
      data: {
        access_token: 'jwt-123',
        expires_in_minutes: 60,
        user_id: 'user-1',
        email: 'client@example.com',
        name: 'Client User',
        role: 'client',
      },
    });
    vi.mocked(api.logoutRequest).mockRejectedValue(new Error('network'));

    const { result } = renderHook(() => useAuth(), { wrapper });

    await act(async () => {
      await result.current.login('client@example.com', 'secret');
    });

    await act(async () => {
      await result.current.logout();
    });

    expect(result.current.isAuthenticated).toBe(false);
    expect(localStorage.getItem(TOKEN_KEY)).toBeNull();
  });
});
