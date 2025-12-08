-- Risk Engine Database Schema
-- This database stores risk metrics, calculations, and analytics

-- Risk calculations table
CREATE TABLE IF NOT EXISTS risk_calculations (
    calculation_id VARCHAR(128) PRIMARY KEY,
    portfolio_id VARCHAR(128) NOT NULL,
    user_id VARCHAR(128),

    -- Risk metrics
    risk_score DECIMAL(5,4),
    var_1d DECIMAL(18,2),
    var_7d DECIMAL(18,2),
    var_30d DECIMAL(18,2),
    cvar_1d DECIMAL(18,2),
    cvar_7d DECIMAL(18,2),
    cvar_30d DECIMAL(18,2),

    -- Portfolio metrics
    total_value_usd DECIMAL(18,2),
    total_positions INTEGER,
    volatility DECIMAL(8,4),

    -- Timestamps
    calculated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

-- Risk alerts table
CREATE TABLE IF NOT EXISTS risk_alerts (
    alert_id VARCHAR(128) PRIMARY KEY,
    user_id VARCHAR(128) NOT NULL,

    -- Alert configuration
    alert_type VARCHAR(64) NOT NULL,
    threshold DECIMAL(10,4),
    current_value DECIMAL(10,4),
    status VARCHAR(32) NOT NULL DEFAULT 'active',

    -- Metadata
    metadata JSONB,

    -- Timestamps
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

-- Margin requirements table
CREATE TABLE IF NOT EXISTS margin_requirements (
    margin_id VARCHAR(128) PRIMARY KEY,
    user_id VARCHAR(128) NOT NULL,

    -- Margin metrics
    total_collateral DECIMAL(18,2),
    total_margin DECIMAL(18,2),
    initial_margin DECIMAL(18,2),
    maintenance_margin DECIMAL(18,2),
    available_margin DECIMAL(18,2),
    margin_ratio DECIMAL(10,4),

    -- Timestamps
    calculated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

-- Stress test results table
CREATE TABLE IF NOT EXISTS stress_test_results (
    test_id VARCHAR(128) PRIMARY KEY,
    portfolio_id VARCHAR(128) NOT NULL,
    scenario VARCHAR(128) NOT NULL,

    -- Results
    portfolio_value_before DECIMAL(18,2),
    portfolio_value_after DECIMAL(18,2),
    loss_amount DECIMAL(18,2),
    loss_percentage DECIMAL(8,4),

    -- Timestamps
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

-- Indexes for performance
CREATE INDEX IF NOT EXISTS idx_risk_calculations_portfolio ON risk_calculations(portfolio_id);
CREATE INDEX IF NOT EXISTS idx_risk_calculations_user ON risk_calculations(user_id);
CREATE INDEX IF NOT EXISTS idx_risk_calculations_created ON risk_calculations(created_at);

CREATE INDEX IF NOT EXISTS idx_risk_alerts_user ON risk_alerts(user_id);
CREATE INDEX IF NOT EXISTS idx_risk_alerts_status ON risk_alerts(status);

CREATE INDEX IF NOT EXISTS idx_margin_requirements_user ON margin_requirements(user_id);

CREATE INDEX IF NOT EXISTS idx_stress_test_portfolio ON stress_test_results(portfolio_id);
