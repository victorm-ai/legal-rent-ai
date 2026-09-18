import type { ChatMessage } from '../types/delivery';
import { submitContractChatMessage } from './contractChat';
import * as api from './api';

vi.mock('./api', () => ({
  sendChatMessageStreamRequest: vi.fn(),
}));

describe('submitContractChatMessage', () => {
  it('optimistically adds user and assistant placeholders', async () => {
    vi.mocked(api.sendChatMessageStreamRequest).mockImplementation(
      async (_auth, _session, _text, onChunk) => {
        onChunk('Partial ');
        onChunk('reply');
        return {
          ok: true,
          data: {
            id: 'server-assistant-1',
            role: 'assistant',
            content: 'Partial reply',
            references: [],
            created_at: '2026-01-01T00:00:00.000Z',
          },
        };
      },
    );

    const snapshots: ChatMessage[][] = [];
    const onMessagesUpdate = vi.fn((updater: (previous: ChatMessage[]) => ChatMessage[]) => {
      const previous = snapshots.length > 0 ? snapshots[snapshots.length - 1] : [];
      snapshots.push(updater(previous));
    });

    const result = await submitContractChatMessage(
      'Bearer t',
      'session-1',
      'Hello',
      onMessagesUpdate,
    );

    expect(result).toEqual({ ok: true });

    const initialMessages = snapshots[0] ?? [];
    expect(initialMessages.some((message) => message.role === 'user' && message.content === 'Hello')).toBe(
      true,
    );
    expect(
      initialMessages.some((message) => message.role === 'assistant' && message.content === ''),
    ).toBe(true);

    const finalMessages = snapshots[snapshots.length - 1] ?? [];
    expect(finalMessages.some((message) => message.id === 'server-assistant-1')).toBe(true);
  });

  it('removes assistant placeholder when stream request fails', async () => {
    vi.mocked(api.sendChatMessageStreamRequest).mockResolvedValue({
      ok: false,
      detail: 'Stream failed',
    });

    const snapshots: ChatMessage[][] = [];
    const onMessagesUpdate = vi.fn((updater: (previous: ChatMessage[]) => ChatMessage[]) => {
      const previous = snapshots.length > 0 ? snapshots[snapshots.length - 1] : [];
      snapshots.push(updater(previous));
    });

    const result = await submitContractChatMessage(
      'Bearer t',
      'session-1',
      'Hello',
      onMessagesUpdate,
    );

    expect(result).toEqual({ ok: false, detail: 'Stream failed' });
    const lastSnapshot = snapshots[snapshots.length - 1] ?? [];
    expect(lastSnapshot.some((message) => message.role === 'assistant')).toBe(false);
    expect(lastSnapshot.some((message) => message.role === 'user')).toBe(true);
  });
});
