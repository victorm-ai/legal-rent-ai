import { useCallback, useEffect, useRef, useState } from 'react';
import Alert from '@mui/material/Alert';
import Box from '@mui/material/Box';
import Button from '@mui/material/Button';
import Chip from '@mui/material/Chip';
import CircularProgress from '@mui/material/CircularProgress';
import Dialog from '@mui/material/Dialog';
import DialogActions from '@mui/material/DialogActions';
import DialogContent from '@mui/material/DialogContent';
import DialogContentText from '@mui/material/DialogContentText';
import DialogTitle from '@mui/material/DialogTitle';
import Paper from '@mui/material/Paper';
import Tab from '@mui/material/Tab';
import Table from '@mui/material/Table';
import TableBody from '@mui/material/TableBody';
import TableCell from '@mui/material/TableCell';
import TableContainer from '@mui/material/TableContainer';
import TableHead from '@mui/material/TableHead';
import TableRow from '@mui/material/TableRow';
import Tabs from '@mui/material/Tabs';
import TextField from '@mui/material/TextField';
import Typography from '@mui/material/Typography';
import {
  CLAUSE_CATEGORY_LABELS,
  EDITED_ANALYSIS_DOCUMENT_SCOPE,
  EXTRACTED_FIELD_LABELS,
  STATUS_LABELS,
} from '../../config';
import { useAuth } from '../../context/useAuth';
import {
  createRevisionComparisonRequest,
  downloadDocumentRequest,
  getContractRequest,
  getLatestRevisionComparisonRequest,
  listAnalysesRequest,
  type ComparisonResult,
  updateContractRequest,
} from '../../services/api';
import {
  clientCanApproveEditedContract,
  isContractLocked,
} from '../../utils/contractLifecycle';
import type { Contract } from '../../types/contracts';
import {
  ensureAnalysisChatSession,
  restoreAnalysisChatSession,
  submitContractChatMessage,
} from '../../services/contractChat';
import type { ChatMessage, ChatSession } from '../../types/delivery';
import ChatMessageBubble from './ChatMessageBubble';

interface RevisionComparisonDialogProps {
  open: boolean;
  contractId: string | null;
  contractTitle: string | null;
  contractStatus: string | null;
  onClose: () => void;
  onCompared?: () => void;
  onContractStatusUpdated?: (contract: Contract) => void;
}

function formatCellValue(value: string | null | undefined): string {
  if (value == null || value.trim() === '') {
    return '—';
  }
  return value;
}

function itemLabel(row: ComparisonResult['rows'][number]): string {
  if (row.item_type === 'clause') {
    return `Clause: ${CLAUSE_CATEGORY_LABELS[row.item_key] ?? row.item_key}`;
  }
  return EXTRACTED_FIELD_LABELS[row.item_key] ?? row.item_key;
}

function differenceChipColor(changeType: string): 'default' | 'success' | 'warning' | 'error' {
  if (changeType === 'unchanged') {
    return 'success';
  }
  if (changeType === 'modified') {
    return 'warning';
  }
  if (changeType === 'added' || changeType === 'removed') {
    return 'error';
  }
  return 'default';
}

function formatReference(ref: Record<string, unknown>): string {
  const type = String(ref.type ?? 'reference');
  const title = ref.title ? String(ref.title) : null;
  const section = ref.section ? String(ref.section) : null;
  const page = ref.page != null ? `p.${ref.page}` : null;
  const parts = [type, title, section, page].filter(Boolean);
  return parts.join(' · ');
}

function downloadBlob(blob: Blob, fileName: string) {
  const url = URL.createObjectURL(blob);
  const anchor = document.createElement('a');
  anchor.href = url;
  anchor.download = fileName;
  anchor.click();
  URL.revokeObjectURL(url);
}

export default function RevisionComparisonDialog({
  open,
  contractId,
  contractTitle,
  contractStatus,
  onClose,
  onCompared,
  onContractStatusUpdated,
}: RevisionComparisonDialogProps) {
  const { user, getAuthHeader } = useAuth();
  const [tab, setTab] = useState(0);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [comparison, setComparison] = useState<ComparisonResult | null>(null);
  const [editedAnalysisId, setEditedAnalysisId] = useState<string | null>(null);
  const chatContextContractRef = useRef<string | null>(null);
  const [chatSession, setChatSession] = useState<ChatSession | null>(null);
  const [chatMessages, setChatMessages] = useState<ChatMessage[]>([]);
  const [chatInput, setChatInput] = useState('');
  const [chatLoading, setChatLoading] = useState(false);
  const [suggestions, setSuggestions] = useState<string[]>([]);
  const [approving, setApproving] = useState(false);
  const [approveConfirmOpen, setApproveConfirmOpen] = useState(false);
  const [downloadingEdited, setDownloadingEdited] = useState(false);
  const [editedDocumentId, setEditedDocumentId] = useState<string | null>(null);
  const [liveStatus, setLiveStatus] = useState<string | null>(contractStatus);

  useEffect(() => {
    setLiveStatus(contractStatus);
  }, [contractId, contractStatus]);
  const onComparedRef = useRef(onCompared);
  onComparedRef.current = onCompared;

  const resolveEditedAnalysisId = useCallback(
    async (authHeader: string, targetContractId: string) => {
      const analyses = await listAnalysesRequest(authHeader, targetContractId);
      if (!analyses.ok) {
        return null;
      }
      const edited = analyses.data.find(
        (item) => (item.document_scope ?? 'original') === EDITED_ANALYSIS_DOCUMENT_SCOPE,
      );
      return edited?.id ?? null;
    },
    [],
  );

  const resolveEditedDocumentId = useCallback(async (authHeader: string, targetContractId: string) => {
    const contract = await getContractRequest(authHeader, targetContractId);
    if (!contract.ok) {
      return null;
    }
    const revision = contract.data.documents.find(
      (document) => document.document_type === EDITED_ANALYSIS_DOCUMENT_SCOPE,
    );
    return revision?.id ?? null;
  }, []);

  const loadComparison = useCallback(async () => {
    if (!contractId) {
      return;
    }
    const authHeader = getAuthHeader();
    if (!authHeader) {
      setError('Your session has expired. Please sign in again.');
      return;
    }

    setLoading(true);
    setError(null);

    const latest = await getLatestRevisionComparisonRequest(authHeader, contractId);
    if (latest.ok) {
      setComparison(latest.data);
      const [analysisId, documentId] = await Promise.all([
        resolveEditedAnalysisId(authHeader, contractId),
        resolveEditedDocumentId(authHeader, contractId),
      ]);
      setEditedAnalysisId(analysisId);
      setEditedDocumentId(documentId);
      setLoading(false);
      return;
    }

    if (latest.status !== 404) {
      setLoading(false);
      setError(latest.detail);
      return;
    }

    const created = await createRevisionComparisonRequest(authHeader, contractId);
    setLoading(false);

    if (!created.ok) {
      setError(created.detail);
      return;
    }

    setComparison(created.data);
    const [analysisId, documentId] = await Promise.all([
      resolveEditedAnalysisId(authHeader, contractId),
      resolveEditedDocumentId(authHeader, contractId),
    ]);
    setEditedAnalysisId(analysisId);
    setEditedDocumentId(documentId);
    onComparedRef.current?.();
  }, [contractId, getAuthHeader, resolveEditedAnalysisId, resolveEditedDocumentId]);

  const ensureChatSession = useCallback(async (): Promise<ChatSession | null> => {
    if (!contractId || !editedAnalysisId) {
      return null;
    }
    if (chatSession) {
      return chatSession;
    }
    const authHeader = getAuthHeader();
    if (!authHeader) {
      return null;
    }

    setChatLoading(true);
    const ensured = await ensureAnalysisChatSession(authHeader, contractId, editedAnalysisId);
    if (!ensured.ok) {
      setError(ensured.detail);
      setChatLoading(false);
      return null;
    }
    setChatSession(ensured.session);
    setChatMessages(ensured.messages);
    setSuggestions(ensured.suggestions);
    setChatLoading(false);
    return ensured.session;
  }, [chatSession, contractId, editedAnalysisId, getAuthHeader]);

  useEffect(() => {
    if (!open || !contractId) {
      return;
    }
    if (chatContextContractRef.current !== contractId) {
      setChatSession(null);
      setChatMessages([]);
      setChatInput('');
      setSuggestions([]);
      chatContextContractRef.current = contractId;
    }
    setTab(0);
    setComparison(null);
    setEditedAnalysisId(null);
    setEditedDocumentId(null);
    void loadComparison();
  }, [open, contractId, loadComparison]);

  useEffect(() => {
    if (!open || !contractId || !editedAnalysisId) {
      return;
    }

    let cancelled = false;
    const authHeader = getAuthHeader();
    if (!authHeader) {
      return;
    }

    setChatLoading(true);
    void restoreAnalysisChatSession(authHeader, contractId, editedAnalysisId).then((restored) => {
      if (cancelled) {
        return;
      }
      setChatSession(restored.session);
      setChatMessages(restored.messages);
      setSuggestions(restored.suggestions);
      setChatLoading(false);
    });

    return () => {
      cancelled = true;
    };
  }, [open, contractId, editedAnalysisId, getAuthHeader]);

  useEffect(() => {
    if (tab === 1 && editedAnalysisId && !chatSession) {
      void ensureChatSession();
    }
  }, [tab, editedAnalysisId, chatSession, ensureChatSession]);

  const handleSendChat = async () => {
    const session = chatSession ?? (await ensureChatSession());
    if (!session || !chatInput.trim()) {
      return;
    }
    const authHeader = getAuthHeader();
    if (!authHeader) {
      return;
    }

    const userText = chatInput.trim();
    setChatInput('');
    setChatLoading(true);

    const result = await submitContractChatMessage(
      authHeader,
      session.id,
      userText,
      setChatMessages,
    );
    setChatLoading(false);
    if (!result.ok) {
      setError(result.detail);
    }
  };

  const handleClose = () => {
    if (loading) {
      return;
    }
    setComparison(null);
    setEditedAnalysisId(null);
    setEditedDocumentId(null);
    setTab(0);
    setError(null);
    setApproveConfirmOpen(false);
    onClose();
  };

  const changedCount = comparison?.changes.length ?? 0;
  const canApproveEditedContract =
    clientCanApproveEditedContract(user?.role, liveStatus ?? '') &&
    !isContractLocked(liveStatus ?? '') &&
    Boolean(comparison);

  const handleApproveContract = async () => {
    if (!contractId) {
      return;
    }
    const authHeader = getAuthHeader();
    if (!authHeader) {
      setError('Your session has expired. Please sign in again.');
      return;
    }

    setApproving(true);
    setError(null);
    const result = await updateContractRequest(authHeader, contractId, {
      status: 'approved',
    });
    setApproving(false);

    if (!result.ok) {
      setError(result.detail);
      return;
    }

    setLiveStatus(result.data.status);
    onContractStatusUpdated?.(result.data);
  };

  const canDownloadEditedContract = Boolean(comparison && editedDocumentId);

  const handleDownloadEditedContract = async () => {
    if (!contractId || !editedDocumentId) {
      return;
    }
    const authHeader = getAuthHeader();
    if (!authHeader) {
      setError('Your session has expired. Please sign in again.');
      return;
    }

    setDownloadingEdited(true);
    setError(null);
    const result = await downloadDocumentRequest(authHeader, contractId, editedDocumentId);
    setDownloadingEdited(false);

    if (!result.ok) {
      setError(result.detail);
      return;
    }

    downloadBlob(result.data.blob, result.data.fileName);
  };

  return (
    <Dialog open={open} onClose={handleClose} fullWidth maxWidth="lg">
      <DialogTitle>
        Comparison — {contractTitle ?? 'Contract'}
        <Chip label="Original vs edited" size="small" sx={{ ml: 1 }} />
      </DialogTitle>
      <DialogContent dividers>
        {loading && (
          <Box sx={{ display: 'flex', justifyContent: 'center', py: 6 }}>
            <CircularProgress />
          </Box>
        )}

        {!loading && error && (
          <Alert severity="error" sx={{ mb: 2 }}>
            {error}
          </Alert>
        )}

        {!loading && comparison && (
          <>
            <Tabs value={tab} onChange={(_, value) => setTab(value)} sx={{ mb: 2 }}>
              <Tab label="Comparison" />
              <Tab label="Chat" />
            </Tabs>

            {tab === 0 && (
              <>
                <Typography variant="body2" color="text.secondary" sx={{ mb: 2 }}>
                  {comparison.summary ?? 'Comparison complete.'} Changes detected: {changedCount}.
                </Typography>
                <TableContainer component={Paper} variant="outlined">
                  <Table size="small" stickyHeader>
                    <TableHead>
                      <TableRow>
                        <TableCell sx={{ fontWeight: 700, minWidth: 180 }}>Compared field</TableCell>
                        <TableCell sx={{ fontWeight: 700, minWidth: 200 }}>Original contract</TableCell>
                        <TableCell sx={{ fontWeight: 700, minWidth: 200 }}>New contract</TableCell>
                        <TableCell sx={{ fontWeight: 700, minWidth: 160 }}>Difference</TableCell>
                      </TableRow>
                    </TableHead>
                    <TableBody>
                      {comparison.rows.map((row) => (
                        <TableRow
                          key={`${row.item_type}-${row.item_key}`}
                          sx={{
                            bgcolor: row.change_type === 'unchanged' ? 'inherit' : 'action.hover',
                          }}
                        >
                          <TableCell>{itemLabel(row)}</TableCell>
                          <TableCell sx={{ whiteSpace: 'pre-wrap' }}>
                            {formatCellValue(row.original_value)}
                          </TableCell>
                          <TableCell sx={{ whiteSpace: 'pre-wrap' }}>
                            {formatCellValue(row.new_value)}
                          </TableCell>
                          <TableCell>
                            <Chip
                              label={row.difference}
                              size="small"
                              color={differenceChipColor(row.change_type)}
                              variant={row.change_type === 'unchanged' ? 'outlined' : 'filled'}
                            />
                          </TableCell>
                        </TableRow>
                      ))}
                      {comparison.rows.length === 0 && (
                        <TableRow>
                          <TableCell colSpan={4}>
                            <Typography
                              variant="body2"
                              color="text.secondary"
                              align="center"
                              sx={{ py: 3 }}
                            >
                              No comparable data yet.
                            </Typography>
                          </TableCell>
                        </TableRow>
                      )}
                    </TableBody>
                  </Table>
                </TableContainer>
              </>
            )}

            {tab === 1 && (
              <Box sx={{ display: 'flex', flexDirection: 'column', gap: 2, minHeight: 320 }}>
                <Typography variant="body2" color="text.secondary">
                  The assistant uses the comparison table (original vs edited) and the edited version
                  text to answer questions.
                </Typography>
                {!editedAnalysisId && (
                  <Alert severity="warning">
                    There is no analysis of the edited version yet, so chat is unavailable.
                  </Alert>
                )}
                {editedAnalysisId && chatLoading && chatMessages.length === 0 && (
                  <Box sx={{ display: 'flex', justifyContent: 'center', py: 4 }}>
                    <CircularProgress size={28} />
                  </Box>
                )}
                {editedAnalysisId && suggestions.length > 0 && (
                  <Box sx={{ display: 'flex', gap: 1, flexWrap: 'wrap' }}>
                    {suggestions.map((item) => (
                      <Chip
                        key={item}
                        label={item.length > 60 ? `${item.slice(0, 60)}…` : item}
                        size="small"
                        onClick={() => setChatInput(item)}
                        variant="outlined"
                      />
                    ))}
                  </Box>
                )}
                <Box sx={{ flex: 1, overflowY: 'auto', maxHeight: 360 }}>
                  {chatMessages
                    .filter((message) => message.role !== 'system')
                    .map((message) => (
                      <ChatMessageBubble
                        key={message.id}
                        role={message.role}
                        authorLabel={message.role === 'user' ? 'You' : 'Assistant'}
                        content={message.content}
                        references={message.references}
                        formatReference={formatReference}
                      />
                    ))}
                </Box>
                <Box sx={{ display: 'flex', gap: 1 }}>
                  <TextField
                    fullWidth
                    size="small"
                    placeholder="Ask about the edited contract…"
                    value={chatInput}
                    onChange={(event) => setChatInput(event.target.value)}
                    disabled={!editedAnalysisId}
                    onKeyDown={(event) => {
                      if (event.key === 'Enter' && !event.shiftKey) {
                        event.preventDefault();
                        void handleSendChat();
                      }
                    }}
                  />
                  <Button
                    variant="contained"
                    onClick={() => void handleSendChat()}
                    disabled={chatLoading || !editedAnalysisId}
                  >
                    Send
                  </Button>
                </Box>
              </Box>
            )}
          </>
        )}
      </DialogContent>
      <DialogActions sx={{ px: 3, py: 1.5, justifyContent: 'space-between' }}>
        <Box>
          {liveStatus && (
            <Chip
              size="small"
              label={STATUS_LABELS[liveStatus] ?? liveStatus}
              color={liveStatus === 'approved' ? 'success' : 'info'}
            />
          )}
        </Box>
        <Box sx={{ display: 'flex', gap: 1 }}>
          {canDownloadEditedContract && (
            <Button
              variant="outlined"
              onClick={() => void handleDownloadEditedContract()}
              disabled={loading || approving || downloadingEdited}
            >
              {downloadingEdited ? 'Downloading…' : 'Download new contract'}
            </Button>
          )}
          {canApproveEditedContract && (
            <Button
              variant="contained"
              color="success"
              onClick={() => setApproveConfirmOpen(true)}
              disabled={loading || approving || downloadingEdited}
            >
              {approving ? 'Approving…' : 'Mark as Approved'}
            </Button>
          )}
          <Button onClick={handleClose} disabled={loading || approving || downloadingEdited}>
            Close
          </Button>
        </Box>
      </DialogActions>

      <Dialog
        open={approveConfirmOpen}
        onClose={() => {
          if (!approving) {
            setApproveConfirmOpen(false);
          }
        }}
      >
        <DialogTitle>Confirm approval</DialogTitle>
        <DialogContent>
          <DialogContentText>
            Do you accept the edited version of the contract? The case file will move to approved
            status. This confirms your agreement with the lawyer’s changes.
          </DialogContentText>
        </DialogContent>
        <DialogActions>
          <Button onClick={() => setApproveConfirmOpen(false)} disabled={approving}>
            Cancel
          </Button>
          <Button
            variant="contained"
            color="success"
            autoFocus
            onClick={() => {
              setApproveConfirmOpen(false);
              void handleApproveContract();
            }}
            disabled={approving}
          >
            Yes, approve
          </Button>
        </DialogActions>
      </Dialog>
    </Dialog>
  );
}
