import Box from '@mui/material/Box';
import Button from '@mui/material/Button';
import AppBar from '@mui/material/AppBar';
import Container from '@mui/material/Container';
import Toolbar from '@mui/material/Toolbar';
import Typography from '@mui/material/Typography';
import { DocumentIcon } from '../icons/Icons';
import { useAuth } from '../../context/useAuth';

interface HeaderProps {
  onLogout: () => void;
  showLogout?: boolean;
}

export default function Header({ onLogout, showLogout = false }: HeaderProps) {
  const { isAuthenticated } = useAuth();
  const displayLogout = isAuthenticated && showLogout;

  return (
    <AppBar
      position="sticky"
      elevation={0}
      sx={{
        bgcolor: 'background.paper',
        borderBottom: 1,
        borderColor: 'grey.200',
      }}
    >
      <Container maxWidth="lg">
        <Toolbar disableGutters sx={{ py: 1, justifyContent: 'space-between' }}>
          <Box sx={{ display: 'flex', alignItems: 'center', gap: 1.5, color: 'primary.main' }}>
            <DocumentIcon sx={{ fontSize: 32 }} />
            <Typography variant="h6" component="span" fontWeight={700} color="primary.main">
              Legal Rent AI
            </Typography>
          </Box>

          {displayLogout && (
            <Button
              variant="outlined"
              color="primary"
              onClick={onLogout}
              sx={{ fontWeight: 600 }}
            >
              Log out
            </Button>
          )}
        </Toolbar>
      </Container>
    </AppBar>
  );
}
