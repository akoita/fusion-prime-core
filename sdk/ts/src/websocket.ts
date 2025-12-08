/**
 * WebSocket client for real-time settlement command status updates
 * Implements auto-reconnection, heartbeat, and event subscriptions
 */

import { EventEmitter } from 'events';

export interface WebSocketConfig {
  url: string;
  reconnectInterval?: number;
  reconnectMaxAttempts?: number;
  heartbeatInterval?: number;
  heartbeatTimeout?: number;
}

export interface CommandStatusUpdate {
  command_id: string;
  status: string;
  timestamp: string;
  transaction_hash?: string;
  block_number?: number;
  error?: string;
}

export interface SubscriptionRequest {
  type: 'subscribe' | 'unsubscribe';
  command_ids?: string[];
  account_id?: string;
}

export enum WebSocketState {
  CONNECTING = 'CONNECTING',
  CONNECTED = 'CONNECTED',
  DISCONNECTED = 'DISCONNECTED',
  RECONNECTING = 'RECONNECTING',
  CLOSED = 'CLOSED',
}

export class FusionPrimeWebSocket extends EventEmitter {
  private ws: WebSocket | null = null;
  private config: Required<WebSocketConfig>;
  private state: WebSocketState = WebSocketState.DISCONNECTED;
  private reconnectAttempts = 0;
  private reconnectTimer: ReturnType<typeof setTimeout> | null = null;
  private heartbeatTimer: ReturnType<typeof setInterval> | null = null;
  private heartbeatTimeoutTimer: ReturnType<typeof setTimeout> | null = null;
  private subscribedCommands: Set<string> = new Set();
  private subscribedAccounts: Set<string> = new Set();

  constructor(config: WebSocketConfig) {
    super();
    this.config = {
      url: config.url,
      reconnectInterval: config.reconnectInterval ?? 5000,
      reconnectMaxAttempts: config.reconnectMaxAttempts ?? 10,
      heartbeatInterval: config.heartbeatInterval ?? 30000,
      heartbeatTimeout: config.heartbeatTimeout ?? 5000,
    };
  }

  /**
   * Connect to WebSocket server
   */
  connect(): void {
    if (this.state === WebSocketState.CONNECTED || this.state === WebSocketState.CONNECTING) {
      return;
    }

    this.setState(WebSocketState.CONNECTING);

    try {
      this.ws = new WebSocket(this.config.url);

      this.ws.onopen = this.handleOpen.bind(this);
      this.ws.onclose = this.handleClose.bind(this);
      this.ws.onerror = this.handleError.bind(this);
      this.ws.onmessage = this.handleMessage.bind(this);
    } catch (error) {
      this.emit('error', error);
      this.scheduleReconnect();
    }
  }

  /**
   * Disconnect from WebSocket server
   */
  disconnect(): void {
    this.clearTimers();
    this.setState(WebSocketState.CLOSED);

    if (this.ws) {
      this.ws.close(1000, 'Client requested disconnect');
      this.ws = null;
    }
  }

  /**
   * Subscribe to command status updates
   */
  subscribeToCommand(commandId: string): void {
    this.subscribedCommands.add(commandId);

    if (this.state === WebSocketState.CONNECTED) {
      this.send({
        type: 'subscribe',
        command_ids: [commandId],
      });
    }
  }

  /**
   * Subscribe to all commands for an account
   */
  subscribeToAccount(accountId: string): void {
    this.subscribedAccounts.add(accountId);

    if (this.state === WebSocketState.CONNECTED) {
      this.send({
        type: 'subscribe',
        account_id: accountId,
      });
    }
  }

  /**
   * Unsubscribe from command updates
   */
  unsubscribeFromCommand(commandId: string): void {
    this.subscribedCommands.delete(commandId);

    if (this.state === WebSocketState.CONNECTED) {
      this.send({
        type: 'unsubscribe',
        command_ids: [commandId],
      });
    }
  }

  /**
   * Unsubscribe from account updates
   */
  unsubscribeFromAccount(accountId: string): void {
    this.subscribedAccounts.delete(accountId);

    if (this.state === WebSocketState.CONNECTED) {
      this.send({
        type: 'unsubscribe',
        account_id: accountId,
      });
    }
  }

  /**
   * Get current connection state
   */
  getState(): WebSocketState {
    return this.state;
  }

  /**
   * Check if connected
   */
  isConnected(): boolean {
    return this.state === WebSocketState.CONNECTED;
  }

  /**
   * Handle WebSocket open event
   */
  private handleOpen(): void {
    this.setState(WebSocketState.CONNECTED);
    this.reconnectAttempts = 0;
    this.emit('connected');

    // Start heartbeat
    this.startHeartbeat();

    // Re-subscribe to all previous subscriptions
    this.resubscribe();
  }

  /**
   * Handle WebSocket close event
   */
  private handleClose(event: CloseEvent): void {
    this.clearTimers();

    if (this.state === WebSocketState.CLOSED) {
      return; // Intentional close, don't reconnect
    }

    this.setState(WebSocketState.DISCONNECTED);
    this.emit('disconnected', {
      code: event.code,
      reason: event.reason,
    });

    // Attempt reconnection
    this.scheduleReconnect();
  }

  /**
   * Handle WebSocket error event
   */
  private handleError(event: Event): void {
    this.emit('error', new Error('WebSocket error occurred'));
  }

  /**
   * Handle incoming WebSocket messages
   */
  private handleMessage(event: MessageEvent): void {
    try {
      const data = JSON.parse(event.data);

      // Handle different message types
      switch (data.type) {
        case 'status_update':
          this.handleStatusUpdate(data.payload as CommandStatusUpdate);
          break;

        case 'pong':
          this.handlePong();
          break;

        case 'error':
          this.emit('error', new Error(data.message));
          break;

        case 'subscribed':
          this.emit('subscribed', data.payload);
          break;

        case 'unsubscribed':
          this.emit('unsubscribed', data.payload);
          break;

        default:
          this.emit('message', data);
      }
    } catch (error) {
      this.emit('error', new Error(`Failed to parse message: ${error}`));
    }
  }

  /**
   * Handle command status update
   */
  private handleStatusUpdate(update: CommandStatusUpdate): void {
    this.emit('status_update', update);
    this.emit(`status:${update.command_id}`, update);
  }

  /**
   * Handle pong response
   */
  private handlePong(): void {
    if (this.heartbeatTimeoutTimer) {
      clearTimeout(this.heartbeatTimeoutTimer);
      this.heartbeatTimeoutTimer = null;
    }
  }

  /**
   * Send message to server
   */
  private send(data: unknown): void {
    if (!this.ws || this.ws.readyState !== WebSocket.OPEN) {
      throw new Error('WebSocket is not connected');
    }

    this.ws.send(JSON.stringify(data));
  }

  /**
   * Start heartbeat mechanism
   */
  private startHeartbeat(): void {
    this.heartbeatTimer = setInterval(() => {
      if (this.ws && this.ws.readyState === WebSocket.OPEN) {
        this.send({ type: 'ping' });

        // Set timeout for pong response
        this.heartbeatTimeoutTimer = setTimeout(() => {
          // No pong received, close connection
          this.ws?.close(1000, 'Heartbeat timeout');
        }, this.config.heartbeatTimeout);
      }
    }, this.config.heartbeatInterval);
  }

  /**
   * Schedule reconnection attempt
   */
  private scheduleReconnect(): void {
    if (this.reconnectAttempts >= this.config.reconnectMaxAttempts) {
      this.emit('reconnect_failed', {
        attempts: this.reconnectAttempts,
        max_attempts: this.config.reconnectMaxAttempts,
      });
      this.setState(WebSocketState.CLOSED);
      return;
    }

    this.setState(WebSocketState.RECONNECTING);
    this.reconnectAttempts++;

    const delay = Math.min(
      this.config.reconnectInterval * Math.pow(2, this.reconnectAttempts - 1),
      30000 // Max 30 seconds
    );

    this.emit('reconnecting', {
      attempt: this.reconnectAttempts,
      delay,
    });

    this.reconnectTimer = setTimeout(() => {
      this.connect();
    }, delay);
  }

  /**
   * Re-subscribe to all previous subscriptions
   */
  private resubscribe(): void {
    if (this.subscribedCommands.size > 0) {
      this.send({
        type: 'subscribe',
        command_ids: Array.from(this.subscribedCommands),
      });
    }

    for (const accountId of this.subscribedAccounts) {
      this.send({
        type: 'subscribe',
        account_id: accountId,
      });
    }
  }

  /**
   * Update connection state
   */
  private setState(newState: WebSocketState): void {
    const oldState = this.state;
    this.state = newState;

    if (oldState !== newState) {
      this.emit('state_change', {
        old: oldState,
        new: newState,
      });
    }
  }

  /**
   * Clear all timers
   */
  private clearTimers(): void {
    if (this.reconnectTimer) {
      clearTimeout(this.reconnectTimer);
      this.reconnectTimer = null;
    }

    if (this.heartbeatTimer) {
      clearInterval(this.heartbeatTimer);
      this.heartbeatTimer = null;
    }

    if (this.heartbeatTimeoutTimer) {
      clearTimeout(this.heartbeatTimeoutTimer);
      this.heartbeatTimeoutTimer = null;
    }
  }
}

/**
 * Create a WebSocket client
 */
export function createWebSocketClient(config: WebSocketConfig): FusionPrimeWebSocket {
  return new FusionPrimeWebSocket(config);
}

