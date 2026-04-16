CREATE TABLE IF NOT EXISTS users (
    uid TEXT PRIMARY KEY,
    name TEXT NOT NULL,
    email TEXT NOT NULL UNIQUE,
    image TEXT DEFAULT '',
    provider TEXT NOT NULL DEFAULT 'google',
    kite_connected BOOLEAN NOT NULL DEFAULT FALSE,
    is_kite_user BOOLEAN,
    onboarding_step TEXT NOT NULL DEFAULT 'auth',
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    last_login_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE TABLE IF NOT EXISTS user_preferences (
    uid TEXT PRIMARY KEY REFERENCES users(uid) ON DELETE CASCADE,
    theme TEXT NOT NULL DEFAULT 'gains-dark',
    compare_mode BOOLEAN NOT NULL DEFAULT TRUE,
    preferred_time_horizon TEXT DEFAULT 'balanced',
    preferred_market_data_order TEXT DEFAULT 'kite_mcp,jugaad_data,yfinance',
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);
