# Fusion Prime Risk Dashboard

Real-time portfolio risk monitoring dashboard for institutional treasury managers, risk officers, and compliance analysts.

## Features

### Portfolio Overview
- Multi-chain collateral visualization with aggregate USD values
- Real-time margin health gauge (0-100 scale)
- Position breakdown by asset and chain with drill-down
- Historical PnL chart with configurable time ranges

### Margin Monitoring
- Live margin call and liquidation alerts with severity indicators
- Account-level risk ranking with sortable data table
- Concentration risk heatmap by asset and chain
- Alert notification preferences (email, SMS, webhook)

### Analytics & Reports
- Value-at-Risk (VaR) and Expected Shortfall (ES) trends
- Settlement latency distribution histogram
- Cross-chain utilization patterns with geographic overlay
- Regulatory reporting exports (CSV, PDF)

## Technology Stack

- **Frontend Framework**: React 18 + TypeScript
- **State Management**: React Query for server state, Zustand for UI state
- **Routing**: React Router v6
- **Charts**: Recharts (for real-time charts) + D3.js (for custom visualizations)
- **Styling**: Tailwind CSS + shadcn/ui components
- **API Client**: Axios with retry and circuit breaker logic
- **WebSocket**: Socket.io for real-time updates
- **Testing**: Vitest + React Testing Library + Playwright

## Architecture

```
┌─────────────────────────────────────────┐
│      Risk Dashboard (React)             │
│  ┌─────────────┐  ┌─────────────────┐  │
│  │ Portfolio   │  │ Margin Monitor  │  │
│  │ Overview    │  │                 │  │
│  └─────────────┘  └─────────────────┘  │
│  ┌─────────────┐  ┌─────────────────┐  │
│  │ Analytics   │  │ Alerts          │  │
│  │ & Reports   │  │                 │  │
│  └─────────────┘  └─────────────────┘  │
└──────────────┬──────────────────────────┘
               │
               │ REST API + WebSocket
               ▼
┌─────────────────────────────────────────┐
│    Risk Analytics API (FastAPI)         │
│  - Query BigQuery                       │
│  - Serve cached aggregates              │
│  - Stream real-time updates             │
└──────────────┬──────────────────────────┘
               │
               ▼
┌─────────────────────────────────────────┐
│    BigQuery (risk.* dataset)            │
│  - portfolio_exposures                  │
│  - asset_exposures                      │
│  - margin_events                        │
└─────────────────────────────────────────┘
```

## Getting Started

### Prerequisites

```bash
# Install Node.js 20+ and pnpm
curl -fsSL https://get.pnpm.io/install.sh | sh -

# Clone the repository
cd fusion-prime/frontend/risk-dashboard

# Install dependencies
pnpm install
```

### Environment Variables

Create a `.env` file:

```bash
# API Configuration
VITE_API_BASE_URL=http://localhost:8001
VITE_WS_URL=ws://localhost:8001/ws

# Feature Flags
VITE_ENABLE_REAL_TIME=true
VITE_ENABLE_ANALYTICS=true

# Auth (Identity-Aware Proxy in production)
VITE_AUTH_ENABLED=false
VITE_AUTH_ISSUER=https://accounts.google.com
VITE_AUTH_CLIENT_ID=<client-id>
```

### Development

```bash
# Start dev server
pnpm dev

# Run tests
pnpm test

# Run e2e tests
pnpm test:e2e

# Lint and format
pnpm lint
pnpm format

# Build for production
pnpm build
```

## Project Structure

```
risk-dashboard/
├── src/
│   ├── components/        # Reusable UI components
│   │   ├── charts/        # Chart components (LineChart, Heatmap, Gauge)
│   │   ├── layout/        # Layout components (Header, Sidebar)
│   │   └── ui/            # shadcn/ui primitives
│   ├── features/          # Feature-specific modules
│   │   ├── portfolio/     # Portfolio overview feature
│   │   ├── margin/        # Margin monitoring feature
│   │   ├── analytics/     # Analytics & reports feature
│   │   └── alerts/        # Alerts & notifications feature
│   ├── hooks/             # Custom React hooks
│   │   ├── usePortfolioData.ts
│   │   ├── useRealTimeUpdates.ts
│   │   └── useAlerts.ts
│   ├── lib/               # Utility functions
│   │   ├── api.ts         # API client
│   │   ├── formatters.ts  # Data formatters
│   │   └── websocket.ts   # WebSocket client
│   ├── stores/            # Zustand stores
│   │   ├── uiStore.ts
│   │   └── alertStore.ts
│   ├── types/             # TypeScript types
│   │   └── risk.ts
│   ├── App.tsx            # Root component
│   ├── main.tsx           # Entry point
│   └── router.tsx         # Route configuration
├── tests/
│   ├── unit/              # Unit tests
│   ├── integration/       # Integration tests
│   └── e2e/               # Playwright e2e tests
├── public/                # Static assets
├── index.html
├── package.json
├── tsconfig.json
├── vite.config.ts
├── tailwind.config.js
└── README.md
```

## Key Components

### PortfolioOverview

```tsx
import { PortfolioOverview } from '@/features/portfolio/PortfolioOverview';

<PortfolioOverview accountRef="acct-123" />
```

### MarginHealthGauge

```tsx
import { MarginHealthGauge } from '@/components/charts/MarginHealthGauge';

<MarginHealthGauge score={75.5} threshold={30} />
```

### AlertNotifications

```tsx
import { AlertNotifications } from '@/features/alerts/AlertNotifications';

<AlertNotifications onAcknowledge={handleAcknowledge} />
```

## API Integration

### Fetching Portfolio Data

```typescript
import { usePortfolioData } from '@/hooks/usePortfolioData';

const { data, isLoading, error } = usePortfolioData('acct-123');
```

### Real-time Updates

```typescript
import { useRealTimeUpdates } from '@/hooks/useRealTimeUpdates';

useRealTimeUpdates('acct-123', (update) => {
  console.log('Margin health updated:', update.marginHealthScore);
});
```

## Deployment

### Production Build

```bash
pnpm build
# Output: dist/

# Serve with Cloud Run or Cloud Storage + CDN
```

### Cloud Run Deployment

```bash
# Build container
docker build -t gcr.io/fusion-prime/risk-dashboard:latest .

# Push to GCR
docker push gcr.io/fusion-prime/risk-dashboard:latest

# Deploy to Cloud Run
gcloud run deploy risk-dashboard \
  --image gcr.io/fusion-prime/risk-dashboard:latest \
  --platform managed \
  --region us-central1 \
  --allow-unauthenticated
```

### Cloud Storage + CDN (Recommended)

```bash
# Upload to Cloud Storage
gsutil -m rsync -r dist/ gs://fusion-prime-risk-dashboard/

# Configure Cloud CDN
# (See infra/terraform/modules/frontend_cdn)
```

## Testing

### Unit Tests

```bash
pnpm test
# Uses Vitest + React Testing Library
```

### E2E Tests

```bash
pnpm test:e2e
# Uses Playwright for browser automation
```

### Integration Tests

```bash
pnpm test:integration
# Tests API integration with mock server
```

## Performance Optimization

- **Code Splitting**: Lazy load routes and heavy components
- **Memoization**: Use React.memo and useMemo for expensive computations
- **Virtual Scrolling**: For large data tables (react-window)
- **Debouncing**: For search and filter inputs
- **Service Worker**: Cache static assets and API responses

## Security

- **Authentication**: Integrated with Identity-Aware Proxy in production
- **Authorization**: Row-level security enforced by backend API
- **XSS Protection**: React auto-escapes, CSP headers configured
- **CSRF Protection**: SameSite cookies + CSRF tokens
- **Audit Logging**: All user actions logged to Cloud Logging

## Monitoring

### Key Metrics
- **Page Load Time**: Target <2s for initial render
- **Time to Interactive**: Target <3s
- **API Latency**: Target <500ms p95
- **Error Rate**: Target <0.1%

### Observability
- **RUM**: Google Analytics 4 + Web Vitals
- **Error Tracking**: Sentry
- **Performance**: Lighthouse CI in build pipeline

## References

- [Risk Analytics Pipeline Architecture](../../docs/architecture/risk-analytics-pipeline.md)
- [Fusion Prime API Documentation](../../docs/api/README.md)
- [shadcn/ui Documentation](https://ui.shadcn.com/)
- [React Query Documentation](https://tanstack.com/query/latest)

