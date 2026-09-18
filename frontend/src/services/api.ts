import { API_URL } from '../config';
import type { LoginResponse } from '../types/auth';
import type { AnalysisDetail, AnalysisStatusResponse, AnalysisSummary, AnalysisApproval, FindingReview } from '../types/analysis';
import type { ChatMessage, ChatSession, ReportSummary } from '../types/delivery';
import type { Contract, ContractSummary, CreateContractParams, DocumentText, UpdateContractParams } from '../types/contracts';
import type { RetentionPolicy } from '../types/retention';

async function parseErrorDetail(response: Response): Promise<string> {
  try {
    const data = await response.json();
    if (typeof data.detail === 'string') {
      return data.detail;
    }
    return 'Request failed. Please try again.';
  } catch {
    return 'Request failed. Please try again.';
  }
}

export async function loginRequest(
  email: string,
  password: string,
): Promise<{ ok: true; data: LoginResponse } | { ok: false; detail: string }> {
  const response = await fetch(`${API_URL}/auth/login`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ email, password }),
  });

  const data = await response.json();

  if (response.ok) {
    return { ok: true, data: data as LoginResponse };
  }

  return { ok: false, detail: data.detail ?? 'Sign-in failed. Please check your credentials.' };
}

export async function logoutRequest(authHeader: string): Promise<void> {
  await fetch(`${API_URL}/auth/logout`, {
    method: 'POST',
    headers: {
      Authorization: authHeader,
      'Content-Type': 'application/json',
    },
  });
}

export async function listContractsRequest(
  authHeader: string,
): Promise<{ ok: true; data: ContractSummary[] } | { ok: false; detail: string }> {
  const response = await fetch(`${API_URL}/contracts`, {
    headers: { Authorization: authHeader },
  });

  if (response.ok) {
    return { ok: true, data: (await response.json()) as ContractSummary[] };
  }

  return { ok: false, detail: await parseErrorDetail(response) };
}

export async function createContractRequest(
  authHeader: string,
  params: CreateContractParams,
): Promise<{ ok: true; data: Contract } | { ok: false; detail: string }> {
  const formData = new FormData();
  formData.append('file', params.file);
  formData.append('perspective', params.perspective);
  if (params.title) {
    formData.append('title', params.title);
  }

  const response = await fetch(`${API_URL}/contracts`, {
    method: 'POST',
    headers: { Authorization: authHeader },
    body: formData,
  });

  if (response.ok) {
    return { ok: true, data: (await response.json()) as Contract };
  }

  return { ok: false, detail: await parseErrorDetail(response) };
}

export async function getRetentionPolicyRequest(
  authHeader: string,
): Promise<{ ok: true; data: RetentionPolicy } | { ok: false; detail: string }> {
  const response = await fetch(`${API_URL}/contracts/retention-policy`, {
    headers: { Authorization: authHeader },
  });

  if (response.ok) {
    return { ok: true, data: (await response.json()) as RetentionPolicy };
  }

  return { ok: false, detail: await parseErrorDetail(response) };
}

export async function deleteContractRequest(
  authHeader: string,
  contractId: string,
): Promise<{ ok: true } | { ok: false; detail: string }> {
  const response = await fetch(`${API_URL}/contracts/${contractId}`, {
    method: 'DELETE',
    headers: { Authorization: authHeader },
  });

  if (response.status === 204) {
    return { ok: true };
  }

  return { ok: false, detail: await parseErrorDetail(response) };
}

export async function startAnalysisRequest(
  authHeader: string,
  contractId: string,
  perspective: string,
  documentScope: string = 'original',
): Promise<{ ok: true; data: AnalysisDetail } | { ok: false; detail: string }> {
  const response = await fetch(`${API_URL}/contracts/${contractId}/analyses`, {
    method: 'POST',
    headers: {
      Authorization: authHeader,
      'Content-Type': 'application/json',
    },
    body: JSON.stringify({ perspective, document_scope: documentScope }),
  });

  if (response.ok) {
    return { ok: true, data: (await response.json()) as AnalysisDetail };
  }

  return { ok: false, detail: await parseErrorDetail(response) };
}

export async function listAnalysesRequest(
  authHeader: string,
  contractId: string,
): Promise<{ ok: true; data: AnalysisSummary[] } | { ok: false; detail: string }> {
  const response = await fetch(`${API_URL}/contracts/${contractId}/analyses`, {
    headers: { Authorization: authHeader },
  });

  if (response.ok) {
    return { ok: true, data: (await response.json()) as AnalysisSummary[] };
  }

  return { ok: false, detail: await parseErrorDetail(response) };
}

export async function getAnalysisRequest(
  authHeader: string,
  analysisId: string,
): Promise<{ ok: true; data: AnalysisDetail } | { ok: false; detail: string }> {
  const response = await fetch(`${API_URL}/analyses/${analysisId}`, {
    headers: { Authorization: authHeader },
  });

  if (response.ok) {
    return { ok: true, data: (await response.json()) as AnalysisDetail };
  }

  return { ok: false, detail: await parseErrorDetail(response) };
}

export async function getAnalysisStatusRequest(
  authHeader: string,
  analysisId: string,
): Promise<{ ok: true; data: AnalysisStatusResponse } | { ok: false; detail: string }> {
  const response = await fetch(`${API_URL}/analyses/${analysisId}/status`, {
    headers: { Authorization: authHeader },
  });

  if (response.ok) {
    return { ok: true, data: (await response.json()) as AnalysisStatusResponse };
  }

  return { ok: false, detail: await parseErrorDetail(response) };
}

export async function updateAnalysisStatusRequest(
  authHeader: string,
  analysisId: string,
  status: string,
): Promise<{ ok: true; data: AnalysisSummary } | { ok: false; detail: string }> {
  const response = await fetch(`${API_URL}/analyses/${analysisId}/status`, {
    method: 'PATCH',
    headers: {
      Authorization: authHeader,
      'Content-Type': 'application/json',
    },
    body: JSON.stringify({ status }),
  });

  if (response.ok) {
    return { ok: true, data: (await response.json()) as AnalysisSummary };
  }

  return { ok: false, detail: await parseErrorDetail(response) };
}

export async function reviewFindingRequest(
  authHeader: string,
  analysisId: string,
  findingId: string,
  verdict: string,
  notes?: string,
): Promise<{ ok: true; data: FindingReview } | { ok: false; detail: string }> {
  const response = await fetch(
    `${API_URL}/analyses/${analysisId}/findings/${findingId}/review`,
    {
      method: 'POST',
      headers: {
        Authorization: authHeader,
        'Content-Type': 'application/json',
      },
      body: JSON.stringify({ verdict, notes: notes ?? null }),
    },
  );

  if (response.ok) {
    return { ok: true, data: (await response.json()) as FindingReview };
  }

  return { ok: false, detail: await parseErrorDetail(response) };
}

export async function approveAnalysisRequest(
  authHeader: string,
  analysisId: string,
  notes?: string,
): Promise<{ ok: true; data: AnalysisApproval } | { ok: false; detail: string }> {
  const response = await fetch(`${API_URL}/analyses/${analysisId}/approve`, {
    method: 'POST',
    headers: {
      Authorization: authHeader,
      'Content-Type': 'application/json',
    },
    body: JSON.stringify({ notes: notes ?? null }),
  });

  if (response.ok) {
    return { ok: true, data: (await response.json()) as AnalysisApproval };
  }

  return { ok: false, detail: await parseErrorDetail(response) };
}

export async function updateContractRequest(
  authHeader: string,
  contractId: string,
  params: UpdateContractParams,
): Promise<{ ok: true; data: Contract } | { ok: false; detail: string }> {
  const response = await fetch(`${API_URL}/contracts/${contractId}`, {
    method: 'PATCH',
    headers: {
      Authorization: authHeader,
      'Content-Type': 'application/json',
    },
    body: JSON.stringify(params),
  });

  if (response.ok) {
    return { ok: true, data: (await response.json()) as Contract };
  }

  return { ok: false, detail: await parseErrorDetail(response) };
}

export async function getDocumentTextRequest(
  authHeader: string,
  contractId: string,
  documentId: string,
): Promise<{ ok: true; data: DocumentText } | { ok: false; detail: string }> {
  const response = await fetch(
    `${API_URL}/contracts/${contractId}/documents/${documentId}/text`,
    { headers: { Authorization: authHeader } },
  );

  if (response.ok) {
    return { ok: true, data: (await response.json()) as DocumentText };
  }

  return { ok: false, detail: await parseErrorDetail(response) };
}

export async function uploadLawyerRevisionRequest(
  authHeader: string,
  contractId: string,
  file: File,
): Promise<{ ok: true; data: import('../types/contracts').ContractDocument } | { ok: false; detail: string }> {
  const formData = new FormData();
  formData.append('file', file);

  const response = await fetch(`${API_URL}/contracts/${contractId}/lawyer-revision`, {
    method: 'POST',
    headers: { Authorization: authHeader },
    body: formData,
  });

  if (response.ok) {
    return {
      ok: true,
      data: (await response.json()) as import('../types/contracts').ContractDocument,
    };
  }

  return { ok: false, detail: await parseErrorDetail(response) };
}

export async function getContractRequest(
  authHeader: string,
  contractId: string,
): Promise<{ ok: true; data: Contract } | { ok: false; detail: string }> {
  const response = await fetch(`${API_URL}/contracts/${contractId}`, {
    headers: { Authorization: authHeader },
  });

  if (response.ok) {
    return { ok: true, data: (await response.json()) as Contract };
  }

  return { ok: false, detail: await parseErrorDetail(response) };
}

export async function downloadDocumentRequest(
  authHeader: string,
  contractId: string,
  documentId: string,
): Promise<
  | { ok: true; data: { blob: Blob; fileName: string; mimeType: string } }
  | { ok: false; detail: string }
> {
  const response = await fetch(
    `${API_URL}/contracts/${contractId}/documents/${documentId}/download`,
    { headers: { Authorization: authHeader } },
  );

  if (!response.ok) {
    return { ok: false, detail: await parseErrorDetail(response) };
  }

  const blob = await response.blob();
  const disposition = response.headers.get('Content-Disposition') ?? '';
  const fileNameMatch = disposition.match(/filename="(.+)"/);
  const fileName = fileNameMatch?.[1] ?? 'document';
  const mimeType = response.headers.get('Content-Type') ?? blob.type;

  return { ok: true, data: { blob, fileName, mimeType } };
}

export async function generateReportRequest(
  authHeader: string,
  analysisId: string,
  format: 'pdf' | 'json',
): Promise<{ ok: true; data: ReportSummary } | { ok: false; detail: string }> {
  const response = await fetch(`${API_URL}/analyses/${analysisId}/reports`, {
    method: 'POST',
    headers: {
      Authorization: authHeader,
      'Content-Type': 'application/json',
    },
    body: JSON.stringify({ format }),
  });

  if (response.ok) {
    return { ok: true, data: (await response.json()) as ReportSummary };
  }
  return { ok: false, detail: await parseErrorDetail(response) };
}

export async function downloadReportRequest(
  authHeader: string,
  reportId: string,
): Promise<
  | { ok: true; data: { blob: Blob; fileName: string; mimeType: string } }
  | { ok: false; detail: string }
> {
  const response = await fetch(`${API_URL}/reports/${reportId}/download`, {
    headers: { Authorization: authHeader },
  });

  if (!response.ok) {
    return { ok: false, detail: await parseErrorDetail(response) };
  }

  const blob = await response.blob();
  const disposition = response.headers.get('Content-Disposition') ?? '';
  const fileNameMatch = disposition.match(/filename="(.+)"/);
  const fileName = fileNameMatch?.[1] ?? 'report';
  const mimeType = response.headers.get('Content-Type') ?? blob.type;
  return { ok: true, data: { blob, fileName, mimeType } };
}

export async function listChatSessionsRequest(
  authHeader: string,
  contractId: string,
): Promise<{ ok: true; data: ChatSession[] } | { ok: false; detail: string }> {
  const response = await fetch(`${API_URL}/contracts/${contractId}/chat/sessions`, {
    headers: { Authorization: authHeader },
  });

  if (response.ok) {
    return { ok: true, data: (await response.json()) as ChatSession[] };
  }

  return { ok: false, detail: await parseErrorDetail(response) };
}

export async function createChatSessionRequest(
  authHeader: string,
  contractId: string,
  analysisId: string,
): Promise<{ ok: true; data: ChatSession } | { ok: false; detail: string }> {
  const response = await fetch(`${API_URL}/contracts/${contractId}/chat/sessions`, {
    method: 'POST',
    headers: {
      Authorization: authHeader,
      'Content-Type': 'application/json',
    },
    body: JSON.stringify({ analysis_id: analysisId }),
  });

  if (response.ok) {
    return { ok: true, data: (await response.json()) as ChatSession };
  }
  return { ok: false, detail: await parseErrorDetail(response) };
}

export async function listChatMessagesRequest(
  authHeader: string,
  sessionId: string,
): Promise<{ ok: true; data: ChatMessage[] } | { ok: false; detail: string }> {
  const response = await fetch(`${API_URL}/chat/sessions/${sessionId}/messages`, {
    headers: { Authorization: authHeader },
  });

  if (response.ok) {
    return { ok: true, data: (await response.json()) as ChatMessage[] };
  }
  return { ok: false, detail: await parseErrorDetail(response) };
}

export async function sendChatMessageRequest(
  authHeader: string,
  sessionId: string,
  content: string,
): Promise<{ ok: true; data: ChatMessage } | { ok: false; detail: string }> {
  const response = await fetch(`${API_URL}/chat/sessions/${sessionId}/messages`, {
    method: 'POST',
    headers: {
      Authorization: authHeader,
      'Content-Type': 'application/json',
    },
    body: JSON.stringify({ content }),
  });

  if (response.ok) {
    return { ok: true, data: (await response.json()) as ChatMessage };
  }
  return { ok: false, detail: await parseErrorDetail(response) };
}

type ChatStreamEvent =
  | { type: 'delta'; content: string }
  | { type: 'done'; message: ChatMessage }
  | { type: 'error'; detail: string };

function parseChatStreamChunk(buffer: string): { events: ChatStreamEvent[]; rest: string } {
  const parts = buffer.split('\n\n');
  const rest = parts.pop() ?? '';
  const events: ChatStreamEvent[] = [];
  for (const part of parts) {
    const line = part.split('\n').find((entry) => entry.startsWith('data: '));
    if (!line) {
      continue;
    }
    try {
      events.push(JSON.parse(line.slice(6)) as ChatStreamEvent);
    } catch {
      // ignore malformed chunks
    }
  }
  return { events, rest };
}

export async function sendChatMessageStreamRequest(
  authHeader: string,
  sessionId: string,
  content: string,
  onDelta: (content: string) => void,
): Promise<{ ok: true; data: ChatMessage } | { ok: false; detail: string }> {
  const response = await fetch(`${API_URL}/chat/sessions/${sessionId}/messages/stream`, {
    method: 'POST',
    headers: {
      Authorization: authHeader,
      'Content-Type': 'application/json',
    },
    body: JSON.stringify({ content }),
  });

  if (!response.ok) {
    return { ok: false, detail: await parseErrorDetail(response) };
  }

  const reader = response.body?.getReader();
  if (!reader) {
    return { ok: false, detail: 'Streaming is not supported in this browser.' };
  }

  const decoder = new TextDecoder();
  let buffer = '';
  let finalMessage: ChatMessage | null = null;

  while (true) {
    const { done, value } = await reader.read();
    if (done) {
      break;
    }
    buffer += decoder.decode(value, { stream: true });
    const parsed = parseChatStreamChunk(buffer);
    buffer = parsed.rest;
    for (const event of parsed.events) {
      if (event.type === 'delta') {
        onDelta(event.content);
      } else if (event.type === 'done') {
        finalMessage = event.message;
      } else if (event.type === 'error') {
        return { ok: false, detail: event.detail };
      }
    }
  }

  buffer += decoder.decode();
  const trailing = parseChatStreamChunk(buffer);
  for (const event of trailing.events) {
    if (event.type === 'delta') {
      onDelta(event.content);
    } else if (event.type === 'done') {
      finalMessage = event.message;
    } else if (event.type === 'error') {
      return { ok: false, detail: event.detail };
    }
  }

  if (!finalMessage) {
    return { ok: false, detail: 'Stream ended without a complete response.' };
  }
  return { ok: true, data: finalMessage };
}

export async function getChatSuggestionsRequest(
  authHeader: string,
  sessionId: string,
): Promise<{ ok: true; data: string[] } | { ok: false; detail: string }> {
  const response = await fetch(`${API_URL}/chat/sessions/${sessionId}/suggestions`, {
    headers: { Authorization: authHeader },
  });

  if (response.ok) {
    const data = (await response.json()) as { suggestions: string[] };
    return { ok: true, data: data.suggestions };
  }
  return { ok: false, detail: await parseErrorDetail(response) };
}

export async function listReviewMessagesRequest(
  authHeader: string,
  analysisId: string,
): Promise<{ ok: true; data: import('../types/delivery').ReviewMessage[] } | { ok: false; detail: string }> {
  const response = await fetch(`${API_URL}/analyses/${analysisId}/review-messages`, {
    headers: { Authorization: authHeader },
  });

  if (response.ok) {
    return { ok: true, data: (await response.json()) as import('../types/delivery').ReviewMessage[] };
  }
  return { ok: false, detail: await parseErrorDetail(response) };
}

export async function listContractReviewMessagesRequest(
  authHeader: string,
  contractId: string,
): Promise<{ ok: true; data: import('../types/delivery').ReviewMessage[] } | { ok: false; detail: string }> {
  const response = await fetch(`${API_URL}/contracts/${contractId}/review-messages`, {
    headers: { Authorization: authHeader },
  });

  if (response.ok) {
    return { ok: true, data: (await response.json()) as import('../types/delivery').ReviewMessage[] };
  }
  return { ok: false, detail: await parseErrorDetail(response) };
}

export async function markReviewMessagesReadRequest(
  authHeader: string,
  contractId: string,
): Promise<{ ok: true } | { ok: false; detail: string }> {
  const response = await fetch(`${API_URL}/contracts/${contractId}/review-messages/mark-read`, {
    method: 'POST',
    headers: { Authorization: authHeader },
  });

  if (response.status === 204 || response.ok) {
    return { ok: true };
  }

  return { ok: false, detail: await parseErrorDetail(response) };
}

export async function sendReviewMessageRequest(
  authHeader: string,
  analysisId: string,
  content: string,
): Promise<{ ok: true; data: import('../types/delivery').ReviewMessage } | { ok: false; detail: string }> {
  const response = await fetch(`${API_URL}/analyses/${analysisId}/review-messages`, {
    method: 'POST',
    headers: {
      Authorization: authHeader,
      'Content-Type': 'application/json',
    },
    body: JSON.stringify({ content }),
  });

  if (response.ok) {
    return { ok: true, data: (await response.json()) as import('../types/delivery').ReviewMessage };
  }
  return { ok: false, detail: await parseErrorDetail(response) };
}

export async function sendContractReviewMessageRequest(
  authHeader: string,
  contractId: string,
  content: string,
): Promise<{ ok: true; data: import('../types/delivery').ReviewMessage } | { ok: false; detail: string }> {
  const response = await fetch(`${API_URL}/contracts/${contractId}/review-messages`, {
    method: 'POST',
    headers: {
      Authorization: authHeader,
      'Content-Type': 'application/json',
    },
    body: JSON.stringify({ content }),
  });

  if (response.ok) {
    return { ok: true, data: (await response.json()) as import('../types/delivery').ReviewMessage };
  }
  return { ok: false, detail: await parseErrorDetail(response) };
}

export interface ComparisonResult {
  id: string;
  base_contract_id: string;
  compare_contract_id: string;
  summary: string | null;
  risk_delta: string | null;
  created_at: string;
  changes: Array<{
    id: string;
    change_type: string;
    category: string | null;
    description: string | null;
    old_value: string | null;
    new_value: string | null;
  }>;
  rows: Array<{
    item_key: string;
    item_type: string;
    original_value: string | null;
    new_value: string | null;
    change_type: string;
    difference: string;
  }>;
}

export async function compareContractsRequest(
  authHeader: string,
  baseContractId: string,
  compareContractId: string,
): Promise<{ ok: true; data: ComparisonResult } | { ok: false; detail: string }> {
  const response = await fetch(`${API_URL}/comparisons`, {
    method: 'POST',
    headers: {
      Authorization: authHeader,
      'Content-Type': 'application/json',
    },
    body: JSON.stringify({
      base_contract_id: baseContractId,
      compare_contract_id: compareContractId,
    }),
  });

  if (response.ok) {
    return { ok: true, data: (await response.json()) as ComparisonResult };
  }
  return { ok: false, detail: await parseErrorDetail(response) };
}

export async function createRevisionComparisonRequest(
  authHeader: string,
  contractId: string,
): Promise<{ ok: true; data: ComparisonResult } | { ok: false; detail: string }> {
  const response = await fetch(`${API_URL}/contracts/${contractId}/revision-comparison`, {
    method: 'POST',
    headers: {
      Authorization: authHeader,
      'Content-Type': 'application/json',
    },
  });

  if (response.ok) {
    return { ok: true, data: (await response.json()) as ComparisonResult };
  }

  return { ok: false, detail: await parseErrorDetail(response) };
}

export async function getLatestRevisionComparisonRequest(
  authHeader: string,
  contractId: string,
): Promise<
  | { ok: true; data: ComparisonResult }
  | { ok: false; detail: string; status: number }
> {
  const response = await fetch(`${API_URL}/contracts/${contractId}/revision-comparison/latest`, {
    headers: { Authorization: authHeader },
  });

  if (response.ok) {
    return { ok: true, data: (await response.json()) as ComparisonResult };
  }

  return { ok: false, detail: await parseErrorDetail(response), status: response.status };
}
