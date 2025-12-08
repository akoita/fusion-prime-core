-- Migration: Create webhook_subscriptions table
-- Purpose: Store webhook subscription configurations for event streaming

CREATE TABLE IF NOT EXISTS webhook_subscriptions (
    subscription_id VARCHAR(128) PRIMARY KEY,
    url VARCHAR(512) NOT NULL,
    secret VARCHAR(256) NOT NULL,
    event_types TEXT NOT NULL,  -- JSON array of event type strings
    enabled BOOLEAN NOT NULL DEFAULT TRUE,
    description VARCHAR(512),
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX idx_webhook_subscriptions_enabled ON webhook_subscriptions(enabled);

