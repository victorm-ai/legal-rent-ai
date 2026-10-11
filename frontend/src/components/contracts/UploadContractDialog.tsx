import { useRef, useState } from 'react';
import Alert from '@mui/material/Alert';
import Box from '@mui/material/Box';
import Button from '@mui/material/Button';
import Dialog from '@mui/material/Dialog';
import DialogActions from '@mui/material/DialogActions';
import DialogContent from '@mui/material/DialogContent';
import DialogTitle from '@mui/material/DialogTitle';
import TextField from '@mui/material/TextField';
import Typography from '@mui/material/Typography';
import { DEFAULT_ANALYSIS_PERSPECTIVE, MAX_UPLOAD_SIZE_BYTES } from '../../config';
import { useAuth } from '../../context/useAuth';
import { createContractRequest } from '../../services/api';
import type { Contract } from '../../types/contracts';

const ALLOWED_EXTENSIONS = ['.pdf', '.docx'];

interface UploadContractDialogProps {
  open: boolean;
  onClose: () => void;
  onSuccess: (contract: Contract) => void;
}

function isAllowedFile(file: File): boolean {
  const name = file.name.toLowerCase();
  return ALLOWED_EXTENSIONS.some((ext) => name.endsWith(ext));
}

export default function UploadContractDialog({
  open,
  onClose,
  onSuccess,
}: UploadContractDialogProps) {
  const { getAuthHeader } = useAuth();
  const fileInputRef = useRef<HTMLInputElement>(null);

  const [title, setTitle] = useState('');
  const [selectedFile, setSelectedFile] = useState<File | null>(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const resetForm = () => {
    setTitle('');
    setSelectedFile(null);
    setError(null);
    if (fileInputRef.current) {
      fileInputRef.current.value = '';
    }
  };

  const handleClose = () => {
    if (loading) {
      return;
    }
    resetForm();
    onClose();
  };

  const handleChooseFile = () => {
    fileInputRef.current?.click();
  };

  const handleFileChange = (event: React.ChangeEvent<HTMLInputElement>) => {
    const file = event.target.files?.[0];
    setError(null);

    if (!file) {
      setSelectedFile(null);
      return;
    }

    if (!isAllowedFile(file)) {
      setError('Only PDF and DOCX files are allowed.');
      setSelectedFile(null);
      event.target.value = '';
      return;
    }

    if (file.size > MAX_UPLOAD_SIZE_BYTES) {
      setError('File exceeds the maximum allowed size of 25 MB.');
      setSelectedFile(null);
      event.target.value = '';
      return;
    }

    setSelectedFile(file);
    if (!title.trim()) {
      setTitle(file.name.replace(/\.(pdf|docx)$/i, ''));
    }
  };

  const handleSubmit = async () => {
    setError(null);

    if (!selectedFile) {
      setError('Please select a PDF or DOCX file.');
      return;
    }

    const authHeader = getAuthHeader();
    if (!authHeader) {
      setError('Your session has expired. Please sign in again.');
      return;
    }

    setLoading(true);

    try {
      const result = await createContractRequest(authHeader, {
        file: selectedFile,
        perspective: DEFAULT_ANALYSIS_PERSPECTIVE,
        title: title.trim() || undefined,
      });

      if (!result.ok) {
        setError(result.detail);
        return;
      }

      onSuccess(result.data);
      resetForm();
      onClose();
    } catch {
      setError('Network error while uploading the contract.');
    } finally {
      setLoading(false);
    }
  };

  return (
    <Dialog open={open} onClose={handleClose} fullWidth maxWidth="sm">
      <DialogTitle>New contract analysis</DialogTitle>
      <DialogContent>
        <Typography variant="body2" color="text.secondary" sx={{ mb: 2 }}>
          Upload a lease contract in PDF or DOCX format (max 25 MB). The system
          will automatically detect whether the file is a main contract, annex,
          or other related document, then start the analysis from the tenant
          perspective.
        </Typography>

        <input
          ref={fileInputRef}
          type="file"
          accept=".pdf,.docx,application/pdf,application/vnd.openxmlformats-officedocument.wordprocessingml.document"
          hidden
          onChange={handleFileChange}
        />

        <Box sx={{ mb: 2 }}>
          <Button variant="outlined" onClick={handleChooseFile} disabled={loading}>
            Choose file
          </Button>
          {selectedFile && (
            <Typography variant="body2" sx={{ mt: 1 }}>
              Selected: <strong>{selectedFile.name}</strong> (
              {(selectedFile.size / 1024 / 1024).toFixed(2)} MB)
            </Typography>
          )}
        </Box>

        <TextField
          fullWidth
          margin="normal"
          label="Contract title (optional)"
          value={title}
          onChange={(e) => setTitle(e.target.value)}
          disabled={loading}
        />

        {error && (
          <Alert severity="error" sx={{ mt: 2 }}>
            {error}
          </Alert>
        )}
      </DialogContent>
      <DialogActions sx={{ px: 3, pb: 2 }}>
        <Button onClick={handleClose} disabled={loading}>
          Cancel
        </Button>
        <Button variant="contained" onClick={handleSubmit} disabled={loading || !selectedFile}>
          {loading ? 'Uploading…' : 'Upload and analyze'}
        </Button>
      </DialogActions>
    </Dialog>
  );
}
