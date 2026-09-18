import { useCallback, useMemo, useState, type ReactNode } from 'react';
import { TOKEN_KEY, USER_KEY } from '../config';
import { loginRequest, logoutRequest } from '../services/api';
import type { AuthToken, LoginResponse, User } from '../types/auth';
import { AuthContext } from './auth-context';

function buildSession(data: LoginResponse): { token: AuthToken; user: User } {
  return {
    token: {
      token: data.access_token,
      expiresAt: Date.now() + (data.expires_in_minutes || 60) * 60 * 1000,
    },
    user: {
      id: data.user_id,
      email: data.email,
      name: data.name,
      role: data.role,
    },
  };
}

function clearStoredSession(): void {
  localStorage.removeItem(TOKEN_KEY);
  localStorage.removeItem(USER_KEY);
}

function saveStoredSession(token: AuthToken, user: User): void {
  localStorage.setItem(TOKEN_KEY, JSON.stringify(token));
  localStorage.setItem(USER_KEY, JSON.stringify(user));
}

function loadStoredSession(): { token: AuthToken; user: User } | null {
  try {
    const tokenRaw = localStorage.getItem(TOKEN_KEY);
    const userRaw = localStorage.getItem(USER_KEY);
    if (!tokenRaw || !userRaw) {
      return null;
    }

    const token = JSON.parse(tokenRaw) as AuthToken;
    const user = JSON.parse(userRaw) as User;

    if (!token.token || token.expiresAt <= Date.now()) {
      clearStoredSession();
      return null;
    }

    return { token, user };
  } catch {
    clearStoredSession();
    return null;
  }
}

export function AuthProvider({ children }: { children: ReactNode }) {
  const storedSession = loadStoredSession();
  const [authToken, setAuthToken] = useState<AuthToken | null>(storedSession?.token ?? null);
  const [user, setUser] = useState<User | null>(storedSession?.user ?? null);

  const clearSession = useCallback(() => {
    clearStoredSession();
    setAuthToken(null);
    setUser(null);
  }, []);

  const getAuthHeader = useCallback((): string | null => {
    if (!authToken) {
      return null;
    }

    if (authToken.expiresAt <= Date.now()) {
      clearSession();
      return null;
    }

    return `Bearer ${authToken.token}`;
  }, [authToken, clearSession]);

  const login = useCallback(async (email: string, password: string) => {
    if (!email || !password) {
      return { success: false, message: 'Please fill in all fields.' };
    }

    try {
      const result = await loginRequest(email, password);

      if (!result.ok) {
        return { success: false, message: result.detail };
      }

      const session = buildSession(result.data);
      setAuthToken(session.token);
      setUser(session.user);
      saveStoredSession(session.token, session.user);

      return {
        success: true,
        message: `Welcome, ${result.data.name}! Sign-in successful.`,
      };
    } catch {
      if (!navigator.onLine) {
        return {
          success: false,
          message: 'No internet connection. Is the backend running?',
        };
      }
      return { success: false, message: 'Network error while connecting to the server.' };
    }
  }, []);

  const logout = useCallback(async () => {
    try {
      const authHeader = authToken ? `Bearer ${authToken.token}` : null;
      if (authHeader) {
        await logoutRequest(authHeader);
      }
    } catch (error) {
      console.error('Logout error:', error);
    } finally {
      clearSession();
    }
  }, [authToken, clearSession]);

  const value = useMemo(
    () => ({
      user,
      isAuthenticated: user !== null,
      login,
      logout,
      getAuthHeader,
    }),
    [user, login, logout, getAuthHeader],
  );

  return <AuthContext.Provider value={value}>{children}</AuthContext.Provider>;
}
