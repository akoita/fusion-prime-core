# Fusion Prime Developer Portal

React-based developer portal for Fusion Prime API documentation, testing, and API key management.

## Features

- **API Reference**: Interactive API documentation
- **Playground**: Test API endpoints with live requests
- **API Key Management**: Create, view, and revoke API keys
- **Rate Limit Display**: Show usage and limits per tier

## Development

```bash
# Install dependencies
npm install

# Run development server
npm run dev

# Build for production
npm run build
```

## Configuration

Set environment variables:
- `VITE_API_BASE_URL`: API Gateway base URL
- `VITE_API_KEY_SERVICE_URL`: API Key Service URL

## Deployment

Deploy to Cloud Run or Cloud Storage for static hosting.
