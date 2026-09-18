import { createContext } from 'react';
import type { User } from '../types/auth';

export interface AuthContextValue {
  user: User | null;
  isAuthenticated: boolean;
  login: (email: string, password: string) => Promise<{ success: boolean; message: string }>;
  logout: () => Promise<void>;
  getAuthHeader: () => string | null;
}

export const AuthContext = createContext<AuthContextValue | null>(null);
