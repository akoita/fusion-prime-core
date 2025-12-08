import { describe, expect, it, vi } from 'vitest';

vi.mock('../src/httpClient', () => ({
  post: vi.fn(async () => ({ status: 'accepted', command_id: 'cmd-123' })),
  get: vi.fn(async () => ({ command_id: 'cmd-999', status: 'confirmed' })),
  deleteRequest: vi.fn(async () => undefined),
}));

import { ingestCommand, getCommandStatus, createWebhook, listWebhooks, deleteWebhook } from '../src/client';
import { post, get, deleteRequest } from '../src/httpClient';

const mockedPost = post as unknown as ReturnType<typeof vi.fn>;
const mockedGet = get as unknown as ReturnType<typeof vi.fn>;
const mockedDelete = deleteRequest as unknown as ReturnType<typeof vi.fn>;

describe('SDK client', () => {
  it('publishes ingest requests via HTTP client', async () => {
    const response = await ingestCommand({
      commandId: 'cmd-123',
      workflowId: 'wf-1',
      accountRef: 'acct-9',
      assetSymbol: 'USDC',
      amount: '1000',
    });

    expect(mockedPost).toHaveBeenCalledWith('/commands/ingest', {
      command_id: 'cmd-123',
      workflow_id: 'wf-1',
      account_ref: 'acct-9',
      asset_symbol: 'USDC',
      amount: '1000',
    });
    expect(response.status).toBe('accepted');
  });

  it('fetches command status via HTTP client', async () => {
    const response = await getCommandStatus('cmd-999');

    expect(mockedGet).toHaveBeenCalledWith('/commands/cmd-999');
    expect(response.status).toBe('confirmed');
  });
});

describe('SDK webhook management', () => {
  it('creates webhook subscription', async () => {
    mockedPost.mockResolvedValueOnce({
      subscription_id: 'wh_abc123',
      url: 'https://example.com/webhook',
      secret: 'secret_key',
      event_types: ['settlement.confirmed'],
      enabled: true,
    });

    const response = await createWebhook({
      url: 'https://example.com/webhook',
      eventTypes: ['settlement.confirmed'],
    });

    expect(mockedPost).toHaveBeenCalledWith('/webhooks', {
      url: 'https://example.com/webhook',
      event_types: ['settlement.confirmed'],
      description: undefined,
    });
    expect(response.subscriptionId).toBe('wh_abc123');
    expect(response.eventTypes).toEqual(['settlement.confirmed']);
  });

  it('lists webhook subscriptions', async () => {
    mockedGet.mockResolvedValueOnce([
      {
        subscription_id: 'wh_1',
        url: 'https://example.com/webhook1',
        secret: 'secret1',
        event_types: ['settlement.confirmed'],
        enabled: true,
      },
      {
        subscription_id: 'wh_2',
        url: 'https://example.com/webhook2',
        secret: 'secret2',
        event_types: ['settlement.failed'],
        enabled: true,
      },
    ]);

    const response = await listWebhooks();

    expect(mockedGet).toHaveBeenCalledWith('/webhooks');
    expect(response).toHaveLength(2);
    expect(response[0].subscriptionId).toBe('wh_1');
  });

  it('deletes webhook subscription', async () => {
    await deleteWebhook('wh_abc123');

    expect(mockedDelete).toHaveBeenCalledWith('/webhooks/wh_abc123');
  });
});
