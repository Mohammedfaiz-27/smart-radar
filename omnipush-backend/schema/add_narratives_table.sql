-- Narratives table for Narrative Bank feature
CREATE TABLE IF NOT EXISTS narratives (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    tenant_id UUID NOT NULL,
    title TEXT NOT NULL,
    description TEXT NOT NULL,
    category TEXT NOT NULL DEFAULT 'policy',
    priority TEXT NOT NULL DEFAULT 'medium',
    tags TEXT[] DEFAULT '{}',
    usage_count INTEGER DEFAULT 0,
    last_used TIMESTAMPTZ,
    created_by TEXT,
    is_active BOOLEAN DEFAULT TRUE,
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_narratives_tenant ON narratives(tenant_id);
CREATE INDEX IF NOT EXISTS idx_narratives_category ON narratives(tenant_id, category);
CREATE INDEX IF NOT EXISTS idx_narratives_active ON narratives(tenant_id, is_active);
