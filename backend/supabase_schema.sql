-- SMART RADAR - Supabase Schema
-- Run this entire file in Supabase Dashboard → SQL Editor

-- Enable UUID extension
CREATE EXTENSION IF NOT EXISTS "pgcrypto";

-- ─── CLUSTERS ────────────────────────────────────────────────────────────────
CREATE TABLE IF NOT EXISTS clusters (
    id          UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    name        TEXT NOT NULL,
    cluster_type TEXT NOT NULL CHECK (cluster_type IN ('own', 'competitor')),
    dashboard_type TEXT NOT NULL DEFAULT 'Own',
    keywords    TEXT[] NOT NULL DEFAULT '{}',
    thresholds  JSONB NOT NULL DEFAULT '{}',
    platform_config JSONB NOT NULL DEFAULT '{}',
    fetch_frequency_minutes INTEGER NOT NULL DEFAULT 30,
    is_active   BOOLEAN NOT NULL DEFAULT true,
    created_at  TIMESTAMPTZ NOT NULL DEFAULT now(),
    updated_at  TIMESTAMPTZ NOT NULL DEFAULT now()
);

-- ─── POSTS TABLE ─────────────────────────────────────────────────────────────
CREATE TABLE IF NOT EXISTS posts_table (
    id                      UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    platform_post_id        TEXT NOT NULL,
    platform                TEXT NOT NULL,
    cluster_id              TEXT NOT NULL,
    author_username         TEXT DEFAULT 'Unknown',
    author_followers        INTEGER DEFAULT 0,
    post_text               TEXT NOT NULL,
    post_url                TEXT NOT NULL,
    posted_at               TIMESTAMPTZ NOT NULL,
    likes                   INTEGER DEFAULT 0,
    comments                INTEGER DEFAULT 0,
    shares                  INTEGER DEFAULT 0,
    views                   INTEGER DEFAULT 0,
    sentiment_score         FLOAT DEFAULT 0.0,
    sentiment_label         TEXT DEFAULT 'Neutral',
    is_threat               BOOLEAN DEFAULT false,
    threat_level            TEXT DEFAULT 'None',
    threat_score            FLOAT DEFAULT 0.0,
    key_narratives          TEXT[] DEFAULT '{}',
    language                TEXT DEFAULT 'English',
    has_been_responded_to   BOOLEAN DEFAULT false,
    llm_analysis            JSONB,
    entity_sentiments       JSONB DEFAULT '{}',
    comparative_analysis    JSONB,
    fetched_at              TIMESTAMPTZ NOT NULL DEFAULT now(),
    created_at              TIMESTAMPTZ NOT NULL DEFAULT now(),
    updated_at              TIMESTAMPTZ NOT NULL DEFAULT now(),
    UNIQUE (platform, platform_post_id)
);

CREATE INDEX IF NOT EXISTS idx_posts_cluster_id   ON posts_table (cluster_id);
CREATE INDEX IF NOT EXISTS idx_posts_platform      ON posts_table (platform);
CREATE INDEX IF NOT EXISTS idx_posts_posted_at     ON posts_table (posted_at DESC);
CREATE INDEX IF NOT EXISTS idx_posts_is_threat     ON posts_table (is_threat);
CREATE INDEX IF NOT EXISTS idx_posts_sentiment     ON posts_table (sentiment_label);

-- ─── RESPONSE LOGS ───────────────────────────────────────────────────────────
CREATE TABLE IF NOT EXISTS response_logs (
    id                      UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    original_post_id        TEXT NOT NULL,
    source_platform         TEXT NOT NULL,
    narrative_used_id       TEXT DEFAULT '',
    generated_response_text TEXT NOT NULL,
    responded_by_user       TEXT DEFAULT 'user',
    responded_at            TIMESTAMPTZ NOT NULL DEFAULT now()
);

-- ─── Row Level Security (open for backend service role) ───────────────────────
ALTER TABLE clusters      DISABLE ROW LEVEL SECURITY;
ALTER TABLE posts_table   DISABLE ROW LEVEL SECURITY;
ALTER TABLE response_logs DISABLE ROW LEVEL SECURITY;
