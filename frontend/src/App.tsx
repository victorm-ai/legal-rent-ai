import { useCallback, useMemo } from 'react';
import Box from '@mui/material/Box';
import Container from '@mui/material/Container';
import CssBaseline from '@mui/material/CssBaseline';
import { ThemeProvider } from '@mui/material/styles';
import { BrowserRouter, Navigate, Route, Routes, useNavigate } from 'react-router-dom';
import ProtectedRoute from './components/auth/ProtectedRoute';
import RootRedirect from './components/auth/RootRedirect';
import Dashboard from './components/dashboard/Dashboard';
import Footer from './components/layout/Footer';
import Header from './components/layout/Header';
import LoginForm from './components/login/LoginForm';
import ScheduleSigningPage from './components/signing/ScheduleSigningPage';
import { AuthProvider } from './context/AuthContext';
import { useAuth } from './context/useAuth';
import { createAppTheme } from './theme';

function LoginPage() {
  const { isAuthenticated } = useAuth();
  const navigate = useNavigate();

  if (isAuthenticated) {
    return <Navigate to="/dashboard" replace />;
  }

  return <LoginForm onSuccess={() => navigate('/dashboard', { replace: true })} />;
}

function AppLayout() {
  const { logout, isAuthenticated } = useAuth();
  const navigate = useNavigate();

  const handleLogout = useCallback(async () => {
    if (!window.confirm('Are you sure you want to log out?')) {
      return;
    }

    await logout();
    navigate('/login', { replace: true });
  }, [logout, navigate]);

  return (
    <Box sx={{ display: 'flex', flexDirection: 'column', minHeight: '100vh' }}>
      <Header onLogout={handleLogout} showLogout={isAuthenticated} />
      <Box component="main" sx={{ flex: 1, py: 4 }}>
        <Container maxWidth="lg">
          <Routes>
            <Route path="/" element={<RootRedirect />} />
            <Route path="/login" element={<LoginPage />} />
            <Route path="/schedule-signing" element={<ScheduleSigningPage />} />
            <Route element={<ProtectedRoute />}>
              <Route path="/dashboard" element={<Dashboard />} />
            </Route>
            <Route path="*" element={<Navigate to="/login" replace />} />
          </Routes>
        </Container>
      </Box>
      <Footer />
    </Box>
  );
}

function ThemedApp() {
  const { user } = useAuth();
  const theme = useMemo(() => createAppTheme(user?.role), [user?.role]);

  return (
    <ThemeProvider theme={theme}>
      <CssBaseline />
      <BrowserRouter>
        <AppLayout />
      </BrowserRouter>
    </ThemeProvider>
  );
}

export default function App() {
  return (
    <AuthProvider>
      <ThemedApp />
    </AuthProvider>
  );
}
