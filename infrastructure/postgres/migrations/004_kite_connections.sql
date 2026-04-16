CREATE TABLE IF NOT EXISTS kite_connections (
    uid TEXT PRIMARY KEY REFERENCES users(uid) ON DELETE CASCADE,
    mcp_session_id TEXT NOT NULL,
    login_url TEXT DEFAULT '',
    warning_text TEXT DEFAULT '',
    status TEXT NOT NULL DEFAULT 'pending',
    profile JSONB NOT NULL DEFAULT '{}'::jsonb,
    last_error TEXT DEFAULT '',
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    last_validated_at TIMESTAMPTZ
);
