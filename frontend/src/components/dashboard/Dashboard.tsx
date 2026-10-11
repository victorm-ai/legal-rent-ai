import { useCallback, useEffect, useMemo, useState, type ReactNode } from 'react';
import Alert from '@mui/material/Alert';
import Backdrop from '@mui/material/Backdrop';
import Badge from '@mui/material/Badge';
import Box from '@mui/material/Box';
import Button from '@mui/material/Button';
import Card from '@mui/material/Card';
import CardContent from '@mui/material/CardContent';
import CardHeader from '@mui/material/CardHeader';
import Chip from '@mui/material/Chip';
import CircularProgress from '@mui/material/CircularProgress';
import IconButton from '@mui/material/IconButton';
import Grid from '@mui/material/Grid2';
import Paper from '@mui/material/Paper';
import Tooltip from '@mui/material/Tooltip';
import Typography from '@mui/material/Typography';
import UploadContractDialog from '../contracts/UploadContractDialog';
import DocumentViewerDialog from '../contracts/DocumentViewerDialog';
import DocumentTypeChips from '../contracts/DocumentTypeChips';
import DeleteContractDialog from '../contracts/DeleteContractDialog';
import AnalysisResultsDialog from '../contracts/AnalysisResultsDialog';
import RevisionComparisonDialog from '../contracts/RevisionComparisonDialog';
import LawyerCommunicationDialog from '../contracts/LawyerCommunicationDialog';
import {
  AnalysisDocumentIcon,
  NotificationBellIcon,
  PersonIcon,
} from '../icons/Icons';
import { isContractLocked } from '../../utils/contractLifecycle';
import {
  ANALYSIS_DOCUMENT_SCOPE_LABELS,
  ANALYSIS_STATUS_LABELS,
  DEFAULT_ANALYSIS_PERSPECTIVE,
  DOCUMENT_TYPE_LABELS,
  EDITED_ANALYSIS_DOCUMENT_SCOPE,
  PARTY_TYPE_LABELS,
  PERSPECTIVE_LABELS,
  ROLE_LABELS,
  STATUS_LABELS,
} from '../../config';
import { useAuth } from '../../context/useAuth';
import { listAnalysesRequest, listContractsRequest, startAnalysisRequest } from '../../services/api';
import type { AnalysisDocumentScope, AnalysisSummary } from '../../types/analysis';
import type { Contract, ContractDocumentType, ContractPerspective, ContractSummary } from '../../types/contracts';

interface ActionCardProps {
  icon: ReactNode;
  title: string;
  description: string;
  buttonLabel: string;
  primary?: boolean;
  onClick?: () => void;
}

function ActionCard({
  icon,
  title,
  description,
  buttonLabel,
  primary = false,
  onClick,
}: ActionCardProps) {
  return (
    <Paper
      elevation={0}
      sx={{
        p: 3,
        textAlign: 'center',
        bgcolor: 'grey.50',
        border: 1,
        borderColor: 'transparent',
        transition: 'all 0.3s ease',
        '&:hover': {
          transform: 'translateY(-4px)',
          boxShadow: 4,
          bgcolor: 'background.paper',
        },
      }}
    >
      <Box sx={{ color: 'primary.main', mb: 2 }}>{icon}</Box>
      <Typography variant="h6" gutterBottom>
        {title}
      </Typography>
      <Typography variant="body2" color="text.secondary" sx={{ mb: 2.5 }}>
        {description}
      </Typography>
      <Button
        variant={primary ? 'contained' : 'outlined'}
        color={primary ? 'primary' : 'inherit'}
        onClick={onClick}
      >
        {buttonLabel}
      </Button>
    </Paper>
  );
}

function formatDate(isoDate: string): string {
  return new Date(isoDate).toLocaleDateString('en-US');
}

function formatDateTime(isoDate: string): string {
  return new Date(isoDate).toLocaleString('en-US');
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

function riskChipColor(risk: string | null | undefined): 'success' | 'warning' | 'error' | 'default' {
  if (risk === 'low') return 'success';
  if (risk === 'medium') return 'warning';
  if (risk === 'high') return 'error';
  return 'default';
}

const VIEWABLE_ANALYSIS_STATUSES = [
  'ai_generated',
  'pending_review',
  'reviewed',
  'approved',
  'processing',
] as const;

function normalizeAnalysisScope(scope?: AnalysisDocumentScope): AnalysisDocumentScope {
  return scope ?? 'original';
}

function getAnalysisForPerspective(
  analyses: AnalysisSummary[],
  perspective: ContractPerspective,
  documentScope: AnalysisDocumentScope = 'original',
): AnalysisSummary | undefined {
  return analyses.find(
    (item) =>
      item.perspective === perspective &&
      normalizeAnalysisScope(item.document_scope) === documentScope &&
      VIEWABLE_ANALYSIS_STATUSES.includes(item.status as typeof VIEWABLE_ANALYSIS_STATUSES[number]),
  );
}

function contractHasLawyerRevision(contract: ContractSummary): boolean {
  return contract.document_types.includes('lawyer_revision');
}

function isReviewChatAvailable(contract: ContractSummary): boolean {
  if (contract.is_deleted || contract.status === 'draft' || isContractLocked(contract.status)) {
    return false;
  }
  return true;
}

function contractToSummary(contract: Contract): ContractSummary {
  return {
    id: contract.id,
    user_id: contract.user_id,
    perspective: contract.perspective,
    jurisdiction: contract.jurisdiction,
    status: contract.status,
    title: contract.title,
    document_count: contract.documents.length,
    document_types: contract.documents.map((document) => document.document_type),
    parties: contract.parties ?? [],
    is_deleted: false,
    deleted_at: null,
    purge_eligible_at: null,
    unread_review_messages: 0,
    created_at: contract.created_at,
    updated_at: contract.updated_at,
  };
}

interface AnalysisDialogState {
  contract: ContractSummary;
  analysisId: string;
  documentScope: AnalysisDocumentScope;
}

interface LawyerCommDialogState {
  contract: ContractSummary;
  analyses: AnalysisSummary[];
}

interface RevisionComparisonDialogState {
  contract: ContractSummary;
}

export default function Dashboard() {
  const { user, getAuthHeader } = useAuth();
  const [uploadOpen, setUploadOpen] = useState(false);
  const [viewerContractId, setViewerContractId] = useState<string | null>(null);
  const [viewerInitialPage, setViewerInitialPage] = useState<number | null>(null);
  const [viewerPreferredDocumentType, setViewerPreferredDocumentType] =
    useState<ContractDocumentType | null>(null);
  const [analysisDialog, setAnalysisDialog] = useState<AnalysisDialogState | null>(null);
  const [deleteTarget, setDeleteTarget] = useState<ContractSummary | null>(null);
  const [contracts, setContracts] = useState<ContractSummary[]>([]);
  const [analysesByContract, setAnalysesByContract] = useState<Record<string, AnalysisSummary[]>>({});
  const [loadError, setLoadError] = useState<string | null>(null);
  const [successMessage, setSuccessMessage] = useState<string | null>(null);
  const [startingAnalysis, setStartingAnalysis] = useState(false);
  const [lawyerCommDialog, setLawyerCommDialog] = useState<LawyerCommDialogState | null>(null);
  const [revisionComparisonDialog, setRevisionComparisonDialog] =
    useState<RevisionComparisonDialogState | null>(null);

  const isLawyer = user?.role === 'lawyer';
  const isPureLawyer = user?.role === 'lawyer';

  const pauseNotificationPolling = useMemo(
    () =>
      uploadOpen ||
      viewerContractId !== null ||
      analysisDialog !== null ||
      deleteTarget !== null ||
      lawyerCommDialog !== null ||
      revisionComparisonDialog !== null,
    [
      uploadOpen,
      viewerContractId,
      analysisDialog,
      deleteTarget,
      lawyerCommDialog,
      revisionComparisonDialog,
    ],
  );

  const loadContractAnalyses = useCallback(
    async (contractIds: string[]) => {
      const authHeader = getAuthHeader();
      if (!authHeader || contractIds.length === 0) {
        return;
      }

      const entries = await Promise.all(
        contractIds.map(async (contractId) => {
          const result = await listAnalysesRequest(authHeader, contractId);
          return [contractId, result.ok ? result.data : []] as const;
        }),
      );

      setAnalysesByContract(Object.fromEntries(entries));
    },
    [getAuthHeader],
  );

  const handleRevisionCompared = useCallback(() => {
    const contractId = revisionComparisonDialog?.contract.id;
    if (contractId) {
      void loadContractAnalyses([contractId]);
    }
  }, [revisionComparisonDialog?.contract.id, loadContractAnalyses]);

  const refreshContractSummaries = useCallback(async () => {
    const authHeader = getAuthHeader();
    if (!authHeader) {
      return;
    }

    const result = await listContractsRequest(authHeader);
    if (result.ok) {
      setContracts(result.data);
      setLoadError(null);
    } else {
      setLoadError(result.detail);
    }
  }, [getAuthHeader]);

  const loadContracts = useCallback(async () => {
    const authHeader = getAuthHeader();
    if (!authHeader) {
      return;
    }

    const result = await listContractsRequest(authHeader);
    if (result.ok) {
      setContracts(result.data);
      setLoadError(null);
      await loadContractAnalyses(result.data.map((contract) => contract.id));
    } else {
      setLoadError(result.detail);
    }
  }, [getAuthHeader, loadContractAnalyses]);

  useEffect(() => {
    void loadContracts();
  }, [loadContracts]);

  useEffect(() => {
    if (pauseNotificationPolling) {
      return;
    }
    const timer = setInterval(() => {
      void refreshContractSummaries();
    }, 5_000);
    return () => clearInterval(timer);
  }, [pauseNotificationPolling, refreshContractSummaries]);

  useEffect(() => {
    if (!successMessage) {
      return;
    }
    const timer = setTimeout(() => setSuccessMessage(null), 5000);
    return () => clearTimeout(timer);
  }, [successMessage]);

  const handleUploadSuccess = async (contract: Contract) => {
    const summary = contractToSummary(contract);
    const detectedType = contract.documents[0]?.document_type;
    const typeLabel = detectedType
      ? DOCUMENT_TYPE_LABELS[detectedType] ?? detectedType
      : 'Document';
    const contractLabel = contract.title ?? contract.documents[0]?.file_name ?? 'Contract';

    const authHeader = getAuthHeader();
    if (!authHeader) {
      setLoadError('Your session has expired. Please sign in again.');
      return;
    }

    setStartingAnalysis(true);
    const result = await startAnalysisRequest(authHeader, contract.id, DEFAULT_ANALYSIS_PERSPECTIVE);
    setStartingAnalysis(false);

    if (result.ok) {
      setSuccessMessage(
        `"${contractLabel}" uploaded and analyzed from ${PERSPECTIVE_LABELS[DEFAULT_ANALYSIS_PERSPECTIVE]} perspective. Detected type: ${typeLabel}.`,
      );
      await loadContracts();
      setAnalysisDialog({
        contract: summary,
        analysisId: result.data.id,
        documentScope: 'original',
      });
      return;
    }

    setSuccessMessage(
      `"${contractLabel}" uploaded successfully. Detected type: ${typeLabel}.`,
    );
    await loadContracts();
    setLoadError(result.detail);
  };

  const handleStartAnalysis = async (contract: ContractSummary) => {
    const authHeader = getAuthHeader();
    if (!authHeader) {
      setLoadError('Your session has expired. Please sign in again.');
      return;
    }

    setStartingAnalysis(true);
    const result = await startAnalysisRequest(authHeader, contract.id, DEFAULT_ANALYSIS_PERSPECTIVE);
    setStartingAnalysis(false);

    if (!result.ok) {
      setLoadError(result.detail);
      return;
    }

    setAnalysisDialog({
      contract,
      analysisId: result.data.id,
      documentScope: 'original',
    });
    await loadContractAnalyses([contract.id]);
  };

  const refreshAnalyses = () => {
    void loadContractAnalyses(contracts.map((contract) => contract.id));
  };

  const canDeleteContracts = user?.role === 'client';

  const handleDeleteSuccess = (contractId: string) => {
    setSuccessMessage('Contract removed from your list. It was archived, not permanently deleted.');
    setContracts((current) => current.filter((contract) => contract.id !== contractId));
    if (viewerContractId === contractId) {
      setViewerContractId(null);
    }
  };

  return (
    <>
      <Backdrop open={startingAnalysis} sx={{ color: '#fff', zIndex: (theme) => theme.zIndex.drawer + 1 }}>
        <Box sx={{ textAlign: 'center' }}>
          <CircularProgress color="inherit" />
          <Typography sx={{ mt: 2 }}>Analyzing contract…</Typography>
        </Box>
      </Backdrop>

      <Card sx={{ animation: 'fadeIn 0.3s ease-out', '@keyframes fadeIn': { from: { opacity: 0 }, to: { opacity: 1 } } }}>
        <CardHeader title="Dashboard" titleTypographyProps={{ variant: 'h5' }} />

        <Box
          sx={{
            background: (theme) =>
              `linear-gradient(135deg, ${theme.palette.primary.main} 0%, ${theme.palette.primary.dark} 100%)`,
            color: 'white',
            px: 4,
            py: 3,
          }}
        >
          <Box sx={{ display: 'flex', alignItems: 'center', gap: 2 }}>
            <PersonIcon sx={{ fontSize: 64 }} />
            <Box>
              <Typography variant="h5" fontWeight={700}>
                Hello, {user?.name ?? 'User'}
              </Typography>
              <Chip
                label={ROLE_LABELS[user?.role ?? ''] ?? user?.role}
                size="small"
                sx={{
                  mt: 0.5,
                  bgcolor: 'rgba(255,255,255,0.2)',
                  color: 'white',
                  textTransform: 'capitalize',
                }}
              />
            </Box>
          </Box>
        </Box>

        <CardContent sx={{ px: 4, pb: 4 }}>
          {successMessage && (
            <Alert severity="success" sx={{ mb: 2 }}>
              {successMessage}
            </Alert>
          )}

          {loadError && (
            <Alert severity="warning" sx={{ mb: 2 }}>
              {loadError}
            </Alert>
          )}

          {!isLawyer && (
            <Grid container spacing={3} sx={{ mb: 4, justifyContent: 'center' }}>
              <Grid size={{ xs: 12, sm: 8, md: 5, lg: 4 }}>
                <ActionCard
                  icon={<AnalysisDocumentIcon sx={{ fontSize: 48 }} />}
                  title="New Analysis"
                  description="Upload a PDF or DOCX contract to start the analysis"
                  buttonLabel="Get started"
                  primary
                  onClick={() => setUploadOpen(true)}
                />
              </Grid>
            </Grid>
          )}

          <Typography variant="h6" sx={{ mb: 2, pl: 1 }}>
            Recent Analyses
          </Typography>

          {contracts.length === 0 ? (
            <Typography
              variant="body2"
              color="text.secondary"
              align="center"
              sx={{ py: 6, fontStyle: 'italic' }}
            >
              {isLawyer
                ? 'No contracts pending review.'
                : 'No recent analyses. Click "Get started" to upload your first contract.'}
            </Typography>
          ) : (
            contracts.map((contract) => {
              const contractAnalyses = analysesByContract[contract.id] ?? [];
              const reviewChatAvailable = isReviewChatAvailable(contract);

              return (
              <Paper
                key={contract.id}
                elevation={1}
                sx={{
                  display: 'flex',
                  justifyContent: 'space-between',
                  alignItems: 'flex-start',
                  p: 2,
                  mb: 1.5,
                  flexWrap: 'wrap',
                  gap: 2,
                  opacity: contract.is_deleted ? 0.65 : 1,
                }}
              >
                <Box sx={{ flex: 1, minWidth: 240 }}>
                  <Box sx={{ display: 'flex', alignItems: 'center', gap: 1, flexWrap: 'wrap' }}>
                    <Typography fontWeight={600}>
                      {contract.title ?? 'Untitled contract'}
                    </Typography>
                    {contract.is_deleted && (
                      <Chip
                        label="Deleted"
                        size="small"
                        color="default"
                        sx={{ height: 22, fontSize: '0.7rem', fontWeight: 600 }}
                      />
                    )}
                  </Box>
                  <Typography variant="caption" color="text.secondary" display="block">
                    Created: {formatDate(contract.created_at)} | Documents: {contract.document_count}{' '}
                    | Status:{' '}
                    <Chip
                      label={STATUS_LABELS[contract.status] ?? contract.status}
                      size="small"
                      color={statusChipColor(contract.status)}
                      sx={{ ml: 0.5, height: 22, fontSize: '0.7rem', fontWeight: 600 }}
                    />
                  </Typography>
                  {contract.document_types.length > 0 && (
                    <Box sx={{ mt: 0.75 }}>
                      <DocumentTypeChips types={contract.document_types} />
                    </Box>
                  )}
                  {!contract.is_deleted && (
                    <Box sx={{ mt: 0.75, display: 'flex', gap: 1, flexWrap: 'wrap' }}>
                      {contract.jurisdiction ? (
                        <Chip
                          label={`Jurisdiction: ${contract.jurisdiction}`}
                          size="small"
                          color="info"
                          variant="outlined"
                          sx={{ height: 22, fontSize: '0.7rem', fontWeight: 600 }}
                        />
                      ) : contractAnalyses.some((item) =>
                          ['ai_generated', 'pending_review', 'reviewed', 'approved'].includes(item.status),
                        ) ? (
                        <Chip
                          label="Jurisdiction missing or inconsistent"
                          size="small"
                          color="warning"
                          variant="outlined"
                          sx={{ height: 22, fontSize: '0.7rem', fontWeight: 600 }}
                        />
                      ) : null}
                    </Box>
                  )}
                  {!contract.is_deleted && contract.parties.length > 0 && (
                    <Box sx={{ mt: 0.75, display: 'flex', gap: 1, flexWrap: 'wrap' }}>
                      {contract.parties.map((party) => (
                        <Chip
                          key={`${party.party_type}-${party.name}`}
                          label={`${PARTY_TYPE_LABELS[party.party_type] ?? party.party_type}: ${party.name}`}
                          size="small"
                          variant="outlined"
                          sx={{ height: 22, fontSize: '0.7rem', fontWeight: 600 }}
                        />
                      ))}
                    </Box>
                  )}
                  {!contract.is_deleted && (() => {
                    const existingOriginal = getAnalysisForPerspective(
                      contractAnalyses,
                      DEFAULT_ANALYSIS_PERSPECTIVE,
                      'original',
                    );
                    const existingEdited = contractHasLawyerRevision(contract)
                      ? getAnalysisForPerspective(
                          contractAnalyses,
                          DEFAULT_ANALYSIS_PERSPECTIVE,
                          EDITED_ANALYSIS_DOCUMENT_SCOPE,
                        )
                      : undefined;
                    const showOriginalChip = Boolean(existingOriginal) || !isPureLawyer;
                    const showEditedChip =
                      !isPureLawyer && contractHasLawyerRevision(contract);

                    if (!showOriginalChip && !showEditedChip) {
                      return null;
                    }

                    return (
                      <Box sx={{ mt: 1.25, display: 'flex', gap: 1, flexWrap: 'wrap' }}>
                        {showOriginalChip &&
                          (existingOriginal ? (
                            <Chip
                              label={`${PERSPECTIVE_LABELS[DEFAULT_ANALYSIS_PERSPECTIVE]} · ${
                                ANALYSIS_STATUS_LABELS[existingOriginal.status] ?? existingOriginal.status
                              }`}
                              color={
                                existingOriginal.status === 'approved'
                                  ? 'success'
                                  : existingOriginal.status === 'pending_review'
                                    ? 'warning'
                                    : riskChipColor(existingOriginal.general_risk)
                              }
                              variant="outlined"
                              clickable
                              onClick={() =>
                                setAnalysisDialog({
                                  contract,
                                  analysisId: existingOriginal.id,
                                  documentScope: 'original',
                                })
                              }
                              sx={{ fontWeight: 600 }}
                            />
                          ) : (
                            <Chip
                              label={`${PERSPECTIVE_LABELS[DEFAULT_ANALYSIS_PERSPECTIVE]} · Pending`}
                              variant="outlined"
                              clickable={!isContractLocked(contract.status)}
                              onClick={() => {
                                if (!isContractLocked(contract.status)) {
                                  void handleStartAnalysis(contract);
                                }
                              }}
                              sx={{ fontWeight: 600 }}
                            />
                          ))}
                        {showEditedChip && (
                          <Chip
                            label={
                              existingEdited
                                ? `${ANALYSIS_DOCUMENT_SCOPE_LABELS.lawyer_revision} · Compared`
                                : `${ANALYSIS_DOCUMENT_SCOPE_LABELS.lawyer_revision} · Pending`
                            }
                            color={existingEdited ? 'info' : 'default'}
                            variant="outlined"
                            clickable
                            onClick={() => setRevisionComparisonDialog({ contract })}
                            sx={{ fontWeight: 600 }}
                          />
                        )}
                      </Box>
                    );
                  })()}
                  {contract.is_deleted && contract.purge_eligible_at && (
                    <Typography variant="caption" color="text.secondary" display="block" sx={{ mt: 0.5 }}>
                      Purge eligible after: {formatDateTime(contract.purge_eligible_at)}
                    </Typography>
                  )}
                </Box>
                <Box sx={{ display: 'flex', gap: 1, flexWrap: 'wrap', alignItems: 'center' }}>
                  {!contract.is_deleted && reviewChatAvailable && (
                    <Tooltip
                      title={
                        (contract.unread_review_messages ?? 0) > 0
                          ? `${contract.unread_review_messages} new message${
                              contract.unread_review_messages === 1 ? '' : 's'
                            }`
                          : 'No new messages'
                      }
                    >
                      <IconButton
                        size="small"
                        color={(contract.unread_review_messages ?? 0) > 0 ? 'primary' : 'default'}
                        aria-label="Review message notifications"
                        onClick={() =>
                          setLawyerCommDialog({ contract, analyses: contractAnalyses })
                        }
                      >
                        <Badge
                          badgeContent={contract.unread_review_messages ?? 0}
                          color="error"
                          invisible={(contract.unread_review_messages ?? 0) === 0}
                        >
                          <NotificationBellIcon fontSize="small" />
                        </Badge>
                      </IconButton>
                    </Tooltip>
                  )}
                  {!contract.is_deleted && (
                    <Button
                      variant="outlined"
                      size="small"
                      disabled={!reviewChatAvailable}
                      onClick={() =>
                        setLawyerCommDialog({ contract, analyses: contractAnalyses })
                      }
                    >
                      {isLawyer ? 'Chat with client' : 'Chat with lawyer'}
                    </Button>
                  )}
                  {!contract.is_deleted && (
                    <Button
                      variant="outlined"
                      size="small"
                      onClick={() => {
                        setViewerPreferredDocumentType(null);
                        setViewerContractId(contract.id);
                      }}
                    >
                      View
                    </Button>
                  )}
                  {canDeleteContracts && !contract.is_deleted && !isContractLocked(contract.status) && (
                    <Button
                      variant="outlined"
                      size="small"
                      color="error"
                      onClick={() => setDeleteTarget(contract)}
                    >
                      Delete
                    </Button>
                  )}
                </Box>
              </Paper>
              );
            })
          )}
        </CardContent>
      </Card>

      <UploadContractDialog
        open={uploadOpen}
        onClose={() => setUploadOpen(false)}
        onSuccess={handleUploadSuccess}
      />

      <DocumentViewerDialog
        open={viewerContractId !== null}
        contractId={viewerContractId}
        initialPage={viewerInitialPage}
        preferredDocumentType={viewerPreferredDocumentType}
        onClose={() => {
          setViewerContractId(null);
          setViewerInitialPage(null);
          setViewerPreferredDocumentType(null);
        }}
        onContractUpdated={(updated) => {
          setContracts((current) =>
            current.map((contract) =>
              contract.id === updated.id ? { ...contract, status: updated.status } : contract,
            ),
          );
          setAnalysisDialog((current) =>
            current && current.contract.id === updated.id
              ? { ...current, contract: { ...current.contract, status: updated.status } }
              : current,
          );
        }}
      />

      <DeleteContractDialog
        open={deleteTarget !== null}
        contract={deleteTarget}
        onClose={() => setDeleteTarget(null)}
        onDeleted={handleDeleteSuccess}
      />

      <AnalysisResultsDialog
        open={analysisDialog !== null}
        contractId={analysisDialog?.contract.id ?? null}
        contractTitle={analysisDialog?.contract.title ?? null}
        analysisId={analysisDialog?.analysisId ?? null}
        onClose={() => setAnalysisDialog(null)}
        onAnalysesChanged={refreshAnalyses}
        onViewDocument={(contractId, page) => {
          setViewerInitialPage(page ?? null);
          setViewerPreferredDocumentType(
            analysisDialog?.documentScope === EDITED_ANALYSIS_DOCUMENT_SCOPE
              ? 'lawyer_revision'
              : 'main_contract',
          );
          setViewerContractId(contractId);
        }}
      />

      <RevisionComparisonDialog
        open={revisionComparisonDialog !== null}
        contractId={revisionComparisonDialog?.contract.id ?? null}
        contractTitle={revisionComparisonDialog?.contract.title ?? null}
        contractStatus={revisionComparisonDialog?.contract.status ?? null}
        onClose={() => setRevisionComparisonDialog(null)}
        onCompared={handleRevisionCompared}
        onContractStatusUpdated={(updated) => {
          setContracts((items) =>
            items.map((item) =>
              item.id === updated.id ? { ...item, status: updated.status } : item,
            ),
          );
          setRevisionComparisonDialog((current) =>
            current
              ? { contract: { ...current.contract, status: updated.status } }
              : null,
          );
        }}
      />

      <LawyerCommunicationDialog
        open={lawyerCommDialog !== null}
        contractId={lawyerCommDialog?.contract.id ?? null}
        contractTitle={lawyerCommDialog?.contract.title ?? null}
        contractStatus={lawyerCommDialog?.contract.status ?? null}
        analyses={lawyerCommDialog?.analyses ?? []}
        onClose={() => setLawyerCommDialog(null)}
        onMarkedRead={() => void loadContracts()}
      />
    </>
  );
}
