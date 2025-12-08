import { request } from 'undici';
import { ResilientClient, RetryConfig, CircuitBreakerConfig } from './resilience';

const DEFAULT_BASE_URL = process.env.FUSION_PRIME_API_BASE_URL ?? 'http://localhost:8000';

// Default resilience configuration
const DEFAULT_RETRY_CONFIG: Partial<RetryConfig> = {
  maxAttempts: 3,
  initialDelayMs: 1000,
  maxDelayMs: 10000,
  backoffMultiplier: 2,
  retryableStatusCodes: [408, 429, 500, 502, 503, 504],
};

const DEFAULT_CIRCUIT_BREAKER_CONFIG: Partial<CircuitBreakerConfig> = {
  failureThreshold: 5,
  successThreshold: 2,
  timeoutMs: 60000,
  resetTimeoutMs: 30000,
};

// Global resilient client instance
let resilientClient: ResilientClient | null = null;

/**
 * Configure resilience settings for the HTTP client
 */
export function configureResilience(
  retryConfig?: Partial<RetryConfig>,
  circuitBreakerConfig?: Partial<CircuitBreakerConfig>
): void {
  resilientClient = new ResilientClient(
    { ...DEFAULT_CIRCUIT_BREAKER_CONFIG, ...circuitBreakerConfig },
    { ...DEFAULT_RETRY_CONFIG, ...retryConfig }
  );
}

/**
 * Get or create resilient client
 */
function getResilientClient(): ResilientClient {
  if (!resilientClient) {
    resilientClient = new ResilientClient(
      DEFAULT_CIRCUIT_BREAKER_CONFIG,
      DEFAULT_RETRY_CONFIG
    );
  }
  return resilientClient;
}

/**
 * Get circuit breaker state
 */
export function getCircuitState() {
  return getResilientClient().getCircuitState();
}

/**
 * Reset circuit breaker
 */
export function resetCircuit(): void {
  getResilientClient().resetCircuit();
}

function resolveUrl(path: string): string {
  const base = DEFAULT_BASE_URL.endsWith('/') ? DEFAULT_BASE_URL : `${DEFAULT_BASE_URL}/`;
  return new URL(path.replace(/^\//, ''), base).toString();
}

interface HttpError extends Error {
  status: number;
}

async function parseJson<T>(response: Awaited<ReturnType<typeof request>>): Promise<T> {
  if (response.statusCode >= 400) {
    const error = new Error(`Request failed with status ${response.statusCode}`) as HttpError;
    error.status = response.statusCode;
    throw error;
  }

  return (await response.body.json()) as T;
}

export async function post<T>(path: string, body: unknown): Promise<T> {
  const client = getResilientClient();

  return client.execute(async () => {
    const response = await request(resolveUrl(path), {
      method: 'POST',
      body: JSON.stringify(body),
      headers: {
        'content-type': 'application/json',
      },
    });

    return parseJson<T>(response);
  });
}

export async function get<T>(path: string): Promise<T> {
  const client = getResilientClient();

  return client.execute(async () => {
    const response = await request(resolveUrl(path));
    return parseJson<T>(response);
  });
}

export async function deleteRequest(path: string): Promise<void> {
  const client = getResilientClient();

  return client.execute(async () => {
    const response = await request(resolveUrl(path), {
      method: 'DELETE',
    });

    if (response.statusCode >= 400) {
      const error = new Error(`Request failed with status ${response.statusCode}`) as HttpError;
      error.status = response.statusCode;
      throw error;
    }
  });
}
