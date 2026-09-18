import { useEffect, useState } from 'react';
import Alert from '@mui/material/Alert';
import Button from '@mui/material/Button';
import Dialog from '@mui/material/Dialog';
import DialogActions from '@mui/material/DialogActions';
import DialogContent from '@mui/material/DialogContent';
import DialogContentText from '@mui/material/DialogContentText';
import DialogTitle from '@mui/material/DialogTitle';
import { useAuth } from '../../context/useAuth';
import { deleteContractRequest, getRetentionPolicyRequest } from '../../services/api';
import type { ContractSummary } from '../../types/contracts';
import type { RetentionPolicy } from '../../types/retention';

interface DeleteContractDialogProps {
  contract: ContractSummary | null;
  open: boolean;
  onClose: () => void;
  onDeleted: (contractId: string) => void;
}

export default function DeleteContractDialog({
  contract,
  open,
  onClose,
  onDeleted,
}: DeleteContractDialogProps) {
  const { getAuthHeader } = useAuth();
  const [deleting, setDeleting] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [policy, setPolicy] = useState<RetentionPolicy | null>(null);

  useEffect(() => {
    if (!open) {
      return;
    }

    const authHeader = getAuthHeader();
    if (!authHeader) {
      return;
    }

    void getRetentionPolicyRequest(authHeader).then((result) => {
      if (result.ok) {
        setPolicy(result.data);
      }
    });
  }, [open, getAuthHeader]);

  const handleClose = () => {
    if (deleting) {
      return;
    }
    setError(null);
    onClose();
  };

  const handleConfirm = async () => {
    if (!contract) {
      return;
    }

    const authHeader = getAuthHeader();
    if (!authHeader) {
      setError('Your session has expired. Please sign in again.');
      return;
    }

    setDeleting(true);
    setError(null);

    const result = await deleteContractRequest(authHeader, contract.id);
    setDeleting(false);

    if (result.ok) {
      onDeleted(contract.id);
      setError(null);
      onClose();
      return;
    }

    setError(result.detail);
  };

  const contractLabel = contract?.title ?? 'this contract';

  return (
    <Dialog open={open} onClose={handleClose} maxWidth="sm" fullWidth>
      <DialogTitle>Delete contract?</DialogTitle>
      <DialogContent>
        {error && (
          <Alert severity="error" sx={{ mb: 2 }}>
            {error}
          </Alert>
        )}
        <DialogContentText sx={{ mb: 1.5 }}>
          &quot;{contractLabel}&quot; will be removed from your list. The contract and its
          documents are kept in the system and are not permanently erased.
        </DialogContentText>
        {policy && (
          <DialogContentText color="text.secondary">
            Retention policy: archived records are kept for{' '}
            <strong>{policy.soft_delete_retention_days} days</strong> before they may be
            permanently removed according to system retention rules.
          </DialogContentText>
        )}
      </DialogContent>
      <DialogActions sx={{ px: 3, pb: 2 }}>
        <Button onClick={handleClose} disabled={deleting}>
          Cancel
        </Button>
        <Button onClick={handleConfirm} color="error" variant="contained" disabled={deleting}>
          {deleting ? 'Deleting…' : 'Delete'}
        </Button>
      </DialogActions>
    </Dialog>
  );
}
