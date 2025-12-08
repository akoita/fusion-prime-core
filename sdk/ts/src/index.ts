export const version = '0.1.0';

// Re-export all client functions
export {
  ingestCommand,
  getCommandStatus,
  createWebhook,
  getWebhook,
  listWebhooks,
  deleteWebhook,
  type CommandIngestRequest,
  type WebhookSubscription,
  type CreateWebhookRequest,
} from './client';

// Re-export resilience utilities
export {
  configureResilience,
  getCircuitState,
  resetCircuit,
} from './httpClient';

export {
  CircuitState,
  CircuitBreaker,
  retryWithBackoff,
  ResilientClient,
  type RetryConfig,
  type CircuitBreakerConfig,
} from './resilience';

// Re-export WebSocket utilities
export {
  FusionPrimeWebSocket,
  createWebSocketClient,
  WebSocketState,
  type WebSocketConfig,
  type CommandStatusUpdate,
  type SubscriptionRequest,
} from './websocket';

