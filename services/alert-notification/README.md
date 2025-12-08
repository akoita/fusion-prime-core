# Alert Notification Service

**Purpose**: Consumes margin alerts from Pub/Sub and delivers notifications via email, SMS, and webhooks.

## Features

- 📧 **Email Delivery** via SendGrid
- 📱 **SMS Delivery** via Twilio
- 🔗 **Webhook Delivery** for custom integrations
- 📊 **Pub/Sub Integration** - automatically processes margin alerts
- ⚙️ **User Preferences** - configurable notification channels and thresholds
- 🛡️ **Deduplication** - prevents duplicate notifications (5-minute window)

## Architecture

```
Margin Health Calculator (Risk Engine)
    ↓ (detects event)
Pub/Sub: alerts.margin.v1
    ↓ (consumes)
Alert Notification Service
    ↓ (routes)
├─ Email (SendGrid)
├─ SMS (Twilio)
└─ Webhook (Custom)
```

## API Endpoints

### Health
- `GET /health/` - Basic health check
- `GET /health/detailed` - Detailed health with component status
- `GET /health/live` - Liveness probe
- `GET /health/ready` - Readiness probe

### Notifications
- `POST /api/v1/notifications/send` - Send notification manually
- `GET /api/v1/notifications/history/{user_id}` - Get notification history
- `POST /api/v1/notifications/preferences` - Update user preferences
- `GET /api/v1/notifications/preferences/{user_id}` - Get user preferences

## Environment Variables

```bash
# Database
DATABASE_URL=postgresql://user:password@host:5432/db

# SendGrid (Email)
SENDGRID_API_KEY=SG.xxxxx

# Twilio (SMS)
TWILIO_ACCOUNT_SID=ACxxxxx
TWILIO_AUTH_TOKEN=xxxxx

# GCP
GCP_PROJECT=fusion-prime
```

## Deployment

```bash
# Deploy to Cloud Run
gcloud run deploy alert-notification \
  --source=. \
  --region=us-central1 \
  --platform=managed \
  --allow-unauthenticated \
  --set-env-vars="GCP_PROJECT=fusion-prime,SENDGRID_API_KEY=xxx,TWILIO_ACCOUNT_SID=xxx,TWILIO_AUTH_TOKEN=xxx"
```

## Notification Channels

### Email (SendGrid)
- High deliverability
- HTML content support
- Used for all severity levels

### SMS (Twilio)
- Real-time delivery
- Used for HIGH and CRITICAL alerts only
- 160-character limit

### Webhook (Custom)
- Direct API integration
- User-configured endpoints
- Full payload delivery

## Alert Routing

Alerts are routed based on severity:

- **CRITICAL** (liquidation imminent): Email + SMS + Webhook
- **HIGH** (margin call): Email + Webhook
- **MEDIUM** (warning): Email
- **LOW** (info): Email (optional)

## Deduplication

Notifications are deduplicated within a 5-minute window to prevent:
- Alert spam
- User fatigue
- Unnecessary costs

## Status

✅ **Core Components**: Complete
✅ **Pub/Sub Integration**: Implemented
✅ **Email Channel**: Ready (requires SendGrid API key)
✅ **SMS Channel**: Ready (requires Twilio credentials)
✅ **Webhook Channel**: Ready
✅ **Preferences API**: Ready
🟡 **Database Integration**: Pending
🟡 **Production Deployment**: Pending

---

**Created**: 2025-10-27
**Status**: Core implementation complete, ready for deployment
