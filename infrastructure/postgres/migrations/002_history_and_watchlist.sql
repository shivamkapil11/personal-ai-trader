CREATE TABLE IF NOT EXISTS search_history (
    id BIGSERIAL PRIMARY KEY,
    uid TEXT NOT NULL REFERENCES users(uid) ON DELETE CASCADE,
    query TEXT NOT NULL,
    thoughts TEXT DEFAULT '',
    mode TEXT NOT NULL DEFAULT 'single',
    symbols JSONB NOT NULL DEFAULT '[]'::jsonb,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_search_history_uid_created_at
    ON search_history (uid, created_at DESC);

CREATE TABLE IF NOT EXISTS watchlist_items (
    id BIGSERIAL PRIMARY KEY,
    uid TEXT NOT NULL REFERENCES users(uid) ON DELETE CASCADE,
    symbol TEXT NOT NULL,
    note TEXT DEFAULT '',
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    UNIQUE (uid, symbol)
);
