import { io, Socket } from 'socket.io-client'

const WS_URL =
  import.meta.env.VITE_WS_URL ||
  import.meta.env.VITE_API_BASE_URL?.replace('http://', 'ws://').replace('https://', 'wss://') ||
  'wss://risk-engine-961424092563.us-central1.run.app'

class WebSocketManager {
  private socket: Socket | null = null
  private reconnectAttempts = 0
  private maxReconnectAttempts = 5
  private reconnectDelay = 1000 // Start with 1 second

  connect(userId?: string): Socket {
    if (this.socket?.connected) {
      return this.socket
    }

    this.socket = io(WS_URL, {
      transports: ['websocket'],
      reconnection: true,
      reconnectionAttempts: this.maxReconnectAttempts,
      reconnectionDelay: this.reconnectDelay,
      reconnectionDelayMax: 30000,
    })

    this.socket.on('connect', () => {
      console.log('✅ WebSocket connected')
      this.reconnectAttempts = 0
      this.reconnectDelay = 1000

      // Join user-specific room if userId provided
      if (userId) {
        this.socket?.emit('join', { userId })
      }
    })

    this.socket.on('disconnect', (reason) => {
      console.warn('⚠️ WebSocket disconnected:', reason)
      if (reason === 'io server disconnect') {
        // Server disconnected, manual reconnect needed
        this.socket?.connect()
      }
    })

    this.socket.on('connect_error', (error) => {
      console.error('❌ WebSocket connection error:', error)
      this.reconnectAttempts++
      if (this.reconnectAttempts < this.maxReconnectAttempts) {
        this.reconnectDelay = Math.min(this.reconnectDelay * 2, 30000)
        console.log(`🔄 Reconnecting in ${this.reconnectDelay}ms...`)
      }
    })

    return this.socket
  }

  disconnect(): void {
    if (this.socket) {
      this.socket.disconnect()
      this.socket = null
    }
  }

  on(event: string, callback: (...args: any[]) => void): void {
    this.socket?.on(event, callback)
  }

  off(event: string, callback?: (...args: any[]) => void): void {
    this.socket?.off(event, callback)
  }

  emit(event: string, data?: any): void {
    this.socket?.emit(event, data)
  }

  isConnected(): boolean {
    return this.socket?.connected || false
  }
}

// Singleton instance
export const websocketManager = new WebSocketManager()
