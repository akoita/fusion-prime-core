/// <reference types="vite/client" />

interface ImportMetaEnv {
  readonly VITE_API_BASE_URL?: string
  readonly VITE_WS_URL?: string
  readonly VITE_ENABLE_REAL_TIME?: string
  readonly VITE_ENABLE_ANALYTICS?: string
  readonly VITE_AUTH_ENABLED?: string
  readonly VITE_AUTH_ISSUER?: string
  readonly VITE_AUTH_CLIENT_ID?: string
}

interface ImportMeta {
  readonly env: ImportMetaEnv
}
