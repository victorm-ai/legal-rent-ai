import { useEffect, useMemo, useState } from 'react';
import Alert from '@mui/material/Alert';
import Box from '@mui/material/Box';
import Button from '@mui/material/Button';
import Dialog from '@mui/material/Dialog';
import DialogActions from '@mui/material/DialogActions';
import DialogContent from '@mui/material/DialogContent';
import DialogContentText from '@mui/material/DialogContentText';
import DialogTitle from '@mui/material/DialogTitle';
import Chip from '@mui/material/Chip';
import FormControl from '@mui/material/FormControl';
import InputLabel from '@mui/material/InputLabel';
import MenuItem from '@mui/material/MenuItem';
import Select from '@mui/material/Select';
import Typography from '@mui/material/Typography';
import type { SelectChangeEvent } from '@mui/material/Select';
import { STATUS_LABELS } from '../../config';
import { useAuth } from '../../context/useAuth';
import { updateContractRequest } from '../../services/api';
import {
  isContractLocked,
  lawyerMustCloseWithNotes,
} from '../../utils/contractLifecycle';
import type { Contract, ContractStatus } from '../../types/contracts';
import ContractClosureDialog from './ContractClosureDialog';

const CLIENT_TRANSITIONS: Record<string, string[]> = {
  draft: ['in_review'],
  in_review: [],
  approved: [],
  in_signing: [],
  signed: [],
  expired: [],
  terminated: [],
};

const LAWYER_TRANSITIONS: Record<string, string[]> = {
  draft: [],
  in_review: [],
  approved: ['terminated'],
  in_signing: [],
  signed: [],
  expired: [],
  terminated: [],
};

function allowedTargets(role: string, currentStatus: string): string[] {
  if (role === 'lawyer') {
    return LAWYER_TRANSITIONS[currentStatus] ?? [];
  }
  return CLIENT_TRANSITIONS[currentStatus] ?? [];
}

function statusConfirmMessage(fromStatus: string, toStatus: string): string {
  if (fromStatus === 'draft' && toStatus === 'in_review') {
    return 'Send this contract for legal review? The lawyer will be able to view the case file.';
  }

  const fromLabel = STATUS_LABELS[fromStatus] ?? fromStatus;
  const toLabel = STATUS_LABELS[toStatus] ?? toStatus;
  return `Change status from "${fromLabel}" to "${toLabel}"?`;
}

function applyButtonLabel(fromStatus: string, toStatus: string): string {
  if (fromStatus === 'draft' && toStatus === 'in_review') {
    return 'Send for review';
  }
  return 'Apply change';
}

function statusChipColor(status: string): 'success' | 'warning' | 'error' | 'default' | 'info' {
  if (status === 'in_review') {
    return 'info';
  }
  if (status === 'approved' || status === 'signed') {
    return 'success';
  }
  if (status === 'draft' || status === 'in_signing' || status === 'pending') {
    return 'warning';
  }
  if (status === 'rejected' || status === 'terminated' || status === 'expired') {
    return 'error';
  }
  return 'default';
}

function statusHint(role: string | undefined, status: string): string | null {
  if (isContractLocked(status)) {
    return 'Case file closed. No further changes allowed.';
  }
  if (role === 'lawyer' && status === 'in_review') {
    return 'In legal review. Upload the edited version when ready.';
  }
  if (role === 'client' && status === 'in_review') {
    return 'Waiting for the lawyer’s edited version.';
  }
  if (role === 'client' && status === 'approved') {
    return 'Contract approved. Waiting for the lawyer to close the case file.';
  }
  if (role === 'lawyer' && status === 'approved') {
    return 'The client approved the edited version. You may close the case file.';
  }
  return null;
}

interface ContractStatusSelectProps {
  contract: Contract;
  onUpdated: (contract: Contract) => void;
}

export default function ContractStatusSelect({
  contract,
  onUpdated,
}: ContractStatusSelectProps) {
  const { user, getAuthHeader } = useAuth();
  const [pendingStatus, setPendingStatus] = useState(contract.status);
  const [confirmOpen, setConfirmOpen] = useState(false);
  const [closureOpen, setClosureOpen] = useState(false);
  const [saving, setSaving] = useState(false);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    setPendingStatus(contract.status);
    setConfirmOpen(false);
    setClosureOpen(false);
    setError(null);
  }, [contract.id, contract.status]);

  const options = useMemo(() => {
    const targets = allowedTargets(user?.role ?? '', contract.status);
    return [contract.status, ...targets.filter((status) => status !== contract.status)];
  }, [contract.status, user?.role]);

  const canChangeStatus = !isContractLocked(contract.status) && options.length > 1;
  const hasPendingChange = pendingStatus !== contract.status;
  const hint = statusHint(user?.role, contract.status);

  const handleSelectChange = (event: SelectChangeEvent<string>) => {
    setPendingStatus(event.target.value);
    setError(null);
  };

  const handleApplyClick = () => {
    if (!hasPendingChange) {
      return;
    }
    if (lawyerMustCloseWithNotes(user?.role, contract.status, pendingStatus)) {
      setClosureOpen(true);
      return;
    }
    setConfirmOpen(true);
  };

  const handleConfirmCancel = () => {
    setConfirmOpen(false);
    setPendingStatus(contract.status);
  };

  const submitUpdate = async (
    status: ContractStatus,
    closureNotes?: string,
  ): Promise<boolean> => {
    const authHeader = getAuthHeader();
    if (!authHeader) {
      setError('Your session has expired. Please sign in again.');
      setPendingStatus(contract.status);
      return false;
    }

    setSaving(true);
    setError(null);

    const result = await updateContractRequest(authHeader, contract.id, {
      status,
      closure_notes: closureNotes,
    });

    setSaving(false);

    if (!result.ok) {
      setError(result.detail);
      setPendingStatus(contract.status);
      return false;
    }

    onUpdated(result.data);
    setPendingStatus(result.data.status);
    return true;
  };

  const handleConfirmYes = async () => {
    setConfirmOpen(false);
    await submitUpdate(pendingStatus as ContractStatus);
  };

  const handleClosureConfirm = async (notes: string) => {
    const ok = await submitUpdate('terminated', notes);
    if (ok) {
      setClosureOpen(false);
    }
  };

  if (!canChangeStatus) {
    return (
      <Box sx={{ display: 'flex', flexDirection: 'column', gap: 0.5, alignItems: 'flex-end' }}>
        <Box sx={{ display: 'flex', alignItems: 'center', gap: 1, flexWrap: 'wrap' }}>
          <Chip
            label={STATUS_LABELS[contract.status] ?? contract.status}
            color={statusChipColor(contract.status)}
            size="small"
          />
        </Box>
        {hint && (
          <Typography variant="caption" color="text.secondary" align="right">
            {hint}
          </Typography>
        )}
        {contract.closure_notes && (
          <Alert severity="info" sx={{ mt: 0.5, maxWidth: 420 }}>
            <Typography variant="caption" component="div" sx={{ fontWeight: 600 }}>
              Lawyer’s closing notes
            </Typography>
            <Typography variant="body2" sx={{ whiteSpace: 'pre-wrap' }}>
              {contract.closure_notes}
            </Typography>
          </Alert>
        )}
      </Box>
    );
  }

  return (
    <>
      <Box sx={{ display: 'flex', flexDirection: 'column', gap: 0.5, alignItems: 'flex-end' }}>
        <Box sx={{ display: 'flex', alignItems: 'center', gap: 1, flexWrap: 'wrap' }}>
          <FormControl size="small" sx={{ minWidth: 180 }} disabled={saving}>
            <InputLabel id="contract-status-label">Status</InputLabel>
            <Select
              labelId="contract-status-label"
              label="Status"
              value={pendingStatus}
              onChange={handleSelectChange}
            >
              {options.map((status) => (
                <MenuItem key={status} value={status}>
                  {STATUS_LABELS[status] ?? status}
                </MenuItem>
              ))}
            </Select>
          </FormControl>
          {hasPendingChange && (
            <Button
              variant="contained"
              size="small"
              onClick={handleApplyClick}
              disabled={saving}
            >
              {applyButtonLabel(contract.status, pendingStatus)}
            </Button>
          )}
        </Box>
        {hint && (
          <Typography variant="caption" color="text.secondary" align="right">
            {hint}
          </Typography>
        )}
        {error && (
          <Alert severity="error" sx={{ mt: 0.5 }}>
            {error}
          </Alert>
        )}
      </Box>

      <Dialog open={confirmOpen} onClose={handleConfirmCancel}>
        <DialogTitle>Confirm status change</DialogTitle>
        <DialogContent>
          <DialogContentText>
            {statusConfirmMessage(contract.status, pendingStatus)}
          </DialogContentText>
        </DialogContent>
        <DialogActions>
          <Button onClick={handleConfirmCancel}>Cancel</Button>
          <Button variant="contained" onClick={() => void handleConfirmYes()} autoFocus>
            Yes
          </Button>
        </DialogActions>
      </Dialog>

      <ContractClosureDialog
        open={closureOpen}
        saving={saving}
        error={error}
        onClose={() => {
          if (saving) {
            return;
          }
          setClosureOpen(false);
          setPendingStatus(contract.status);
          setError(null);
        }}
        onConfirm={(notes) => void handleClosureConfirm(notes)}
      />
    </>
  );
}
