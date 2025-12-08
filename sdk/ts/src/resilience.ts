/**
 * Resilience utilities for SDK HTTP client
 * Implements retry logic with exponential backoff and circuit breaker pattern
 */

export interface RetryConfig {
  maxAttempts: number;
  initialDelayMs: number;
  maxDelayMs: number;
  backoffMultiplier: number;
  retryableStatusCodes: number[];
}

export interface CircuitBreakerConfig {
  failureThreshold: number;
  successThreshold: number;
  timeoutMs: number;
  resetTimeoutMs: number;
}

export enum CircuitState {
  CLOSED = 'CLOSED', // Normal operation
  OPEN = 'OPEN', // Failing, reject requests
  HALF_OPEN = 'HALF_OPEN', // Testing if service recovered
}

/**
 * Circuit Breaker implementation
 * Prevents cascading failures by failing fast when a service is down
 */
export class CircuitBreaker {
  private state: CircuitState = CircuitState.CLOSED;
  private failureCount = 0;
  private successCount = 0;
  private nextAttemptTime = 0;
  private readonly config: CircuitBreakerConfig;

  constructor(config: Partial<CircuitBreakerConfig> = {}) {
    this.config = {
      failureThreshold: config.failureThreshold ?? 5,
      successThreshold: config.successThreshold ?? 2,
      timeoutMs: config.timeoutMs ?? 60000, // 1 minute
      resetTimeoutMs: config.resetTimeoutMs ?? 30000, // 30 seconds
    };
  }

  /**
   * Check if request is allowed
   */
  async call<T>(fn: () => Promise<T>): Promise<T> {
    if (!this.canAttempt()) {
      throw new Error(`Circuit breaker is ${this.state}. Request rejected.`);
    }

    try {
      const result = await fn();
      this.onSuccess();
      return result;
    } catch (error) {
      this.onFailure();
      throw error;
    }
  }

  private canAttempt(): boolean {
    const now = Date.now();

    switch (this.state) {
      case CircuitState.CLOSED:
        return true;

      case CircuitState.OPEN:
        // Check if enough time has passed to try again
        if (now >= this.nextAttemptTime) {
          this.state = CircuitState.HALF_OPEN;
          this.successCount = 0;
          return true;
        }
        return false;

      case CircuitState.HALF_OPEN:
        return true;

      default:
        return false;
    }
  }

  private onSuccess(): void {
    this.failureCount = 0;

    if (this.state === CircuitState.HALF_OPEN) {
      this.successCount++;
      if (this.successCount >= this.config.successThreshold) {
        this.state = CircuitState.CLOSED;
        this.successCount = 0;
      }
    }
  }

  private onFailure(): void {
    this.failureCount++;

    if (
      this.state === CircuitState.CLOSED &&
      this.failureCount >= this.config.failureThreshold
    ) {
      this.state = CircuitState.OPEN;
      this.nextAttemptTime = Date.now() + this.config.resetTimeoutMs;
    } else if (this.state === CircuitState.HALF_OPEN) {
      this.state = CircuitState.OPEN;
      this.nextAttemptTime = Date.now() + this.config.resetTimeoutMs;
    }
  }

  /**
   * Get current circuit state
   */
  getState(): CircuitState {
    return this.state;
  }

  /**
   * Reset circuit breaker to closed state
   */
  reset(): void {
    this.state = CircuitState.CLOSED;
    this.failureCount = 0;
    this.successCount = 0;
    this.nextAttemptTime = 0;
  }
}

/**
 * Retry with exponential backoff
 */
export async function retryWithBackoff<T>(
  fn: () => Promise<T>,
  config: Partial<RetryConfig> = {}
): Promise<T> {
  const retryConfig: RetryConfig = {
    maxAttempts: config.maxAttempts ?? 3,
    initialDelayMs: config.initialDelayMs ?? 1000,
    maxDelayMs: config.maxDelayMs ?? 30000,
    backoffMultiplier: config.backoffMultiplier ?? 2,
    retryableStatusCodes: config.retryableStatusCodes ?? [408, 429, 500, 502, 503, 504],
  };

  let lastError: Error | undefined;
  let attempt = 0;

  while (attempt < retryConfig.maxAttempts) {
    try {
      return await fn();
    } catch (error) {
      attempt++;
      lastError = error as Error;

      // Check if error is retryable
      if (!isRetryableError(error, retryConfig.retryableStatusCodes)) {
        throw error;
      }

      // Don't wait after last attempt
      if (attempt >= retryConfig.maxAttempts) {
        break;
      }

      // Calculate delay with exponential backoff
      const delayMs = Math.min(
        retryConfig.initialDelayMs * Math.pow(retryConfig.backoffMultiplier, attempt - 1),
        retryConfig.maxDelayMs
      );

      // Add jitter to prevent thundering herd
      const jitter = Math.random() * 0.3 * delayMs; // ±30% jitter
      const finalDelay = delayMs + jitter;

      await sleep(finalDelay);
    }
  }

  throw lastError ?? new Error('Max retry attempts exceeded');
}

/**
 * Check if error is retryable
 */
function isRetryableError(error: unknown, retryableStatusCodes: number[]): boolean {
  if (!error || typeof error !== 'object') {
    return false;
  }

  // Check for HTTP status codes
  if ('status' in error && typeof error.status === 'number') {
    return retryableStatusCodes.includes(error.status);
  }

  // Check for network errors
  if ('code' in error && typeof error.code === 'string') {
    const networkErrors = [
      'ECONNRESET',
      'ECONNREFUSED',
      'ETIMEDOUT',
      'ENOTFOUND',
      'ENETUNREACH',
    ];
    return networkErrors.includes(error.code);
  }

  return false;
}

/**
 * Sleep utility
 */
function sleep(ms: number): Promise<void> {
  return new Promise((resolve) => setTimeout(resolve, ms));
}

/**
 * Resilient HTTP client wrapper
 * Combines retry logic and circuit breaker
 */
export class ResilientClient {
  private readonly circuitBreaker: CircuitBreaker;
  private readonly retryConfig: Partial<RetryConfig>;

  constructor(
    circuitBreakerConfig: Partial<CircuitBreakerConfig> = {},
    retryConfig: Partial<RetryConfig> = {}
  ) {
    this.circuitBreaker = new CircuitBreaker(circuitBreakerConfig);
    this.retryConfig = retryConfig;
  }

  /**
   * Execute request with retry and circuit breaker
   */
  async execute<T>(fn: () => Promise<T>): Promise<T> {
    return this.circuitBreaker.call(async () => {
      return retryWithBackoff(fn, this.retryConfig);
    });
  }

  /**
   * Get circuit breaker state
   */
  getCircuitState(): CircuitState {
    return this.circuitBreaker.getState();
  }

  /**
   * Reset circuit breaker
   */
  resetCircuit(): void {
    this.circuitBreaker.reset();
  }
}

