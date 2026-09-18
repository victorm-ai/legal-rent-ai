import { useEffect, useState } from 'react';
import Alert from '@mui/material/Alert';
import Button from '@mui/material/Button';
import Dialog from '@mui/material/Dialog';
import DialogActions from '@mui/material/DialogActions';
import DialogContent from '@mui/material/DialogContent';
import DialogContentText from '@mui/material/DialogContentText';
import DialogTitle from '@mui/material/DialogTitle';
import TextField from '@mui/material/TextField';

interface ContractClosureDialogProps {
  open: boolean;
  saving: boolean;
  error: string | null;
  onClose: () => void;
  onConfirm: (notes: string) => void;
}

export default function ContractClosureDialog({
  open,
  saving,
  error,
  onClose,
  onConfirm,
}: ContractClosureDialogProps) {
  const [notes, setNotes] = useState('');

  useEffect(() => {
    if (open) {
      setNotes('');
    }
  }, [open]);

  const canSubmit = notes.trim().length >= 1;

  return (
    <Dialog open={open} onClose={saving ? undefined : onClose} fullWidth maxWidth="sm">
      <DialogTitle>Cerrar expediente</DialogTitle>
      <DialogContent>
        <DialogContentText sx={{ mb: 2 }}>
          Indique las notas finales para el cliente antes de marcar el contrato como Terminado.
        </DialogContentText>
        {error && (
          <Alert severity="error" sx={{ mb: 2 }}>
            {error}
          </Alert>
        )}
        <TextField
          fullWidth
          multiline
          minRows={4}
          label="Notas finales"
          value={notes}
          onChange={(event) => setNotes(event.target.value)}
          disabled={saving}
        />
      </DialogContent>
      <DialogActions>
        <Button onClick={onClose} disabled={saving}>
          Cancelar
        </Button>
        <Button
          variant="contained"
          onClick={() => onConfirm(notes.trim())}
          disabled={saving || !canSubmit}
        >
          {saving ? 'Guardando…' : 'Marcar como Terminado'}
        </Button>
      </DialogActions>
    </Dialog>
  );
}
