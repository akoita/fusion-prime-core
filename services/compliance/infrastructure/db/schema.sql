-- Compliance Service Database Schema
-- Stores compliance data including KYC, AML, sanctions screening

-- KYC Cases
CREATE TABLE IF NOT EXISTS kyc_cases (
    case_id VARCHAR(128) PRIMARY KEY,
    user_id VARCHAR(128) NOT NULL,
    document_type VARCHAR(64) NOT NULL,
    document_data JSONB,
    personal_info JSONB,
    status VARCHAR(32) NOT NULL DEFAULT 'pending',
    verification_score DECIMAL(5,2),
    required_actions JSONB,
    reviewer_id VARCHAR(128),
    reviewed_at TIMESTAMP WITH TIME ZONE,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

-- AML Alerts
CREATE TABLE IF NOT EXISTS aml_alerts (
    alert_id VARCHAR(128) PRIMARY KEY,
    user_id VARCHAR(128) NOT NULL,
    transaction_id VARCHAR(128),
    transaction_amount DECIMAL(18,8),
    transaction_type VARCHAR(64),
    source_address VARCHAR(128),
    destination_address VARCHAR(128),
    risk_score DECIMAL(5,4),
    risk_level VARCHAR(32),
    flags JSONB,
    recommendations JSONB,
    status VARCHAR(32) NOT NULL DEFAULT 'open',
    assigned_to VARCHAR(128),
    investigated_at TIMESTAMP WITH TIME ZONE,
    resolved_at TIMESTAMP WITH TIME ZONE,
    resolution_notes TEXT,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

-- Sanctions Checks
CREATE TABLE IF NOT EXISTS sanctions_checks (
    check_id VARCHAR(128) PRIMARY KEY,
    user_id VARCHAR(128),
    address VARCHAR(128) NOT NULL,
    network VARCHAR(32),
    matches JSONB,
    risk_level VARCHAR(32),
    checked_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

-- Compliance Cases (General)
CREATE TABLE IF NOT EXISTS compliance_cases (
    case_id VARCHAR(128) PRIMARY KEY,
    user_id VARCHAR(128) NOT NULL,
    case_type VARCHAR(64) NOT NULL,
    status VARCHAR(32) NOT NULL DEFAULT 'open',
    priority VARCHAR(32) DEFAULT 'normal',
    title VARCHAR(256),
    description TEXT,
    metadata JSONB,
    assigned_to VARCHAR(128),
    created_by VARCHAR(128),
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    resolved_at TIMESTAMP WITH TIME ZONE,
    resolution TEXT
);

-- Compliance Checks (linked to escrow/transaction)
CREATE TABLE IF NOT EXISTS compliance_checks (
    check_id VARCHAR(128) PRIMARY KEY,
    check_type VARCHAR(64) NOT NULL,
    escrow_address VARCHAR(128),
    user_id VARCHAR(128),
    transaction_hash VARCHAR(128),
    status VARCHAR(32) NOT NULL,
    score DECIMAL(5,4),
    risk_score DECIMAL(5,4),
    flags JSONB,
    notes TEXT,
    metadata JSONB,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    checked_at TIMESTAMP WITH TIME ZONE
);

-- Indexes for performance
CREATE INDEX IF NOT EXISTS idx_kyc_cases_user ON kyc_cases(user_id);
CREATE INDEX IF NOT EXISTS idx_kyc_cases_status ON kyc_cases(status);

CREATE INDEX IF NOT EXISTS idx_aml_alerts_user ON aml_alerts(user_id);
CREATE INDEX IF NOT EXISTS idx_aml_alerts_status ON aml_alerts(status);
CREATE INDEX IF NOT EXISTS idx_aml_alerts_risk_level ON aml_alerts(risk_level);

CREATE INDEX IF NOT EXISTS idx_sanctions_checks_address ON sanctions_checks(address);
CREATE INDEX IF NOT EXISTS idx_sanctions_checks_user ON sanctions_checks(user_id);

CREATE INDEX IF NOT EXISTS idx_compliance_cases_user ON compliance_cases(user_id);
CREATE INDEX IF NOT EXISTS idx_compliance_cases_status ON compliance_cases(status);
CREATE INDEX IF NOT EXISTS idx_compliance_cases_type ON compliance_cases(case_type);

CREATE INDEX IF NOT EXISTS idx_compliance_checks_escrow ON compliance_checks(escrow_address);
CREATE INDEX IF NOT EXISTS idx_compliance_checks_user ON compliance_checks(user_id);
CREATE INDEX IF NOT EXISTS idx_compliance_checks_type ON compliance_checks(check_type);
