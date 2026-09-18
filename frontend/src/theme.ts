import { createTheme, type ThemeOptions } from '@mui/material/styles';
import type { UserRole } from './types/auth';

const sharedThemeOptions: ThemeOptions = {
  palette: {
    secondary: {
      main: '#0f172a',
      dark: '#020617',
      light: '#334155',
    },
    success: {
      main: '#10b981',
    },
    warning: {
      main: '#f59e0b',
    },
    error: {
      main: '#ef4444',
    },
    info: {
      main: '#3b82f6',
    },
    background: {
      default: '#f8fafc',
      paper: '#ffffff',
    },
    text: {
      primary: '#0f172a',
      secondary: '#475569',
    },
  },
  typography: {
    fontFamily: '"Inter", -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, sans-serif',
    h1: { fontWeight: 700 },
    h2: { fontWeight: 600 },
    h3: { fontWeight: 600 },
    h4: { fontWeight: 600 },
  },
  shape: {
    borderRadius: 8,
  },
  components: {
    MuiButton: {
      styleOverrides: {
        root: {
          textTransform: 'none',
          fontWeight: 500,
        },
      },
    },
    MuiCard: {
      styleOverrides: {
        root: {
          boxShadow: '0 4px 6px -1px rgba(0, 0, 0, 0.1), 0 2px 4px -1px rgba(0, 0, 0, 0.06)',
        },
      },
    },
  },
};

const rolePrimaryPalettes: Record<'client' | 'lawyer', ThemeOptions['palette']> = {
  client: {
    primary: {
      main: '#2563eb',
      dark: '#1d4ed8',
      light: '#60a5fa',
    },
  },
  lawyer: {
    primary: {
      main: '#059669',
      dark: '#047857',
      light: '#34d399',
    },
  },
};

function resolveRolePaletteKey(role: UserRole | null | undefined): 'client' | 'lawyer' {
  if (role === 'lawyer') {
    return 'lawyer';
  }
  return 'client';
}

export function createAppTheme(role?: UserRole | null) {
  const paletteKey = resolveRolePaletteKey(role);
  return createTheme({
    ...sharedThemeOptions,
    palette: {
      ...sharedThemeOptions.palette,
      ...rolePrimaryPalettes[paletteKey],
    },
  });
}

const theme = createAppTheme();

export default theme;
