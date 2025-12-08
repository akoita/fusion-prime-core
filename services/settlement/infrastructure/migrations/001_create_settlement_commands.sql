CREATE TABLE IF NOT EXISTS settlement_commands (
    command_id VARCHAR(128) PRIMARY KEY,
    workflow_id VARCHAR(128) NOT NULL,
    account_ref VARCHAR(128) NOT NULL,
    payer VARCHAR(128),
    payee VARCHAR(128),
    asset_symbol VARCHAR(64),
    amount_numeric NUMERIC(38, 18),
    status VARCHAR(32) NOT NULL,
    last_updated TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);
