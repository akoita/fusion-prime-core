import React from 'react'
import ReactDOM from 'react-dom/client'
import { QueryClient, QueryClientProvider } from '@tanstack/react-query'
import { BrowserRouter } from 'react-router-dom'
import { WagmiProvider } from 'wagmi'
import { RainbowKitProvider } from '@rainbow-me/rainbowkit'
import App from './App'
import './index.css'
import '@rainbow-me/rainbowkit/styles.css'

// Web3 configuration
import { wagmiConfig } from './config/wagmi'

// Update API client to use auth token
import { apiClient } from './lib/api'
import { authManager } from './lib/auth'

// Set auth token in API client
const token = authManager.getToken()
if (token) {
  apiClient.defaults.headers.common['Authorization'] = `Bearer ${token}`
}

const queryClient = new QueryClient({
  defaultOptions: {
    queries: {
      refetchOnWindowFocus: false,
      retry: 1,
      staleTime: 5 * 60 * 1000, // 5 minutes
    },
  },
})

ReactDOM.createRoot(document.getElementById('root')!).render(
  <React.StrictMode>
    <WagmiProvider config={wagmiConfig}>
      <QueryClientProvider client={queryClient}>
        <RainbowKitProvider>
          <BrowserRouter>
            <App />
          </BrowserRouter>
        </RainbowKitProvider>
      </QueryClientProvider>
    </WagmiProvider>
  </React.StrictMode>,
)
