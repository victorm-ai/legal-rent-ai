import { useCallback, useEffect, useRef, useState } from 'react';
import Alert from '@mui/material/Alert';
import Box from '@mui/material/Box';
import Button from '@mui/material/Button';
import CircularProgress from '@mui/material/CircularProgress';
import Dialog from '@mui/material/Dialog';
import DialogActions from '@mui/material/DialogActions';
import DialogContent from '@mui/material/DialogContent';
import DialogTitle from '@mui/material/DialogTitle';
import Tab from '@mui/material/Tab';
import Tabs from '@mui/material/Tabs';
import Typography from '@mui/material/Typography';
import { renderAsync } from 'docx-preview';
import DocumentTypeChips from './DocumentTypeChips';
import ContractStatusSelect from './ContractStatusSelect';
import { DOCUMENT_TYPE_LABELS, MAX_UPLOAD_SIZE_BYTES, PERSPECTIVE_LABELS } from '../../config';
import { useAuth } from '../../context/useAuth';
import {
  downloadDocumentRequest,
  getContractRequest,
  uploadLawyerRevisionRequest,
} from '../../services/api';
import type { Contract, ContractDocument } from '../../types/contracts';
import { documentTypeDisplayLabel } from '../../utils/contractLifecycle';
import '../../styles/docx-viewer.css';

interface DocumentViewerDialogProps {
  contractId: string | null;
  open: boolean;
  onClose: () => void;
  initialPage?: number | null;
  preferredDocumentType?: ContractDocument['document_type'] | null;
  onContractUpdated?: (contract: Contract) => void;
}

const DOCUMENT_TAB_ORDER: Record<string, number> = {
  main_contract: 0,
  annex: 1,
  other: 2,
  lawyer_revision: 3,
};

function isPdfDocument(document: ContractDocument): boolean {
  return (
    document.mime_type === 'application/pdf' ||
    document.file_name.toLowerCase().endsWith('.pdf')
  );
}

function isDocxDocument(document: ContractDocument): boolean {
  return (
    document.mime_type ===
      'application/vnd.openxmlformats-officedocument.wordprocessingml.document' ||
    document.file_name.toLowerCase().endsWith('.docx')
  );
}

function sortDocuments(documents: ContractDocument[]): ContractDocument[] {
  return [...documents].sort((left, right) => {
    const leftOrder = DOCUMENT_TAB_ORDER[left.document_type] ?? 99;
    const rightOrder = DOCUMENT_TAB_ORDER[right.document_type] ?? 99;
    if (leftOrder !== rightOrder) {
      return leftOrder - rightOrder;
    }
    return left.file_name.localeCompare(right.file_name);
  });
}

function defaultDocumentIndex(
  documents: ContractDocument[],
  preferredDocumentType?: ContractDocument['document_type'] | null,
): number {
  const sorted = sortDocuments(documents);
  if (preferredDocumentType) {
    const preferredIndex = sorted.findIndex((item) => item.document_type === preferredDocumentType);
    if (preferredIndex >= 0) {
      return preferredIndex;
    }
  }
  const mainIndex = sorted.findIndex((item) => item.document_type === 'main_contract');
  return mainIndex >= 0 ? mainIndex : 0;
}

function canUploadLawyerRevision(userRole: string | undefined, contractStatus: string): boolean {
  return (
    userRole === 'lawyer' &&
    contractStatus !== 'draft' &&
    contractStatus !== 'terminated'
  );
}

function documentTabLabel(document: ContractDocument, contractStatus?: string | null): string {
  if (document.document_type === 'lawyer_revision') {
    return documentTypeDisplayLabel(document.document_type, contractStatus);
  }
  if (document.document_type === 'main_contract') {
    return DOCUMENT_TYPE_LABELS.main_contract;
  }
  return document.file_name;
}

function downloadBlob(blob: Blob, fileName: string) {
  const url = URL.createObjectURL(blob);
  const anchor = document.createElement('a');
  anchor.href = url;
  anchor.download = fileName;
  anchor.click();
  URL.revokeObjectURL(url);
}

export default function DocumentViewerDialog({
  contractId,
  open,
  onClose,
  initialPage = null,
  preferredDocumentType = null,
  onContractUpdated,
}: DocumentViewerDialogProps) {
  const { user, getAuthHeader } = useAuth();
  const docxContainerRef = useRef<HTMLDivElement>(null);
  const pdfUrlRef = useRef<string | null>(null);
  const uploadInputRef = useRef<HTMLInputElement>(null);

  const [contract, setContract] = useState<Contract | null>(null);
  const [selectedIndex, setSelectedIndex] = useState(0);
  const [loadingContract, setLoadingContract] = useState(false);
  const [loadingDocument, setLoadingDocument] = useState(false);
  const [downloading, setDownloading] = useState(false);
  const [uploading, setUploading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [successMessage, setSuccessMessage] = useState<string | null>(null);
  const [pdfUrl, setPdfUrl] = useState<string | null>(null);
  const [pdfPage, setPdfPage] = useState<number | null>(null);

  const sortedDocuments = contract ? sortDocuments(contract.documents) : [];

  const revokePdfUrl = useCallback(() => {
    if (pdfUrlRef.current) {
      URL.revokeObjectURL(pdfUrlRef.current);
      pdfUrlRef.current = null;
    }
    setPdfUrl(null);
  }, []);

  const clearDocxPreview = useCallback(() => {
    if (docxContainerRef.current) {
      docxContainerRef.current.innerHTML = '';
    }
  }, []);

  const resetState = useCallback(() => {
    revokePdfUrl();
    clearDocxPreview();
    setContract(null);
    setSelectedIndex(0);
    setError(null);
    setSuccessMessage(null);
    setLoadingContract(false);
    setLoadingDocument(false);
    setDownloading(false);
    setUploading(false);
    setPdfPage(null);
  }, [clearDocxPreview, revokePdfUrl]);

  const refreshContract = useCallback(async () => {
    if (!contractId) {
      return null;
    }
    const authHeader = getAuthHeader();
    if (!authHeader) {
      return null;
    }
    const result = await getContractRequest(authHeader, contractId);
    if (result.ok) {
      setContract(result.data);
      onContractUpdated?.(result.data);
      return result.data;
    }
    setError(result.detail);
    return null;
  }, [contractId, getAuthHeader, onContractUpdated]);

  const handleClose = () => {
    resetState();
    onClose();
  };

  useEffect(() => {
    if (!open || !contractId) {
      return;
    }

    const authHeader = getAuthHeader();
    if (!authHeader) {
      setError('Your session has expired. Please sign in again.');
      return;
    }

    let cancelled = false;
    setLoadingContract(true);
    setError(null);
    setSuccessMessage(null);
    setContract(null);
    setPdfPage(initialPage ?? null);

    void getContractRequest(authHeader, contractId)
      .then((result) => {
        if (cancelled) {
          return;
        }

        if (!result.ok) {
          setError(result.detail);
          return;
        }

        if (result.data.documents.length === 0) {
          setError('This contract has no documents to display.');
          return;
        }

        setContract(result.data);
        setSelectedIndex(defaultDocumentIndex(result.data.documents, preferredDocumentType));
      })
      .catch(() => {
        if (!cancelled) {
          setError('Failed to load contract details.');
        }
      })
      .finally(() => {
        if (!cancelled) {
          setLoadingContract(false);
        }
      });

    return () => {
      cancelled = true;
    };
  }, [open, contractId, getAuthHeader, initialPage, preferredDocumentType]);

  useEffect(() => {
    if (!open || !contract) {
      return;
    }

    const documents = sortDocuments(contract.documents);
    const document = documents[selectedIndex];
    if (!document) {
      return;
    }

    const authHeader = getAuthHeader();
    if (!authHeader) {
      setError('Your session has expired. Please sign in again.');
      return;
    }

    let cancelled = false;
    revokePdfUrl();
    clearDocxPreview();
    setLoadingDocument(true);
    setError(null);

    void downloadDocumentRequest(authHeader, contract.id, document.id)
      .then(async (result) => {
        if (cancelled) {
          return;
        }

        if (!result.ok) {
          setError(result.detail);
          return;
        }

        const { blob } = result.data;

        if (isPdfDocument(document)) {
          const url = URL.createObjectURL(blob);
          pdfUrlRef.current = url;
          setPdfUrl(url);
          return;
        }

        if (isDocxDocument(document)) {
          const container = docxContainerRef.current;
          if (!container) {
            setError('Failed to load the document preview.');
            return;
          }
          await renderAsync(blob, container, undefined, {
            className: 'docx-preview-container',
            inWrapper: true,
            ignoreWidth: false,
            ignoreHeight: false,
            breakPages: true,
          });
          return;
        }

        setError('Unsupported document format.');
      })
      .catch(() => {
        if (!cancelled) {
          setError('Failed to load the document preview.');
        }
      })
      .finally(() => {
        if (!cancelled) {
          setLoadingDocument(false);
        }
      });

    return () => {
      cancelled = true;
    };
  }, [open, contract, selectedIndex, clearDocxPreview, getAuthHeader, revokePdfUrl]);

  useEffect(() => {
    return () => {
      revokePdfUrl();
    };
  }, [revokePdfUrl]);

  const handleTabChange = (_event: React.SyntheticEvent, newIndex: number) => {
    setSelectedIndex(newIndex);
    setSuccessMessage(null);
  };

  const handleDownload = async () => {
    if (!contract) {
      return;
    }
    const document = sortedDocuments[selectedIndex];
    if (!document) {
      return;
    }

    const authHeader = getAuthHeader();
    if (!authHeader) {
      setError('Your session has expired. Please sign in again.');
      return;
    }

    setDownloading(true);
    setError(null);
    const result = await downloadDocumentRequest(authHeader, contract.id, document.id);
    setDownloading(false);

    if (!result.ok) {
      setError(result.detail);
      return;
    }

    downloadBlob(result.data.blob, result.data.fileName);
  };

  const handleUploadClick = () => {
    uploadInputRef.current?.click();
  };

  const handleUploadChange = async (event: React.ChangeEvent<HTMLInputElement>) => {
    const file = event.target.files?.[0];
    event.target.value = '';
    if (!file || !contract) {
      return;
    }

    if (file.size > MAX_UPLOAD_SIZE_BYTES) {
      setError('File exceeds the maximum allowed size of 25 MB.');
      return;
    }

    const lowerName = file.name.toLowerCase();
    if (!lowerName.endsWith('.pdf') && !lowerName.endsWith('.docx')) {
      setError('Only PDF and DOCX files are allowed.');
      return;
    }

    const authHeader = getAuthHeader();
    if (!authHeader) {
      setError('Your session has expired. Please sign in again.');
      return;
    }

    setUploading(true);
    setError(null);
    setSuccessMessage(null);

    const result = await uploadLawyerRevisionRequest(authHeader, contract.id, file);
    setUploading(false);

    if (!result.ok) {
      setError(result.detail);
      return;
    }

    const refreshed = await refreshContract();
    if (refreshed) {
      const nextDocuments = sortDocuments(refreshed.documents);
      const revisionIndex = nextDocuments.findIndex(
        (item) => item.document_type === 'lawyer_revision',
      );
      if (revisionIndex >= 0) {
        setSelectedIndex(revisionIndex);
      }
    }

    setSuccessMessage('Edited version uploaded successfully. It replaced the previous revision.');
  };

  const selectedDocument = sortedDocuments[selectedIndex];
  const showPdf = Boolean(selectedDocument && isPdfDocument(selectedDocument) && pdfUrl);
  const canUpload = contract ? canUploadLawyerRevision(user?.role, contract.status) : false;

  return (
    <Dialog open={open} onClose={handleClose} fullWidth maxWidth="lg">
      <DialogTitle>{contract?.title ?? 'Contract viewer'}</DialogTitle>
      <DialogContent dividers sx={{ minHeight: 480, p: 0 }}>
        {loadingContract && (
          <Box sx={{ display: 'flex', justifyContent: 'center', py: 8 }}>
            <CircularProgress />
          </Box>
        )}

        {!loadingContract && error && !loadingDocument && (
          <Alert severity="error" sx={{ m: 2 }}>
            {error}
          </Alert>
        )}

        {successMessage && (
          <Alert severity="success" sx={{ m: 2 }}>
            {successMessage}
          </Alert>
        )}

        {!loadingContract && contract && (
          <Box
            sx={{
              px: 2,
              py: 1.5,
              bgcolor: 'grey.50',
              borderBottom: 1,
              borderColor: 'divider',
              display: 'flex',
              alignItems: 'center',
              justifyContent: 'space-between',
              gap: 2,
              flexWrap: 'wrap',
            }}
          >
            <Typography variant="body2" color="text.secondary">
              Perspective: {PERSPECTIVE_LABELS[contract.perspective] ?? contract.perspective}
            </Typography>
            <ContractStatusSelect
              contract={contract}
              onUpdated={(updated) => {
                setContract(updated);
                onContractUpdated?.(updated);
              }}
            />
          </Box>
        )}

        {!loadingContract && sortedDocuments.length > 0 && (
          <Tabs
            value={selectedIndex}
            onChange={handleTabChange}
            variant="scrollable"
            scrollButtons="auto"
            sx={{ px: 2, borderBottom: 1, borderColor: 'divider' }}
          >
            {sortedDocuments.map((document) => (
              <Tab
                key={document.id}
                label={
                  <Box sx={{ display: 'inline-flex', alignItems: 'center', gap: 1 }}>
                    <span>{documentTabLabel(document, contract?.status)}</span>
                    <DocumentTypeChips
                      types={[document.document_type]}
                      contractStatus={contract?.status}
                    />
                  </Box>
                }
              />
            ))}
          </Tabs>
        )}

        {!loadingContract && selectedDocument && (
          <Box
            sx={{
              px: 2,
              py: 1,
              bgcolor: 'grey.50',
              borderBottom: 1,
              borderColor: 'divider',
              display: 'flex',
              alignItems: 'center',
              justifyContent: 'space-between',
              gap: 2,
              flexWrap: 'wrap',
            }}
          >
            <Typography variant="body2" color="text.secondary">
              {selectedDocument.file_name} ·{' '}
              {(selectedDocument.file_size_bytes / 1024 / 1024).toFixed(2)} MB
            </Typography>
            <DocumentTypeChips
              types={[selectedDocument.document_type]}
              contractStatus={contract?.status}
            />
          </Box>
        )}

        {selectedDocument && isPdfDocument(selectedDocument) && (
          <Box sx={{ position: 'relative', height: '70vh' }}>
            {loadingDocument && (
              <Box
                sx={{
                  position: 'absolute',
                  inset: 0,
                  display: 'flex',
                  alignItems: 'center',
                  justifyContent: 'center',
                  bgcolor: 'grey.200',
                  zIndex: 1,
                }}
              >
                <CircularProgress size={32} />
              </Box>
            )}
            {showPdf && (
              <Box
                component="iframe"
                src={
                  pdfUrl
                    ? pdfPage != null
                      ? `${pdfUrl}#page=${pdfPage}`
                      : pdfUrl
                    : undefined
                }
                title={selectedDocument.file_name}
                sx={{
                  width: '100%',
                  height: '70vh',
                  border: 0,
                  display: 'block',
                  bgcolor: 'grey.200',
                }}
              />
            )}
          </Box>
        )}

        {selectedDocument && isDocxDocument(selectedDocument) && (
          <Box
            sx={{
              position: 'relative',
              height: '70vh',
              overflow: 'auto',
              bgcolor: 'grey.100',
              p: 2,
            }}
          >
            {loadingDocument && (
              <Box
                sx={{
                  position: 'absolute',
                  inset: 0,
                  display: 'flex',
                  alignItems: 'center',
                  justifyContent: 'center',
                  bgcolor: 'grey.100',
                  zIndex: 1,
                }}
              >
                <CircularProgress size={32} />
              </Box>
            )}
            <Box
              ref={docxContainerRef}
              sx={{
                bgcolor: 'background.paper',
                boxShadow: 1,
                mx: 'auto',
                maxWidth: 900,
                minHeight: '100%',
              }}
            />
          </Box>
        )}
      </DialogContent>
      <DialogActions sx={{ px: 3, py: 1.5, gap: 1, flexWrap: 'wrap' }}>
        <input
          ref={uploadInputRef}
          type="file"
          accept=".pdf,.docx,application/pdf,application/vnd.openxmlformats-officedocument.wordprocessingml.document"
          hidden
          onChange={(event) => void handleUploadChange(event)}
        />
        {canUpload && (
          <Button
            variant="contained"
            onClick={handleUploadClick}
            disabled={uploading || loadingContract}
          >
            {uploading ? 'Uploading…' : 'Upload edited version'}
          </Button>
        )}
        {selectedDocument && (
          <Button variant="outlined" onClick={() => void handleDownload()} disabled={downloading}>
            {downloading ? 'Downloading…' : 'Download'}
          </Button>
        )}
        <Button onClick={handleClose}>Close</Button>
      </DialogActions>
    </Dialog>
  );
}
