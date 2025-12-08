import { post, get } from './httpClient';
import { SettlementCommand } from './gen/fusionprime/settlement/v1/settlement';

export interface CommandIngestRequest {
  commandId: string;
  workflowId: string;
  accountRef: string;
  assetSymbol: string;
  amount: string;
}

interface CommandStatusResponse {
  command_id: string;
  status: string;
}

export async function ingestCommand(request: CommandIngestRequest): Promise<SettlementCommand> {
  const payload = {
    command_id: request.commandId,
    workflow_id: request.workflowId,
    account_ref: request.accountRef,
    asset_symbol: request.assetSymbol,
    amount: request.amount,
  };

  const response = await post<{ status: string; command_id: string }>('/commands/ingest', payload);

  return {
    status: response.status,
    commandId: response.command_id,
    workflowId: request.workflowId,
    accountRef: request.accountRef,
    assetSymbol: request.assetSymbol,
    amount: request.amount,
  } satisfies SettlementCommand;
}

export async function getCommandStatus(commandId: string): Promise<{ commandId: string; status: string }> {
  const response = await get<CommandStatusResponse>(`/commands/${commandId}`);
  return { commandId: response.command_id, status: response.status };
}

// Webhook management

export interface WebhookSubscription {
  subscriptionId: string;
  url: string;
  secret: string;
  eventTypes: string[];
  enabled: boolean;
  description?: string;
}

export interface CreateWebhookRequest {
  url: string;
  eventTypes: string[];
  description?: string;
}

interface WebhookResponse {
  subscription_id: string;
  url: string;
  secret: string;
  event_types: string[];
  enabled: boolean;
  description?: string;
}

function mapWebhookResponse(response: WebhookResponse): WebhookSubscription {
  return {
    subscriptionId: response.subscription_id,
    url: response.url,
    secret: response.secret,
    eventTypes: response.event_types,
    enabled: response.enabled,
    description: response.description,
  };
}

export async function createWebhook(request: CreateWebhookRequest): Promise<WebhookSubscription> {
  const payload = {
    url: request.url,
    event_types: request.eventTypes,
    description: request.description,
  };

  const response = await post<WebhookResponse>('/webhooks', payload);
  return mapWebhookResponse(response);
}

export async function getWebhook(subscriptionId: string): Promise<WebhookSubscription> {
  const response = await get<WebhookResponse>(`/webhooks/${subscriptionId}`);
  return mapWebhookResponse(response);
}

export async function listWebhooks(): Promise<WebhookSubscription[]> {
  const response = await get<WebhookResponse[]>('/webhooks');
  return response.map(mapWebhookResponse);
}

export async function deleteWebhook(subscriptionId: string): Promise<void> {
  const { deleteRequest } = await import('./httpClient');
  await deleteRequest(`/webhooks/${subscriptionId}`);
}
