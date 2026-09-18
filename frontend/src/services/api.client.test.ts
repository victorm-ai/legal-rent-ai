import { listContractsRequest, loginRequest } from './api';

describe('api client (fetch wrapper)', () => {
  it('loginRequest returns parsed success payload', async () => {
    vi.stubGlobal(
      'fetch',
      vi.fn().mockResolvedValue({
        ok: true,
        json: async () => ({
          access_token: 'token-abc',
          expires_in_minutes: 60,
          user_id: 'u1',
          email: 'client@example.com',
          name: 'Client',
          role: 'client',
        }),
      }),
    );

    const result = await loginRequest('client@example.com', 'secret');

    expect(result.ok).toBe(true);
    if (result.ok) {
      expect(result.data.access_token).toBe('token-abc');
    }
  });

  it('loginRequest returns backend detail on failure', async () => {
    vi.stubGlobal(
      'fetch',
      vi.fn().mockResolvedValue({
        ok: false,
        json: async () => ({ detail: 'Invalid credentials' }),
      }),
    );

    const result = await loginRequest('client@example.com', 'wrong');

    expect(result).toEqual({ ok: false, detail: 'Invalid credentials' });
  });

  it('listContractsRequest uses generic message when error body is not JSON', async () => {
    vi.stubGlobal(
      'fetch',
      vi.fn().mockResolvedValue({
        ok: false,
        json: async () => {
          throw new Error('not json');
        },
      }),
    );

    const result = await listContractsRequest('Bearer x');

    expect(result.ok).toBe(false);
    if (!result.ok) {
      expect(result.detail).toBe('Request failed. Please try again.');
    }
  });

  it('listContractsRequest forwards string detail from JSON errors', async () => {
    vi.stubGlobal(
      'fetch',
      vi.fn().mockResolvedValue({
        ok: false,
        json: async () => ({ detail: 'Session expired' }),
      }),
    );

    const result = await listContractsRequest('Bearer x');

    expect(result).toEqual({ ok: false, detail: 'Session expired' });
  });
});
