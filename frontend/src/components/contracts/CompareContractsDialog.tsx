import { useState } from 'react';
import Alert from '@mui/material/Alert';
import Box from '@mui/material/Box';
import Button from '@mui/material/Button';
import Dialog from '@mui/material/Dialog';
import DialogActions from '@mui/material/DialogActions';
import DialogContent from '@mui/material/DialogContent';
import DialogTitle from '@mui/material/DialogTitle';
import FormControl from '@mui/material/FormControl';
import InputLabel from '@mui/material/InputLabel';
import MenuItem from '@mui/material/MenuItem';
import Select from '@mui/material/Select';
import Typography from '@mui/material/Typography';
import { useAuth } from '../../context/useAuth';
import { compareContractsRequest } from '../../services/api';
import type { ContractSummary } from '../../types/contracts';

interface CompareContractsDialogProps {
  open: boolean;
  contracts: ContractSummary[];
  onClose: () => void;
}

export default function CompareContractsDialog({
  open,
  contracts,
  onClose,
}: CompareContractsDialogProps) {
  const { getAuthHeader } = useAuth();
  const [baseId, setBaseId] = useState('');
  const [compareId, setCompareId] = useState('');
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [resultSummary, setResultSummary] = useState<string | null>(null);

  const handleCompare = async () => {
    const authHeader = getAuthHeader();
    if (!authHeader || !baseId || !compareId) return;
    setLoading(true);
    setError(null);
    setResultSummary(null);
    const result = await compareContractsRequest(authHeader, baseId, compareId);
    setLoading(false);
    if (!result.ok) {
      setError(result.detail);
      return;
    }
    setResultSummary(
      `${result.data.summary ?? 'Comparison complete.'} (${result.data.changes.length} changes)`,
    );
  };

  const handleClose = () => {
    if (loading) return;
    setBaseId('');
    setCompareId('');
    setError(null);
    setResultSummary(null);
    onClose();
  };

  return (
    <Dialog open={open} onClose={handleClose} fullWidth maxWidth="sm">
      <DialogTitle>Compare contract versions</DialogTitle>
      <DialogContent dividers>
        <Typography variant="body2" color="text.secondary" sx={{ mb: 2 }}>
          Both contracts need a completed analysis for their upload perspective. The comparison detects clause and field changes (RF-59–62).
        </Typography>
        <Box sx={{ display: 'flex', flexDirection: 'column', gap: 2 }}>
          <FormControl fullWidth>
            <InputLabel>Base contract</InputLabel>
            <Select label="Base contract" value={baseId} onChange={(e) => setBaseId(e.target.value)}>
              {contracts.map((c) => (
                <MenuItem key={c.id} value={c.id}>
                  {c.title ?? c.id.slice(0, 8)}
                </MenuItem>
              ))}
            </Select>
          </FormControl>
          <FormControl fullWidth>
            <InputLabel>Compare contract</InputLabel>
            <Select label="Compare contract" value={compareId} onChange={(e) => setCompareId(e.target.value)}>
              {contracts.map((c) => (
                <MenuItem key={c.id} value={c.id}>
                  {c.title ?? c.id.slice(0, 8)}
                </MenuItem>
              ))}
            </Select>
          </FormControl>
        </Box>
        {error && <Alert severity="error" sx={{ mt: 2 }}>{error}</Alert>}
        {resultSummary && <Alert severity="success" sx={{ mt: 2 }}>{resultSummary}</Alert>}
      </DialogContent>
      <DialogActions>
        <Button onClick={handleClose}>Close</Button>
        <Button variant="contained" onClick={() => void handleCompare()} disabled={loading || !baseId || !compareId || baseId === compareId}>
          Compare
        </Button>
      </DialogActions>
    </Dialog>
  );
}
