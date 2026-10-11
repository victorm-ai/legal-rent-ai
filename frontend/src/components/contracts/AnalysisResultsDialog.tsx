import { useCallback, useEffect, useRef, useState } from 'react';
import Alert from '@mui/material/Alert';
import Box from '@mui/material/Box';
import Button from '@mui/material/Button';
import Chip from '@mui/material/Chip';
import CircularProgress from '@mui/material/CircularProgress';
import Dialog from '@mui/material/Dialog';
import DialogActions from '@mui/material/DialogActions';
import DialogContent from '@mui/material/DialogContent';
import DialogTitle from '@mui/material/DialogTitle';
import Divider from '@mui/material/Divider';
import List from '@mui/material/List';
import ListItem from '@mui/material/ListItem';
import ListItemText from '@mui/material/ListItemText';
import Tab from '@mui/material/Tab';
import Tabs from '@mui/material/Tabs';
import TextField from '@mui/material/TextField';
import Typography from '@mui/material/Typography';
import ButtonGroup from '@mui/material/ButtonGroup';
import {
  ANALYSIS_DOCUMENT_SCOPE_LABELS,
  ANALYSIS_STATUS_LABELS,
  CLAUSE_CATEGORY_LABELS,
  EXTRACTED_FIELD_LABELS,
  FINDING_TYPE_LABELS,
  FINDING_VERDICT_LABELS,
  PERSPECTIVE_LABELS,
  RISK_LABELS,
} from '../../config';
import { useAuth } from '../../context/useAuth';
import {
  downloadReportRequest,
  generateReportRequest,
  getAnalysisRequest,
  getAnalysisStatusRequest,
  reviewFindingRequest,
  startAnalysisRequest,
} from '../../services/api';
import {
  ensureAnalysisChatSession,
  restoreAnalysisChatSession,
  submitContractChatMessage,
} from '../../services/contractChat';
import type { AnalysisDetail, FindingVerdict } from '../../types/analysis';
import type { ChatMessage, ChatSession } from '../../types/delivery';
import ChatMessageBubble from './ChatMessageBubble';

const SHOW_REPORT_DOWNLOADS = false;

interface AnalysisResultsDialogProps {
  open: boolean;
  contractId: string | null;
  contractTitle: string | null;
  analysisId: string | null;
  onClose: () => void;
  onAnalysesChanged?: () => void;
  onViewDocument?: (contractId: string, page?: number | null) => void;
}

const PARTY_FIELD_NAMES = new Set([
  'arrendador',
  'arrendatario',
  'fiador',
  'obligado_solidario',
  'representante_arrendador',
  'representante_arrendatario',
]);

function riskColor(risk: string | null): 'success' | 'warning' | 'error' | 'default' {
  if (risk === 'low') return 'success';
  if (risk === 'medium') return 'warning';
  if (risk === 'high') return 'error';
  return 'default';
}

function isJurisdictionFinding(finding: { title?: string | null; description?: string | null }): boolean {
  const title = (finding.title ?? '').toLowerCase();
  const description = (finding.description ?? '').toLowerCase();
  return (
    title.includes('jurisdiction') ||
    title.includes('jurisdicción') ||
    description.includes('jurisdiction') ||
    description.includes('jurisdicción') ||
    description.includes('foro') ||
    description.includes('competencia')
  );
}

function downloadBlob(blob: Blob, fileName: string) {
  const url = URL.createObjectURL(blob);
  const anchor = document.createElement('a');
  anchor.href = url;
  anchor.download = fileName;
  anchor.click();
  URL.revokeObjectURL(url);
}

function formatReference(ref: Record<string, unknown>): string {
  const type = String(ref.type ?? 'reference');
  const title = ref.title ? String(ref.title) : null;
  const section = ref.section ? String(ref.section) : null;
  const page = ref.page != null ? `p.${ref.page}` : null;
  const parts = [type, title, section, page].filter(Boolean);
  return parts.join(' · ');
}

export default function AnalysisResultsDialog({
  open,
  contractId,
  contractTitle,
  analysisId,
  onClose,
  onAnalysesChanged,
  onViewDocument,
}: AnalysisResultsDialogProps) {
  const { user, getAuthHeader } = useAuth();
  const [tab, setTab] = useState(0);
  const [analysis, setAnalysis] = useState<AnalysisDetail | null>(null);
  const [loading, setLoading] = useState(false);
  const [running, setRunning] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const chatContextRef = useRef<{ contractId: string; analysisId: string } | null>(null);
  const [chatSession, setChatSession] = useState<ChatSession | null>(null);
  const [chatMessages, setChatMessages] = useState<ChatMessage[]>([]);
  const [chatInput, setChatInput] = useState('');
  const [chatLoading, setChatLoading] = useState(false);
  const [suggestions, setSuggestions] = useState<string[]>([]);

  const [reviewingFindingId, setReviewingFindingId] = useState<string | null>(null);

  const isLawyer = user?.role === 'lawyer';
  const canReviewFindings =
    isLawyer &&
    analysis &&
    ['pending_review', 'reviewed', 'approved'].includes(analysis.status);

  const loadAnalysis = useCallback(async () => {
    if (!contractId || !analysisId) return;
    const authHeader = getAuthHeader();
    if (!authHeader) {
      setError('Your session has expired. Please sign in again.');
      return;
    }

    setLoading(true);
    setError(null);
    setAnalysis(null);

    const detail = await getAnalysisRequest(authHeader, analysisId);
    setLoading(false);
    if (!detail.ok) {
      setError(detail.detail);
      return;
    }
    setAnalysis(detail.data);
  }, [analysisId, contractId, getAuthHeader]);

  useEffect(() => {
    if (!open || !contractId || !analysisId) return;
    setTab(0);
    setReviewingFindingId(null);
    void loadAnalysis();
  }, [open, contractId, analysisId, loadAnalysis]);

  useEffect(() => {
    if (!open || !contractId || !analysisId) return;

    const prev = chatContextRef.current;
    if (prev?.contractId !== contractId || prev?.analysisId !== analysisId) {
      setChatSession(null);
      setChatMessages([]);
      setSuggestions([]);
      chatContextRef.current = { contractId, analysisId };
    }

    let cancelled = false;
    const authHeader = getAuthHeader();
    if (!authHeader) return;

    setChatLoading(true);
    void restoreAnalysisChatSession(authHeader, contractId, analysisId).then((restored) => {
      if (cancelled) return;
      setChatSession(restored.session);
      setChatMessages(restored.messages);
      setSuggestions(restored.suggestions);
      setChatLoading(false);
    });

    return () => {
      cancelled = true;
    };
  }, [open, contractId, analysisId, getAuthHeader]);

  useEffect(() => {
    if (!analysis || analysis.status !== 'processing') return;
    const authHeader = getAuthHeader();
    if (!authHeader || !analysisId) return;

    const timer = window.setInterval(async () => {
      const status = await getAnalysisStatusRequest(authHeader, analysisId);
      if (!status.ok) return;
      if (status.data.status !== 'processing') {
        window.clearInterval(timer);
        await loadAnalysis();
        onAnalysesChanged?.();
      }
    }, 2000);

    return () => window.clearInterval(timer);
  }, [analysis?.status, analysisId, getAuthHeader, loadAnalysis, onAnalysesChanged]);

  const handleRetry = async () => {
    if (!contractId || !analysis) return;
    const authHeader = getAuthHeader();
    if (!authHeader) return;
    setRunning(true);
    setError(null);
    const result = await startAnalysisRequest(
      authHeader,
      contractId,
      analysis.perspective,
      analysis.document_scope ?? 'original',
    );
    setRunning(false);
    if (!result.ok) {
      setError(result.detail);
      return;
    }
    setAnalysis(result.data);
    onAnalysesChanged?.();
  };

  const handleDownloadReport = async (format: 'pdf' | 'json') => {
    if (!analysis) return;
    const authHeader = getAuthHeader();
    if (!authHeader) return;
    setRunning(true);
    const generated = await generateReportRequest(authHeader, analysis.id, format);
    if (!generated.ok) {
      setRunning(false);
      setError(generated.detail);
      return;
    }
    const downloaded = await downloadReportRequest(authHeader, generated.data.id);
    setRunning(false);
    if (!downloaded.ok) {
      setError(downloaded.detail);
      return;
    }
    downloadBlob(downloaded.data.blob, downloaded.data.fileName);
  };

  const ensureChatSession = async (): Promise<ChatSession | null> => {
    if (!contractId || !analysis) return null;
    if (chatSession) return chatSession;
    const authHeader = getAuthHeader();
    if (!authHeader) return null;

    setChatLoading(true);
    const ensured = await ensureAnalysisChatSession(authHeader, contractId, analysis.id);
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
  };

  useEffect(() => {
    if (tab === 1 && analysis && !chatSession) {
      void ensureChatSession();
    }
  }, [tab, analysis, chatSession]);

  const handleSendChat = async () => {
    const session = chatSession ?? (await ensureChatSession());
    if (!session || !chatInput.trim()) return;
    const authHeader = getAuthHeader();
    if (!authHeader) return;

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

  const handleReviewFinding = async (findingId: string, verdict: FindingVerdict) => {
    if (!analysis || reviewingFindingId) return;
    const authHeader = getAuthHeader();
    if (!authHeader) return;

    setReviewingFindingId(findingId);
    const result = await reviewFindingRequest(authHeader, analysis.id, findingId, verdict);
    setReviewingFindingId(null);
    if (!result.ok) {
      setError(result.detail);
      return;
    }

    setAnalysis((current) => {
      if (!current) {
        return current;
      }
      return {
        ...current,
        findings: current.findings.map((finding) =>
          finding.id === findingId ? { ...finding, review: result.data } : finding,
        ),
      };
    });
  };

  const extractedEntries = analysis ? Object.entries(analysis.extracted_data) : [];
  const partyEntries = extractedEntries.filter(([fieldName]) => PARTY_FIELD_NAMES.has(fieldName));
  const nonPartyEntries = extractedEntries.filter(([fieldName]) => !PARTY_FIELD_NAMES.has(fieldName));
  const jurisdictionFindings = analysis
    ? analysis.findings.filter((finding) => isJurisdictionFinding(finding))
    : [];

  return (
    <>
      <Dialog open={open} onClose={onClose} fullWidth maxWidth="md">
        <DialogTitle>
          Analysis — {contractTitle ?? 'Contract'}
          {analysis && (
            <>
              <Chip
                label={PERSPECTIVE_LABELS[analysis.perspective] ?? analysis.perspective}
                size="small"
                sx={{ ml: 1 }}
              />
              <Chip
                label={
                  ANALYSIS_DOCUMENT_SCOPE_LABELS[analysis.document_scope ?? 'original'] ??
                  analysis.document_scope ??
                  'Original contract'
                }
                size="small"
                variant="outlined"
                sx={{ ml: 1 }}
              />
            </>
          )}
        </DialogTitle>
      <DialogContent dividers>
        {(loading || running) && !analysis && (
          <Box sx={{ display: 'flex', justifyContent: 'center', py: 6 }}>
            <CircularProgress />
          </Box>
        )}

        {error && (
          <Alert severity="error" sx={{ mb: 2 }}>
            {error}
          </Alert>
        )}

        {analysis && (
          <>
            <Tabs value={tab} onChange={(_, value) => setTab(value)} sx={{ mb: 2 }}>
              <Tab label="Results" />
              <Tab label="Chat" />
            </Tabs>

            {tab === 0 && (
              <Box sx={{ display: 'flex', flexDirection: 'column', gap: 2 }}>
                <Box sx={{ display: 'flex', gap: 1, flexWrap: 'wrap' }}>
                  <Chip
                    label={ANALYSIS_STATUS_LABELS[analysis.status] ?? analysis.status}
                    size="small"
                  />
                  {analysis.general_risk && (
                    <Chip
                      label={`Risk: ${RISK_LABELS[analysis.general_risk] ?? analysis.general_risk}`}
                      size="small"
                      color={riskColor(analysis.general_risk)}
                    />
                  )}
                </Box>

                {jurisdictionFindings.length > 0 && (
                  <Alert severity="warning">
                    {jurisdictionFindings.length === 1
                      ? jurisdictionFindings[0].title
                      : `${jurisdictionFindings.length} jurisdiction issues detected. Review findings below.`}
                  </Alert>
                )}

                {analysis.approval && (
                  <Alert severity="success">
                    Approved on {new Date(analysis.approval.approved_at).toLocaleString('en-US')}
                    {analysis.approval.notes ? ` — ${analysis.approval.notes}` : ''}
                  </Alert>
                )}

                {analysis.summary_executive && (
                  <Box>
                    <Typography variant="subtitle1" fontWeight={600} gutterBottom>
                      Executive summary
                    </Typography>
                    <Typography variant="body2" color="text.secondary">
                      {analysis.summary_executive}
                    </Typography>
                  </Box>
                )}

                {partyEntries.length > 0 && (
                  <>
                    <Divider />
                    <Typography variant="subtitle1" fontWeight={600}>
                      Contract parties
                    </Typography>
                    <List dense disablePadding>
                      {partyEntries.map(([fieldName, field]) => (
                        <ListItem key={fieldName} disableGutters>
                          <ListItemText
                            primary={EXTRACTED_FIELD_LABELS[fieldName] ?? fieldName}
                            secondary={
                              <>
                                {field.requires_review ? '~' : ''}{field.value}
                                {' · Confidence: '}{(field.confidence * 100).toFixed(0)}%
                              </>
                            }
                          />
                        </ListItem>
                      ))}
                    </List>
                  </>
                )}

                {nonPartyEntries.length > 0 && (
                  <>
                    <Divider />
                    <Typography variant="subtitle1" fontWeight={600}>
                      Extracted data
                    </Typography>
                    <List dense disablePadding>
                      {nonPartyEntries.map(([fieldName, field]) => (
                        <ListItem key={fieldName} disableGutters>
                          <ListItemText
                            primary={
                              <Box sx={{ display: 'flex', gap: 1, flexWrap: 'wrap', alignItems: 'center' }}>
                                <span>{EXTRACTED_FIELD_LABELS[fieldName] ?? fieldName}</span>
                                {field.requires_review && (
                                  <Chip label="Needs review" size="small" color="warning" variant="outlined" />
                                )}
                              </Box>
                            }
                            secondary={
                              <>
                                {field.requires_review ? '~' : ''}{field.value}
                                {' · Confidence: '}{(field.confidence * 100).toFixed(0)}%
                                {field.source?.text_snippet && (
                                  <> · Source: {field.source.text_snippet.slice(0, 120)}…</>
                                )}
                              </>
                            }
                          />
                        </ListItem>
                      ))}
                    </List>
                  </>
                )}

                {analysis.findings.length > 0 && (
                  <>
                    <Divider />
                    <Typography variant="subtitle1" fontWeight={600}>
                      Findings ({analysis.findings.length})
                    </Typography>
                    <List dense disablePadding>
                      {analysis.findings.map((finding) => {
                        const linkedClause = finding.clause_id
                          ? analysis.clauses.find((c) => c.id === finding.clause_id)
                          : null;
                        return (
                        <ListItem key={finding.id} disableGutters sx={{ mb: 1, flexDirection: 'column', alignItems: 'stretch' }}>
                          <ListItemText
                            primary={
                              <Box sx={{ display: 'flex', gap: 1, flexWrap: 'wrap', alignItems: 'center' }}>
                                <Chip label={RISK_LABELS[finding.severity]} size="small" color={riskColor(finding.severity)} />
                                <Chip
                                  label={FINDING_TYPE_LABELS[finding.finding_type] ?? finding.finding_type}
                                  size="small"
                                  variant="outlined"
                                />
                                <Typography variant="body2" fontWeight={600}>{finding.title}</Typography>
                                {finding.review && (
                                  <Chip
                                    label={FINDING_VERDICT_LABELS[finding.review.verdict] ?? finding.review.verdict}
                                    size="small"
                                    color={finding.review.verdict === 'correct' ? 'success' : finding.review.verdict === 'incorrect' ? 'error' : 'default'}
                                  />
                                )}
                                {finding.confidence != null && (
                                  <Chip
                                    label={`Confidence ${(finding.confidence * 100).toFixed(0)}%`}
                                    size="small"
                                    variant="outlined"
                                  />
                                )}
                              </Box>
                            }
                            secondary={
                              <Box component="span" sx={{ display: 'block' }}>
                                <Typography variant="body2" component="span" color="text.secondary">
                                  {finding.description}
                                </Typography>
                                {finding.recommendation && (
                                  <Typography variant="body2" component="div" sx={{ mt: 0.5 }}>
                                    <strong>Recommendation:</strong> {finding.recommendation}
                                  </Typography>
                                )}
                                {finding.legal_basis && (
                                  <Typography variant="body2" component="div" sx={{ mt: 0.5 }}>
                                    <strong>Legal basis:</strong> {finding.legal_basis}
                                    {finding.source_law ? ` (${finding.source_law})` : ''}
                                  </Typography>
                                )}
                                {finding.evidence_text && (
                                  <Typography variant="caption" component="div" sx={{ mt: 0.5, display: 'block' }}>
                                    <strong>Evidence:</strong> {finding.evidence_text.slice(0, 300)}
                                    {finding.evidence_page != null ? ` · Page ${finding.evidence_page}` : ''}
                                  </Typography>
                                )}
                                {linkedClause && (
                                  <Typography variant="caption" component="div" sx={{ mt: 0.5, display: 'block' }}>
                                    <strong>Linked clause:</strong> {CLAUSE_CATEGORY_LABELS[linkedClause.category] ?? linkedClause.category}
                                    {linkedClause.section ? ` · ${linkedClause.section}` : ''}
                                  </Typography>
                                )}
                                {finding.suggested_rewording && (
                                  <Typography variant="body2" component="div" sx={{ mt: 0.5, fontStyle: 'italic' }}>
                                    <strong>Suggested wording:</strong> {finding.suggested_rewording}
                                  </Typography>
                                )}
                                {onViewDocument && contractId && (finding.evidence_text || finding.evidence_page != null || linkedClause) && (
                                  <Button
                                    size="small"
                                    variant="text"
                                    sx={{ mt: 0.5, px: 0 }}
                                    onClick={() => onViewDocument(contractId, finding.evidence_page ?? linkedClause?.page ?? null)}
                                  >
                                    View in document
                                  </Button>
                                )}
                              </Box>
                            }
                          />
                          {canReviewFindings && analysis.status !== 'approved' && (
                            <ButtonGroup size="small" sx={{ mt: 0.5 }}>
                              {(['correct', 'incorrect', 'not_relevant'] as FindingVerdict[]).map((verdict) => (
                                <Button
                                  key={verdict}
                                  variant={finding.review?.verdict === verdict ? 'contained' : 'outlined'}
                                  onClick={() => void handleReviewFinding(finding.id, verdict)}
                                  disabled={reviewingFindingId !== null}
                                >
                                  {FINDING_VERDICT_LABELS[verdict]}
                                </Button>
                              ))}
                            </ButtonGroup>
                          )}
                        </ListItem>
                        );
                      })}
                    </List>
                  </>
                )}

                {analysis.clauses.length > 0 && (
                  <>
                    <Divider />
                    <Typography variant="subtitle1" fontWeight={600}>
                      Clauses ({analysis.clauses.length})
                    </Typography>
                    <List dense disablePadding>
                      {analysis.clauses.slice(0, 6).map((clause) => (
                        <ListItem key={clause.id} disableGutters>
                          <ListItemText
                            primary={CLAUSE_CATEGORY_LABELS[clause.category] ?? clause.category}
                            secondary={clause.text.length > 180 ? `${clause.text.slice(0, 180)}…` : clause.text}
                          />
                        </ListItem>
                      ))}
                    </List>
                  </>
                )}
              </Box>
            )}

            {tab === 1 && (
              <Box sx={{ display: 'flex', flexDirection: 'column', gap: 2, minHeight: 320 }}>
                {chatLoading && chatMessages.length === 0 && (
                  <Box sx={{ display: 'flex', justifyContent: 'center', py: 4 }}>
                    <CircularProgress size={28} />
                  </Box>
                )}
                {suggestions.length > 0 && (
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
                  {chatMessages.filter((m) => m.role !== 'system').map((message) => (
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
                    placeholder="Ask about the contract in plain language…"
                    value={chatInput}
                    onChange={(e) => setChatInput(e.target.value)}
                    onKeyDown={(e) => {
                      if (e.key === 'Enter' && !e.shiftKey) {
                        e.preventDefault();
                        void handleSendChat();
                      }
                    }}
                  />
                  <Button variant="contained" onClick={() => void handleSendChat()} disabled={chatLoading}>
                    Send
                  </Button>
                </Box>
              </Box>
            )}

          </>
        )}
      </DialogContent>
      <DialogActions>
        {SHOW_REPORT_DOWNLOADS && analysis && tab === 0 && (
          <>
            <Button onClick={() => void handleDownloadReport('json')} disabled={running}>
              Download JSON
            </Button>
            <Button onClick={() => void handleDownloadReport('pdf')} disabled={running}>
              Download PDF
            </Button>
          </>
        )}
        {error && (
          <Button onClick={() => void handleRetry()} disabled={running}>
            Retry
          </Button>
        )}
        <Button onClick={onClose}>Close</Button>
      </DialogActions>
      </Dialog>
    </>
  );
}
