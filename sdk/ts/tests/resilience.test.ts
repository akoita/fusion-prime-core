import { describe, it, expect, vi, beforeEach } from 'vitest';
import {
  CircuitBreaker,
  CircuitState,
  retryWithBackoff,
  ResilientClient,
} from '../src/resilience';

describe('CircuitBreaker', () => {
  let circuitBreaker: CircuitBreaker;

  beforeEach(() => {
    circuitBreaker = new CircuitBreaker({
      failureThreshold: 3,
      successThreshold: 2,
      resetTimeoutMs: 1000,
    });
  });

  it('starts in CLOSED state', () => {
    expect(circuitBreaker.getState()).toBe(CircuitState.CLOSED);
  });

  it('remains CLOSED on successful calls', async () => {
    await circuitBreaker.call(async () => 'success');
    await circuitBreaker.call(async () => 'success');
    await circuitBreaker.call(async () => 'success');

    expect(circuitBreaker.getState()).toBe(CircuitState.CLOSED);
  });

  it('opens after reaching failure threshold', async () => {
    const failingFn = async () => {
      throw new Error('Service unavailable');
    };

    // Fail 3 times (threshold)
    for (let i = 0; i < 3; i++) {
      try {
        await circuitBreaker.call(failingFn);
      } catch {
        // Expected
      }
    }

    expect(circuitBreaker.getState()).toBe(CircuitState.OPEN);
  });

  it('rejects requests when OPEN', async () => {
    const failingFn = async () => {
      throw new Error('Service unavailable');
    };

    // Open the circuit
    for (let i = 0; i < 3; i++) {
      try {
        await circuitBreaker.call(failingFn);
      } catch {
        // Expected
      }
    }

    // Try to call when OPEN
    await expect(circuitBreaker.call(async () => 'success')).rejects.toThrow('Circuit breaker is OPEN');
  });

  it('transitions to HALF_OPEN after reset timeout', async () => {
    const failingFn = async () => {
      throw new Error('Service unavailable');
    };

    // Open the circuit
    for (let i = 0; i < 3; i++) {
      try {
        await circuitBreaker.call(failingFn);
      } catch {
        // Expected
      }
    }

    expect(circuitBreaker.getState()).toBe(CircuitState.OPEN);

    // Wait for reset timeout
    await new Promise((resolve) => setTimeout(resolve, 1100));

    // Next call should transition to HALF_OPEN
    try {
      await circuitBreaker.call(failingFn);
    } catch {
      // Expected
    }

    // It should be OPEN again after failing in HALF_OPEN
    expect(circuitBreaker.getState()).toBe(CircuitState.OPEN);
  });

  it('closes after successful calls in HALF_OPEN', async () => {
    const failingFn = async () => {
      throw new Error('Service unavailable');
    };

    // Open the circuit
    for (let i = 0; i < 3; i++) {
      try {
        await circuitBreaker.call(failingFn);
      } catch {
        // Expected
      }
    }

    // Wait for reset timeout
    await new Promise((resolve) => setTimeout(resolve, 1100));

    // Succeed enough times to close
    await circuitBreaker.call(async () => 'success');
    await circuitBreaker.call(async () => 'success');

    expect(circuitBreaker.getState()).toBe(CircuitState.CLOSED);
  });

  it('resets to CLOSED state', async () => {
    const failingFn = async () => {
      throw new Error('Service unavailable');
    };

    // Open the circuit
    for (let i = 0; i < 3; i++) {
      try {
        await circuitBreaker.call(failingFn);
      } catch {
        // Expected
      }
    }

    expect(circuitBreaker.getState()).toBe(CircuitState.OPEN);

    // Reset
    circuitBreaker.reset();

    expect(circuitBreaker.getState()).toBe(CircuitState.CLOSED);
  });
});

describe('retryWithBackoff', () => {
  it('succeeds on first attempt', async () => {
    const fn = vi.fn(async () => 'success');

    const result = await retryWithBackoff(fn, { maxAttempts: 3 });

    expect(result).toBe('success');
    expect(fn).toHaveBeenCalledTimes(1);
  });

  it('retries on retryable errors', async () => {
    const fn = vi
      .fn()
      .mockRejectedValueOnce({ status: 503 })
      .mockRejectedValueOnce({ status: 503 })
      .mockResolvedValueOnce('success');

    const result = await retryWithBackoff(fn, {
      maxAttempts: 3,
      initialDelayMs: 10,
      maxDelayMs: 100,
    });

    expect(result).toBe('success');
    expect(fn).toHaveBeenCalledTimes(3);
  });

  it('does not retry on non-retryable errors', async () => {
    const fn = vi.fn().mockRejectedValue({ status: 400 });

    await expect(
      retryWithBackoff(fn, {
        maxAttempts: 3,
        initialDelayMs: 10,
      })
    ).rejects.toEqual({ status: 400 });

    expect(fn).toHaveBeenCalledTimes(1);
  });

  it('throws after max attempts', async () => {
    const fn = vi.fn().mockRejectedValue({ status: 503 });

    await expect(
      retryWithBackoff(fn, {
        maxAttempts: 3,
        initialDelayMs: 10,
        maxDelayMs: 100,
      })
    ).rejects.toEqual({ status: 503 });

    expect(fn).toHaveBeenCalledTimes(3);
  });

  it('retries on network errors', async () => {
    const fn = vi
      .fn()
      .mockRejectedValueOnce({ code: 'ECONNRESET' })
      .mockResolvedValueOnce('success');

    const result = await retryWithBackoff(fn, {
      maxAttempts: 3,
      initialDelayMs: 10,
    });

    expect(result).toBe('success');
    expect(fn).toHaveBeenCalledTimes(2);
  });

  it('applies exponential backoff', async () => {
    const fn = vi
      .fn()
      .mockRejectedValueOnce({ status: 503 })
      .mockRejectedValueOnce({ status: 503 })
      .mockResolvedValueOnce('success');

    const startTime = Date.now();

    await retryWithBackoff(fn, {
      maxAttempts: 3,
      initialDelayMs: 100,
      backoffMultiplier: 2,
      maxDelayMs: 1000,
    });

    const elapsed = Date.now() - startTime;

    // Should wait at least initialDelay (100ms) + second delay (200ms)
    // With jitter, expect at least 200ms (accounting for some variance)
    expect(elapsed).toBeGreaterThan(200);
  });
});

describe('ResilientClient', () => {
  it('executes successful requests', async () => {
    const client = new ResilientClient();
    const fn = vi.fn(async () => 'success');

    const result = await client.execute(fn);

    expect(result).toBe('success');
    expect(fn).toHaveBeenCalledTimes(1);
  });

  it('retries and circuit breaks on failures', async () => {
    const client = new ResilientClient(
      { failureThreshold: 2, successThreshold: 1, resetTimeoutMs: 1000 },
      { maxAttempts: 2, initialDelayMs: 10 }
    );

    const fn = vi.fn().mockRejectedValue({ status: 503 });

    // First request: retries twice, fails
    await expect(client.execute(fn)).rejects.toEqual({ status: 503 });
    expect(fn).toHaveBeenCalledTimes(2);

    // Second request: retries twice, fails, opens circuit
    await expect(client.execute(fn)).rejects.toEqual({ status: 503 });
    expect(fn).toHaveBeenCalledTimes(4);

    // Third request: circuit is OPEN, rejected immediately
    await expect(client.execute(fn)).rejects.toThrow('Circuit breaker is OPEN');
    expect(fn).toHaveBeenCalledTimes(4); // No new calls
  });

  it('provides circuit state', () => {
    const client = new ResilientClient();
    expect(client.getCircuitState()).toBe(CircuitState.CLOSED);
  });

  it('allows circuit reset', async () => {
    const client = new ResilientClient(
      { failureThreshold: 1, successThreshold: 1 },
      { maxAttempts: 1 }
    );

    const fn = vi.fn().mockRejectedValue({ status: 503 });

    // Open the circuit
    await expect(client.execute(fn)).rejects.toEqual({ status: 503 });

    expect(client.getCircuitState()).toBe(CircuitState.OPEN);

    // Reset
    client.resetCircuit();

    expect(client.getCircuitState()).toBe(CircuitState.CLOSED);

    // Should be able to make requests again
    fn.mockResolvedValueOnce('success');
    const result = await client.execute(fn);
    expect(result).toBe('success');
  });
});

