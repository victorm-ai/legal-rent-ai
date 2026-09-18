import {
  createChatSessionRequest,
  getChatSuggestionsRequest,
  listChatMessagesRequest,
  listChatSessionsRequest,
  sendChatMessageStreamRequest,
} from './api';
import type { ChatMessage, ChatSession } from '../types/delivery';

export async function submitContractChatMessage(
  authHeader: string,
  sessionId: string,
  userText: string,
  onMessagesUpdate: (updater: (previous: ChatMessage[]) => ChatMessage[]) => void,
): Promise<{ ok: true } | { ok: false; detail: string }> {
  const userMessage: ChatMessage = {
    id: `local-user-${Date.now()}`,
    role: 'user',
    content: userText,
    references: [],
    created_at: new Date().toISOString(),
  };
  const assistantId = `local-assistant-${Date.now()}`;
  onMessagesUpdate((previous) => [
    ...previous,
    userMessage,
    {
      id: assistantId,
      role: 'assistant',
      content: '',
      references: [],
      created_at: null,
    },
  ]);

  const result = await sendChatMessageStreamRequest(authHeader, sessionId, userText, (content) => {
    onMessagesUpdate((previous) =>
      previous.map((message) => (message.id === assistantId ? { ...message, content } : message)),
    );
  });

  if (!result.ok) {
    onMessagesUpdate((previous) => previous.filter((message) => message.id !== assistantId));
    return result;
  }

  onMessagesUpdate((previous) =>
    previous.map((message) => (message.id === assistantId ? result.data : message)),
  );
  return { ok: true };
}

export async function restoreAnalysisChatSession(
  authHeader: string,
  contractId: string,
  analysisId: string,
): Promise<{ session: ChatSession | null; messages: ChatMessage[]; suggestions: string[] }> {
  const sessions = await listChatSessionsRequest(authHeader, contractId);
  if (!sessions.ok) {
    return { session: null, messages: [], suggestions: [] };
  }

  const existing = sessions.data.find((session) => session.analysis_id === analysisId);
  if (!existing) {
    return { session: null, messages: [], suggestions: [] };
  }

  const messages = await listChatMessagesRequest(authHeader, existing.id);
  const suggestions = await getChatSuggestionsRequest(authHeader, existing.id);

  return {
    session: existing,
    messages: messages.ok ? messages.data : [],
    suggestions: suggestions.ok ? suggestions.data : [],
  };
}

export async function ensureAnalysisChatSession(
  authHeader: string,
  contractId: string,
  analysisId: string,
): Promise<
  | { ok: true; session: ChatSession; messages: ChatMessage[]; suggestions: string[] }
  | { ok: false; detail: string }
> {
  const restored = await restoreAnalysisChatSession(authHeader, contractId, analysisId);
  if (restored.session) {
    return {
      ok: true,
      session: restored.session,
      messages: restored.messages,
      suggestions: restored.suggestions,
    };
  }

  const created = await createChatSessionRequest(authHeader, contractId, analysisId);
  if (!created.ok) {
    return { ok: false, detail: created.detail };
  }

  const messages = await listChatMessagesRequest(authHeader, created.data.id);
  const suggestions = await getChatSuggestionsRequest(authHeader, created.data.id);

  return {
    ok: true,
    session: created.data,
    messages: messages.ok ? messages.data : [],
    suggestions: suggestions.ok ? suggestions.data : [],
  };
}
