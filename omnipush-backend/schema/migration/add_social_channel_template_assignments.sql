-- Social Channel Template Assignments Schema
-- This schema manages template assignments for different social channels
-- allowing each social channel to have specific news card templates for content with and without images

-- Create table for social channel template assignments
CREATE TABLE IF NOT EXISTS social_channel_template_assignments (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    tenant_id UUID NOT NULL REFERENCES tenants(id) ON DELETE CASCADE,
    social_account_id UUID NOT NULL REFERENCES social_accounts(id) ON DELETE CASCADE,
    platform VARCHAR(50) NOT NULL, -- facebook, instagram, twitter, linkedin, whatsapp, etc.

    -- Template assignments
    template_with_image VARCHAR(255), -- Template to use when content has images
    template_without_image VARCHAR(255), -- Template to use when content has no images

    -- Metadata
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW(),
    created_by UUID REFERENCES users(id),

    -- Constraints
    UNIQUE(tenant_id, social_account_id), -- One assignment per social account per tenant
    CHECK (template_with_image IS NOT NULL OR template_without_image IS NOT NULL), -- At least one template must be assigned
    CHECK (platform IN ('facebook', 'instagram', 'twitter', 'linkedin', 'youtube', 'tiktok', 'pinterest', 'whatsapp'))
);

-- Create RLS policy for multi-tenant isolation
ALTER TABLE social_channel_template_assignments ENABLE ROW LEVEL SECURITY;

-- Policy: Users can only access template assignments for their own tenant
CREATE POLICY social_channel_template_assignments_tenant_isolation ON social_channel_template_assignments
    FOR ALL
    USING (tenant_id = auth.jwt() ->> 'tenant_id'::text);

-- Policy: Users can only access template assignments for social accounts they own
CREATE POLICY social_channel_template_assignments_social_account_access ON social_channel_template_assignments
    FOR ALL
    USING (
        social_account_id IN (
            SELECT id FROM social_accounts
            WHERE tenant_id = auth.jwt() ->> 'tenant_id'::text
        )
    );

-- Create indexes for performance
CREATE INDEX IF NOT EXISTS idx_social_channel_template_assignments_tenant_id
    ON social_channel_template_assignments(tenant_id);
CREATE INDEX IF NOT EXISTS idx_social_channel_template_assignments_social_account_id
    ON social_channel_template_assignments(social_account_id);
CREATE INDEX IF NOT EXISTS idx_social_channel_template_assignments_platform
    ON social_channel_template_assignments(platform);

-- Create function to automatically update updated_at timestamp
CREATE OR REPLACE FUNCTION update_social_channel_template_assignments_updated_at()
RETURNS TRIGGER AS $$
BEGIN
    NEW.updated_at = NOW();
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

-- Create trigger for automatic updated_at timestamp
CREATE TRIGGER trigger_update_social_channel_template_assignments_updated_at
    BEFORE UPDATE ON social_channel_template_assignments
    FOR EACH ROW
    EXECUTE FUNCTION update_social_channel_template_assignments_updated_at();

-- Create table for available newscard templates (metadata table)
CREATE TABLE IF NOT EXISTS newscard_templates (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    template_name VARCHAR(255) UNIQUE NOT NULL,
    template_display_name VARCHAR(255) NOT NULL,
    template_path VARCHAR(500) NOT NULL,
    supports_images BOOLEAN NOT NULL DEFAULT false,
    description TEXT,

    -- Metadata
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW(),
    is_active BOOLEAN DEFAULT true
);

-- Insert available templates from the file system
INSERT INTO newscard_templates (template_name, template_display_name, template_path, supports_images, description) VALUES
-- Templates without images
('template_1_modern_gradient', 'Modern Gradient', '/templates/newscard/template_1_modern_gradient.html', false, 'Modern gradient background design'),
('template_2_dark_tech', 'Dark Tech', '/templates/newscard/template_2_dark_tech.html', false, 'Dark theme with tech styling'),
('template_3_clean_minimal', 'Clean Minimal', '/templates/newscard/template_3_clean_minimal.html', false, 'Clean and minimal design'),
('template_4_newspaper', 'Newspaper', '/templates/newscard/template_4_newspaper.html', false, 'Traditional newspaper style'),
('template_5_magazine', 'Magazine', '/templates/newscard/template_5_magazine.html', false, 'Magazine-style layout'),
('template_6_corporate', 'Corporate', '/templates/newscard/template_6_corporate.html', false, 'Professional corporate design'),

-- Templates with images
('template_1_modern_card_with_image', 'Modern Card with Image', '/templates/newscard/with_images/template_1_modern_card.html', true, 'Modern card design with image support'),
('template_2_side_by_side_with_image', 'Side by Side with Image', '/templates/newscard/with_images/template_2_side_by_side.html', true, 'Side-by-side layout with image'),
('template_3_magazine_overlay_with_image', 'Magazine Overlay with Image', '/templates/newscard/with_images/template_3_magazine_overlay.html', true, 'Magazine style with image overlay'),
('template_4_minimal_circular_with_image', 'Minimal Circular with Image', '/templates/newscard/with_images/template_4_minimal_circular.html', true, 'Minimal design with circular image'),
('template_5_news_bulletin_with_image', 'News Bulletin with Image', '/templates/newscard/with_images/template_5_news_bulletin.html', true, 'News bulletin style with image'),

-- Newscard Nue templates without images
('left_content_right_image_without_image', 'Left Content Right Image (No Image)', '/templates/newscard_nue/without_images/left_content_right_image.html', false, 'Left content, right image layout for content without images'),
('vertical_image_without_image', 'Vertical Image (No Image)', '/templates/newscard_nue/without_images/vertical_image.html', false, 'Vertical layout optimized for content without images'),
('news-card-hero-left-stack_without_image', 'News Card Hero Left Stack (No Image)', '/templates/newscard_nue/without_images/news-card-hero-left-stack.html', false, 'Hero layout with left-stacked content for content without images'),
('full_bleed_image_without_image', 'Full Bleed Image (No Image)', '/templates/newscard_nue/without_images/full_bleed_image.html', false, 'Full bleed layout with drawer design for content without images'),
('horizontal_image_without_image', 'Horizontal Image (No Image)', '/templates/newscard_nue/without_images/horizontal_image.html', false, 'Horizontal layout optimized for content without images'),
('top_bar_with_logo_without_image', 'Top Bar with Logo (No Image)', '/templates/newscard_nue/without_images/top_bar_with_logo.html', false, 'Top bar layout with logo for content without images'),

-- Newscard Nue templates with images
('left_content_right_image_with_image', 'Left Content Right Image (With Image)', '/templates/newscard_nue/with_images/left_content_right_image.html', true, 'Left content, right image layout supporting images'),
('vertical_image_with_image', 'Vertical Image (With Image)', '/templates/newscard_nue/with_images/vertical_image.html', true, 'Vertical layout optimized for content with images'),
('news-card-hero-left-stack_with_image', 'News Card Hero Left Stack (With Image)', '/templates/newscard_nue/with_images/news-card-hero-left-stack.html', true, 'Hero layout with left-stacked content supporting images'),
('full_bleed_image_with_image', 'Full Bleed Image (With Image)', '/templates/newscard_nue/with_images/full_bleed_image.html', true, 'Full bleed layout with drawer design supporting images'),
('horizontal_image_with_image', 'Horizontal Image (With Image)', '/templates/newscard_nue/with_images/horizontal_image.html', true, 'Horizontal layout optimized for content with images'),
('top_bar_with_logo_with_image', 'Top Bar with Logo (With Image)', '/templates/newscard_nue/with_images/top_bar_with_logo.html', true, 'Top bar layout with logo supporting images')
ON CONFLICT (template_name) DO UPDATE SET
    template_display_name = EXCLUDED.template_display_name,
    template_path = EXCLUDED.template_path,
    supports_images = EXCLUDED.supports_images,
    description = EXCLUDED.description,
    updated_at = NOW();

-- Create indexes for newscard_templates
CREATE INDEX IF NOT EXISTS idx_newscard_templates_supports_images
    ON newscard_templates(supports_images);
CREATE INDEX IF NOT EXISTS idx_newscard_templates_is_active
    ON newscard_templates(is_active);

-- Create function to automatically update updated_at timestamp for newscard_templates
CREATE OR REPLACE FUNCTION update_newscard_templates_updated_at()
RETURNS TRIGGER AS $$
BEGIN
    NEW.updated_at = NOW();
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

-- Create trigger for automatic updated_at timestamp
CREATE TRIGGER trigger_update_newscard_templates_updated_at
    BEFORE UPDATE ON newscard_templates
    FOR EACH ROW
    EXECUTE FUNCTION update_newscard_templates_updated_at();

-- Add comments for documentation
COMMENT ON TABLE social_channel_template_assignments IS 'Stores template assignments for each social channel, allowing different templates for content with and without images';
COMMENT ON TABLE newscard_templates IS 'Master table of available newscard templates with metadata';
COMMENT ON COLUMN social_channel_template_assignments.template_with_image IS 'Template to use when content includes images';
COMMENT ON COLUMN social_channel_template_assignments.template_without_image IS 'Template to use when content has no images';
COMMENT ON COLUMN newscard_templates.supports_images IS 'Whether this template supports displaying images';