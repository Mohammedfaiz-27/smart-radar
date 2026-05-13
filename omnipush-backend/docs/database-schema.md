# Database Schema

This document outlines the database schema required for the OmniChannel Content Orchestrator.

## Core Tables

### tenants
Multi-tenant workspace information.

```sql
CREATE TABLE tenants (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  name VARCHAR(100) NOT NULL,
  subscription_tier VARCHAR(20) NOT NULL DEFAULT 'basic', -- 'basic', 'pro', 'enterprise'
  subscription_status VARCHAR(20) NOT NULL DEFAULT 'active', -- 'active', 'inactive', 'canceled', 'past_due'
  billing_email VARCHAR(255),
  created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
  updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);
```

### users
User accounts with tenant association.

```sql
CREATE TABLE users (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  tenant_id UUID NOT NULL REFERENCES tenants(id) ON DELETE CASCADE,
  email VARCHAR(255) NOT NULL,
  password_hash VARCHAR(255) NOT NULL,
  first_name VARCHAR(50) NOT NULL,
  last_name VARCHAR(50) NOT NULL,
  role VARCHAR(20) NOT NULL DEFAULT 'creator', -- 'admin', 'editor', 'creator', 'analyst'
  status VARCHAR(20) NOT NULL DEFAULT 'active', -- 'active', 'inactive', 'pending'
  last_login TIMESTAMP WITH TIME ZONE,
  created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
  updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
  UNIQUE(email, tenant_id)
);
```

### posts
Content posts with multi-platform support.

```sql
CREATE TABLE posts (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  tenant_id UUID NOT NULL REFERENCES tenants(id) ON DELETE CASCADE,
  title VARCHAR(200) NOT NULL,
  content JSONB NOT NULL, -- {text: string, media_ids: UUID[]}
  channels JSONB NOT NULL, -- [{platform: string, account_id: UUID, customizations: {}}]
  status VARCHAR(20) NOT NULL DEFAULT 'draft', -- 'draft', 'pending_approval', 'approved', 'scheduled', 'published', 'failed', 'rejected'
  created_by UUID NOT NULL REFERENCES users(id),
  scheduled_at TIMESTAMP WITH TIME ZONE,
  published_at TIMESTAMP WITH TIME ZONE,
  created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
  updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);
```

### media
Media library with tenant isolation.

```sql
CREATE TABLE media (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  tenant_id UUID NOT NULL REFERENCES tenants(id) ON DELETE CASCADE,
  filename VARCHAR(255) NOT NULL,
  type VARCHAR(20) NOT NULL, -- 'image', 'video', 'document'
  size INTEGER NOT NULL, -- bytes
  url TEXT NOT NULL,
  thumbnail_url TEXT,
  metadata JSONB, -- {width: int, height: int, duration: float, format: string}
  tags TEXT[] DEFAULT '{}',
  description TEXT,
  generation_prompt TEXT, -- for AI-generated content
  uploaded_by UUID NOT NULL REFERENCES users(id),
  created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
  updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);
```

### social_accounts
Connected social media accounts.

```sql
CREATE TABLE social_accounts (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  tenant_id UUID NOT NULL REFERENCES tenants(id) ON DELETE CASCADE,
  platform VARCHAR(20) NOT NULL, -- 'facebook', 'instagram', 'twitter', etc.
  account_name VARCHAR(100) NOT NULL,
  account_id VARCHAR(100) NOT NULL, -- platform-specific ID
  status VARCHAR(20) NOT NULL DEFAULT 'connected', -- 'connected', 'disconnected', 'error', 'expired'
  permissions TEXT[] DEFAULT '{}',
  access_token_encrypted TEXT, -- encrypted access token
  refresh_token_encrypted TEXT, -- encrypted refresh token
  token_expires_at TIMESTAMP WITH TIME ZONE,
  connected_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
  last_sync TIMESTAMP WITH TIME ZONE,
  created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
  updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
  UNIQUE(tenant_id, platform, account_id)
);
```

## Supporting Tables

### subscriptions
Detailed subscription information.

```sql
CREATE TABLE subscriptions (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  tenant_id UUID NOT NULL REFERENCES tenants(id) ON DELETE CASCADE,
  tier VARCHAR(20) NOT NULL DEFAULT 'basic',
  status VARCHAR(20) NOT NULL DEFAULT 'active',
  current_period_start TIMESTAMP WITH TIME ZONE NOT NULL,
  current_period_end TIMESTAMP WITH TIME ZONE NOT NULL,
  stripe_customer_id VARCHAR(100),
  stripe_subscription_id VARCHAR(100),
  created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
  updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
  UNIQUE(tenant_id)
);
```

### invitations
User invitations to tenants.

```sql
CREATE TABLE invitations (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  tenant_id UUID NOT NULL REFERENCES tenants(id) ON DELETE CASCADE,
  email VARCHAR(255) NOT NULL,
  role VARCHAR(20) NOT NULL DEFAULT 'creator',
  first_name VARCHAR(50) NOT NULL,
  last_name VARCHAR(50) NOT NULL,
  status VARCHAR(20) NOT NULL DEFAULT 'pending', -- 'pending', 'accepted', 'expired'
  expires_at TIMESTAMP WITH TIME ZONE NOT NULL,
  invited_by UUID NOT NULL REFERENCES users(id),
  created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
  updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);
```

### workflows
Approval workflows.

```sql
CREATE TABLE workflows (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  tenant_id UUID NOT NULL REFERENCES tenants(id) ON DELETE CASCADE,
  name VARCHAR(100) NOT NULL,
  description TEXT,
  steps JSONB NOT NULL, -- [{order: int, type: string, approvers: UUID[], required: bool}]
  is_default BOOLEAN DEFAULT FALSE,
  created_by UUID NOT NULL REFERENCES users(id),
  created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
  updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);
```

### webhooks
Webhook configurations.

```sql
CREATE TABLE webhooks (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  tenant_id UUID NOT NULL REFERENCES tenants(id) ON DELETE CASCADE,
  url TEXT NOT NULL,
  events TEXT[] NOT NULL, -- ['post.published', 'post.failed', etc.]
  secret VARCHAR(255) NOT NULL,
  is_active BOOLEAN DEFAULT TRUE,
  created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
  updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);
```

## Row Level Security (RLS)

Enable RLS on all tenant-scoped tables:

```sql
-- Enable RLS
ALTER TABLE users ENABLE ROW LEVEL SECURITY;
ALTER TABLE posts ENABLE ROW LEVEL SECURITY;
ALTER TABLE media ENABLE ROW LEVEL SECURITY;
ALTER TABLE social_accounts ENABLE ROW LEVEL SECURITY;
ALTER TABLE subscriptions ENABLE ROW LEVEL SECURITY;
ALTER TABLE invitations ENABLE ROW LEVEL SECURITY;
ALTER TABLE workflows ENABLE ROW LEVEL SECURITY;
ALTER TABLE webhooks ENABLE ROW LEVEL SECURITY;

-- Create policies (example for users table)
CREATE POLICY "Users can only access their tenant data" ON users
  USING (tenant_id = current_setting('app.tenant_id')::uuid);

-- Similar policies should be created for all tenant-scoped tables
```

## Indexes

```sql
-- Performance indexes
CREATE INDEX idx_users_tenant_id ON users(tenant_id);
CREATE INDEX idx_users_email ON users(email);
CREATE INDEX idx_posts_tenant_id ON posts(tenant_id);
CREATE INDEX idx_posts_status ON posts(status);
CREATE INDEX idx_posts_created_by ON posts(created_by);
CREATE INDEX idx_posts_scheduled_at ON posts(scheduled_at);
CREATE INDEX idx_media_tenant_id ON media(tenant_id);
CREATE INDEX idx_media_type ON media(type);
CREATE INDEX idx_social_accounts_tenant_id ON social_accounts(tenant_id);
CREATE INDEX idx_social_accounts_platform ON social_accounts(platform);
```